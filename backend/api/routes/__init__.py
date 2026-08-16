"""API 路由聚合：按域拆分为 market/stocks/watchlist/alerts/ai/meta
@author ygw
"""
from fastapi import APIRouter

from . import market, stocks, watchlist, alerts, ai, meta, screener, lhb_moves
from .common import clear_cache, ttl_cache  # noqa: F401 — 供外部/测试复用

router = APIRouter(prefix="/api")
router.include_router(meta.router)
router.include_router(market.router)
router.include_router(stocks.router)
router.include_router(watchlist.router)
router.include_router(alerts.router)
router.include_router(ai.router)
router.include_router(screener.router)
router.include_router(lhb_moves.router)
