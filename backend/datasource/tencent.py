"""腾讯行情客户端（个股详情 + 五档盘口）

qt.gtimg.cn 返回 GBK 编码的 `v_sh600519="..."` 字符串，字段以 ~ 分隔。
字段索引（已验证）：
  0 市场标志  1 名称  2 代码  3 现价  4 昨收  5 今开  6 成交量(手)
  7 外盘  8 内盘
  9..28 买卖五档：买一价,买一量,买二价,买二量,...,买五价,买五量,
                  卖一价,卖一量,...,卖五价,卖五量
  30 时间(yyyyMMddHHmmss)  31 涨跌  32 涨跌幅%  33 最高  34 最低
  36 成交量(手)  37 成交额(万)  38 换手率%  39 市盈率(动)
  43 振幅%  44 流通市值(亿)  45 总市值(亿)  46 市净率
  47 涨停价  48 跌停价  49 量比  50 委差(手)  51 均价  52 市盈率TTM
"""
import re
import threading
import time
from typing import Dict, List, Optional

import httpx

from .. import config
from ..logging_config import logger
from .models import TrendPoint


def to_tencent_symbol(code: str) -> str:
    """A股代码转腾讯 symbol：sh600519 / sz000001 / bj830799"""
    code = code.strip().upper()
    if code.startswith(("6", "9", "5")):
        return f"sh{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sz{code}"


