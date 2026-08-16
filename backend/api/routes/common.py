"""路由公共：TTL 缓存、标签补全、个股详情合并、Pydantic 模型
@author ygw
"""
import functools
import threading
import time
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field

from ... import config
from ...analyzer import schedule
from ...analyzer.indicators import calc_indicators
from ...datasource import eastmoney, tencent
from ...datasource.models import StockDetail, OrderBook
from ...db.tags import infer_board
from ...db import store as db



class WatchBody(BaseModel):
    """自选股写入参数"""
    code: str = Field(..., min_length=6, max_length=6)


class WatchImportBody(BaseModel):
    """自选股批量导入"""
    codes: list = Field(default_factory=list)


class SettingBody(BaseModel):
    """单条设置"""
    key: str
    value: str = ""


class SettingsBulkBody(BaseModel):
    """批量设置"""
    items: dict = Field(default_factory=dict)


class ActionLogBody(BaseModel):
    """前端行为日志批量上报"""
    items: list = Field(default_factory=list)


class PositionBody(BaseModel):
    """持仓录入"""
    code: str = Field(..., min_length=6, max_length=6)
    shares: float = 0
    cost: float = 0
    note: str = ""


class BackupBody(BaseModel):
    """用户数据备份恢复"""
    payload: dict = Field(default_factory=dict)


class AlertBody(BaseModel):
    """价格/跌幅监控规则"""
    target_type: str = Field("stock", pattern="^(stock|index)$")
    code: str = Field(..., min_length=1, max_length=32)
    name: str = ""
    metric: str = Field("price", pattern="^(price|points|change_pct|zhangsu)$")
    op: str = Field("lte", pattern="^(lte|gte)$")
    threshold: float
    cooldown_sec: int = Field(300, ge=30, le=86400)
    note: str = ""
    enabled: Optional[bool] = True


class AlertPatchBody(BaseModel):
    """监控规则局部更新"""
    name: Optional[str] = None
    metric: Optional[str] = Field(None, pattern="^(price|points|change_pct|zhangsu)$")
    op: Optional[str] = Field(None, pattern="^(lte|gte)$")
    threshold: Optional[float] = None
    cooldown_sec: Optional[int] = Field(None, ge=30, le=86400)
    note: Optional[str] = None
    enabled: Optional[bool] = None

# ------------------------------------------------------------------ TTL 缓存
_cache: Dict[str, tuple] = {}
_cache_lock = threading.Lock()


def ttl_cache(ttl: float = config.CACHE_TTL):
    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{args}:{sorted(kwargs.items())}"
            now = time.monotonic()
            effective = ttl
            try:
                if not schedule.is_trading_time():
                    effective = max(ttl, config.CACHE_TTL_OFFHOURS)
            except Exception:
                pass
            with _cache_lock:
                hit = _cache.get(key)
                if hit and now - hit[0] < effective:
                    return hit[1]
            val = fn(*args, **kwargs)
            with _cache_lock:
                _cache[key] = (now, val)
            return val
        return wrapper
    return deco


def clear_cache():
    with _cache_lock:
        _cache.clear()


# ------------------------------------------------------------------ 涨停/炸板池共享缓存
@ttl_cache(ttl=config.CACHE_TTL)
def cached_limit_up_pool() -> list:
    """共享涨停池缓存（固定 300 条），供涨停池/连板梯队/个股标签复用。

    @author ygw
    返回: 已补全标签的涨停股 dict 列表
    """
    return _enrich_rows(eastmoney.get_client().limit_up_pool(300))


@ttl_cache(ttl=config.CACHE_TTL)
def cached_limit_break_pool() -> list:
    """共享炸板池缓存（固定 300 条），供炸板池/个股标签复用。

    @author ygw
    返回: 已补全标签的炸板股 dict 列表
    """
    return _enrich_rows(eastmoney.get_client().limit_break_pool(300))


