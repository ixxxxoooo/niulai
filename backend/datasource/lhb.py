"""东方财富龙虎榜（datacenter 免费接口）+ 席位分类 + 上榜次数
@author ygw
"""
import datetime
from typing import Any, Dict, List, Optional

import httpx

from .. import config
from ..logging_config import logger

DC_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def _dc_get(report: str, columns: str, filt: str, page_size: int = 50,
            sort_columns: str = "", sort_types: str = "") -> List[dict]:
    """调用东财 datacenter 列表接口。"""
    params = {
        "reportName": report,
        "columns": columns,
        "filter": filt,
        "pageNumber": 1,
        "pageSize": str(page_size),
        "source": "WEB",
        "client": "WEB",
    }
    if sort_columns:
        params["sortColumns"] = sort_columns
        params["sortTypes"] = sort_types or "-1"
    try:
        resp = httpx.get(
            DC_URL, params=params,
            headers={"User-Agent": config.USER_AGENT, "Referer": "https://data.eastmoney.com/"},
            timeout=config.REQUEST_TIMEOUT, follow_redirects=True,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        logger.info("龙虎榜接口失败 %s %s", report, e)
        return []
    return ((body or {}).get("result") or {}).get("data") or []


def _recent_days(n: int = 10) -> List[str]:
    """最近 n 个工作日 YYYY-MM-DD。"""
    out = []
    d = datetime.date.today()
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.strftime("%Y-%m-%d"))
        d -= datetime.timedelta(days=1)
    return out


def _row_list(it: dict) -> dict:
    """将东财原始行映射为标准字段。"""
    return {
        "code": str(it.get("SECURITY_CODE") or ""),
        "name": it.get("SECURITY_NAME_ABBR") or "",
        "price": it.get("CLOSE_PRICE"),
        "change_pct": it.get("CHANGE_RATE"),
        "net": it.get("BILLBOARD_NET_AMT"),
        "buy": it.get("BILLBOARD_BUY_AMT"),
        "sell": it.get("BILLBOARD_SELL_AMT"),
        "reason": it.get("EXPLANATION") or "",
        "date": str(it.get("TRADE_DATE") or "")[:10],
    }


def _classify_seat(name: str) -> dict:
    """
    对席位名称进行分类，返回含 type/nickname/label 的字典。
    委托给 lhb_seats.classify_seat，导入失败时回退为 broker。
    """
    try:
        from ..db.lhb_seats import classify_seat
        return classify_seat(name)
    except Exception:
        return {"type": "broker", "nickname": None, "style": None, "premium": None, "label": "营业部"}


def _seat(it: dict) -> dict:
    """席位行映射，含类型分类。"""
    name = it.get("OPERATEDEPT_NAME") or ""
    cls = _classify_seat(name)
    return {
        "name": name,
        "buy": it.get("BUY"),
        "sell": it.get("SELL"),
        "net": it.get("NET"),
        "type": cls["type"],
        "nickname": cls.get("nickname"),
        "label": cls["label"],
        "style": cls.get("style"),
        "premium": cls.get("premium"),
    }


def _dedup_seats(rows: List[dict]) -> List[dict]:
    """同一股票同日因多个上榜原因会重复返回相同营业部，按（营业部名+净额）去重。

    不能用营业部名单独去重：机构专用/深股通专用是多家不同实体的占位名，
    同股同日可能出现多家机构（各自净额不同）；而多榜单重复时同营业部净额一致。
    """
    seen: set = set()
    out: List[dict] = []
    for r in rows:
        n = r.get("OPERATEDEPT_NAME") or ""
        key = (n, r.get("NET"))
        if n and key in seen:
            continue
        if n:
            seen.add(key)
        out.append(r)
    return out


def fetch_lhb_list(limit: int = 50) -> Dict[str, Any]:
    """最近一个有数据的交易日龙虎榜列表。"""
    cols = ("SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,"
            "BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,EXPLANATION")
    for day in _recent_days():
        rows = _dc_get(
            "RPT_DAILYBILLBOARD_DETAILSNEW", cols,
            f"(TRADE_DATE='{day}')", page_size=limit,
            sort_columns="BILLBOARD_NET_AMT", sort_types="-1",
        )
        if rows:
            return {"date": day, "items": [_row_list(it) for it in rows[:limit]]}
    return {"date": None, "items": []}


def fetch_lhb_stock(code: str, lookback_days: int = 12) -> Optional[Dict[str, Any]]:
    """
    个股龙虎榜增强：最新一次席位明细 + 近 N 日上榜次数与历史。
    采用两阶段策略：先快速找最新上榜日（最多查 lookback_days），
    再一次性通过 datacenter 批量查近 90 天上榜记录。

    参数:
        code: 股票代码
        lookback_days: 查找最新上榜日的回溯工作日数（默认 12）

    返回:
        含 appear_count/appear_dates/latest/history 的字典
    """
    code = (code or "").strip()
    if not code:
        return None

    # ── 阶段1：找最新上榜日的席位明细（最多查 lookback_days 天） ──
    summary = None
    day = None
    cols = ("SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,"
            "BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,EXPLANATION")
    for d in _recent_days(lookback_days):
        rows = _dc_get(
            "RPT_DAILYBILLBOARD_DETAILSNEW", cols,
            f"(TRADE_DATE='{d}')(SECURITY_CODE=\"{code}\")", page_size=5,
        )
        if rows:
            summary = _row_list(rows[0])
            day = d
            break
    if not summary:
        return None

    buy_cols = "OPERATEDEPT_NAME,BUY,SELL,NET,EXPLANATION,TRADE_DATE"
    filt = f"(TRADE_DATE='{day}')(SECURITY_CODE=\"{code}\")"
    buys = _dedup_seats(_dc_get("RPT_BILLBOARD_DAILYDETAILSBUY", buy_cols, filt, page_size=10))
    sells = _dedup_seats(_dc_get("RPT_BILLBOARD_DAILYDETAILSSELL", buy_cols, filt, page_size=10))

    # ── 阶段2：一次性批量查近 90 天的全部上榜记录（单次请求） ──
    appear_dates = [day]
    history = [{"date": day, "reason": summary.get("reason", ""), "net": summary.get("net")}]
    try:
        import datetime as _dt
        start = (_dt.date.today() - _dt.timedelta(days=90)).strftime("%Y-%m-%d")
        hist_rows = _dc_get(
            "RPT_DAILYBILLBOARD_DETAILSNEW", cols,
            f"(TRADE_DATE>='{start}')(SECURITY_CODE=\"{code}\")",
            page_size=50,
            sort_columns="TRADE_DATE", sort_types="-1",
        )
        seen = {day}
        for hr in hist_rows:
            hd = str(hr.get("TRADE_DATE") or "")[:10]
            if hd and hd not in seen:
                seen.add(hd)
                appear_dates.append(hd)
                if len(history) < 10:
                    r = _row_list(hr)
                    history.append({"date": hd, "reason": r.get("reason", ""), "net": r.get("net")})
        appear_dates.sort(reverse=True)
    except Exception as e:
        logger.debug("龙虎榜历史查询失败 %s: %s", code, e)

    return {
        "appear_count": len(appear_dates),
        "appear_dates": appear_dates,
        "latest": {
            "date": day,
            "reason": summary.get("reason") or "",
            "price": summary.get("price"),
            "change_pct": summary.get("change_pct"),
            "net": summary.get("net"),
            "buy": summary.get("buy"),
            "sell": summary.get("sell"),
            "buy_seats": [_seat(x) for x in buys],
            "sell_seats": [_seat(x) for x in sells],
        },
        "history": history,
    }