def _f(fields: List[str], i: int) -> Optional[float]:
    if i >= len(fields):
        return None
    s = fields[i].strip()
    if s in ("", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


class TencentClient:
    def __init__(self):
        self._headers = {
            "User-Agent": config.USER_AGENT,
            "Referer": config.TENCENT_REFERER,
        }
        self._http = httpx.Client(
            timeout=float(config.REQUEST_TIMEOUT),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0),
            headers=self._headers,
        )

    def fetch_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """批量获取个股详情（原始解析 dict），key 为标准 6 位代码"""
        if not codes:
            return {}
        symbols = [to_tencent_symbol(c) for c in codes]
        url = config.TENCENT_QUOTE_URL + ",".join(symbols)
        t0 = time.monotonic()
        try:
            resp = self._http.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            text = resp.content.decode("gbk", errors="replace")
            ms = (time.monotonic() - t0) * 1000
            logger.debug("TX quotes %s ok %.0fms", ",".join(symbols), ms)
            try:
                from ..db import store as db
                db.log_ds("tencent", "qt.gtimg.cn", "/q", True, ms)
            except Exception:
                pass
        except Exception as e:
            ms = (time.monotonic() - t0) * 1000
            logger.debug("TX quotes %s 失败 (%.0fms)", ",".join(symbols), ms)
            try:
                from ..db import store as db
                db.log_ds("tencent", "qt.gtimg.cn", "/q", False, ms, f"{type(e).__name__}: {e}")
            except Exception:
                pass
            return {}
        out: Dict[str, dict] = {}
        for line in text.split(";"):
            line = line.strip()
            if not line or '="' not in line:
                continue
            try:
                symbol = line.split("=")[0].rsplit("_", 1)[-1]
                body = line.split('="', 1)[1].rsplit('"', 1)[0]
            except (IndexError, ValueError):
                continue
            f = body.split("~")
            if len(f) < 40:
                continue
            code = f[2].strip()
            bids, asks = [], []
            for i in range(5):
                p, v = _f(f, 9 + i * 2), _f(f, 10 + i * 2)
                if p is not None and v is not None:
                    bids.append({"price": p, "volume": v})
            for i in range(5):
                p, v = _f(f, 19 + i * 2), _f(f, 20 + i * 2)
                if p is not None and v is not None:
                    asks.append({"price": p, "volume": v})
            ts = f[30].strip()
            if len(ts) >= 14:
                ts = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}:{ts[12:14]}"
            out[code] = {
                "name": f[1].strip(),
                "price": _f(f, 3),
                "prev_close": _f(f, 4),
                "open": _f(f, 5),
                "volume": _f(f, 6),
                "outer": _f(f, 7),
                "inner": _f(f, 8),
                "orderbook": {"bid": bids, "ask": asks},
                "time": ts,
                "change": _f(f, 31),
                "change_pct": _f(f, 32),
                "high": _f(f, 33),
                "low": _f(f, 34),
                "amount_wan": _f(f, 37),
                "turnover": _f(f, 38),
                "pe": _f(f, 39),
                "amplitude": _f(f, 43),
                "float_mv_yi": _f(f, 44),
                "total_mv_yi": _f(f, 45),
                "pb": _f(f, 46),
                "limit_up": _f(f, 47),
                "limit_down": _f(f, 48),
                "volume_ratio": _f(f, 49),
                "weicha": _f(f, 50),
                "avg_price": _f(f, 51),
                "pe_ttm": _f(f, 52),
            }
        return out

    def fetch_us_extended_quotes(self, tickers: List[str]) -> Dict[str, dict]:
        """批量获取美股盘前/盘后与常规行情（毫秒级极速聚合）。"""
        if not tickers:
            return {}
        out = {}
        chunk_size = 70
        for i in range(0, len(tickers), chunk_size):
            chunk = tickers[i:i + chunk_size]
            syms = [f"us{t}" for t in chunk]
            url = f"{config.TENCENT_QUOTE_URL}{','.join(syms)}"
            try:
                resp = self._http.get(url, timeout=config.REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    continue
                for line in resp.text.strip().split(";\n"):
                    if not line:
                        continue
                    parts = line.split("~")
                    if len(parts) < 33:
                        continue
                    code = parts[2].split(".")[0].replace("us", "").upper()
                    reg_price = _f(parts, 3)
                    pre_close = _f(parts, 4)
                    reg_pct = _f(parts, 32)
                    ext_price = _f(parts, 67) if len(parts) > 67 else None
                    ext_pct = round((ext_price - reg_price) / reg_price * 100, 2) if ext_price and reg_price else None
                    ext_chg = round(ext_price - reg_price, 2) if ext_price and reg_price else None
                    out[code] = {
                        "reg_price": reg_price,
                        "reg_pct": reg_pct,
                        "ext_price": ext_price,
                        "ext_pct": ext_pct,
                        "ext_chg": ext_chg,
                        "pre_close": pre_close,
                    }
            except Exception:
                continue
        return out

    def minute_quotes(self, code: str, symbol: Optional[str] = None) -> Optional[Dict]:
        """腾讯分时数据（东财 push2his 的降级备选）

        symbol 可直传腾讯代码（如 hkHSI / usNDX 国际指数）；缺省按 A 股规则转换。
        返回 {"points": [TrendPoint...], "pre_close": float, "name": str}
        腾讯分钟数据为累计量/累计额，可换算每分钟量并推导均价线。
        """
        symbol = symbol or to_tencent_symbol(code)
        url = f"https://web.ifzq.gtimg.cn/appstock/app/minute/query?code={symbol}"
        try:
            resp = self._http.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            d = resp.json()
        except Exception:
            return None
        node = ((d or {}).get("data") or {}).get(symbol) or {}
        rows = ((node.get("data") or {}).get("data")) or []
        if not rows:
            return None
        points: List[TrendPoint] = []
        prev_vol = prev_amt = 0.0
        # A 股指数：sh000xxx / sz399xxx，不能用个股「额÷(量×100)」均价公式
        is_index = bool(re.match(r"^(sh000|sz399)", symbol or ""))
        cum_pv = 0.0  # 指数量价累计，用于成交量加权均价（点位）
        cum_v = 0.0
        for row in rows:
            parts = str(row).split()
            if len(parts) < 4:
                continue
            t = parts[0]
            if len(t) == 4:
                t = f"{t[0:2]}:{t[2:4]}"
            try:
                price = float(parts[1])
                cum_vol = float(parts[2])
                cum_amt = float(parts[3])
            except ValueError:
                continue
            vol = max(cum_vol - prev_vol, 0.0)   # 每分钟量（手）
            amt = max(cum_amt - prev_amt, 0.0)   # 每分钟额（元）
            if is_index:
                cum_pv += price * vol
                cum_v += vol
                avg = (cum_pv / cum_v) if cum_v > 0 else price
            else:
                avg = cum_amt / (cum_vol * 100.0) if cum_vol > 0 else price
            prev_vol, prev_amt = cum_vol, cum_amt
            points.append(TrendPoint(
                time=t, price=price, avg=round(avg, 3 if not is_index else 2),
                volume=vol, amount=amt, high=price, low=price,
            ))
        qt = (node.get("qt") or {}).get(symbol) or []
        pre_close = _f(qt, 4)
        name = qt[1].strip() if len(qt) > 1 else ""
        if pre_close is None:
            return None
        return {"points": points, "pre_close": pre_close, "name": name}

    def kline(self, code: str, period: str = "day", limit: int = 120,
              symbol: Optional[str] = None) -> Optional[Dict]:
        """腾讯 K 线（前复权）。period: day/week/month

        symbol 可直传腾讯代码（如 hkHSI / usNDX 国际指数）；缺省按 A 股规则转换。
        返回 {"points": [{date, open, close, high, low, volume}], "name": str}
        腾讯格式：[日期, 开, 收, 高, 低, 量(手)]
        """
        if period not in ("day", "week", "month"):
            period = "day"
        symbol = symbol or to_tencent_symbol(code)
        if symbol.startswith("us"):
            base_url = "https://web.ifzq.gtimg.cn/appstock/app/usfqkline/get"
        elif symbol.startswith("hk"):
            base_url = "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get"
        else:
            base_url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
        url = f"{base_url}?param={symbol},{period},,,{limit},qfq"
        try:
            resp = self._http.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            d = resp.json()
        except Exception:
            return None
        node = ((d or {}).get("data") or {}).get(symbol) or {}
        rows = node.get(f"qfq{period}") or node.get(period) or []
        points = []
        for row in rows:
            if len(row) < 6:
                continue
            try:
                points.append({
                    "date": str(row[0]),
                    "open": float(row[1]),
                    "close": float(row[2]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "volume": float(row[5]),
                })
            except (ValueError, TypeError):
                continue
        if not points:
            return None
        return {"points": points, "name": node.get("qt", {}).get(symbol, [None, ""])[1] or ""}


_client: Optional[TencentClient] = None
_lock = threading.Lock()


def get_client() -> TencentClient:
    global _client
    with _lock:
        if _client is None:
            _client = TencentClient()
        return _client
