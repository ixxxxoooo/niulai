"""交易时段判断"""
import datetime
from typing import Tuple

from .. import config


def _parse(t: str) -> datetime.time:
    h, m = t.split(":")
    return datetime.time(int(h), int(m))


_SESSIONS: Tuple[Tuple[datetime.time, datetime.time], ...] = tuple(
    (_parse(a), _parse(b)) for a, b in config.TRADING_SESSIONS
)


def _custom_holidays() -> set:
    try:
        from ..db import store as db
        v = db.get_setting("custom_holidays")
        if v:
            return {s.strip() for s in v.replace("\n", ",").split(",") if s.strip()}
    except Exception:
        pass
    return set()


def is_trading_day(d: datetime.date) -> bool:
    """是否交易日（周末 + 静态节假日表 + 动态自定义节假日）"""
    if d.weekday() >= 5:
        return False
    iso = d.isoformat()
    if iso in config.TRADING_HOLIDAYS:
        return False
    if iso in _custom_holidays():
        return False
    return True



def is_trading_time(now: datetime.datetime | None = None) -> bool:
    """当前是否盘中（含集合竞价 9:15 起）"""
    now = now or datetime.datetime.now()
    if not is_trading_day(now.date()):
        return False
    t = now.time()
    return any(a <= t <= b for a, b in _SESSIONS)


def session_label(now: datetime.datetime | None = None) -> str:
    """当前时段标签"""
    now = now or datetime.datetime.now()
    if not is_trading_day(now.date()):
        return "休市"
    t = now.time()
    if t < _SESSIONS[0][0]:
        return "盘前"
    if _SESSIONS[0][0] <= t <= _SESSIONS[0][1]:
        return "上午盘中"
    if _SESSIONS[0][1] < t < _SESSIONS[1][0]:
        return "午间休市"
    if _SESSIONS[1][0] <= t <= _SESSIONS[1][1]:
        return "下午盘中"
    return "已收盘"
