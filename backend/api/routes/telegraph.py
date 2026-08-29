"""7x24 实时财经电报与快讯 API 路由。
@author ygw
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from backend.api.routes.common import ttl_cache
from backend.datasource.telegraph import get_telegraph_client

router = APIRouter()


@router.get("/telegraph")
@ttl_cache(ttl=5)
def get_telegraph_list(
    category: str = Query("all", min_length=1, max_length=20, description="分类: all/red/company/watch/hk_us/fund"),
    last_time: Optional[int] = Query(None, ge=0, description="时间戳，用于分页向下加载历史"),
    rn: int = Query(30, ge=1, le=100, description="返回数量"),
) -> Dict[str, Any]:
    """获取 7x24 实时财经电报（财联社主源 + 东财快讯备源）。"""
    client = get_telegraph_client()
    items = client.fetch_telegraph(category=category, last_time=last_time, rn=rn)
    return {
        "items": items,
        "total": len(items),
        "category": category,
        "last_time": items[-1].get("timestamp") if items else None,
    }
