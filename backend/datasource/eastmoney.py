"""东方财富公开行情客户端

- 多节点自动故障转移（push2 主节点群 → push2delay 延迟节点）
- 请求重试、超时
- 各接口封装：指数 / 板块 / 成分股 / 榜单 / 个股快照 / 分时 / 成交明细 / 资金流历史 / 涨停池
"""
import datetime
import logging
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from .. import config
from ..logging_config import logger
from ..db.tags import infer_board
from .models import (
    IndexQuote, StockBrief, SectorQuote, StockDetail, OrderBook,
    IntradayTrend, TrendPoint, Tick, MoneyFlowDay, LimitUpStock,
)


class EastMoneyError(RuntimeError):
    """东方财富接口错误"""


class _FailoverClient:
    """多节点故障转移 HTTP 客户端

    - 节点健康：近期失败的节点进入冷却，优先使用健康节点
    - 请求合并：相同 path+params 的并发请求共用一次结果
    - 非交易时段缩短超时，减少「全部节点不可用」时的长时间卡住
    """

    def __init__(self, hosts: List[str], base_path: str = "/api/qt"):
        self._hosts = hosts
        self._base_path = base_path
        self._lock = threading.Lock()
        self._current = 0
        self._fail_until: Dict[str, float] = {}
        self._inflight: Dict[tuple, dict] = {}
        self._inflight_lock = threading.Lock()
        self._headers = {
            "User-Agent": config.USER_AGENT,
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "*/*",
        }

    def _parse_json(self, resp: httpx.Response) -> Any:
        """解析 JSON，兼容 UTF-8 BOM（部分节点返回带 BOM 内容）"""
        try:
            return resp.json()
        except Exception:
            text = resp.content.decode("utf-8-sig", errors="replace")
            import json as _json
            return _json.loads(text)

    def _timeout(self) -> float:
        try:
            from ..analyzer import schedule
            if not schedule.is_trading_time():
                return float(config.REQUEST_TIMEOUT_OFFHOURS)
        except Exception:
            pass
        return float(config.REQUEST_TIMEOUT)

    def _retries(self) -> int:
        try:
            from ..analyzer import schedule
            if not schedule.is_trading_time():
                return 1
        except Exception:
            pass
        return max(1, int(config.REQUEST_RETRIES))

    def _mark_fail(self, host: str) -> None:
        self._fail_until[host] = time.monotonic() + config.NODE_FAIL_COOLDOWN

    def _mark_ok(self, host: str) -> None:
        self._fail_until.pop(host, None)

    def _host_order(self) -> List[int]:
        """优先当前节点，跳过冷却中的；若全部冷却则按冷却到期排序仍尝试。"""
        n = len(self._hosts)
        now = time.monotonic()
        with self._lock:
            start = self._current
        healthy, cooling = [], []
        for i in range(n):
            idx = (start + i) % n
            host = self._hosts[idx]
            until = self._fail_until.get(host, 0)
            if until > now:
                cooling.append((until, idx))
            else:
                healthy.append(idx)
        if healthy:
            return healthy
        cooling.sort()
        return [idx for _, idx in cooling]

    def _log_ds(self, host: str, path: str, ok: bool, ms: float, err: str = "") -> None:
        try:
            from ..db import store as db
            db.log_ds("eastmoney", host, path, ok, ms, err)
        except Exception:
            pass

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        """带请求合并的 GET：相同参数并发只打一次数据源。
        超时保护：等待者最多等 10s，超时后独立发请求，避免整体卡死。
        """
        key = (path, tuple(sorted((params or {}).items())))
        owner = False
        with self._inflight_lock:
            holder = self._inflight.get(key)
            if holder is None:
                holder = {"event": threading.Event(), "result": None, "error": None,
                          "ts": time.monotonic()}
                self._inflight[key] = holder
                owner = True
            elif time.monotonic() - holder.get("ts", 0) > 15:
                self._inflight.pop(key, None)
                holder = {"event": threading.Event(), "result": None, "error": None,
                          "ts": time.monotonic()}
                self._inflight[key] = holder
                owner = True
        if not owner:
            got = holder["event"].wait(timeout=10)
            if not got:
                return self._get_impl(path, params)
            if holder["error"] is not None:
                raise holder["error"]
            return holder["result"]
        try:
            result = self._get_impl(path, params)
            holder["result"] = result
            return result
        except Exception as e:
            holder["error"] = e
            raise
        finally:
            holder["event"].set()
            with self._inflight_lock:
                self._inflight.pop(key, None)

    def _get_impl(self, path: str, params: Optional[Dict] = None) -> Any:
        last_err: Optional[Exception] = None
        timeout = self._timeout()
        retries = self._retries()
        tried = 0
        deadline = time.monotonic() + timeout * 2.5
        for idx in self._host_order():
            if time.monotonic() > deadline:
                break
            host = self._hosts[idx]
            url = f"https://{host}{self._base_path}{path}"
            for attempt in range(retries):
                if time.monotonic() > deadline:
                    break
                t0 = time.monotonic()
                tried += 1
                remaining = max(1.0, deadline - t0)
                req_timeout = min(timeout, remaining)
                try:
                    resp = httpx.get(
                        url, params=params, headers=self._headers, timeout=req_timeout,
                        follow_redirects=False,
                    )
                    if resp.status_code in (301, 302, 303, 307, 308):
                        raise EastMoneyError(f"{host} 重定向（节点已下线）")
                    resp.raise_for_status()
                    data = self._parse_json(resp)
                    if data is None or data.get("rc") not in (None, 0):
                        raise EastMoneyError(f"{host} 返回异常: {str(data)[:120]}")
                    with self._lock:
                        self._current = idx
                    self._mark_ok(host)
                    ms = (time.monotonic() - t0) * 1000
                    logger.debug("EM %s%s ok %.0fms (尝试%d)", host, path, ms, attempt + 1)
                    self._log_ds(host, path, True, ms)
                    return data
                except Exception as e:  # noqa: BLE001 - 节点失败继续尝试下一个
                    last_err = e
                    ms = (time.monotonic() - t0) * 1000
                    logger.info("EM %s%s 失败 %s (%.0fms, 尝试%d)", host, path,
                                type(e).__name__, ms, attempt + 1)
                    self._log_ds(host, path, False, ms, f"{type(e).__name__}: {e}")
                    continue
            self._mark_fail(host)
        logger.warning("EM 全部节点不可用 path=%s tried=%s timeout=%.0fs: %s",
                       path, tried, timeout, last_err)
        raise EastMoneyError(f"全部数据节点不可用: {last_err}")

    def get_raw(self, url: str, params: Optional[Dict] = None) -> Any:
        """直接请求完整 URL（用于非 /api/qt 前缀的接口）"""
        last_err: Optional[Exception] = None
        timeout = self._timeout()
        retries = self._retries()
        deadline = time.monotonic() + timeout * 2.5
        for host in self._hosts:
            if time.monotonic() > deadline:
                break
            for attempt in range(retries):
                if time.monotonic() > deadline:
                    break
                t0 = time.monotonic()
                remaining = max(1.0, deadline - t0)
                req_timeout = min(timeout, remaining)
                try:
                    resp = httpx.get(
                        url, params=params, headers=self._headers, timeout=req_timeout,
                        follow_redirects=False,
                    )
                    if resp.status_code in (301, 302, 303, 307, 308):
                        raise EastMoneyError(f"{host} 重定向（节点已下线）")
                    resp.raise_for_status()
                    ms = (time.monotonic() - t0) * 1000
                    logger.debug("EM raw %s ok %.0fms", host, ms)
                    self._log_ds(host, url, True, ms)
                    return self._parse_json(resp)
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    ms = (time.monotonic() - t0) * 1000
                    logger.info("EM raw %s 失败 %s (%.0fms)", host, type(e).__name__, ms)
                    self._log_ds(host, url, False, ms, f"{type(e).__name__}: {e}")
                    continue
            self._mark_fail(host)
        logger.warning("EM raw 全部失败 url=%s: %s", url, last_err)
        raise EastMoneyError(f"请求失败: {url} -> {last_err}")


