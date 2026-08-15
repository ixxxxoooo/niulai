"""大盘/板块/榜单/全球/指数路由
@author ygw
"""
from fastapi import APIRouter, HTTPException, Query

from ...analyzer import market as market_an
from ...analyzer import rank as rank_an
from ...analyzer import sector as sector_an
from ...datasource import eastmoney

from .common import ttl_cache, _calc_indicators, _enrich_rows

router = APIRouter()

@router.get("/market/overview")
@ttl_cache()
def market_overview():
    return market_an.market_overview().model_dump()


@router.get("/market/volume")
@ttl_cache(ttl=30)
def market_volume():
    """全 A 两市量能（放量/缩量）。需拉指数日K，30s 缓存避免频繁请求"""
    v = market_an.market_volume()
    if v is None:
        raise HTTPException(status_code=503, detail="量能数据暂不可用")
    return v


@router.get("/sectors")
@ttl_cache()
def sectors(
    type: str = Query("industry", pattern="^(industry|concept)$"),
    sort: str = Query("change_pct", pattern="^(change_pct|main_inflow|amount)$"),
    limit: int = Query(100, ge=1, le=300),
):
    return [s.model_dump() for s in sector_an.sector_list(type, sort, limit)]


@router.get("/sectors/moneyflow")
@ttl_cache(ttl=5)
def sectors_moneyflow(
    type: str = Query("industry", pattern="^(industry|concept)$"),
    limit: int = Query(100, ge=1, le=300),
):
    """板块主力净流入排行（全量拉取后排序，含净流出板块）"""
    return [s.model_dump() for s in rank_an.sector_moneyflow(type, limit)]


@router.get("/sectors/{code}")
@ttl_cache()
def sector_detail(code: str, sort: str = Query("change_pct"), limit: int = Query(100, ge=1, le=300)):
    out = sector_an.sector_detail(code, limit, sort)
    return {
        "sector": out["sector"].model_dump() if out["sector"] else None,
        "stocks": _enrich_rows(out["stocks"]),
    }


@router.get("/rank/hot")
@ttl_cache()
def rank_hot(
    by: str = Query("change_pct", pattern="^(change_pct|amount|turnover|volume_ratio|zhangsu)$"),
    limit: int = Query(50, ge=1, le=200),
):
    return _enrich_rows(rank_an.hot_stocks(by, limit))


@router.get("/rank/zhangsu")
@ttl_cache()
def rank_zhangsu(limit: int = Query(50, ge=1, le=200)):
    return _enrich_rows(rank_an.zhangsu_rank(limit))


@router.get("/rank/moneyflow")
@ttl_cache()
def rank_moneyflow(limit: int = Query(50, ge=1, le=200)):
    return _enrich_rows(rank_an.moneyflow_rank(limit))


