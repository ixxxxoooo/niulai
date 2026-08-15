"""热门股与资金流榜单"""
from typing import List

from ..datasource import eastmoney
from ..datasource.models import StockBrief, SectorQuote


def hot_stocks(by: str = "change_pct", limit: int = 50) -> List[StockBrief]:
    """热门股榜：by ∈ change_pct|amount|turnover|volume_ratio|zhangsu"""
    client = eastmoney.get_client()
    return client.hot_stocks(by=by, limit=limit)


def zhangsu_rank(limit: int = 50) -> List[StockBrief]:
    """涨速榜"""
    return eastmoney.get_client().zhangsu_rank(limit)


def moneyflow_rank(limit: int = 50) -> List[StockBrief]:
    """个股主力净流入榜"""
    return eastmoney.get_client().moneyflow_rank(limit)


def sector_moneyflow(stype: str = "industry", limit: int = 100) -> List[SectorQuote]:
    """板块主力净流入榜"""
    return eastmoney.get_client().sector_moneyflow(stype=stype, limit=limit)
