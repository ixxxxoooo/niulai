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


def is_trading_day(d: datetime.date) -> bool:
    """是否交易日（周末 + 节假日表）"""
    if d.weekday() >= 5:
        return False
    return d.isoformat() not in config.TRADING_HOLIDAYS


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
