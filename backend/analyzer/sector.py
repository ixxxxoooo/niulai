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


def market_heatmap_data(
    scope: str = "all_top300",
    size_by: str = "amount",
    limit: int = 300,
) -> dict:
    """
    构建符合金融业界标准的大盘热力云图（Market Treemap）
    双层树状结构：
      Level 1: 行业/板块大区（含行业标题、总成交/总市值体量、加权涨跌幅）
      Level 2: 该板块下的每一只成分股方块（面积=成交额/市值，颜色=涨跌幅）
    支持全市场 TOP 300/500、沪深300、双创核心、中证500、我的自选股、31大行业全景等多种维度。
    """
    from ..db import store as db
    client = eastmoney.get_client()

    # 1. 行业板块全景概览模式
    if scope == "industry_overview":
        sectors = client.sector_list(stype="industry", sort_by="amount", limit=35)
        def _fetch_ind_stocks(sec_code: str):
            try:
                stocks = client.sector_stocks(sec_code, limit=6, sort_by="amount")
                return [
                    {
                        "name": s.name,
                        "code": s.code,
                        "value": max(s.amount or 1.0, 1.0) if size_by == "amount" else 1.0,
                        "change_pct": s.change_pct or 0.0,
                        "price": s.price,
                        "amount": s.amount or 0.0,
                        "main_inflow": s.main_inflow,
                        "isStock": True,
                    }
                    for s in stocks
                ]
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {s.code: ex.submit(_fetch_ind_stocks, s.code) for s in sectors}
            children_map = {code: f.result() for code, f in futures.items()}

        items = []
        total_amount = 0.0
        for s in sectors:
            amt = float(s.amount or 0.0)
            total_amount += amt
            children = children_map.get(s.code, [])
            val = max(amt, 1000000.0)
            items.append({
                "name": s.name,
                "code": s.code,
                "value": val,
                "change_pct": s.change_pct if s.change_pct is not None else 0.0,
                "amount": amt,
                "main_inflow": s.main_inflow or 0.0,
                "leader_name": s.leader_name or "",
                "leader_pct": s.leader_pct or 0.0,
                "up_count": s.up_count or 0,
                "down_count": s.down_count or 0,
                "stock_count": len(children),
                "children": children,
            })
        return {
            "scope": scope,
            "size_by": size_by,
            "total_amount": total_amount,
            "stock_count": sum(len(it.get("children", [])) for it in items),
            "count": len(items),
            "items": items,
        }

    # 2. 概念题材概览模式
    if scope == "concept_overview":
        sectors = client.sector_list(stype="concept", sort_by="amount", limit=50)
        def _fetch_cpt_stocks(sec_code: str):
            try:
                stocks = client.sector_stocks(sec_code, limit=5, sort_by="amount")
                return [
                    {
                        "name": s.name,
                        "code": s.code,
                        "value": max(s.amount or 1.0, 1.0) if size_by == "amount" else 1.0,
                        "change_pct": s.change_pct or 0.0,
                        "price": s.price,
                        "amount": s.amount or 0.0,
                        "main_inflow": s.main_inflow,
                        "isStock": True,
                    }
                    for s in stocks
                ]
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {s.code: ex.submit(_fetch_cpt_stocks, s.code) for s in sectors}
            children_map = {code: f.result() for code, f in futures.items()}

        items = []
        total_amount = 0.0
        for s in sectors:
            amt = float(s.amount or 0.0)
            total_amount += amt
            children = children_map.get(s.code, [])
            val = max(amt, 1000000.0)
            items.append({
                "name": s.name,
                "code": s.code,
                "value": val,
                "change_pct": s.change_pct if s.change_pct is not None else 0.0,
                "amount": amt,
                "main_inflow": s.main_inflow or 0.0,
                "leader_name": s.leader_name or "",
                "leader_pct": s.leader_pct or 0.0,
                "up_count": s.up_count or 0,
                "down_count": s.down_count or 0,
                "stock_count": len(children),
                "children": children,
            })
        return {
            "scope": scope,
            "size_by": size_by,
            "total_amount": total_amount,
            "stock_count": sum(len(it.get("children", [])) for it in items),
            "count": len(items),
            "items": items,
        }

    # 3. 自选股全景模式
    if scope == "watchlist":
        codes = db.watchlist_codes()
        if not codes:
            return {"scope": scope, "size_by": size_by, "total_amount": 0.0, "stock_count": 0, "count": 0, "items": []}
        stocks_brief = client.ulist_briefs(codes[:400])
        groups: Dict[str, List[Dict[str, Any]]] = {}
        total_amount = 0.0
        for s in stocks_brief:
            ind = s.industry or "其他"
            amt = float(s.amount or 0.0)
            total_amount += amt
            val = max(amt, 10000.0)
            groups.setdefault(ind, []).append({
                "name": s.name,
                "code": s.code,
                "value": val,
                "price": s.price,
                "change_pct": s.change_pct or 0.0,
                "amount": amt,
                "turnover": s.turnover,
                "main_inflow": s.main_inflow,
                "industry": ind,
                "isStock": True,
            })

        items = []
        for ind_name, st_list in groups.items():
            g_val = sum(x["value"] for x in st_list)
            g_amt = sum(x["amount"] for x in st_list)
            avg_pct = sum(x["change_pct"] * x["value"] for x in st_list) / g_val if g_val > 0 else 0.0
            st_list.sort(key=lambda x: x["value"], reverse=True)
            items.append({
                "name": ind_name,
                "value": g_val,
                "change_pct": avg_pct,
                "amount": g_amt,
                "stock_count": len(st_list),
                "up_count": sum(1 for x in st_list if x["change_pct"] > 0),
                "down_count": sum(1 for x in st_list if x["change_pct"] < 0),
                "children": st_list,
            })
        items.sort(key=lambda g: g["value"], reverse=True)
        return {
            "scope": scope,
            "size_by": size_by,
            "total_amount": total_amount,
            "stock_count": len(stocks_brief),
            "count": len(items),
            "items": items,
        }

    # 4. 行业个股云图模式（全市场 TOP 300 / 500、沪深300、中证500、双创核心）
    pages = 3 if limit <= 300 else 5
    if scope == "all_top500":
        fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        pages = 5
    elif scope == "hs300":
        fs = "b:BK0500"
        pages = 3
    elif scope == "zz500":
        fs = "b:BK0701"
        pages = 3
    elif scope == "cyb_kcb":
        fs = "m:0+t:80,m:1+t:23"
        pages = 3
    else:  # all_top300
        fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        pages = 3

    fields = "f12,f14,f2,f3,f6,f8,f20,f21,f100,f62"
    fid = "f6" if size_by == "amount" else ("f21" if size_by == "float_mv" else "f20")

    def _page(pn: int):
        data = client._q.get("/clist/get", {
            "pn": pn, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
            "fid": fid, "fs": fs, "fields": fields,
        })
        diff = (data or {}).get("data", {}).get("diff") or []
        if isinstance(diff, dict):
            diff = [diff]
        return diff

    with ThreadPoolExecutor(max_workers=pages) as ex:
        raw_pages = list(ex.map(_page, range(1, pages + 1)))

    raw_stocks = [it for p in raw_pages for it in p if it.get("f12")]
    groups: Dict[str, List[Dict[str, Any]]] = {}
    total_amount = 0.0

    for r in raw_stocks:
        code = str(r.get("f12") or "")
        name = str(r.get("f14") or "")
        ind = str(r.get("f100") or "其他").strip() or "其他"
        price = float(r.get("f2") or 0.0) if r.get("f2") is not None and str(r.get("f2")) != "-" else None
        pct = float(r.get("f3") or 0.0) if r.get("f3") is not None and str(r.get("f3")) != "-" else 0.0
        amt = float(r.get("f6") or 0.0) if r.get("f6") is not None and str(r.get("f6")) != "-" else 0.0
        turnover = float(r.get("f8") or 0.0) if r.get("f8") is not None and str(r.get("f8")) != "-" else 0.0
        total_mv = float(r.get("f20") or 0.0) if r.get("f20") is not None and str(r.get("f20")) != "-" else 0.0
        float_mv = float(r.get("f21") or 0.0) if r.get("f21") is not None and str(r.get("f21")) != "-" else 0.0
        main_inflow = float(r.get("f62") or 0.0) if r.get("f62") is not None and str(r.get("f62")) != "-" else 0.0

        total_amount += amt
        if size_by == "float_mv":
            val = float_mv if float_mv > 0 else (total_mv if total_mv > 0 else amt)
        elif size_by == "total_mv":
            val = total_mv if total_mv > 0 else amt
        else:
            val = amt
        val = max(val, 1.0)

        groups.setdefault(ind, []).append({
            "name": name,
            "code": code,
            "value": val,
            "price": price,
            "change_pct": pct,
            "amount": amt,
            "turnover": turnover,
            "total_mv": total_mv,
            "float_mv": float_mv,
            "main_inflow": main_inflow,
            "industry": ind,
            "isStock": True,
        })

    items = []
    for ind_name, st_list in groups.items():
        g_val = sum(x["value"] for x in st_list)
        g_amt = sum(x["amount"] for x in st_list)
        avg_pct = sum(x["change_pct"] * x["value"] for x in st_list) / g_val if g_val > 0 else 0.0
        st_list.sort(key=lambda x: x["value"], reverse=True)
        items.append({
            "name": ind_name,
            "value": g_val,
            "change_pct": avg_pct,
            "amount": g_amt,
            "stock_count": len(st_list),
            "up_count": sum(1 for x in st_list if x["change_pct"] > 0),
            "down_count": sum(1 for x in st_list if x["change_pct"] < 0),
            "children": st_list,
        })

    items.sort(key=lambda g: g["value"], reverse=True)

    return {
        "scope": scope,
        "size_by": size_by,
        "total_amount": total_amount,
        "stock_count": len(raw_stocks),
        "count": len(items),
        "items": items,
    }

