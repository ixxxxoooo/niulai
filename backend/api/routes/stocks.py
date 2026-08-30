"""个股/搜索相关路由
@author ygw
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ... import config
from ...datasource import eastmoney, tencent
from ...db import store as db

from .common import ttl_cache, _calc_indicators, _enrich_rows, _attach_local_tags, _merge_stock_detail, cached_limit_up_pool, cached_limit_break_pool

router = APIRouter()

@router.get("/search")
def search(
    q: str = Query(..., min_length=1, max_length=30, description="股票名称/拼音/代码"),
    limit: int = Query(10, ge=1, le=30),
):
    """股票模糊搜索：优先 SQLite 本地，未命中再降级东财 suggest。"""
    local = db.search_stocks_local(q, limit)
    if local:
        return local
    try:
        remote = eastmoney.get_client().search_stocks(q, limit)
        if remote:
            db.upsert_stocks([
                {
                    "code": s.get("code"),
                    "name": s.get("name") or "",
                    "market": s.get("market"),
                    "classify": "Fund" if "ETF" in str(s.get("type") or "").upper()
                    or "基金" in str(s.get("type") or "") else "AStock",
                }
                for s in remote if s.get("code")
            ])
        return remote
    except Exception:
        return []


@router.get("/stocks/batch")
@ttl_cache()
def stocks_batch(codes: str = Query(..., description="逗号分隔的股票代码")):
    """批量快照（自选股用）：分批并发 ulist 拉涨速/主力净流入，支持最多 800 只标的。"""
    from concurrent.futures import ThreadPoolExecutor
    code_list = [c.strip() for c in codes.split(",") if c.strip()][:800]
    if not code_list:
        return []
    metas = db.get_stocks_map(code_list)
    markets = {}
    for c, m in metas.items():
        if m.get("market") is not None:
            try:
                markets[c] = int(m["market"])
            except (TypeError, ValueError):
                pass

    batch_size = 50
    batches = [code_list[i:i + batch_size] for i in range(0, len(code_list), batch_size)]
    client = eastmoney.get_client()

    def _fetch_batch(b):
        try:
            return client.ulist_briefs(b, markets)
        except Exception:
            return []

    briefs = []
    if len(batches) == 1:
        briefs = _fetch_batch(batches[0])
    else:
        with ThreadPoolExecutor(max_workers=min(len(batches), 8)) as ex:
            for res in ex.map(_fetch_batch, batches):
                briefs.extend(res)

    by_code = {b.code: b for b in briefs}
    out = []
    for c in code_list:
        b = by_code.get(c)
        meta = metas.get(c) or {}
        if b is None:
            try:
                d = _merge_stock_detail(c).model_dump()
            except Exception:
                continue
        else:
            d = b.model_dump()
        d["classify"] = meta.get("classify") or d.get("classify") or (

            "Fund" if "ETF" in str(d.get("name") or "").upper() else "AStock"
        )
        d["board"] = meta.get("board") or d.get("board")
        d["is_st"] = meta.get("is_st") if meta.get("is_st") is not None else d.get("is_st")
        if not d.get("industry"):
            d["industry"] = meta.get("industry")
        d["concepts"] = meta.get("concepts") or d.get("concepts")
        out.append(d)
    return out


@router.get("/stocks/{code}")
@ttl_cache()
def stock_detail(code: str):
    """个股详情：行情 + 本地标签；概念缺失时即时补 F10 并回写 SQLite。"""
    d = _merge_stock_detail(code)
    if not d.concepts:
        try:
            boards = eastmoney.get_client().stock_f10_boards(code, d.market)
            if boards.get("industry") and not d.industry:
                d.industry = boards["industry"]
            if boards.get("concepts"):
                d.concepts = ",".join(boards["concepts"])
            if boards.get("industry") or boards.get("concepts"):
                db.update_stock_tags(code, boards.get("industry") or "", boards.get("concepts") or [])
        except Exception:
            pass
    # 快照 f62 偶发异常（如返回 2），用资金流当日值校正
    try:
        if d.main_inflow is None or abs(float(d.main_inflow if d.main_inflow is not None else 0)) < 1000:
            rows = eastmoney.get_client().moneyflow_history(code, days=1)
            if rows and abs(rows[-1].main_inflow) >= 1000:
                d.main_inflow = rows[-1].main_inflow
    except Exception:
        pass
    return d.model_dump()


@router.get("/stocks/{code}/limit-tag")
@ttl_cache(ttl=config.CACHE_TTL)
def stock_limit_tag(code: str):
    """个股连板/炸板标签：命中涨停池返回 lbc 连板数，命中炸板池返回炸板信息，否则返回 None。

    @author ygw
    参数:
        code: 6 位股票代码
    返回: {"lbc": int, "zb_count": int, "kind": "zt"|"zb", "first_time": str} 或 None
    """
    code = (code or "").upper()
    for p in cached_limit_up_pool():
        if p.get("code") == code:
            return {
                "lbc": int(p.get("lbc") or 1),
                "zb_count": int(p.get("zb_count") or 0),
                "kind": "zt",
                "first_time": p.get("first_time") or "",
            }
    for p in cached_limit_break_pool():
        if p.get("code") == code:
            return {
                "lbc": int(p.get("lbc") or 1),
                "zb_count": int(p.get("zb_count") or 0),
                "kind": "zb",
                "first_time": p.get("first_time") or "",
            }
    return None


@router.get("/stocks/{code}/holdings")
@ttl_cache(ttl=config.CACHE_TTL_OFFHOURS)
def stock_holdings(code: str):
    """ETF 持仓成分股（fundf10 前 N 大持仓）。

    @author ygw
    参数:
        code: 6 位基金/ETF 代码
    返回: {"code": str, "is_etf": bool, "items": [{rank, code, name, price, change_pct, ratio, shares, market_value}]}
    """
    code = (code or "").strip()
    try:
        data = eastmoney.get_client().etf_holdings(code, top=10)
        items = data.get("items") or []
        return {"code": code, "is_etf": bool(items), "items": items}
    except Exception:
        return {"code": code, "is_etf": False, "items": []}


@router.get("/stocks/{code}/trends")
@ttl_cache()
def stock_trends(code: str):
    t = eastmoney.get_client().intraday_trends(code)
    if t is None:
        return {
            "code": code,
            "name": "",
            "market": 1,
            "decimal": 2,
            "pre_close": 0.0,
            "points": [],
        }
    return t.model_dump()


@router.get("/stocks/{code}/kline")
@ttl_cache()
def stock_kline(
    code: str,
    period: str = Query("day", pattern="^(day|week|month)$"),
    limit: int = Query(350, ge=10, le=1000),
):
    """K 线（前复权）：day/week/month，附带 MA 均线指标；用百度补齐额/涨跌/换手"""
    k = eastmoney.get_client().kline(code, period=period, limit=limit)
    if k is None or not k.get("points"):
        return {
            "code": code,
            "period": period,
            "points": [],
            "indicators": {"ma5": [], "ma10": [], "ma20": [], "ma60": []}
        }
    _merge_baidu_kline_fields(code, period, k["points"])
    k["indicators"] = _calc_indicators(k["points"])
    return k


def _merge_baidu_kline_fields(code: str, period: str, points: list) -> None:
    """
    用百度 newMarketData 按日期补齐 amount/change_pct/change_amount/turnover。
    东财经常断连降级腾讯时字段不全，悬浮窗需要这些值。
    @author ygw
    """
    if not points:
        return
    # 已有成交额则跳过
    if any(p.get("amount") is not None for p in points[-5:]):
        return
    mapping = _baidu_kline_by_date(code, period)
    if not mapping:
        # 无百度数据时：用昨收推涨跌，用手×价估算成交额
        for i, p in enumerate(points):
            prev = points[i - 1]["close"] if i > 0 else None
            if p.get("change_pct") is None and prev:
                p["change_amount"] = round(p["close"] - prev, 2)
                p["change_pct"] = round((p["close"] - prev) / prev * 100, 2)
            if p.get("amount") is None and p.get("volume") and p.get("close"):
                p["amount"] = round(float(p["volume"]) * 100.0 * float(p["close"]), 2)
        return
    for p in points:
        extra = mapping.get(p.get("date") or "")
        if not extra:
            continue
        for key in ("amount", "change_pct", "change_amount", "turnover", "pre_close"):
            if p.get(key) is None and extra.get(key) is not None:
                p[key] = extra[key]
        # 百度 volume 为股，若本地量缺失可转手
        if (not p.get("volume")) and extra.get("volume_share"):
            p["volume"] = round(extra["volume_share"] / 100.0, 2)


_baidu_cache: dict = {}
_baidu_http = None

def _baidu_kline_by_date(code: str, ktype: str = "day") -> dict:
    """
    拉取百度 K 线明细，返回 date -> 字段字典。
    @author ygw
    """
    import logging
    import time
    import httpx
    global _baidu_http
    logger = logging.getLogger("baidu_kline")
    now = time.monotonic()
    cache_key = (code, ktype)
    if cache_key in _baidu_cache:
        cached_ts, cached_val = _baidu_cache[cache_key]
        if now - cached_ts < 180:
            return cached_val

    try:
        if _baidu_http is None:
            _baidu_http = httpx.Client(
                timeout=4.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0),
                headers={
                    "Accept": "application/vnd.finance-web.v1+json",
                    "Origin": "https://finance.baidu.com",
                    "Referer": "https://finance.baidu.com/",
                    "User-Agent": config.USER_AGENT,
                },
            )
        url = "https://finance.pae.baidu.com/sapi/v1/get_analysis_quotation"
        params = {
            "all": "1", "newFormat": "1",
            "ktype": ktype if ktype in ("day", "week", "month") else "day",
            "group": "quotation_analysis_kline",
            "code": code, "market_type": "ab", "finClientType": "pc",
        }
        resp = _baidu_http.get(url, params=params)
        resp.raise_for_status()
        md = (((resp.json() or {}).get("Result") or {}).get("newMarketData")) or {}
        keys = md.get("keys") or []
        raw = md.get("marketData") or ""
        out = {}
        for row in raw.split(";"):
            if not row.strip():
                continue
            parts = row.split(",")
            item = {keys[i]: parts[i] if i < len(parts) else None for i in range(len(keys))}
            date = item.get("time") or ""
            if not date:
                continue
            out[date] = {
                "amount": _safe_float(item.get("amount")),
                "change_pct": _safe_float(item.get("ratio")),
                "change_amount": _safe_float(item.get("range")),
                "turnover": None,  # 百度此接口无换手，留给快照/东财
                "pre_close": _safe_float(item.get("preClose")),
                "volume_share": _safe_float(item.get("volume")),
            }
        _baidu_cache[cache_key] = (now, out)
        if len(_baidu_cache) > 500:
            # 清理过期缓存
            old_keys = [k for k, (ts, _) in _baidu_cache.items() if now - ts > 180]
            for k in old_keys:
                _baidu_cache.pop(k, None)
        return out
    except Exception as e:
        logger.warning(f"百度K线明细失败 code={code}: {e}")
        return {}


@router.get("/stocks/{code}/chip")
@ttl_cache(ttl=60)
def stock_chip(code: str, days: int = Query(90, ge=30, le=300)):
    """
    筹码分布（成本分布）：基于近N日K线用换手率衰减+均匀分布模型估算。
    核心思路：每日新增筹码均匀分布在[low,high]区间；历史筹码按换手率衰减。
    返回 {bins: [{price, ratio}], avg_cost, profit_ratio, current}
    @author ygw
    """
    k = eastmoney.get_client().kline(code, period="day", limit=days)
    if not k or not k.get("points"):
        return {"bins": [], "avg_cost": 0, "profit_ratio": 0}
    pts = k["points"]
    current_price = pts[-1]["close"]
    # 确定价格区间（只看近期，避免被远古价格拉伸）
    recent = pts[-min(60, len(pts)):]
    all_highs = [p["high"] for p in recent]
    all_lows = [p["low"] for p in recent]
    price_min = min(all_lows) * 0.97
    price_max = max(all_highs) * 1.03
    num_bins = 80
    bin_width = (price_max - price_min) / num_bins
    if bin_width <= 0:
        return {"bins": [], "avg_cost": 0, "profit_ratio": 0}
    bins = [0.0] * num_bins

    for idx, p in enumerate(pts):
        low, high, close = p["low"], p["high"], p["close"]
        vol = p["volume"]
        if vol <= 0:
            continue
        # 换手率衰减：模拟旧筹码被换出
        turnover = p.get("turnover") if p.get("turnover") is not None else 0
        if turnover <= 0:
            turnover = 1.0
        decay = 1 - min(turnover / 100.0, 0.5)
        for b in range(num_bins):
            bins[b] *= decay

        # 新筹码分布：均匀分布在 [low, high]，close 处加权
        if high <= low:
            bi = int((close - price_min) / bin_width)
            bi = max(0, min(num_bins - 1, bi))
            bins[bi] += vol
        else:
            lo_bin = max(0, int((low - price_min) / bin_width))
            hi_bin = min(num_bins - 1, int((high - price_min) / bin_width))
            close_bin = max(lo_bin, min(hi_bin, int((close - price_min) / bin_width)))
            n_bins = hi_bin - lo_bin + 1
            if n_bins <= 0:
                continue
            base_vol = vol / n_bins
            for b in range(lo_bin, hi_bin + 1):
                # 收盘价附近加权（高斯形状）
                dist = abs(b - close_bin)
                weight = 1.0 + 1.5 * max(0, 1 - dist / max(n_bins * 0.3, 1))
                bins[b] += base_vol * weight

    # 归一化输出
    max_bin = max(bins) if bins else 1
    if max_bin <= 0:
        max_bin = 1
    result_bins = []
    total_chip = sum(bins)
    total_cost = 0.0
    profit_vol = 0.0
    for b in range(num_bins):
        bp = round(price_min + (b + 0.5) * bin_width, 2)
        ratio = round(bins[b] / max_bin, 4)
        if ratio > 0.005:
            result_bins.append({"price": bp, "ratio": ratio})
        total_cost += bins[b] * (price_min + (b + 0.5) * bin_width)
        if (price_min + (b + 0.5) * bin_width) <= current_price:
            profit_vol += bins[b]
    avg_cost = round(total_cost / total_chip, 2) if total_chip > 0 else 0
    profit_ratio = round(profit_vol / total_chip * 100, 1) if total_chip > 0 else 0
    return {"bins": result_bins, "avg_cost": avg_cost, "profit_ratio": profit_ratio, "current": current_price}


@router.get("/stocks/{code}/ticks")
@ttl_cache()
def stock_ticks(code: str, limit: int = Query(100, ge=1, le=500)):
    return [t.model_dump() for t in eastmoney.get_client().stock_ticks(code, limit=limit)]


@router.get("/stocks/{code}/moneyflow")
@ttl_cache()
def stock_moneyflow(code: str, days: int = Query(5, ge=1, le=30)):
    """个股资金流历史。返回列表；空列表表示源暂不可用（前端展示数据源标签）。"""
    import time as _time
    rows = [m.model_dump() for m in eastmoney.get_client().moneyflow_history(code, days=days)]
    # 兼容：仍返回 list；额外字段挂在响应外会破坏契约，改由前端空态推断
    # 若有数据则每条附带 source 便于调试/展示
    ts = _time.strftime("%H:%M:%S")
    for r in rows:
        r["data_source"] = "东财"
        r["fetched_at"] = ts
    return rows


@router.get("/stocks/{code}/lhb")
@ttl_cache(ttl=60)
def stock_lhb(code: str):
    """个股最近一次龙虎榜席位。"""
    from ...datasource import lhb
    data = lhb.fetch_lhb_stock(code)
    return data or {"date": None, "buy_seats": [], "sell_seats": []}


@router.get("/stocks/{code}/news")
@ttl_cache(ttl=120)
def stock_news(code: str, limit: int = Query(10, ge=1, le=30)):
    """
    个股相关新闻/公告。优先东财搜索，失败降级同花顺资讯。
    @author ygw
    """
    import httpx, json, logging
    logger = logging.getLogger("stock_news")

    # 尝试从本地 meta 获取股票名称以提高搜索命中率
    meta = db.get_stock(code) or {}
    keyword = (meta.get("name") or code) if meta else code

    # 方法1：东财搜索 API
    try:
        url = "https://search-api-web.eastmoney.com/search/jsonp"
        params = {
            "cb": "jQuery_callback",
            "param": json.dumps({
                "uid": "", "keyword": keyword,
                "type": ["cmsArticleWebOld"],
                "client": "web", "clientType": "web", "clientVersion": "curr",
                "param": {"cmsArticleWebOld": {
                    "searchScope": "default", "sort": "default",
                    "pageIndex": 1, "pageSize": limit,
                    "preTag": "", "postTag": ""
                }}
            }, ensure_ascii=False),
        }
        headers = {"Referer": "https://so.eastmoney.com/", "User-Agent": config.USER_AGENT}
        resp = httpx.get(url, params=params, headers=headers, timeout=6, follow_redirects=False)
        text = resp.text
        start = text.index("(") + 1
        end = text.rindex(")")
        data = json.loads(text[start:end])
        raw = data.get("result", {}).get("cmsArticleWebOld")
        # 兼容两种结构：list 或 {list:[...]}
        if isinstance(raw, list):
            articles = raw
        elif isinstance(raw, dict):
            articles = raw.get("list") or []
        else:
            articles = []
        if articles:
            return [
                {
                    "title": (a.get("title") or "").replace("<em>", "").replace("</em>", ""),
                    "date": a.get("date", ""),
                    "source": a.get("mediaName") or a.get("media_name") or "东方财富",
                    "url": a.get("url") or a.get("Url") or "",
                    "content": a.get("content") or a.get("digest") or "",
                    "image": a.get("image") or a.get("pic") or a.get("imgUrl") or "",
                }
                for a in articles[:limit]
            ]
    except Exception as e:
        logger.warning(f"东财新闻搜索失败 code={code}: {e}")

    # 方法2：东财个股资讯流
    try:
        secid = eastmoney.secid_of(code)
        url2 = f"https://np-listapi.eastmoney.com/comm/wap/getListInfo"
        params2 = {
            "cb": "callback", "client": "wap", "type": "1",
            "mession": "default", "code": secid.replace(".", ""),
            "pageSize": str(limit), "pageIndex": "0",
        }
        resp2 = httpx.get(url2, params=params2, headers=headers, timeout=6)
        text2 = resp2.text
        s2 = text2.index("(") + 1
        e2 = text2.rindex(")")
        d2 = json.loads(text2[s2:e2])
        items = d2.get("data", {}).get("list", [])
        if items:
            return [
                {
                    "title": it.get("title", ""),
                    "date": it.get("showTime", "")[:10],
                    "source": it.get("mediaName", "东方财富"),
                    "url": it.get("url", ""),
                    "content": it.get("digest") or it.get("content") or "",
                    "image": it.get("image") or it.get("pic") or it.get("imgUrl") or "",
                }
                for it in items[:limit]
            ]
    except Exception as e:
        logger.warning(f"东财资讯流失败 code={code}: {e}")

    return []


@router.get("/stocks/{code}/announcements")
@ttl_cache(ttl=300)
def stock_announcements(code: str, limit: int = Query(8, ge=1, le=20)):
    """
    个股公告（东财公告接口）。与新闻分开。
    @author ygw
    """
    import httpx, json, logging
    logger = logging.getLogger("stock_ann")
    try:
        url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        params = {
            "page_size": str(limit),
            "page_index": "1",
            "ann_type": "A",
            "client_source": "web",
            "stock_list": code,
        }
        headers = {"Referer": "https://data.eastmoney.com/", "User-Agent": config.USER_AGENT}
        resp = httpx.get(url, params=params, headers=headers, timeout=6)
        data = resp.json()
        items = (data.get("data") or {}).get("list") or []
        return [
            {
                "title": (it.get("title") or "").strip(),
                "date": (it.get("display_time") or it.get("notice_date") or "")[:10],
                "source": (it.get("columns") or [{}])[0].get("name", "") if it.get("columns") else "",
                "url": f"http://data.eastmoney.com/notices/detail/{code}/{it.get('art_code','')}.html",
            }
            for it in items[:limit] if it.get("title")
        ]
    except Exception as e:
        logger.warning(f"东财公告接口失败 code={code}: {e}")
    return []


@router.get("/stocks/{code}/analysis-data")
@ttl_cache(ttl=5)
def stock_analysis_data(code: str):
    """
    聚合个股全维度数据，供 AI 分析使用。
    包含：快照、分时、日K(60根)、资金流(10日)、技术指标、压力支撑位。
    @author ygw
    """
    from concurrent.futures import ThreadPoolExecutor

    def _snap():
        try:
            return _merge_stock_detail(code).model_dump()
        except Exception:
            return None

    def _trend():
        try:
            t = eastmoney.get_client().intraday_trends(code)
            return t.model_dump() if t else None
        except Exception:
            return None

    def _kline():
        try:
            k = eastmoney.get_client().kline(code, period="day", limit=60)
            if k and k.get("points"):
                k["indicators"] = _calc_indicators(k["points"])
            return k
        except Exception:
            return None

    def _flow():
        try:
            return [m.model_dump() for m in eastmoney.get_client().moneyflow_history(code, days=10)]
        except Exception:
            return []

    def _news():
        try:
            return stock_news(code, limit=5)
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=5) as pool:
        f1 = pool.submit(_snap)
        f2 = pool.submit(_trend)
        f3 = pool.submit(_kline)
        f4 = pool.submit(_flow)
        f5 = pool.submit(_news)
        snap = f1.result()
        trend_data = f2.result()
        kline_data = f3.result()
        flow_data = f4.result()
        news_data = f5.result()

    # 压力/支撑：优先百度行情分析 yl/zc，失败再本地估算
    support_resistance = _baidu_support_resistance(code)
    if not support_resistance.get("support") and not support_resistance.get("resistance"):
        support_resistance = _calc_support_resistance(snap, kline_data, trend_data)

    return {
        "snapshot": snap,
        "trend": trend_data,
        "kline": kline_data,
        "moneyflow": flow_data,
        "support_resistance": support_resistance,
        "news": news_data,
    }


@router.get("/stocks/{code}/baidu-sr")
@ttl_cache(ttl=120)
def stock_baidu_sr(code: str, ktype: str = Query("day")):
    """
    百度财经压力/支撑（analysisData.yl / zc），经后端代理避免前端跨域。
    不依赖登录 cookie；失败返回空结构。
    @author ygw
    """
    return _baidu_support_resistance(code, ktype=ktype)


def _baidu_support_resistance(code: str, ktype: str = "day") -> dict:
    """
    拉取百度 get_analysis_quotation 的压力/支撑。
    @param code 股票代码
    @param ktype day/week/month
    @return {support, resistance, price, update_time, source}
    @author ygw
    """
    import logging
    import httpx
    logger = logging.getLogger("baidu_sr")
    out = {"support": [], "resistance": [], "price": None, "update_time": "", "source": "baidu"}
    if not code or len(code) != 6:
        return out
    try:
        url = "https://finance.pae.baidu.com/sapi/v1/get_analysis_quotation"
        params = {
            "all": "1",
            "newFormat": "1",
            "ktype": ktype if ktype in ("day", "week", "month") else "day",
            "group": "quotation_analysis_kline",
            "code": code,
            "market_type": "ab",
            "finClientType": "pc",
        }
        headers = {
            "Accept": "application/vnd.finance-web.v1+json",
            "Origin": "https://finance.baidu.com",
            "Referer": "https://finance.baidu.com/",
            "User-Agent": config.USER_AGENT,
        }
        resp = httpx.get(url, params=params, headers=headers, timeout=6)
        resp.raise_for_status()
        body = resp.json() or {}
        ad = ((body.get("Result") or {}).get("analysisData")) or {}
        price = _safe_float(ad.get("price"))
        yl = _safe_float(ad.get("yl"))  # 压力
        zc = _safe_float(ad.get("zc"))  # 支撑
        out["price"] = price
        out["update_time"] = str(ad.get("updateTime") or "")
        if yl is not None:
            out["resistance"].append({"price": round(yl, 2), "label": "压力", "type": "baidu"})
        if zc is not None:
            out["support"].append({"price": round(zc, 2), "label": "支撑", "type": "baidu"})
    except Exception as e:
        logger.warning(f"百度压力支撑失败 code={code}: {e}")
    return out


def _safe_float(v):
    """把 '--'/空/字符串转为 float，失败返回 None。"""
    if v is None or v == "" or v == "--":
        return None
    try:
        return float(str(v).replace("+", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _calc_support_resistance(snap, kline, trend):
    """
    本地估算压力/支撑（百度失败时的兜底，仅保留均线+近期高低各一条）。
    @author ygw
    """
    levels = {"support": [], "resistance": []}
    if not snap or not snap.get("price"):
        return levels
    price = snap["price"]

    if kline and kline.get("indicators"):
        ind = kline["indicators"]
        for name, arr_key in [("MA20", "ma20"), ("MA60", "ma60")]:
            arr = ind.get(arr_key) or []
            if arr and arr[-1] is not None:
                val = arr[-1]
                entry = {"price": round(val, 2), "label": name, "type": "ma"}
                if val < price * 0.998:
                    levels["support"].append(entry)
                elif val > price * 1.002:
                    levels["resistance"].append(entry)

    if kline and kline.get("points"):
        pts = kline["points"]
        highs = [p["high"] for p in pts[-20:] if p.get("high") and p["high"] > price * 1.005]
        lows = [p["low"] for p in pts[-20:] if p.get("low") and p["low"] < price * 0.995]
        if highs:
            nearest_h = min(highs, key=lambda h: abs(h - price))
            levels["resistance"].append({"price": round(nearest_h, 2), "label": "近期高点", "type": "high"})
        if lows:
            nearest_l = min(lows, key=lambda l: abs(l - price))
            levels["support"].append({"price": round(nearest_l, 2), "label": "近期低点", "type": "low"})

    for side in ["support", "resistance"]:
        unique = []
        for lv in sorted(levels[side], key=lambda x: abs(x["price"] - price)):
            if any(abs(lv["price"] - u["price"]) / price < 0.005 for u in unique):
                continue
            unique.append(lv)
        levels[side] = unique[:2]
    return levels


@router.get("/stocks/{code}/comment")
@ttl_cache(ttl=60)
def stock_comment(code: str):
    """获取个股综合评分（东财智能诊股），含评分、打败比例、次日上涨概率、文字解读。
    @author ygw
    """
    result = eastmoney.get_client().stock_comment(code)
    if result is None:
        return {}
    return result


@router.get("/stocks/{code}/diagnosis")
@ttl_cache(ttl=60)
def stock_diagnosis(code: str):
    """获取个股千股千评全维度研判（综合评价/主力控盘/趋势研判/技术信号）。
    @author ygw
    """
    result = eastmoney.get_client().stock_diagnosis(code)
    if result is None:
        return {}
    return result


