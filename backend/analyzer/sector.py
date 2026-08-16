"""板块分析"""
from concurrent.futures import ThreadPoolExecutor
from typing import List

from ..datasource import eastmoney
from ..datasource.models import SectorQuote, StockBrief


def sector_list(stype: str = "industry", sort_by: str = "change_pct",
                limit: int = 100, all_pages: bool = False) -> List[SectorQuote]:
    """板块排行（all_pages=True 时全量分页拉取，供概念名→代码映射）"""
    client = eastmoney.get_client()
    return client.sector_list(stype=stype, sort_by=sort_by, limit=limit, all_pages=all_pages)


def sector_detail(sector_code: str, limit: int = 100,
                  sort_by: str = "change_pct") -> dict:
    """板块详情：板块行情 + 成分股（并发拉取，不再扫全部板块列表）"""
    client = eastmoney.get_client()

    def _stocks():
        return client.sector_stocks(sector_code, limit, sort_by)

    def _meta():
        return client.sector_quote(sector_code)

    with ThreadPoolExecutor(max_workers=2) as ex:
        f_stocks = ex.submit(_stocks)
        f_meta = ex.submit(_meta)
        stocks: List[StockBrief] = f_stocks.result()
        meta = f_meta.result()
    return {"sector": meta, "stocks": stocks}
