"""开盘啦（kaipanla）路由：涨停原因题材聚合 / 板块强度 / 板块分时 / 代码映射
@author ygw
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .common import ttl_cache

router = APIRouter()


@router.get("/kaipanla/limit-up-sectors")
@ttl_cache(ttl=30)
def kaipanla_limit_up_sectors(date: str = Query("", max_length=16)):
    """涨停原因板块：按题材聚合当日涨停股（复盘数据，盘中可能无当日数据）。"""
    from ...datasource.kaipanla import limit_up_sectors
    data = limit_up_sectors(date or None)
    if not data:
        raise HTTPException(status_code=503, detail="开盘啦涨停原因数据暂不可用")
    return data


@router.get("/kaipanla/sector-strengths")
@ttl_cache(ttl=30)
def kaipanla_sector_strengths(date: str = Query("", max_length=16)):
    """板块强度榜：涨停相关板块按强度降序（含涨停数/主力净额/领涨股）。"""
    from ...datasource.kaipanla import sector_strengths
    data = sector_strengths(date or None)
    if not data:
        raise HTTPException(status_code=503, detail="开盘啦板块强度数据暂不可用")
    return data


@router.get("/kaipanla/sector-strength")
@ttl_cache(ttl=30)
def kaipanla_sector_strength(code: str = Query(..., min_length=5, max_length=16),
                             date: str = Query("", max_length=16)):
    """板块强度值（开盘啦特色指标）。"""
    from ...datasource.kaipanla import sector_strength
    v = sector_strength(code, date or None)
    if v is None:
        raise HTTPException(status_code=503, detail="板块强度暂不可用")
    return {"code": code, "date": date or None, "strength": v}


@router.get("/kaipanla/sector-intraday")
@ttl_cache(ttl=30)
def kaipanla_sector_intraday(code: str = Query(..., min_length=5, max_length=16),
                             date: str = Query("", max_length=16)):
    """板块分时（每分钟价格/量/额）。"""
    from ...datasource.kaipanla import sector_intraday
    data = sector_intraday(code, date or None)
    if not data:
        raise HTTPException(status_code=503, detail="板块分时暂不可用")
    return data


@router.get("/kaipanla/sector-codes")
@ttl_cache(ttl=300)
def kaipanla_sector_codes():
    """板块名称 → 开盘啦申万代码 映射（每日刷新）。"""
    from ...datasource.kaipanla import sector_codes
    return {"items": sector_codes()}