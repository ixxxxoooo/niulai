"""东方财富龙虎榜（datacenter 免费接口）
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


def fetch_lhb_stock(code: str) -> Optional[Dict[str, Any]]:
    """个股最近一次上榜明细（买卖席位）。"""
    code = (code or "").strip()
    if not code:
        return None
    summary = None
    day = None
    cols = ("SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,"
            "BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,EXPLANATION")
    for d in _recent_days(12):
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
    buys = _dc_get("RPT_BILLBOARD_DAILYDETAILSBUY", buy_cols, filt, page_size=10)
    sells = _dc_get("RPT_BILLBOARD_DAILYDETAILSSELL", buy_cols, filt, page_size=10)

    def _seat(it: dict) -> dict:
        return {
            "name": it.get("OPERATEDEPT_NAME") or "",
            "buy": it.get("BUY"),
            "sell": it.get("SELL"),
            "net": it.get("NET"),
        }

    return {
        "date": day,
        "reason": summary.get("reason") or "",
        "price": summary.get("price"),
        "change_pct": summary.get("change_pct"),
        "net": summary.get("net"),
        "buy": summary.get("buy"),
        "sell": summary.get("sell"),
        "buy_seats": [_seat(x) for x in buys],
        "sell_seats": [_seat(x) for x in sells],
    }
