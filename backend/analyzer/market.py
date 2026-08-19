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
from .. import config
from . import schedule

# 两市代表指数：上证指数=沪市全部，深证成指=深市全部
_TOTAL_AMOUNT_INDICES = {"000001", "399001"}


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001 - 单源失败不影响大盘概况
        return default


def market_overview() -> MarketOverview:
    """聚合大盘概况：指数、两市总成交额、涨跌平家数、涨停/跌停家数（毫秒级轻量接口）

    - 涨跌平家数：直接从东财指数行情（上证指数 + 深证成指）自带的 f104/f105/f106 字段求和获取，无需拉取全市场
    - 涨停/跌停数：复用涨停池/跌停池现成接口数量
    """
    client = eastmoney.get_client()

    # 并发拉取指数、腾讯快照时间、涨跌停池条数（全部使用毫秒级接口，严禁全量分页扫描）
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_indices = ex.submit(client.index_quotes)
        f_tq = ex.submit(lambda: tencent.get_client().fetch_quotes(["000001"]))
        f_zt = ex.submit(lambda: len(client.limit_up_pool(300)))
        f_dt = ex.submit(lambda: len(client.limit_down_pool(300)))

        indices = _safe(lambda: f_indices.result(), [])
        tq = _safe(lambda: f_tq.result(), {})
        limit_up_count = _safe(lambda: f_zt.result(), None)
        limit_down_count = _safe(lambda: f_dt.result(), None)


    total_amount: Optional[float] = None
    up_count = 0
    down_count = 0
    flat_count = 0
    has_stats = False

    for q in indices:
        if q.code in _TOTAL_AMOUNT_INDICES:
            total_amount = (total_amount or 0) + (q.amount or 0)
            if q.up_count is not None:
                up_count += int(q.up_count)
                has_stats = True
            if q.down_count is not None:
                down_count += int(q.down_count)
            if q.flat_count is not None:
                flat_count += int(q.flat_count)

    # 数据时间：优先用腾讯行情的更新时间
    quote_time = None
    if tq:
        quote_time = tq.get("000001", {}).get("time")
    if not quote_time:
        quote_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return MarketOverview(
        indices=indices,
        total_amount=total_amount,
        up_count=up_count if has_stats else None,
        down_count=down_count if has_stats else None,
        flat_count=flat_count if has_stats else None,
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        index_volume=None,
        is_trading_time=schedule.is_trading_time(),
        quote_time=quote_time,
    )



def _fetch_amount_history(symbols: list) -> Optional[dict]:
    """从腾讯 newfqkline 拉指数日K成交额（万元）。

    返回 {symbol: {date: amount_wan}}，amount_wan 为当日成交额（万元）。
    注意：该接口字段为 [日期,开,收,高,低,量,{},涨跌幅,成交额(万),0,0]，
    成交额在索引 8。失败返回 None。
    """
    import httpx

    out = {}
    headers = {"User-Agent": config.USER_AGENT, "Referer": config.TENCENT_REFERER}
    for sym in symbols:
        url = (f"https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get"
               f"?param={sym},day,,,6,qfq")
        try:
            resp = httpx.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            d = resp.json()
        except Exception:
            continue
        node = (((d or {}).get("data") or {}).get(sym)) or {}
        rows = node.get("day") or node.get("qfqday") or []
        seq = {}
        for r in rows:
            if not isinstance(r, list) or len(r) < 9:
                continue
            try:
                amt = float(r[8]) if r[8] else None  # 成交额（万元）
            except (TypeError, ValueError):
                amt = None
            if amt is not None:
                seq[str(r[0])] = amt
        if seq:
            out[sym] = seq
    return out or None


def market_volume() -> Optional[dict]:
    """全 A 股两市量能：今日两市总成交额 vs 上一交易日成交额 → 放量/缩量

    数据源：腾讯 newfqkline（含历史成交额，万）。东财指数 K 线被服务端断连，
    且成交量(手)在高低价股切换时会失真（8/17 成交额放量但手数缩量），故用成交额判断。
    按共有交易日严格对齐沪深两市数据，返回 None 表示暂不可用。
    """
    # 两市代表：上证指数(沪市全部) + 深证成指(深市全部，与深证综指同量值)
    hist = _fetch_amount_history(["sh000001", "sz399001"])
    if not hist:
        return None
    sh_map = hist.get("sh000001") or {}
    sz_map = hist.get("sz399001") or {}
    common_dates = sorted(set(sh_map.keys()) & set(sz_map.keys()))
    if len(common_dates) < 2:
        return None

    today_date = common_dates[-1]
    prev_date = common_dates[-2]
    today_wan = sh_map[today_date] + sz_map[today_date]
    prev_wan = sh_map[prev_date] + sz_map[prev_date]
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

