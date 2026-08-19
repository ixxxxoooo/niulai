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


def market_heatmap_data(stype: str = "industry", sort_by: str = "amount", limit: int = 80) -> dict:
    """构建大盘热力云图数据（支持板块全景与核心成分股钻取）"""
    client = eastmoney.get_client()
    sectors = client.sector_list(stype=stype, sort_by=sort_by, limit=limit)

    # 针对成交额靠前的核心板块（前 12 个），并发拉取其前 4 大权重/领涨成分股构成子层级
    top_sectors = sectors[:12]
    other_sectors = sectors[12:]

    def _fetch_children(sec_code: str):
        try:
            stocks = client.sector_stocks(sec_code, limit=4, sort_by="amount")
            return [
                {
                    "name": s.name,
                    "code": s.code,
                    "value": max(s.amount or 1.0, 1.0),
                    "change_pct": s.change_pct or 0.0,
                    "price": s.price,
                    "amount": s.amount,
                    "main_inflow": s.main_inflow,
                }
                for s in stocks
            ]
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=min(len(top_sectors), 6) or 1) as ex:
        futures = {s.code: ex.submit(_fetch_children, s.code) for s in top_sectors}
        children_map = {code: f.result() for code, f in futures.items()}

    items = []
    total_amount = 0.0
    for s in sectors:
        amt = float(s.amount or 0.0)
        total_amount += amt
        val = max(amt, 1000000.0)
        children = children_map.get(s.code, [])
        item = {
            "name": s.name,
            "code": s.code,
            "value": val,
            "change_pct": s.change_pct if s.change_pct is not None else 0.0,
            "amount": amt,
            "main_inflow": s.main_inflow or 0.0,
            "leader_name": s.leader_name or "",
            "leader_code": s.leader_code or "",
            "leader_pct": s.leader_pct or 0.0,
            "up_count": s.up_count or 0,
            "down_count": s.down_count or 0,
        }
        if children:
            item["children"] = children
        items.append(item)

    return {
        "stype": stype,
        "total_amount": total_amount,
        "count": len(items),
        "items": items,
    }