def fmt_hhmmss(v: Any) -> str:
    """东财封板时间：92500 / 93000 / 105703 → 09:25 / 09:30 / 10:57。"""
    if v is None or v == "":
        return ""
    s = str(v).strip()
    if ":" in s:
        parts = s.split(":")
        if len(parts) >= 2:
            return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        return s
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return ""
    digits = digits.zfill(6)
    return f"{digits[0:2]}:{digits[2:4]}"


def _num(v: Any) -> Optional[float]:
    """东财字段转 float，"-" 或缺失返回 None"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _clean_pct(v: Any) -> Optional[float]:
    """百分比字段：东财 fltt=2 时直接是数值（如 5.82 表示 5.82%）"""
    return _num(v)


def secid_of(code: str, market: Optional[int] = None) -> str:
    """代码转 secid（1.600519 / 0.000001）"""
    code = code.strip().upper()
    if market is not None:
        return f"{market}.{code}"
    if code.startswith(("6", "9", "5")):
        return f"1.{code}"   # 沪市（主板/科创/基金/B股）
    if code.startswith(("4", "8")):
        return f"0.{code}"   # 北交所（东财用 0. 前缀）
    return f"0.{code}"       # 深市


def market_of(secid: str) -> int:
    return int(secid.split(".")[0])


class EastMoneyClient:
    """东方财富数据客户端"""

    def __init__(self):
        self._q = _FailoverClient(config.EASTMONEY_HOSTS)
        self._his = _FailoverClient(config.EASTMONEY_HIS_HOSTS, base_path="/api/qt")
        self._fflow = _FailoverClient(config.EASTMONEY_FFLOW_HOSTS, base_path="/api/qt")
        self._ex = _FailoverClient(config.EASTMONEY_EX_HOSTS, base_path="")
        self._search = _FailoverClient(config.EASTMONEY_SEARCH_HOSTS, base_path="/api")

    # ---------------------------------------------------------------- 搜索
    def search_stocks(self, keyword: str, limit: int = 10) -> List[dict]:
        """股票模糊搜索（支持中文/拼音首字母/代码），仅返回 A 股"""
        data = self._search.get("/suggest/get", {
            "input": keyword, "type": 14,
            "token": config.SEARCH_TOKEN, "count": limit,
        })
        rows = ((data or {}).get("QuotationCodeTable") or {}).get("Data") or []
        out: List[dict] = []
        _allowed = {"AStock", "Fund"}  # A股 + ETF基金
        for it in rows:
            if it.get("Classify") not in _allowed:
                continue
            code = str(it.get("Code") or "")
            if not code:
                continue
            market = None
            qid = str(it.get("QuoteID") or "")
            if "." in qid:
                try:
                    market = int(qid.split(".")[0])
                except ValueError:
                    market = None
            if market is None:
                try:
                    market = int(it.get("MktNum") or 0)
                except ValueError:
                    market = 0
            out.append({
                "code": code,
                "name": it.get("Name") or "",
                "market": market,
                "type": it.get("SecurityTypeName") or "",
            })
        return out

    def list_instruments(self) -> List[dict]:
        """全 A 股 + 沪深 ETF 基础信息（代码/名称/市场/行业），供 SQLite 同步。"""
        fields = "f12,f13,f14,f100"
        a_items = self._clist_all_pages(config.FS_ALL_A, fields, max_pages=80)
        etf_items = self._clist_all_pages("b:MK0021", fields, max_pages=20)
        out: List[dict] = []
        seen = set()
        for it, classify in [(x, "AStock") for x in a_items] + [(x, "Fund") for x in etf_items]:
            code = str(it.get("f12") or "")
            if not code or code in seen:
                continue
            seen.add(code)
            out.append({
                "code": code,
                "name": it.get("f14") or "",
                "market": _num(it.get("f13")),
                "classify": classify,
                "industry": it.get("f100") or "",
            })
        return out

    def ulist_briefs(self, codes: List[str], markets: Optional[Dict[str, int]] = None) -> List[StockBrief]:
        """批量快照（ulist，字段与 clist 一致，含涨速 f22 / 主力净流入 f62）。"""
        if not codes:
            return []
        markets = markets or {}
        secids = []
        for code in codes:
            m = markets.get(code)
            secids.append(secid_of(code, int(m) if m is not None else None))
        fields = "f2,f3,f4,f5,f6,f7,f8,f10,f12,f13,f14,f15,f16,f17,f18,f22,f62,f100,f184"
        data = self._q.get("/ulist.np/get", {
            "fltt": 2, "invt": 2, "secids": ",".join(secids), "fields": fields,
        })
        diff = (data or {}).get("data", {}).get("diff") or []
        if isinstance(diff, dict):
            diff = [diff]
        return [self._brief(it) for it in diff if it.get("f12")]

    def stock_f10_boards(self, code: str, market: Optional[int] = None) -> Dict[str, Any]:
        """F10 所属板块：行业取第一条，其余作概念。"""
        code = (code or "").strip()
        if not code:
            return {"industry": "", "concepts": []}
        prefix = "SH" if (market == 1 or (market is None and code.startswith(("6", "9", "5")))) else "SZ"
        if code.startswith(("4", "8")):
            prefix = "BJ"
        url = "https://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax"
        try:
            resp = httpx.get(
                url, params={"code": f"{prefix}{code}"},
                headers={"User-Agent": config.USER_AGENT, "Referer": "https://emweb.securities.eastmoney.com/"},
                timeout=config.REQUEST_TIMEOUT, follow_redirects=True,
            )
            resp.raise_for_status()
            body = resp.json() or {}
        except Exception:
            return {"industry": "", "concepts": []}
        boards = body.get("ssbk") or []
        names = []
        for it in boards:
            n = (it.get("BOARD_NAME") or "").strip()
            if n and n not in names:
                names.append(n)
        return {"industry": names[0] if names else "", "concepts": names[1:] if len(names) > 1 else []}

    # ---------------------------------------------------------------- 指数
    def index_quotes(self, secids: Optional[List[str]] = None) -> List[IndexQuote]:
        """指数行情（可自定义 secids；默认 A 股主要指数）"""
        if secids is None:
            secids = [s for s, _ in config.INDEX_SECIDS]
        names = dict(config.INDEX_SECIDS)
        # f13=0（深市）在 Python 里是 falsy，不能用 `if f13` 拼 secid
        by_code = {s.split(".", 1)[1]: s for s in secids if "." in s}
        fields = "f2,f3,f4,f5,f6,f7,f12,f13,f14,f15,f16,f104,f105,f106"
        data = self._q.get("/ulist.np/get", {
            "fltt": 2, "invt": 2, "secids": ",".join(secids), "fields": fields,
        })
        diff = (data or {}).get("data", {}).get("diff") or []
        out: List[IndexQuote] = []
        for it in diff:
            code = str(it.get("f12", ""))
            f13 = it.get("f13")
            secid = by_code.get(code)
            if not secid and f13 is not None and str(f13) != "":
                try:
                    secid = f"{int(float(f13))}.{code}"
                except (TypeError, ValueError):
                    secid = f"{f13}.{code}"
            out.append(IndexQuote(
                code=code,
                name=it.get("f14") or names.get(secid or "", "") or code,
                price=_num(it.get("f2")),
                change=_num(it.get("f4")),
                change_pct=_num(it.get("f3")),
                amount=_num(it.get("f6")),
                volume=_num(it.get("f5")),
                high=_num(it.get("f15")),
                low=_num(it.get("f16")),
                amplitude=_num(it.get("f7")),
                up_count=_num(it.get("f104")),
                down_count=_num(it.get("f105")),
                flat_count=_num(it.get("f106")),
                secid=secid,
            ))
        return out

    # ---------------------------------------------------------------- 全球指数
    GLOBAL_INDICES = [
        ("100.N225", "日经225", "日韩"),
        ("100.KS11", "韩国KOSPI", "日韩"),
        ("100.HSI", "恒生指数", "亚太"),
        ("100.NDX", "纳斯达克", "美股"),
        ("100.NDX100", "纳斯达克100", "美股"),
        ("100.SPX", "标普500", "美股"),
        ("100.DJIA", "道琼斯", "美股"),
    ]

    def global_indices(self) -> List[IndexQuote]:
        """全球主要指数（日韩/亚太/美股）"""
        quotes = self.index_quotes([s for s, _, _ in self.GLOBAL_INDICES])
        # 修正 secid（东财 f13 对海外指数可能返回 100）
        for q in quotes:
            for secid, name, region in self.GLOBAL_INDICES:
                if q.code == secid.split(".")[1] or q.name == name:
                    q.secid = secid
                    q.region = region
                    if not q.name:
                        q.name = name
        return quotes

    def global_stock_quotes(self, secids: List[str]) -> List[dict]:
        """美股/日韩个股批量快照（secid 前缀：105/106/107=美股，176=日股，177=韩股）。

        返回 [{secid, code, name, market, price, change, change_pct, amount,
               high, low, open, prev_close, industry}]，仅保留有数据的标的。
        """
        if not secids:
            return []
        fields = "f2,f3,f4,f5,f6,f12,f13,f14,f15,f16,f17,f18,f100"
        data = self._q.get("/ulist.np/get", {
            "fltt": 2, "invt": 2, "secids": ",".join(secids), "fields": fields,
        })
        diff = (data or {}).get("data", {}).get("diff") or []
        if isinstance(diff, dict):
            diff = [diff]
        out: List[dict] = []
        for it in diff:
            code = str(it.get("f12", ""))
            if not code:
                continue
            out.append({
                "secid": f"{it.get('f13')}.{code}",
                "code": code,
                "name": it.get("f14") or "",
                "market": _num(it.get("f13")),
                "price": _num(it.get("f2")),
                "change": _num(it.get("f4")),
                "change_pct": _num(it.get("f3")),
                "volume": _num(it.get("f5")),
                "amount": _num(it.get("f6")),
                "high": _num(it.get("f15")),
                "low": _num(it.get("f16")),
                "open": _num(it.get("f17")),
                "prev_close": _num(it.get("f18")),
                "industry": it.get("f100") or "",
            })
        return out

    def us_sector_boards(self, region: Optional[str] = None) -> List[dict]:
        """全球题材板块涨跌幅（代表股简单平均，成分股一并返回）。

        东财无海外题材板块接口，采用 config.GLOBAL_THEME_SECTORS 配置的代表股
        拉实时快照，板块涨跌幅 = 有数据成分股涨跌幅的算术平均。
        region 可选过滤：us/jp/kr；不传返回全部。
        性能：所有板块代表股一次性合并为单个 ulist 请求，再按板块分组。
        """
        cfg = getattr(config, "GLOBAL_THEME_SECTORS", [])
        if region:
            cfg = [b for b in cfg if b.get("region") == region]
        if not cfg:
            return []
        # 合并全部代表股 secid → 一次批量拉取
        all_secids: List[str] = []
        seen: set = set()
        for board in cfg:
            for sid in board.get("secids") or []:
                if sid and sid not in seen:
                    seen.add(sid)
                    all_secids.append(sid)
        all_quotes = self.global_stock_quotes(all_secids)
        by_secid = {q["secid"]: q for q in all_quotes}

        out: List[dict] = []
        for board in cfg:
            secids = board.get("secids") or []
            quotes = [by_secid[s] for s in secids if s in by_secid]
            pcts = [q["change_pct"] for q in quotes if q.get("change_pct") is not None]
            out.append({
                "key": board.get("key", ""),
                "name": board.get("name", ""),
                "region": board.get("region", ""),
                "change_pct": round(sum(pcts) / len(pcts), 2) if pcts else None,
                "up_count": sum(1 for p in pcts if p > 0),
                "down_count": sum(1 for p in pcts if p < 0),
                "stocks": quotes,
            })
        return out

    # ---------------------------------------------------------------- 榜单
    def clist(self, fs: str, fid: str, limit: int = 100, po: int = 1,
              fields: str = "") -> List[dict]:
        """通用榜单接口"""
        if not fields:
            fields = ("f2,f3,f4,f5,f6,f8,f10,f12,f13,f14,f15,f16,f17,f18,"
                      "f22,f62,f100,f184")
        data = self._q.get("/clist/get", {
            "pn": 1, "pz": limit, "po": po, "np": 1, "fltt": 2, "invt": 2,
            "fid": fid, "fs": fs, "fields": fields,
        })
        diff = (data or {}).get("data", {}).get("diff") or []
        if isinstance(diff, dict):
            diff = [diff]
        return diff

    def _clist_all_pages(self, fs: str, fields: str, concurrency: int = 8,
                         max_pages: int = 80) -> List[dict]:
        """并发分页拉取 clist 全量数据（东财单页上限 100 条）

        先取第 1 页获得 total，再并发拉剩余页。返回全部条目（按涨幅降序）。
        """
        from concurrent.futures import ThreadPoolExecutor

        def _page(pn: int) -> List[dict]:
            data = self._q.get("/clist/get", {
                "pn": pn, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f3", "fs": fs, "fields": fields,
            })
            diff = (data or {}).get("data", {}).get("diff") or []
            if isinstance(diff, dict):
                diff = [diff]
            return diff

        first = _page(1)
        total = 0
        # 第一页里没有 total 信息，单独请求一次获取（避免改接口结构）
        try:
            meta = self._q.get("/clist/get", {
                "pn": 1, "pz": 1, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f3", "fs": fs, "fields": fields,
            })
            total = int(((meta or {}).get("data") or {}).get("total") or 0)
        except (TypeError, ValueError):
            total = 0
        pages = min(max_pages, max(1, (total + 99) // 100))
        if pages <= 1:
            return first
        rest: List[dict] = []
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            for diff in ex.map(_page, range(2, pages + 1)):
                rest.extend(diff)
        return first + rest

    def _brief(self, it: dict) -> StockBrief:
        code = str(it.get("f12", ""))
        name = it.get("f14") or ""
        board, is_st = infer_board(code, name)
        return StockBrief(
            code=code,
            name=name,
            market=_num(it.get("f13")),
            price=_num(it.get("f2")),
            change=_num(it.get("f4")),
            change_pct=_num(it.get("f3")),
            volume=_num(it.get("f5")),
            amount=_num(it.get("f6")),
            turnover=_num(it.get("f8")),
            volume_ratio=_num(it.get("f10")),
            amplitude=_num(it.get("f7")),
            zhangsu=_num(it.get("f22")),
            industry=it.get("f100") or None,
            board=board,
            is_st=is_st,
            main_inflow=_num(it.get("f62")),
            main_inflow_pct=_num(it.get("f184")),
            high=_num(it.get("f15")),
            low=_num(it.get("f16")),
            open=_num(it.get("f17")),
            prev_close=_num(it.get("f18")),
        )

    def hot_stocks(self, by: str = "change_pct", limit: int = 50) -> List[StockBrief]:
        """热门股榜单：by ∈ change_pct/amount/turnover/volume_ratio/zhangsu"""
        fid_map = {
            "change_pct": "f3", "amount": "f6", "turnover": "f8",
            "volume_ratio": "f10", "zhangsu": "f22",
        }
        fid = fid_map.get(by, "f3")
        items = self.clist(config.FS_ALL_A, fid, limit)
        return [self._brief(it) for it in items]

    def zhangsu_rank(self, limit: int = 50) -> List[StockBrief]:
        """涨速榜"""
        items = self.clist(config.FS_ALL_A, "f22", limit)
        return [self._brief(it) for it in items]

    def moneyflow_rank(self, limit: int = 50) -> List[StockBrief]:
        """主力净流入榜"""
        items = self.clist(config.FS_ALL_A, "f62", limit)
        return [self._brief(it) for it in items]

    # ---------------------------------------------------------------- ETF
    def etf_rank(self, by: str = "change_pct", limit: int = 50) -> List[StockBrief]:
        """ETF 涨跌排行（fs=b:MK0021 = 沪深 ETF 板块）"""
        fid_map = {"change_pct": "f3", "amount": "f6", "turnover": "f8",
                   "amplitude": "f7", "volume": "f5"}
        fid = fid_map.get(by, "f3")
        items = self.clist("b:MK0021", fid, limit)
        return [self._brief(it) for it in items]

    def etf_holdings(self, code: str, top: int = 10) -> Dict[str, Any]:
        """ETF 前 N 大持仓股（fundf10 股票投资明细，HTML 解析）。

        返回: {"name": str, "date": str, "items": [{rank, code, name, ratio, price, change_pct, shares, market_value}]}
        失败/非 ETF 时返回空 items。
        """
        url = "https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
        params = {"type": "jjcc", "code": code, "topline": str(max(1, min(top, 20)))}
        headers = {
            "User-Agent": config.USER_AGENT,
            "Referer": f"https://fundf10.eastmoney.com/{code}.html",
        }
        resp = httpx.get(url, params=params, headers=headers,
                         timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        html = resp.content.decode("utf-8", errors="ignore")
        items = self._parse_fund_holdings(html, top)
        return {"code": code, "items": items}

    @staticmethod
    def _parse_fund_holdings(html: str, top: int) -> List[Dict[str, Any]]:
        """解析 fundf10 持仓 HTML。列：序号 | 代码 | 名称 | 最新价(span) | 涨跌幅(span) | 相关资讯 | 占净值比 | 持股数(万股) | 持仓市值(万元)。"""
        import re
        out = []
        if not html:
            return out
        try:
            # 按 <tr> 切分 tbody 行
            body = html.split("<tbody>", 1)
            if len(body) < 2:
                return out
            rows_html = body[1].split("</tbody>", 1)[0].split("<tr")
            for row in rows_html[1:]:
                tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
                if len(tds) < 7:
                    continue
                cells = [re.sub(r"<[^>]+>", "", t).strip() for t in tds]
                rank = cells[0]
                code = re.search(r"\d{6}", tds[1] or "").group(0) if re.search(r"\d{6}", tds[1] or "") else cells[1]
                name = cells[2]
                price = cells[3]
                change_pct = cells[4]
                ratio = cells[6] if len(cells) > 6 else ""
                shares = cells[7] if len(cells) > 7 else ""
                market_value = cells[8] if len(cells) > 8 else ""
                if not code or not name:
                    continue
                def _num(s):
                    s = (s or "").replace(",", "").replace("%", "").strip()
                    try:
                        return float(s)
                    except (TypeError, ValueError):
                        return None
                out.append({
                    "rank": int(rank) if rank.isdigit() else None,
                    "code": code,
                    "name": name,
                    "price": _num(price),
                    "change_pct": _num(change_pct),
                    "ratio": _num(ratio),
                    "shares": _num(shares),
                    "market_value": _num(market_value),
                })
                if len(out) >= top:
                    break
        except Exception:
            pass
        return out

    # ---------------------------------------------------------------- 板块
    def sector_list(self, stype: str = "industry", limit: int = 100,
                    sort_by: str = "change_pct", all_pages: bool = False) -> List[SectorQuote]:
        fs = {
            "industry": config.FS_SECTOR_INDUSTRY,
            "concept": config.FS_SECTOR_CONCEPT,
            "area": config.FS_SECTOR_AREA,
        }.get(stype, config.FS_SECTOR_INDUSTRY)
        fields = ("f2,f3,f6,f12,f14,f62,f104,f105,f106,f128,f136,f140")
        # 按主力净流入排序 或 需要全量（如行业归并）时：并发分页拉取（单页上限 100，负流入板块会被截断）
        if sort_by == "main_inflow" or all_pages:
            items = self._clist_all_pages(fs, fields)
            if sort_by == "main_inflow":
                items.sort(key=lambda it: _num(it.get("f62")) or 0.0, reverse=True)
            items = items[:limit]
        else:
            fid_map = {"change_pct": "f3", "main_inflow": "f62", "amount": "f6"}
            fid = fid_map.get(sort_by, "f3")
            items = self.clist(fs, fid, limit, fields=fields)
        out: List[SectorQuote] = []
        for it in items:
            out.append(SectorQuote(
                code=str(it.get("f12", "")),
                name=it.get("f14") or "",
                price=_num(it.get("f2")),
                change_pct=_num(it.get("f3")),
                amount=_num(it.get("f6")),
                main_inflow=_num(it.get("f62")),
                up_count=_num(it.get("f104")),
                down_count=_num(it.get("f105")),
                flat_count=_num(it.get("f106")),
                leader_code=it.get("f140") or None,
                leader_name=it.get("f128") or None,
                leader_pct=_num(it.get("f136")),
            ))
        return out

    def sector_quote(self, code: str) -> Optional[SectorQuote]:
        """单板块快照（secid=90.BKXXXX），避免为详情页拉取全部板块列表。"""
        data = self._q.get("/ulist.np/get", {
            "fltt": 2, "invt": 2,
            "secids": f"90.{code}",
            "fields": "f2,f3,f6,f12,f14,f62,f104,f105,f106,f128,f136,f140",
        })
        diff = (data or {}).get("data", {}).get("diff") or []
        if isinstance(diff, dict):
            diff = [diff]
        if not diff:
            return None
        it = diff[0]
        return SectorQuote(
            code=str(it.get("f12") or code),
            name=it.get("f14") or "",
            price=_num(it.get("f2")),
            change_pct=_num(it.get("f3")),
            amount=_num(it.get("f6")),
            main_inflow=_num(it.get("f62")),
            up_count=_num(it.get("f104")),
            down_count=_num(it.get("f105")),
            flat_count=_num(it.get("f106")),
            leader_code=it.get("f140") or None,
            leader_name=it.get("f128") or None,
            leader_pct=_num(it.get("f136")),
        )

    def sector_moves(self, direction: str = "up", limit: int = 30) -> List[SectorQuote]:
        """板块异动：按 5 分钟板块涨速排序（up=拉升榜 / down=跳水榜，行业+概念）

        po=-1 东财不支持，统一并发拉全部板块后按涨速排序。
        """
        fs = "m:90+t:2,m:90+t:3"
        fields = ("f2,f3,f6,f12,f14,f22,f62,f104,f105,f128,f136,f140")
        items = self._clist_all_pages(fs, fields)
        items.sort(key=lambda it: _num(it.get("f22")) or 0.0,
                   reverse=(direction == "up"))
        items = items[:limit]
        out: List[SectorQuote] = []
        for it in items:
            out.append(SectorQuote(
                code=str(it.get("f12", "")),
                name=it.get("f14") or "",
                price=_num(it.get("f2")),
                change_pct=_num(it.get("f3")),
                amount=_num(it.get("f6")),
                main_inflow=_num(it.get("f62")),
                zhangsu=_num(it.get("f22")),
                up_count=_num(it.get("f104")),
                down_count=_num(it.get("f105")),
                leader_code=it.get("f140") or None,
                leader_name=it.get("f128") or None,
                leader_pct=_num(it.get("f136")),
            ))
        return out

    def sector_moneyflow_history(self, sector_code: str, days: int = 5) -> tuple:
        """板块近 N 日主力资金流。仅用 delay 节点，push2 主节点经常断连。"""
        secid = f"90.{sector_code}"
        params = {
            "lmt": days, "klt": 101, "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        }
        for path in ("/stock/fflow/daykline/get", "/stock/fflow/kline/get"):
            try:
                data = self._fflow.get(path, params)
            except EastMoneyError:
                continue
            d = (data or {}).get("data")
            rows = (d or {}).get("klines") or []
            if not rows:
                continue
            out = []
            for row in rows:
                parts = str(row).split(",")
                if len(parts) < 6:
                    continue
                out.append({
                    "date": parts[0],
                    "main_inflow": _num(parts[1]) or 0.0,
                    "small": _num(parts[2]) or 0.0,
                    "medium": _num(parts[3]) or 0.0,
                    "large": _num(parts[4]) or 0.0,
                    "extra_large": _num(parts[5]) or 0.0,
                })
            if out:
                return out, True
        return [], False

    def market_moneyflow(self, days: int = 5) -> Dict[str, Any]:
        """大盘资金流向（东财 data.eastmoney.com/zjlx/dpzjlx.html）。

        以沪市代表 secid=1.000001 拉日线/分时净流入；delay 节点可用。
        返回 {available, days, today, minutes}。
        """
        params_day = {
            "lmt": max(days, 10), "klt": 101, "secid": "1.000001",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        }
        params_min = {
            "lmt": 0, "klt": 1, "secid": "1.000001",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        }

        def _parse(rows):
            out = []
            for row in rows:
                parts = str(row).split(",")
                if len(parts) < 6:
                    continue
                out.append({
                    "date": parts[0],
                    "main_inflow": _num(parts[1]) or 0.0,
                    "small": _num(parts[2]) or 0.0,
                    "medium": _num(parts[3]) or 0.0,
                    "large": _num(parts[4]) or 0.0,
                    "extra_large": _num(parts[5]) or 0.0,
                })
            return out

        day_rows: List[dict] = []
        for path in ("/stock/fflow/daykline/get", "/stock/fflow/kline/get"):
            try:
                data = self._fflow.get(path, params_day)
                day_rows = _parse(((data or {}).get("data") or {}).get("klines") or [])
            except EastMoneyError:
                continue
            if day_rows:
                break

        minutes: List[dict] = []
        try:
            data = self._fflow.get("/stock/fflow/kline/get", params_min)
            minutes = _parse(((data or {}).get("data") or {}).get("klines") or [])
        except EastMoneyError:
            pass

        today = day_rows[-1] if day_rows else (minutes[-1] if minutes else None)
        return {
            "available": bool(day_rows or minutes),
            "days": day_rows[-days:] if day_rows else [],
            "today": today,
            "minutes": minutes[-60:] if minutes else [],  # 最近约 1 小时分钟点
            "source": "https://data.eastmoney.com/zjlx/dpzjlx.html",
        }

    def sector_stocks(self, sector_code: str, limit: int = 100,
                      sort_by: str = "change_pct") -> List[StockBrief]:
        """板块成分股"""
        fid_map = {"change_pct": "f3", "amount": "f6", "main_inflow": "f62"}
        fid = fid_map.get(sort_by, "f3")
        items = self.clist(f"b:{sector_code}", fid, limit)
        return [self._brief(it) for it in items]

    def sector_moneyflow(self, stype: str = "industry", limit: int = 100) -> List[SectorQuote]:
        """板块主力净流入排行"""
        return self.sector_list(stype, limit, sort_by="main_inflow")

    # ---------------------------------------------------------------- 个股快照
    def stock_snapshot(self, code: str, market: Optional[int] = None) -> Optional[StockDetail]:
        secid = secid_of(code, market)
        fields = ("f22,f43,f44,f45,f46,f47,f48,f50,f51,f52,f57,f58,f60,f62,"
                  "f107,f116,f117,f162,f167,f168,f169,f170,f171,f292")
        data = self._q.get("/stock/get", {"secid": secid, "fltt": 2, "invt": 2,
                                          "fields": fields})
        d = (data or {}).get("data")
        if not d or not d.get("f57"):
            return None
        return StockDetail(
            code=str(d.get("f57")),
            name=d.get("f58") or "",
            market=_num(d.get("f107")),
            price=_num(d.get("f43")),
            prev_close=_num(d.get("f60")),
            open=_num(d.get("f46")),
            high=_num(d.get("f44")),
            low=_num(d.get("f45")),
            change=_num(d.get("f169")),
            change_pct=_num(d.get("f170")),
            amplitude=_num(d.get("f171")),
            volume=_num(d.get("f47")),
            amount=_num(d.get("f48")),
            turnover=_num(d.get("f168")),
            volume_ratio=_num(d.get("f50")),
            pe=_num(d.get("f162")),
            pb=_num(d.get("f167")),
            total_mv=_num(d.get("f116")),
            float_mv=_num(d.get("f117")),
            limit_up=_num(d.get("f51")),
            limit_down=_num(d.get("f52")),
            zhangsu=_num(d.get("f22")),
            main_inflow=_num(d.get("f62")),
            time=str(d.get("f292") or ""),
        )

    # ---------------------------------------------------------------- 分时 / 明细 / 资金流历史
    # 指数 → 腾讯符号映射（全球 + A股主要指数）
    TENCENT_INDEX_SYMBOL = {
        "100.HSI": "hkHSI",
        "100.NDX": "usNDX",
        "100.SPX": "usSPX",
        "100.DJIA": "usDJI",
        # A 股指数：000001 等代码会被 to_tencent_symbol 误判为深市个股，必须显式映射
        "1.000001": "sh000001",
        "0.399001": "sz399001",
        "0.399006": "sz399006",
        "1.000688": "sh000688",
        "1.000300": "sh000300",
    }

    def _tencent_symbol_of(self, secid: str) -> Optional[str]:
        """A 股指数 secid → 腾讯符号。深市指数 f13=0，必须按 secid 前缀判断。"""
        if not secid:
            return None
        if secid in self.TENCENT_INDEX_SYMBOL:
            return self.TENCENT_INDEX_SYMBOL[secid]
        if "." not in secid:
            return None
        mkt, code = secid.split(".", 1)
        if mkt == "1" and code.startswith("000"):
            return f"sh{code}"
        if mkt == "0" and code.startswith("399"):
            return f"sz{code}"
        return None

    def _resolve_secid(self, code: str, market: Optional[int], secid: Optional[str]) -> str:
        if secid:
            return secid
        return secid_of(code, market)

    def intraday_trends(self, code: str = "", market: Optional[int] = None,
                        secid: Optional[str] = None) -> Optional[IntradayTrend]:
        """分时数据：优先东财 push2his，失败降级腾讯（双源容错）

        可传 secid（如全球指数 100.N225）或 A 股 code。
        """
        secid = self._resolve_secid(code, market, secid)
        tx_symbol = self._tencent_symbol_of(secid)
        if tx_symbol:
            from . import tencent
            tx = tencent.get_client().minute_quotes(code, symbol=tx_symbol)
            if tx and tx.get("points"):
                return IntradayTrend(
                    code=code, name=tx.get("name") or "",
                    pre_close=tx.get("pre_close") or 0.0,
                    points=tx["points"],
                )
        try:
            data = self._his.get("/stock/trends2/get", {
                "secid": secid,
                "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "ndays": 1, "iscr": 0,
            })
        except EastMoneyError:
            data = None
        if data:
            d = data.get("data")
            if d and d.get("trends"):
                points = []
                for row in d["trends"]:
                    parts = str(row).split(",")
                    if len(parts) < 8:
                        continue
                    points.append(TrendPoint(
                        time=parts[0][-5:] if len(parts[0]) >= 5 else parts[0],
                        price=_num(parts[2]) or 0.0,
                        avg=_num(parts[7]) or 0.0,
                        volume=_num(parts[5]) or 0.0,
                        amount=_num(parts[6]) or 0.0,
                        high=_num(parts[3]) or 0.0,
                        low=_num(parts[4]) or 0.0,
                    ))
                return IntradayTrend(
                    code=code, name=d.get("name") or "",
                    pre_close=_num(d.get("preClose")) or 0.0,
                    points=points,
                )
        # 降级：腾讯分时
        from . import tencent
        tx = tencent.get_client().minute_quotes(code, symbol=self.TENCENT_INDEX_SYMBOL.get(secid))
        if tx and tx.get("points"):
            return IntradayTrend(
                code=code, name=tx.get("name") or "",
                pre_close=tx.get("pre_close") or 0.0,
                points=tx["points"],
            )
        return None

    def kline(self, code: str = "", market: Optional[int] = None,
              period: str = "day", limit: int = 120,
              secid: Optional[str] = None) -> Optional[Dict]:
        """K 线（前复权）。period: day/week/month。东财优先，失败降级腾讯。

        可传 secid（如全球指数 100.N225）或 A 股 code。
        返回 {"points": [{date, open, close, high, low, volume}], "name": str}
        """
        klt_map = {"day": 101, "week": 102, "month": 103}
        klt = klt_map.get(period, 101)
        secid = self._resolve_secid(code, market, secid)
        # 指数：腾讯/新浪优先（东财 his 对 000001/399001 等经常断连）
        idx_kl = self._kline_tencent_sina(secid, period, limit)
        if idx_kl:
            return idx_kl
        try:
            data = self._his.get("/stock/kline/get", {
                "secid": secid, "klt": klt, "fqt": 1, "lmt": limit,
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            })
        except EastMoneyError:
            data = None
        if data:
            d = data.get("data")
            rows = (d or {}).get("klines") or []
            if rows:
                points = []
                for row in rows:
                    parts = str(row).split(",")
                    if len(parts) < 6:
                        continue
                    points.append({
                        "date": parts[0],
                        "open": _num(parts[1]) or 0.0,
                        "close": _num(parts[2]) or 0.0,
                        "high": _num(parts[3]) or 0.0,
                        "low": _num(parts[4]) or 0.0,
                        "volume": _num(parts[5]) or 0.0,  # 手
                        # 东财 fields2: f57额 f58振幅 f59涨跌幅 f60涨跌额 f61换手
                        "amount": _num(parts[6]) if len(parts) > 6 else None,
                        "amplitude": _num(parts[7]) if len(parts) > 7 else None,
                        "change_pct": _num(parts[8]) if len(parts) > 8 else None,
                        "change_amount": _num(parts[9]) if len(parts) > 9 else None,
                        "turnover": _num(parts[10]) if len(parts) > 10 else None,
                    })
                return {"points": points, "name": (d or {}).get("name") or ""}
        from . import tencent
        stock_code = code or (secid.split(".", 1)[-1] if secid else "")
        tx = tencent.get_client().kline(stock_code, period, limit,
                                        symbol=self.TENCENT_INDEX_SYMBOL.get(secid))
        if tx and tx.get("points"):
            return tx
        tf_data = self._kline_tickflow(stock_code, period, limit)
        if tf_data:
            return tf_data
        return None

    def _kline_tencent_sina(self, secid: str, period: str, limit: int) -> Optional[Dict]:
        """指数 K 线：腾讯（已验证可用）→ 新浪日/周。"""
        symbol = self._tencent_symbol_of(secid)
        if not symbol:
            return None
        from . import tencent
        tx = tencent.get_client().kline("", period, limit, symbol=symbol)
        if tx and tx.get("points"):
            return tx
        return self._kline_sina(symbol, period, limit)

    def _kline_sina(self, symbol: str, period: str, limit: int) -> Optional[Dict]:
        """新浪 K 线降级（日=240、周=1200；月线接口返回 null）。量单位为股，转成手。"""
        scale = {"day": "240", "week": "1200"}.get(period)
        if not scale or not symbol:
            return None
        try:
            resp = httpx.get(
                "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData",
                params={"symbol": symbol, "scale": scale, "ma": "no", "datalen": str(limit)},
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            rows = resp.json()
        except Exception:
            return None
        if not isinstance(rows, list) or not rows:
            return None
        points = []
        for row in rows:
            try:
                points.append({
                    "date": str(row.get("day") or "")[:10],
                    "open": float(row.get("open") or 0),
                    "close": float(row.get("close") or 0),
                    "high": float(row.get("high") or 0),
                    "low": float(row.get("low") or 0),
                    "volume": float(row.get("volume") or 0) / 100.0,
                })
            except (TypeError, ValueError):
                continue
        if not points:
            return None
        return {"points": points, "name": ""}

    def _kline_tickflow(self, code: str, period: str, limit: int):
        """TickFlow 免费 K 线降级源（仅日/周/月K，IP限60次/分）"""
        period_map = {"day": "1d", "week": "1w", "month": "1M"}
        tf_period = period_map.get(period)
        if not tf_period:
            return None
        try:
            from tickflow import TickFlow
            tf = TickFlow.free()
            symbol = self._to_tickflow_symbol(code)
            df = tf.klines.get(symbol, period=tf_period, count=limit, as_dataframe=True)
            if df is None or df.empty:
                return None
            points = []
            for _, row in df.iterrows():
                points.append({
                    "date": str(row.get("date", row.name))[:10],
                    "open": float(row.get("open", 0)),
                    "close": float(row.get("close", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "volume": float(row.get("volume", 0)),
                })
            return {"points": points, "name": ""}
        except Exception:
            return None

    @staticmethod
    def _to_tickflow_symbol(code: str) -> str:
        """A股代码转 TickFlow 符号格式（如 600519 → 600519.SH）"""
        code = code.split(".")[-1] if "." in code else code
        if code.startswith(("6", "9", "5")):
            return f"{code}.SH"
        elif code.startswith(("0", "3", "2")):
            return f"{code}.SZ"
        elif code.startswith(("4", "8")):
            return f"{code}.BJ"
        return f"{code}.SH"

    def stock_ticks(self, code: str, market: Optional[int] = None,
                    limit: int = 100) -> List[Tick]:
        secid = secid_of(code, market)
        data = self._q.get("/stock/details/get", {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55",
            "pos": -limit, "num": limit,
        })
        d = (data or {}).get("data")
        rows = (d or {}).get("details") or []
        out = []
        for row in rows:
            parts = str(row).split(",")
            if len(parts) < 4:
                continue
            price = _num(parts[1]) or 0.0
            volume = _num(parts[2]) or 0.0
            out.append(Tick(
                time=parts[0],
                price=price,
                volume=volume,
                amount=price * volume * 100.0,  # 手→股×价格 = 成交额（元）
                direction=int(_num(parts[4]) or 0) if len(parts) > 4 else 0,
            ))
        return out

    def moneyflow_history(self, code: str, market: Optional[int] = None,
                          days: int = 5) -> List[MoneyFlowDay]:
        """个股资金流历史。优先 delay 节点；push2 主节点经常断连，有数据就跳过。"""
        secid = secid_of(code, market)
        params = {
            "lmt": max(days, 30), "klt": 101, "secid": secid,
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        }
        best: List[MoneyFlowDay] = []
        for path in ("/stock/fflow/daykline/get", "/stock/fflow/kline/get"):
            try:
                data = self._fflow.get(path, params)
                rows = ((data or {}).get("data") or {}).get("klines") or []
                parsed = self._parse_moneyflow_rows(rows)
            except EastMoneyError:
                continue
            if len(parsed) >= days:
                self._merge_moneyflow_gross(parsed, code, days)
                return parsed[-days:]
            if len(parsed) > len(best):
                best = parsed
        self._merge_moneyflow_gross(best, code, days)
        if len(best) < days:
            try:
                dc = self._moneyflow_datacenter(code, days)
                if len(dc) > len(best):
                    best = dc
            except Exception:
                pass
        return best[-days:] if best else []

    def _moneyflow_datacenter(self, code: str, days: int) -> List[MoneyFlowDay]:
        """datacenter：RPT_DMSK_TS_STOCKNEW（RPT_INDIVIDUAL_FUND_FLOW 已下线）。"""
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "sortColumns": "TRADE_DATE",
            "sortTypes": "-1",
            "pageSize": str(days),
            "pageNumber": "1",
            "reportName": "RPT_DMSK_TS_STOCKNEW",
            "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")',
        }
        resp = httpx.get(url, params=params, headers={
            "User-Agent": config.USER_AGENT,
            "Referer": "https://data.eastmoney.com/",
        }, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        items = ((body or {}).get("result") or {}).get("data") or []
        out = []
        for it in items:
            extra_in = float(it.get("SUPERDEAL_INFLOW") or 0)
            extra_out = float(it.get("SUPERDEAL_OUTFLOW") or 0)
            big_in = float(it.get("BIGDEAL_INFLOW") or 0)
            big_out = float(it.get("BIGDEAL_OUTFLOW") or 0)
            out.append(MoneyFlowDay(
                date=(it.get("TRADE_DATE") or "")[:10],
                main_inflow=float(it.get("PRIME_INFLOW") or it.get("MAIN_NET_INFLOW") or 0),
                small=0.0,
                medium=0.0,
                large=big_in - big_out,
                extra_large=extra_in - extra_out,
                main_in=extra_in + big_in,
                main_out=extra_out + big_out,
            ))
        out.sort(key=lambda x: x.date)
        return out

    def _merge_moneyflow_gross(self, rows: List[MoneyFlowDay], code: str, days: int) -> None:
        """用 datacenter 补充主力流入/流出（超大单+大单总额），失败静默，不影响主数据。"""
        if not rows:
            return
        try:
            dc = self._moneyflow_datacenter(code, days)
        except Exception:
            return
        by_date = {d.date: d for d in dc}
        for row in rows:
            g = by_date.get(row.date)
            if g:
                row.main_in = g.main_in or 0.0
                row.main_out = g.main_out or 0.0

    @staticmethod
    def _parse_moneyflow_rows(rows) -> List[MoneyFlowDay]:
        out = []
        for row in rows:
            parts = str(row).split(",")
            if len(parts) < 6:
                continue
            day = MoneyFlowDay(
                date=parts[0],
                main_inflow=_num(parts[1]) or 0.0,
                small=_num(parts[2]) or 0.0,
                medium=_num(parts[3]) or 0.0,
                large=_num(parts[4]) or 0.0,
                extra_large=_num(parts[5]) or 0.0,
            )
            # CSV: 日期,主力,小单,中单,大单,超大单,主力占比,小单占比,中单占比,大单占比,超大单占比
            if len(parts) >= 11:
                day.main_pct = _num(parts[6]) or 0.0
                day.small_pct = _num(parts[7]) or 0.0
                day.medium_pct = _num(parts[8]) or 0.0
                day.large_pct = _num(parts[9]) or 0.0
                day.extra_large_pct = _num(parts[10]) or 0.0
            out.append(day)
        return out

    def _parse_zt_item(self, p: dict, kind: str = "zt") -> LimitUpStock:
        """涨停/炸板池单条。"""
        code = str(p.get("c") or "")
        name = p.get("n") or ""
        board, is_st = infer_board(code, name)
        zttj = p.get("zttj") or {}
        lbc = int(p.get("lbc") or zttj.get("days") or 0)
        return LimitUpStock(
            code=code,
            name=name,
            price=(p.get("p") or 0) / 100.0,
            change_pct=(p.get("zdp") or 0.0),
            seal_amount=(p.get("fund") or 0),
            lbc=lbc,
            first_time=fmt_hhmmss(p.get("fbt")),
            last_time=fmt_hhmmss(p.get("lbt")),
            zb_count=int(p.get("zbc") or 0),
            industry=p.get("hybk") or "",
            amount=_num(p.get("amount")),
            turnover=_num(p.get("hs")),
            kind=kind,
            board=board,
            is_st=is_st,
        )

    def _topic_pool(self, path: str, limit: int, kind: str) -> List[LimitUpStock]:
        """涨停/炸板池通用拉取。"""
        out: List[LimitUpStock] = []
        url = f"https://push2ex.eastmoney.com/{path}"
        for day in self._recent_trading_dates():
            data = self._ex.get_raw(url, {
                "ut": "7eea3edcaed734bea9cbfc24409ed989",
                "dpt": "wz.ztzt",
                "Pageindex": 0, "pagesize": limit,
                "sort": "fbt:asc", "date": day,
            })
            d = (data or {}).get("data") or {}
            pool = d.get("pool") or []
            if pool or d.get("tc") is not None:
                for p in pool:
                    out.append(self._parse_zt_item(p, kind))
                break
        return out

    def limit_up_pool(self, limit: int = 100) -> List[LimitUpStock]:
        """涨停池。date 为空时东财返回 null，需传最近交易日日期。"""
        return self._topic_pool("getTopicZTPool", limit, "zt")

    def limit_break_pool(self, limit: int = 100) -> List[LimitUpStock]:
        """炸板池（曾涨停后打开）。"""
        return self._topic_pool("getTopicZBPool", limit, "zb")

    def stock_changes(self, limit: int = 80) -> List[dict]:
        """
        盘中个股异动：大笔买入/卖出、急速拉升/跳水、火箭发射等。
        数据来源 push2ex.eastmoney.com。

        参数:
            limit: 返回条数

        返回:
            [{code, name, time, type_name, change_pct, price, info}, ...]
        """
        _TYPE_MAP = {
            "8201": "火箭发射", "8202": "快速反弹", "8193": "大笔买入",
            "4": "封涨停板", "8207": "打开涨停", "8209": "打开跌停",
            "8211": "有大买盘", "8212": "有大卖盘", "8213": "竞价上涨",
            "8214": "竞价下跌", "8215": "高开5%", "8216": "低开5%",
            "8217": "向上缺口", "8218": "向下缺口",
            "8204": "加速下跌", "8203": "高台跳水", "64": "封跌停板",
            "8208": "尾盘拉升", "8210": "尾盘跳水",
        }
        url = "https://push2ex.eastmoney.com/getAllStockChanges"
        params = {
            "type": "8201,8202,8193,4,8207,8209,8211,8212,8208,8210,8204,8203,64",
            "pageindex": 0,
            "pagesize": limit,
            "ut": "7eea3edcaed734bea9004fcb5d7bc605",
            "dpt": "wzchanges",
        }
        try:
            resp = httpx.get(
                url, params=params,
                headers={"User-Agent": config.USER_AGENT, "Referer": "https://quote.eastmoney.com/"},
                timeout=config.REQUEST_TIMEOUT, follow_redirects=True,
            )
            body = resp.json()
        except Exception as e:
            logger.info("个股异动接口失败: %s", e)
            return []

        data = (body or {}).get("data") or {}
        items = data.get("allstock") or []
        result = []
        for it in items:
            tm = it.get("tm") or ""
            if len(tm) == 6:
                tm = f"{tm[:2]}:{tm[2:4]}:{tm[4:]}"
            type_code = str(it.get("type") or "")
            result.append({
                "code": str(it.get("c") or ""),
                "name": it.get("n") or "",
                "time": tm,
                "type_code": type_code,
                "type_name": _TYPE_MAP.get(type_code, f"异动{type_code}"),
                "change_pct": it.get("p"),
                "price": it.get("pc") if it.get("pc") else None,
                "volume": it.get("v"),
                "amount": it.get("a"),
                "info": it.get("i") or "",
            })
        return result

    @staticmethod
    def _recent_trading_dates(days: int = 10) -> List[str]:
        """最近 days 个工作日（YYYYMMDD），从今天往前"""
        out = []
        d = datetime.date.today()
        while len(out) < days:
            if d.weekday() < 5:  # 周末不开盘
                out.append(d.strftime("%Y%m%d"))
            d -= datetime.timedelta(days=1)
        return out


# 全局单例（进程内复用连接池与节点状态）
_client: Optional[EastMoneyClient] = None
_lock = threading.Lock()


def get_client() -> EastMoneyClient:
    global _client
    with _lock:
        if _client is None:
            _client = EastMoneyClient()
        return _client
