"""大盘/板块/榜单/全球/指数路由
@author ygw
"""
from fastapi import APIRouter, HTTPException, Query

from ... import config
from ...analyzer import market as market_an
from ...analyzer import rank as rank_an
from ...analyzer import sector as sector_an
from ...datasource import eastmoney

from .common import ttl_cache, _calc_indicators, _enrich_rows, cached_limit_up_pool, cached_limit_break_pool, attach_youzi

router = APIRouter()


@router.get("/market/indices-trends")
@ttl_cache(ttl=30)
def indices_trends():
    """主要指数分时（盘面总览缩略图用），只返回绘制所需字段以减小体积。

    @author ygw
    返回:
        {"items": [{code, secid, name, pre_close, points: [{time, price}]}]}
    """
    from concurrent.futures import ThreadPoolExecutor

    client = eastmoney.get_client()

    def _fetch(secid: str):
        try:
            t = client.intraday_trends(secid=secid)
            if t is None or not t.points:
                return None
            return {
                "code": t.code,
                "secid": secid,
                "name": t.name,
                "pre_close": t.pre_close,
                "points": [{"time": p.time, "price": p.price} for p in t.points],
            }
        except Exception:  # noqa: BLE001 - 单指数失败不影响其他指数
            return None

    secids = [s for s, _ in config.INDEX_SECIDS]
    with ThreadPoolExecutor(max_workers=max(len(secids), 1)) as ex:
        futures = [ex.submit(_fetch, s) for s in secids]
        items = [f.result() for f in futures if f.result()]
    return {"items": items}

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


_concept_code_cache: dict = {}


def _sector_code_lookup(type: str, name: str):
    """按板块类型取（缓存的）全量列表，名称精确匹配，否则子串双向匹配；返回板块代码或 None"""
    import time
    cache = _concept_code_cache.setdefault(type, {"ts": 0.0, "items": {}})
    now = time.time()
    if now - cache["ts"] > 300 or not cache["items"]:
        try:
            sectors = sector_an.sector_list(type, limit=800, all_pages=True)
            cache["items"] = {s.name: s.code for s in sectors if s.code and s.name}
            cache["ts"] = now
        except Exception:
            pass
    items = cache["items"]
    if not name:
        return None
    code = items.get(name)
    if not code:
        for k, v in items.items():
            if name in k or k in name:
                code = v
                break
    return code


@router.get("/sectors/concept-code")
def sector_concept_code(name: str = Query("", max_length=50),
                        type: str = Query("concept", pattern="^(industry|concept)$")):
    """
    根据行业/概念名称查找东财板块代码（BKxxxx），供标签点击跳转板块页。
    先按指定 type 查找；查不到时自动回退另一类型（东财个股板块标签会混入行业名，
    如"影视院线"实为行业板块）。板块全量列表按 type 各自缓存 5 分钟
    （不用 ttl_cache 装饰，避免按 name 无限缓存膨胀）。
    @author ygw
    """
    if not name:
        return {"code": None, "name": "", "type": type}
    order = [type]
    for t in ("concept", "industry", "area"):
        if t not in order:
            order.append(t)
    code = None
    hit_type = type
    for t in order:
        code = _sector_code_lookup(t, name)
        if code:
            hit_type = t
            break
    return {"code": code, "name": name, "type": hit_type}


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


@router.get("/market/stock-changes")
@ttl_cache(ttl=15)
def stock_changes(limit: int = Query(80, ge=1, le=200)):
    """盘中个股异动：大笔买入/卖出、急速拉升/跳水等"""
    return eastmoney.get_client().stock_changes(limit)


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
def limit_up_pool(limit: int = Query(100, ge=1, le=300)):
    """今日涨停池（共享缓存，limit 仅截断展示数量）。附带最近交易日游资徽章。"""
    rows = cached_limit_up_pool()
    attach_youzi(rows)
    return rows[:limit] if limit < len(rows) else rows


@router.get("/market/limit-break")
def limit_break_pool(limit: int = Query(100, ge=1, le=300)):
    """今日炸板池（共享缓存，limit 仅截断展示数量）。附带最近交易日游资徽章。"""
    rows = cached_limit_break_pool()
    attach_youzi(rows)
    return rows[:limit] if limit < len(rows) else rows


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
    """东财龙虎榜（最近有数据的交易日）。命中游资的股票额外带 youzi 徽章列表。"""
    from ...datasource import lhb
    data = lhb.fetch_lhb_list(limit)
    items = data.get("items") or []
    data["items"] = _enrich_rows(items)
    date = data.get("date")
    if date:
        from ...db.lhb_moves import moves_by_date
        from ...db.lhb_seats import list_seats
        youzi: dict = {}
        try:
            for side in ("buy", "sell"):
                for g in moves_by_date(date, side, limit=500):
                    st = youzi.setdefault(g["code"], set())
                    for s in g["seats"]:
                        st.add(s["nickname"])
        except Exception:
            pass
        style_map: dict = {}
        try:
            for s in list_seats():
                if s.get("nickname"):
                    style_map.setdefault(s["nickname"], {
                        "style": s.get("style") or "",
                        "premium": s.get("premium") or "neutral",
                    })
        except Exception:
            pass
        for it in data["items"]:
            code = it.get("code")
            if code and code in youzi:
                it["youzi"] = [
                    {"nickname": n, "style": (style_map.get(n) or {}).get("style", ""),
                     "premium": (style_map.get(n) or {}).get("premium", "neutral")}
                    for n in sorted(youzi[code])
                ]
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

