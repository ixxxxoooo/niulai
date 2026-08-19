"""限售解禁日历与排雷诊断 API 路由
@author ygw
"""
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...analyzer.risk_radar import diagnose_stock_risk, batch_diagnose_stocks
from ...datasource import eastmoney
from .common import ttl_cache

router = APIRouter()


class BatchRiskRequest(BaseModel):
    codes: List[str]


@router.get("/calendar/unlocks")
@ttl_cache(ttl=120)
def calendar_unlocks(days: int = Query(60, ge=7, le=180), page: int = Query(1, ge=1), page_size: int = Query(80, ge=10, le=200)):
    """获取未来近期限售股解禁列表与大额解禁统计"""
    client = eastmoney.get_client()
    items = client.restricted_unlock_list(days_ahead=days, page=page, page_size=page_size)

    # 统计大额解禁 (比例 >= 5% 或 市值 >= 10亿)
    heavy_count = sum(1 for it in items if float(it.get("ratio_total") or 0) >= 5.0 or float(it.get("market_cap") or 0) >= 1000000000)

    return {
        "days": days,
        "total": len(items),
        "heavy_count": heavy_count,
        "items": items,
    }


@router.get("/stocks/{code}/risk-diagnosis")
@ttl_cache(ttl=60)
def stock_risk_diagnosis(code: str):
    """获取指定个股的智能排雷诊断（解禁压力、业绩预告、ST风险）"""
    return diagnose_stock_risk(code)


@router.post("/stocks/batch-risk")
def batch_stock_risk(req: BatchRiskRequest):
    """批量自选股快速排雷标签"""
    codes = req.codes[:100]  # 最大支持 100 只
    return batch_diagnose_stocks(codes)