# 最近交易日游资动向缓存（复用龙虎榜游资徽章逻辑，避免每次查库）
_youzi_map_cache: Dict[str, list] = {}
_youzi_map_ts = 0.0
_youzi_map_lock = threading.Lock()


def attach_youzi(rows: list) -> list:
    """给涨停/炸板池行附加游资徽章列表（youzi），来源最近已同步的龙虎榜交易日。

    参数:
        rows: 涨停/炸板股 dict 列表
    返回:
        原列表（每行带 youzi 字段，无命中则不带）
    @author ygw
    """
    if not rows:
        return rows
    global _youzi_map_ts
    now = time.monotonic()
    with _youzi_map_lock:
        if now - _youzi_map_ts > 60:
            _youzi_map_ts = now
            _youzi_map_cache.clear()
            try:
                from ...db.lhb_moves import list_dates, moves_by_date
                dates = list_dates()
                mapping: Dict[str, set] = {}
                for day_row in dates[:3]:
                    day = day_row["date"]
                    for side in ("buy", "sell"):
                        for g in moves_by_date(day, side, limit=500):
                            st = mapping.setdefault(g["code"], set())
                            for s in g.get("seats", []):
                                if s.get("nickname"):
                                    st.add(s["nickname"])
                for code, names in mapping.items():
                    _youzi_map_cache[code] = sorted(names)
            except Exception as e:
                _youzi_map_cache.clear()
                from ...logging_config import logger
                logger.warning("attach_youzi 构建失败: %s", e)
    if not _youzi_map_cache:
        return rows
    for r in rows:
        code = r.get("code") or ""
        names = _youzi_map_cache.get(code)
        if names:
            r["youzi"] = names
    return rows


# ------------------------------------------------------------------ 技术指标
def _calc_indicators(points: list) -> dict:
    """基于 K 线数据计算 MA/MACD/KDJ/RSI/BOLL。"""
    return calc_indicators(points)


def _attach_local_tags(detail: StockDetail) -> StockDetail:
    """用 SQLite 标签补全行业/概念/板块。"""
    meta = db.get_stock(detail.code)
    if not meta:
        return detail
    if not detail.industry:
        detail.industry = meta.get("industry") or None
    if not detail.concepts:
        detail.concepts = meta.get("concepts") or None
    detail.classify = meta.get("classify") or detail.classify
    detail.board = meta.get("board") or detail.board
    if meta.get("is_st") is not None:
        detail.is_st = meta.get("is_st")
    return detail


def _enrich_rows(rows: list) -> list:
    """用 SQLite 标签补全行业/概念/板块，并补推断徽标。"""
    if not rows:
        return rows
    dicts = []
    for r in rows:
        if hasattr(r, "model_dump"):
            dicts.append(r.model_dump())
        elif isinstance(r, dict):
            dicts.append(r)
        else:
            dicts.append(dict(r))
    metas = db.get_stocks_map([d.get("code") for d in dicts if d.get("code")])
    for d in dicts:
        m = metas.get(d.get("code") or "") or {}
        if not d.get("industry"):
            d["industry"] = m.get("industry") or d.get("industry")
        if not d.get("concepts"):
            d["concepts"] = m.get("concepts")
        d["board"] = d.get("board") or m.get("board")
        if d.get("is_st") is None:
            d["is_st"] = m.get("is_st")
        if not d.get("board") or d.get("is_st") is None:
            b, st = infer_board(d.get("code") or "", d.get("name") or "")
            d["board"] = d.get("board") or b
            if d.get("is_st") is None:
                d["is_st"] = st
    return dicts


