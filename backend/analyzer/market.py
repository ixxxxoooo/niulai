"""大盘概况聚合

性能说明：
- overview：只聚合页面直接展示的数据（指数/涨停池/时间戳），约 0.3~0.5s。
- market_volume：全 A 两市量能（需拉上证+深证 K 线历史，较重），独立接口 + 30s 缓存，
  总览页单独慢轮询，避免每次刷新都触发 K 线请求。
"""
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from ..datasource import eastmoney, tencent
from ..datasource.models import MarketOverview
from . import schedule

# 两市代表指数：上证指数=沪市全部，深证成指=深市全部
_TOTAL_AMOUNT_INDICES = {"000001", "399001"}


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001 - 单源失败不影响大盘概况
        return default


def market_overview() -> MarketOverview:
    """聚合大盘概况：指数、两市成交额、涨跌家数、涨停家数（不含量能，量能走独立接口）"""
    client = eastmoney.get_client()

    # 并发拉取页面直接展示的数据源
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_indices = ex.submit(client.index_quotes)
        f_pool = ex.submit(lambda: client.limit_up_pool(limit=300))
        f_tq = ex.submit(lambda: tencent.get_client().fetch_quotes(["000001"]))

        indices = _safe(lambda: f_indices.result(), [])
        pool = _safe(lambda: f_pool.result(), [])
        tq = _safe(lambda: f_tq.result(), {})

    total_amount: Optional[float] = None
    up = down = flat = 0
    for q in indices:
        if q.code in _TOTAL_AMOUNT_INDICES:
            total_amount = (total_amount or 0) + (q.amount or 0)
            up += q.up_count or 0
            down += q.down_count or 0
            flat += q.flat_count or 0

    limit_up_count = len(pool) if pool else None

    # 数据时间：优先用腾讯行情的更新时间
    quote_time = None
    if tq:
        quote_time = tq.get("000001", {}).get("time")
    if not quote_time:
        quote_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return MarketOverview(
        indices=indices,
        total_amount=total_amount,
        up_count=up,
        down_count=down,
        flat_count=flat,
        limit_up_count=limit_up_count,
        limit_down_count=None,
        index_volume=None,
        is_trading_time=schedule.is_trading_time(),
        quote_time=quote_time,
    )


def market_volume() -> Optional[dict]:
    """全 A 股两市量能：今日两市总成交量 vs 前 5 日均量 → 放量/缩量 + 成交额差值

    需要上证 + 深证日 K 历史（腾讯数据源），返回 None 表示暂不可用。
    """
    client = eastmoney.get_client()
    with ThreadPoolExecutor(max_workers=2) as ex:
        f_k1 = ex.submit(lambda: client.kline(secid="1.000001", period="day", limit=6))
        f_k2 = ex.submit(lambda: client.kline(secid="0.399001", period="day", limit=6))
        k1 = _safe(lambda: f_k1.result())
        k2 = _safe(lambda: f_k2.result())

    v1 = [p["volume"] for p in (k1 or {}).get("points", [])] if k1 else []
    v2 = [p["volume"] for p in (k2 or {}).get("points", [])] if k2 else []
    if len(v1) < 6 or len(v2) < 6:
        return None

    # 两市总成交额（当日）
    indices = _safe(client.index_quotes, [])
    total_amount: Optional[float] = None
    for q in indices:
        if q.code in _TOTAL_AMOUNT_INDICES:
            total_amount = (total_amount or 0) + (q.amount or 0)
    if not total_amount:
        return None

    today_total = v1[-1] + v2[-1]
    avg5_total = (sum(v1[:-1]) + sum(v2[:-1])) / 5.0
    if avg5_total <= 0:
        return None

    ratio = today_total / avg5_total
    diff_amount = total_amount * (1 - 1.0 / ratio) if ratio > 0 else 0.0
    if ratio > 1.05:
        label = "放量"
    elif ratio < 0.95:
        label = "缩量"
    else:
        label = "平量"
    return {
        "ratio": round(ratio, 2), "label": label,
        "diff_amount": round(diff_amount),
        "today_amount": round(total_amount),
    }
