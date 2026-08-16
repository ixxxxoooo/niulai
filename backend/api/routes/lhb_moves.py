"""龙虎榜游资动向 API（全市场席位明细同步 + 游资买入记录查询）
@author ygw
"""
from datetime import date as _date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class MovesSyncBody(BaseModel):
    """同步日期范围"""
    start: str
    end: str


class MovesAutoBody(BaseModel):
    """每日自动同步开关"""
    enabled: bool = True


def _valid_date(s: str) -> bool:
    try:
        _date.fromisoformat(s)
        return True
    except Exception:
        return False


@router.get("/lhb/moves/dates")
def lhb_moves_dates():
    """已同步交易日列表（供日期选择器置灰无数据日）。"""
    from ...db.lhb_moves import list_dates
    return {"dates": list_dates()}


@router.get("/lhb/moves")
def lhb_moves(date: str = Query(...), side: str = Query("buy", pattern="^(buy|sell)$"),
              nickname: str = ""):
    """当日某方向席位明细（按股票聚合，含参与的游资）。"""
    if not _valid_date(date):
        raise HTTPException(status_code=400, detail="无效日期")
    from ...db.lhb_moves import moves_by_date
    return {"date": date, "side": side, "items": moves_by_date(date, side, nickname)}


@router.get("/lhb/moves/sync/status")
def lhb_moves_sync_status():
    """龙虎榜同步任务进度。"""
    from ...db.lhb_moves import moves_sync_status
    return moves_sync_status()


@router.get("/lhb/moves/auto")
def lhb_moves_auto_get():
    """读取自动同步开关。"""
    from ...db import store as db
    return {"enabled": (db.get_setting("lhbAutoSync") or "1") != "0"}


@router.get("/lhb/moves/{nickname}")
def lhb_moves_nick(nickname: str):
    """某游资买入过的股票汇总（含每只股票哪天买入、买入额明细）。"""
    from ...db.lhb_moves import moves_by_nick
    return {"nickname": nickname, "items": moves_by_nick(nickname)}


@router.post("/lhb/moves/sync")
def lhb_moves_sync(body: MovesSyncBody):
    """后台同步日期范围的全市场席位明细（已同步日期自动跳过）。"""
    if not (_valid_date(body.start) and _valid_date(body.end)):
        raise HTTPException(status_code=400, detail="无效日期范围")
    if body.start > body.end:
        raise HTTPException(status_code=400, detail="start 不能晚于 end")
    from ...db.lhb_moves import start_moves_sync
    return {"ok": True, **start_moves_sync(body.start, body.end)}


@router.post("/lhb/moves/auto")
def lhb_moves_auto(body: MovesAutoBody):
    """每日收盘后自动同步当天龙虎榜开关。"""
    from ...db import store as db
    db.set_setting("lhbAutoSync", "1" if body.enabled else "0")
    return {"ok": True, "enabled": body.enabled}