# ------------------------------------------------------------------ 个股详情
def _merge_stock_detail(code: str, market: Optional[int] = None) -> StockDetail:
    """个股详情：东财快照优先，失败降级腾讯构造（腾讯含盘口/内外盘/委差）"""
    from concurrent.futures import ThreadPoolExecutor
    em = eastmoney.get_client()
    tx = tencent.get_client()

    def _fetch_em():
        try:
            return em.stock_snapshot(code, market)
        except eastmoney.EastMoneyError:
            return None

    def _fetch_tx():
        return tx.fetch_quotes([code])

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_em = pool.submit(_fetch_em)
        f_tx = pool.submit(_fetch_tx)
        snap = f_em.result()
        tx_all = f_tx.result()

    tq = tx_all.get(code if snap is None else snap.code, {})

    if snap is None:
        # 降级：仅用腾讯数据构造
        if not tq or tq.get("price") is None:
            raise HTTPException(status_code=404, detail=f"未找到股票 {code}")
        ob = tq.get("orderbook") or {}
        snap = StockDetail(
            code=code,
            name=tq.get("name") or "",
            price=tq.get("price"),
            prev_close=tq.get("prev_close"),
            open=tq.get("open"),
            high=tq.get("high"),
            low=tq.get("low"),
            change=tq.get("change"),
            change_pct=tq.get("change_pct"),
            amplitude=tq.get("amplitude"),
            volume=tq.get("volume"),
            amount=(tq.get("amount_wan") or 0) * 1e4,
            turnover=tq.get("turnover"),
            volume_ratio=tq.get("volume_ratio"),
            pe=tq.get("pe"),
            pb=tq.get("pb"),
            total_mv=(tq.get("total_mv_yi") or 0) * 1e8,
            float_mv=(tq.get("float_mv_yi") or 0) * 1e8,
            limit_up=tq.get("limit_up"),
            limit_down=tq.get("limit_down"),
            outer=tq.get("outer"),
            inner=tq.get("inner"),
            weicha=tq.get("weicha"),
            avg_price=tq.get("avg_price"),
            time=tq.get("time"),
            orderbook=OrderBook(bid=ob.get("bid", []), ask=ob.get("ask", [])),
            data_source="腾讯",
            fetched_at=time.strftime("%H:%M:%S"),
        )
        return _attach_local_tags(snap)

    ob = tq.get("orderbook") or {}
    detail = snap.model_copy(deep=True)
    if tq:
        detail.name = tq.get("name") or detail.name
        detail.price = tq.get("price") or detail.price
        detail.prev_close = tq.get("prev_close") or detail.prev_close
        detail.open = tq.get("open") or detail.open
        detail.high = tq.get("high") or detail.high
        detail.low = tq.get("low") or detail.low
        detail.change = tq.get("change") or detail.change
        detail.change_pct = tq.get("change_pct") or detail.change_pct
        detail.amplitude = tq.get("amplitude") or detail.amplitude
        detail.turnover = tq.get("turnover") or detail.turnover
        detail.volume_ratio = tq.get("volume_ratio") or detail.volume_ratio
        detail.pe = tq.get("pe") or detail.pe
        detail.pb = tq.get("pb") or detail.pb
        detail.volume = tq.get("volume") or detail.volume
        detail.amount = (tq.get("amount_wan") or 0) * 1e4 or detail.amount
        detail.total_mv = (tq.get("total_mv_yi") or 0) * 1e8 or detail.total_mv
        detail.float_mv = (tq.get("float_mv_yi") or 0) * 1e8 or detail.float_mv
        detail.limit_up = tq.get("limit_up") or detail.limit_up
        detail.limit_down = tq.get("limit_down") or detail.limit_down
        detail.outer = tq.get("outer")
        detail.inner = tq.get("inner")
        detail.weicha = tq.get("weicha")
        detail.avg_price = tq.get("avg_price")
        detail.time = tq.get("time") or detail.time
        detail.orderbook = OrderBook(bid=ob.get("bid", []), ask=ob.get("ask", []))
        detail.data_source = "东财+腾讯"
    else:
        detail.data_source = "东财"
    detail.fetched_at = time.strftime("%H:%M:%S")
    return _attach_local_tags(detail)


