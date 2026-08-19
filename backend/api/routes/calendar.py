"""交易与财经日历路由
@author ygw
"""
from typing import Optional
from fastapi import APIRouter, Query

from ...analyzer.calendar_events import get_calendar_events
from .common import ttl_cache

router = APIRouter()


@router.get("/calendar/events")
@ttl_cache(ttl=60)
def calendar_events(months: int = Query(4, ge=1, le=12)):
    """获取未来关键交易与财经日历（交割日、期权行权、LPR、PMI、休市日等）。"""
    return get_calendar_events(months_ahead=months)
