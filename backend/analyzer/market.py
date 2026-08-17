"""大盘概况聚合

性能说明：
- overview：只聚合页面直接展示的数据（指数/涨停池/时间戳），约 0.3~0.5s。
- market_volume：全 A 两市量能（需拉上证+深证 K 线历史，较重），独立接口 + 30s 缓存，
  总览页单独慢轮询，避免每次刷新都触发 K 线请求。
"""
import datetime
import json
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
    """聚合大盘概况：指数、沪深京三市成交额、涨跌家数、涨停家数（不含量能，量能走独立接口）"""
    client = eastmoney.get_client()

    # 并发拉取页面直接展示的数据源
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_indices = ex.submit(client.index_quotes)
        f_pool = ex.submit(lambda: client.limit_up_pool(limit=300))
        f_tq = ex.submit(lambda: tencent.get_client().fetch_quotes(["000001"]))
        # 北证50：通达信/同花顺涨跌家数为沪深京三市口径，需补北交所
        f_bj = ex.submit(lambda: client.index_quotes(["0.899050"]))

        indices = _safe(lambda: f_indices.result(), [])
        pool = _safe(lambda: f_pool.result(), [])
        tq = _safe(lambda: f_tq.result(), {})
        bj = _safe(lambda: f_bj.result(), [])

    total_amount: Optional[float] = None
    up = down = flat = 0
    for q in indices:
        if q.code in _TOTAL_AMOUNT_INDICES:
            total_amount = (total_amount or 0) + (q.amount or 0)
            up += q.up_count or 0
            down += q.down_count or 0
            flat += q.flat_count or 0
    # 北交所（北证50 的涨跌家数即全北交所，东财对同市场指数返回同一份数据）
    for q in bj:
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


def _fetch_amount_history(symbols: list) -> Optional[dict]:
    """从腾讯 newfqkline 拉指数日K成交额（万元）。

    返回 {symbol: [(date, amount_wan), ...]}，amount_wan 为当日成交额（万元）。
    注意：该接口字段为 [日期,开,收,高,低,量,{},涨跌幅,成交额(万),0,0]，
    成交额在索引 8。失败返回 None。
    """
    import urllib.request

    out = {}
    for sym in symbols:
        url = (f"https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get"
               f"?param={sym},day,,,6,qfq")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                d = json.loads(resp.read().decode("utf-8", "ignore"))
        except Exception:
            continue
        node = (((d or {}).get("data") or {}).get(sym)) or {}
        rows = node.get("day") or node.get("qfqday") or []
        seq = []
        for r in rows:
            if not isinstance(r, list) or len(r) < 9:
                continue
            try:
                amt = float(r[8]) if r[8] else None  # 成交额（万元）
            except (TypeError, ValueError):
                amt = None
            seq.append((str(r[0]), amt))
        if seq:
            out[sym] = seq
    return out or None


def market_volume() -> Optional[dict]:
    """全 A 股两市量能：今日两市总成交额 vs 上一交易日成交额 → 放量/缩量

    数据源：腾讯 newfqkline（含历史成交额，万）。东财指数 K 线被服务端断连，
    且成交量(手)在高低价股切换时会失真（8/17 成交额放量但手数缩量），故用成交额判断。
    返回 None 表示暂不可用。
    """
    # 两市代表：上证指数(沪市全部) + 深证成指(深市全部，与深证综指同量值)
    hist = _fetch_amount_history(["sh000001", "sz399001"])
    if not hist or len(hist.get("sh000001", [])) < 2 or len(hist.get("sz399001", [])) < 2:
        return None

    def _sum_at(idx):
        sh = hist["sh000001"][idx][1]
        sz = hist["sz399001"][idx][1]
        if sh is None or sz is None:
            return None
        return sh + sz  # 万元

    today_wan = _sum_at(-1)
    prev_wan = _sum_at(-2)
    if not today_wan or not prev_wan:
        return None

    # 若今日数据落后（如非交易时段最新一条不是今日），取最末有效交易日
    # 并与其前一交易日对比
    today_amount = today_wan * 1e4  # 万元 → 元
    prev_amount = prev_wan * 1e4
    ratio = today_amount / prev_amount if prev_amount > 0 else 0.0

    diff_amount = today_amount - prev_amount
    if ratio > 1.05:
        label = "放量"
    elif ratio < 0.95:
        label = "缩量"
    else:
        label = "平量"
    return {
        "ratio": round(ratio, 2), "label": label,
        "diff_amount": round(diff_amount),
        "today_amount": round(today_amount),
        "prev_amount": round(prev_amount),
    }