@router.get("/etf/rank")
@ttl_cache()
def etf_rank(
    by: str = Query("change_pct", pattern="^(change_pct|amount|turnover|amplitude|volume)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """ETF 涨跌排行（涨幅/成交额/换手率/振幅/成交量）"""
    return _enrich_rows(eastmoney.get_client().etf_rank(by, limit))


@router.get("/sector-moves")
@ttl_cache()
def sector_moves(
    dir: str = Query("up", pattern="^(up|down)$", description="up=拉升榜 down=跳水榜"),
    limit: int = Query(30, ge=1, le=100),
):
    """板块异动：5 分钟板块涨速排行（行业+概念）"""
    return [s.model_dump() for s in eastmoney.get_client().sector_moves(dir, limit)]


@router.get("/global/indices")
@ttl_cache()
def global_indices():
    """全球主要指数（日韩/亚太/美股）"""
    return [q.model_dump() for q in eastmoney.get_client().global_indices()]


@router.get("/global/{secid}/trends")
@ttl_cache()
def global_trends(secid: str):
    """全球指数分时（东财→腾讯降级）"""
    t = eastmoney.get_client().intraday_trends(secid=secid)
    if t is None:
        raise HTTPException(status_code=404, detail=f"指数 {secid} 分时暂不可用")
    return t.model_dump()


@router.get("/global/{secid}/kline")
@ttl_cache()
def global_kline(
    secid: str,
    period: str = Query("day", pattern="^(day|week|month)$"),
    limit: int = Query(120, ge=10, le=500),
):
    """全球指数 K 线（东财→腾讯降级）"""
    k = eastmoney.get_client().kline(secid=secid, period=period, limit=limit)
    if k is None or not k.get("points"):
        raise HTTPException(status_code=404, detail=f"指数 {secid} K线暂不可用")
    k["indicators"] = _calc_indicators(k["points"])
    return k


@router.get("/sectors/{code}/moneyflow-history")
@ttl_cache()
def sector_moneyflow_history(code: str, days: int = Query(5, ge=1, le=30)):
    """板块近 N 日主力资金流历史（免费接口被风控时 available=false）"""
    rows, available = eastmoney.get_client().sector_moneyflow_history(code, days)
    return {"available": available, "days": rows}


@router.get("/market/limit-up")
@ttl_cache()
def limit_up_pool(limit: int = Query(100, ge=1, le=300)):
    return _enrich_rows(eastmoney.get_client().limit_up_pool(limit))


@router.get("/market/limit-break")
@ttl_cache()
def limit_break_pool(limit: int = Query(100, ge=1, le=300)):
    """今日炸板池。"""
    return _enrich_rows(eastmoney.get_client().limit_break_pool(limit))


@router.get("/ths/hot")
@ttl_cache(ttl=30)
def ths_hot(
    type: str = Query("hour", pattern="^(hour|day)$"),
    limit: int = Query(50, ge=1, le=100),
):
    """同花顺 A 股热榜。"""
    from ...datasource import ths
    return _enrich_rows(ths.fetch_hot_list(type, limit))


@router.get("/market/lhb")
@ttl_cache(ttl=60)
def market_lhb(limit: int = Query(50, ge=1, le=100)):
    """东财龙虎榜（最近有数据的交易日）。"""
    from ...datasource import lhb
    data = lhb.fetch_lhb_list(limit)
    data["items"] = _enrich_rows(data.get("items") or [])
    return data


@router.get("/indices/quote")
@ttl_cache()
def index_quote(secid: str = Query(..., min_length=3, max_length=32)):
    """A 股/全球指数快照（按 secid，如 1.000001）。"""
    quotes = eastmoney.get_client().index_quotes([secid])
    if not quotes:
        raise HTTPException(status_code=404, detail=f"未找到指数 {secid}")
    q = quotes[0]
    if not q.secid:
        q.secid = secid
    return q.model_dump()


@router.get("/indices/quotes")
@ttl_cache()
def indices_quotes(
    secids: str = Query("1.000001,0.399006,1.000688", max_length=200),
):
    """批量指数快照（导航栏用：上证/创业板/科创50）。"""
    ids = [s.strip() for s in secids.split(",") if s.strip()][:8]
    if not ids:
        raise HTTPException(status_code=400, detail="secids 不能为空")
    quotes = eastmoney.get_client().index_quotes(ids)
    out = []
    for q in quotes:
        d = q.model_dump()
        if not d.get("secid"):
            # 按 code 回填 secid
            for sid in ids:
                if sid.endswith("." + d.get("code", "")):
                    d["secid"] = sid
                    break
        out.append(d)
    return out


@router.get("/market/moneyflow")
@ttl_cache(ttl=10)
def market_moneyflow(days: int = Query(5, ge=1, le=30)):
    """大盘资金流向（对应东财 dpzjlx 页）。"""
    return eastmoney.get_client().market_moneyflow(days)


@router.get("/quotes/trends")
@ttl_cache()
def quotes_trends(secid: str = Query(..., min_length=3, max_length=32)):
    """分时：用 query 传 secid，避免路径里的点号被中间层截断。"""
    t = eastmoney.get_client().intraday_trends(secid=secid)
    if t is None:
        raise HTTPException(status_code=404, detail=f"指数 {secid} 分时暂不可用")
    return t.model_dump()


@router.get("/quotes/kline")
@ttl_cache()
def quotes_kline(
    secid: str = Query(..., min_length=3, max_length=32),
    period: str = Query("day", pattern="^(day|week|month)$"),
    limit: int = Query(120, ge=10, le=500),
):
    """K 线：用 query 传 secid。"""
    k = eastmoney.get_client().kline(secid=secid, period=period, limit=limit)
    if k is None or not k.get("points"):
        raise HTTPException(status_code=404, detail=f"指数 {secid} K线暂不可用")
    k["indicators"] = _calc_indicators(k["points"])
    return k

