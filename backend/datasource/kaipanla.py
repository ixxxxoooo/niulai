"""开盘啦（kaipanla）数据层：抓包私有接口，容错降级、低频调用。

说明：
- 数据来自开盘啦 App 私有接口（longhuvip.com），仅供个人研究、低频使用；
- 任何异常一律返回 None/空，绝不影响现有功能；
- config.KAIPANLA_ENABLED=False 时全部返回空（一键关闭）。
@author ygw
"""
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from .. import config
from ..logging_config import logger

HIS_URL = "https://apphis.longhuvip.com/w1/api/index.php"    # 历史数据
REAL_URL = "https://apphwhq.longhuvip.com/w1/api/index.php"  # 实时数据

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SHARK PRS-A0 Build/PQ3A.190605.01141736)",
    "Accept-Encoding": "gzip",
}


def _enabled() -> bool:
    """总开关：False 时整体停用。"""
    return bool(getattr(config, "KAIPANLA_ENABLED", True))


def _post(url: str, data: dict, timeout: float = 6.0, delay: float = 0.0) -> Optional[dict]:
    """开盘啦 POST 请求（uuid 设备号 + apiv 版本），失败返回 None。"""
    if not _enabled():
        return None
    if delay:
        time.sleep(delay)
    params = {"apiv": "w42", "PhoneOSNew": "1", "VerSion": "5.21.0.2"}
    body = {
        "apiv": "w42",
        "PhoneOSNew": "1",
        "VerSion": "5.21.0.2",
        "DeviceID": str(uuid.uuid4()),
    }
    body.update(data)
    try:
        resp = httpx.post(
            url, params=params, data=body, headers=HEADERS,
            timeout=timeout, verify=False,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:  # noqa: BLE001 - 抓包接口异常不扩散
        logger.debug("开盘啦请求失败 %s: %s", url, e)
        return None


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _fmt_seal_time(raw) -> str:
    """封板时间：20.41 → 20:24。"""
    if raw in (None, ""):
        return ""
    try:
        hour = int(raw)
        minute = int(round((raw - hour) * 60))
        if minute >= 60:
            hour += minute // 60
            minute = minute % 60
        if 0 <= hour <= 23:
            return f"{hour:02d}:{minute:02d}"
    except Exception:
        pass
    return str(raw)


def limit_up_sectors(date: Optional[str] = None) -> Optional[dict]:
    """涨停原因板块（GetPlateInfo_w38）：按题材聚合当日涨停股。

    参数:
        date: YYYY-MM-DD，默认当日

    返回:
        {"date", "summary", "sectors"}；失败返回 None
    """
    date = date or _today()
    result = _post(REAL_URL, {
        "a": "GetPlateInfo_w38",
        "st": "100",
        "c": "DailyLimitResumption",
        "Index": "0",
        "Day": date,
    })
    if not result or result.get("errcode") != "0":
        return None

    nums = result.get("nums") or {}
    summary = {
        "date": result.get("date", date),
        "up_count": nums.get("SZJS", 0),
        "down_count": nums.get("XDJS", 0),
        "limit_up_count": nums.get("ZT", 0),
        "limit_down_count": nums.get("DT", 0),
        "up_down_ratio": nums.get("ZBL", 0),
        "yesterday_ratio": nums.get("yestRase", 0),
    }

    sectors = []
    for sd in result.get("list") or []:
        code = sd.get("ZSCode") or ""
        name = sd.get("ZSName") or ""
        stocks = []
        for st in sd.get("StockList") or []:
            if len(st) < 19:
                continue
            stocks.append({
                "code": st[0],
                "name": st[1],
                "limit_up_price": round(st[4], 2) if st[4] else 0,
                "float_mv": st[8] if st[8] else 0,
                "lbc": st[9],
                "lbc_times": st[10],
                "concepts": st[11] or "",
                "seal_amount": st[12] if st[12] else 0,
                "main_inflow": st[13] if st[13] else 0,
                "seal_time": _fmt_seal_time(st[14]),
                "total_mv": st[15] if st[15] else 0,
                "reason": st[16] or "",
                "theme": st[17] or "",
                "is_first": 1 if st[18] else 0,
            })
        if code and name:
            sectors.append({
                "code": code,
                "name": name,
                "stock_count": sd.get("num") or len(stocks),
                "stocks": stocks,
            })
    return {"date": result.get("date", date), "summary": summary, "sectors": sectors}


def sector_strength(code: str, date: Optional[str] = None) -> Optional[float]:
    """板块强度（GetPlate_Info_QJ），强度值在 List 第 2 位。失败返回 None。"""
    date = date or _today()
    result = _post(REAL_URL if date == _today() else HIS_URL, {
        "a": "GetPlate_Info_QJ",
        "c": "ZhiShuRanking",
        "Date": date,
        "PlateID": code,
    }, delay=0.3)
    if not result or result.get("errcode") != "0":
        return None
    lst = result.get("List") or []
    if len(lst) < 2:
        return None
    try:
        return float(lst[1])
    except (TypeError, ValueError):
        return None


def sector_intraday(code: str, date: Optional[str] = None) -> Optional[dict]:
    """板块分时（GetTrendIncremental）。失败返回 None。"""
    result = _post(REAL_URL if date is None else HIS_URL, {
        "a": "GetTrendIncremental",
        "c": "ZhiShuL2Data",
        "StockID": code,
        "Day": date or "",
    }, delay=0.3)
    if not result or result.get("errcode") != "0":
        return None
    trend = result.get("trend") or []
    points = []
    for item in trend:
        if len(item) < 5:
            continue
        points.append({
            "time": item[0],
            "price": float(item[1]),
            "volume": int(item[2]),
            "turnover": float(item[3]),
            "trend": int(item[4]),
        })
    if not points:
        return None
    preclose = result.get("preclose") or points[0]["price"]
    return {
        "code": code,
        "date": result.get("date", date or _today()),
        "preclose": float(preclose),
        "points": points,
    }


# ── 板块名称 → 申万代码 映射（每日缓存） ──
_sector_map: Dict[str, str] = {}
_sector_map_day = ""
_sector_map_lock = threading.Lock()


def sector_codes() -> Dict[str, str]:
    """板块名称 → 开盘啦板块代码（每日从涨停原因板块列表构建，失败返回空）。"""
    global _sector_map, _sector_map_day
    now_day = _today()
    with _sector_map_lock:
        if _sector_map and _sector_map_day == now_day:
            return dict(_sector_map)
        data = limit_up_sectors(now_day)
        mapping: Dict[str, str] = {}
        if data:
            for s in data.get("sectors") or []:
                if s.get("name") and s.get("code"):
                    mapping[s["name"]] = s["code"]
        if mapping:
            _sector_map = mapping
            _sector_map_day = now_day
        return dict(_sector_map)


def sector_capital(code: str, date: Optional[str] = None) -> Optional[dict]:
    """板块资金盘口（GetPanKou）：成交额/涨跌幅/主力净额/涨跌家数。失败返回 None。

    pankou 数组（注意 [3] 是主力买入、[4] 主力卖出、[5] 才是净额 = [3]+[4]）：
    0成交额 1涨跌幅 2主力净占比 3主力买入 4主力卖出 5净额 6上涨 7下跌 8平盘 9流通市值 10总市值 11换手率
    """
    result = _post(REAL_URL if date is None else HIS_URL, {
        "a": "GetPanKou",
        "c": "ZhiShuL2Data",
        "StockID": code,
        "Day": date or "",
    }, delay=0.2)
    if not result or result.get("errcode") != "0":
        return None
    p = result.get("pankou") or []
    if len(p) < 11:
        return None
    return {
        "code": result.get("code", code),
        "date": result.get("date", date or _today()),
        "amount": float(p[0]) if p[0] else 0,
        "change_pct": float(p[1]) if p[1] else 0,
        "main_inflow": float(p[5]) if p[5] else 0,
        "up_count": int(p[6]) if p[6] else 0,
        "down_count": int(p[7]) if p[7] else 0,
    }


def _sub_sectors(stocks: list) -> list:
    """从涨停股 concepts 概念标签聚合子板块（如通信→光模块/CPO/覆铜板）。"""
    from collections import Counter
    c: Counter = Counter()
    for st in stocks:
        raw = (st.get("concepts") or "").replace("、", ",").replace("/", ",").replace("，", ",")
        for tag in raw.split(","):
            tag = tag.strip()
            if tag:
                c[tag] += 1
    return [{"name": n, "count": cnt} for n, cnt in c.most_common()][:12]


# 东财概念板块列表（每日缓存），用于给子板块补涨跌幅/主力净额
_em_concept_cache: List[dict] = []
_em_concept_ts = 0.0
_em_concept_lock = threading.Lock()


def _em_concepts() -> list:
    """东财概念板块全量（code/name/change_pct/main_inflow），每日缓存。失败返回 []。"""
    global _em_concept_cache, _em_concept_ts
    now = time.monotonic()
    with _em_concept_lock:
        if _em_concept_cache and now - _em_concept_ts < 86400:
            return _em_concept_cache
        try:
            from ..datasource import eastmoney
            rows = eastmoney.get_client().sector_list("concept", 500, sort_by="main_inflow")
            items = [{
                "name": s.name or "",
                "change_pct": s.change_pct,
                "main_inflow": s.main_inflow,
            } for s in rows if s.name]
            if items:
                _em_concept_cache = items
                _em_concept_ts = now
            return _em_concept_cache
        except Exception:
            return _em_concept_cache


# 子板块名 → 东财概念板块名 别名（概念标签与东财板块命名差异）
_EM_ALIAS = {
    "光模块": "光通信模块",
    "光芯片": "光通信模块",
    "MPO": "CPO概念",
    "CPO": "CPO概念",
    "液冷": "液冷概念",
    "覆铜板": "覆铜板",
    "PCB": "PCB概念",
    "存储": "存储芯片",
}


def _match_em_sector(name: str) -> Optional[dict]:
    """按名称匹配东财概念板块（别名→精确→双向包含），用于子板块涨跌幅/主力净额。"""
    if not name:
        return None
    cands = [name, _EM_ALIAS.get(name, "")]
    for c in cands:
        if not c:
            continue
        for s in _em_concepts():
            if s["name"] == c:
                return s
    for s in _em_concepts():
        if name in s["name"] or s["name"] in name:
            return s
    return None

def _build_sub_sectors(stocks: list) -> list:
    """涨停股 concepts 聚合子板块，并补东财概念板块的涨跌幅/主力净额、封单合计、领涨股。"""
    from collections import defaultdict
    groups: dict = defaultdict(list)
    for st in stocks:
        raw = (st.get("concepts") or "").replace("、", ",").replace("/", ",").replace("，", ",")
        for tag in raw.split(","):
            tag = tag.strip()
            if tag:
                groups[tag].append(st)
    out = []
    for name, sts in groups.items():
        em = _match_em_sector(name)
        out.append({
            "name": name,
            "count": len(sts),
            "change_pct": (em or {}).get("change_pct"),
            "main_inflow": (em or {}).get("main_inflow"),
            "seal_amount": sum((x.get("seal_amount") or 0) for x in sts),
            "top_stocks": [{"code": x["code"], "name": (x["name"] or "").strip()} for x in sts[:6]],
        })
    out.sort(key=lambda x: -x["count"])
    return out[:12]


def sector_strengths(date: Optional[str] = None) -> Optional[dict]:
    """板块强度榜：当日有涨停的板块列表 + 各板块强度，按强度降序。

    开盘啦没有全量板块强度排行单接口，这里用涨停原因板块列表（GetPlateInfo_w38）
    为基础，并发批量取各板块强度（GetPlate_Info_QJ）合成。

    参数:
        date: YYYY-MM-DD，默认当日

    返回:
        {"date", "summary", "items": [{code, name, strength, limit_up_count,
                                      main_inflow, top_stocks}]}；失败返回 None
    """
    from concurrent.futures import ThreadPoolExecutor

    data = limit_up_sectors(date)
    if not data or not data.get("sectors"):
        return None
    sectors = data["sectors"]

    def _one(sec: dict) -> dict:
        strength = sector_strength(sec["code"], date)
        cap = sector_capital(sec["code"], date)
        stocks = sec.get("stocks") or []
        return {
            "code": sec["code"],
            "name": sec["name"],
            "strength": strength,
            "limit_up_count": sec.get("stock_count") or len(stocks),
            "main_inflow": (cap or {}).get("main_inflow"),
            "change_pct": (cap or {}).get("change_pct"),
            "amount": (cap or {}).get("amount"),
            "up_count": (cap or {}).get("up_count"),
            "down_count": (cap or {}).get("down_count"),
            "sub_sectors": _build_sub_sectors(stocks),
            "top_stocks": [{"code": st["code"], "name": (st["name"] or "").strip()} for st in stocks[:6]],
        }

    with ThreadPoolExecutor(max_workers=8) as ex:
        items = list(ex.map(_one, sectors))
    items.sort(key=lambda x: -(x["strength"] if x["strength"] is not None else -1))
    return {"date": data["date"], "summary": data["summary"], "items": items}