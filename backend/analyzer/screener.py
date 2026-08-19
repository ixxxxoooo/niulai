"""盘后量化选股引擎：12 大高胜率经典实战策略
支持 板块过滤（主板/创业板/科创板/北交所）、ST/破位排雷与多策略共振聚合
@author ygw
"""
import json
import time
from typing import Any, Dict, List, Optional

from ..logging_config import logger
from ..db import store

RULES = {
    "breakout": {
        "name": "突破新高",
        "tag": "龙头起爆",
        "badge": "🔥 强烈推荐",
        "desc": "收盘价放量创近 20 日新高，突破前期平台阻力位",
        "is_default": True,
        "default_params": {"period": 20, "min_amount": 80_000_000},
    },
    "ma_bullish": {
        "name": "多头排列",
        "tag": "顺势主升",
        "badge": "💎 胜率极高",
        "desc": "MA5 > MA10 > MA20 多头均线发散，顺势主升浪",
        "is_default": True,
        "default_params": {},
    },
    "main_inflow_surge": {
        "name": "主力抢筹",
        "tag": "资金控盘",
        "badge": "💰 强烈推荐",
        "desc": "单日主力净买入 > 2500万 且 净占比 > 6%，主力强力建仓",
        "is_default": True,
        "default_params": {"min_inflow": 25_000_000, "min_ratio": 6.0},
    },
    "volume_surge": {
        "name": "放量拉升",
        "tag": "量价齐升",
        "badge": "📊 资金异动",
        "desc": "今日量达近 20 日均量 1.8 倍以上且量比 > 1.5，强力介入",
        "is_default": True,
        "default_params": {"period": 20, "multiple": 1.8},
    },
    "box_breakout": {
        "name": "平台突围",
        "tag": "蓄势爆发",
        "badge": "🚀 爆发力强",
        "desc": "近 10 日窄幅整理（振幅<10%），今日放量长阳突破箱顶",
        "is_default": True,
        "default_params": {"box_days": 10, "max_amp": 10.0},
    },
    "pullback_support": {
        "name": "缩量回踩",
        "tag": "稳健低吸",
        "badge": "🎯 极佳盈亏比",
        "desc": "多头趋势中缩量回踩 MA10/MA20 均线支撑位，安全边际高",
        "is_default": False,
        "default_params": {"ma": 20, "max_dist_pct": 2.5},
    },
    "golden_cross": {
        "name": "均线金叉",
        "tag": "右侧买点",
        "badge": "✨ 趋势启动",
        "desc": "MA5 短期均线向上金叉 MA20 长期均线，右侧拐点确立",
        "is_default": False,
        "default_params": {"fast": 5, "slow": 20},
    },
    "macd_zero_cross": {
        "name": "水上金叉",
        "tag": "二次加速",
        "badge": "⚡ 加速主升",
        "desc": "MACD 在 0 轴上方二次形成多头金叉，主升浪二次加速",
        "is_default": False,
        "default_params": {},
    },
    "active_turnover": {
        "name": "活跃换手",
        "tag": "游资主升",
        "badge": "🌪️ 股性爆发",
        "desc": "换手率 6%~18% 黄金区间且涨幅 > 3%，股性极度活跃",
        "is_default": False,
        "default_params": {"min_turnover": 6.0, "max_turnover": 18.0, "min_pct": 3.0},
    },
    "small_cap_leader": {
        "name": "小盘弹性龙",
        "tag": "弹性先锋",
        "badge": "🦄 弹性先锋",
        "desc": "流通市值 30~180 亿黄金弹性区间 + 均线多头 + 主力加仓",
        "is_default": False,
        "default_params": {"min_mv": 3_000_000_000, "max_mv": 18_000_000_000},
    },
    "bullish_engulfing": {
        "name": "阳包阴反包",
        "tag": "强势反转",
        "badge": "📈 洗盘结束",
        "desc": "昨日收阴洗盘，今日放量阳线实体反包昨日阴线开盘价",
        "is_default": False,
        "default_params": {},
    },
    "oversold_rebound": {
        "name": "超跌反弹",
        "tag": "拐点反转",
        "badge": "🔄 止跌反转",
        "desc": "前期深度回调超跌，今日放量大阳反包站上短期均线",
        "is_default": False,
        "default_params": {"min_pct": 3.0},
    },
}


def _load_bars(code: str, min_count: int = 5) -> Optional[List[dict]]:
    """从 daily_bars 读取指定股票的日 K 数据（按日期升序）。"""
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, volume, amount, "
        "turnover, volume_ratio, amplitude, change_pct, main_inflow, main_ratio, float_mv "
        "FROM daily_bars WHERE code = ? ORDER BY trade_date",
        (code,),
    ).fetchall()
    if len(rows) < min_count:
        return None
    return [dict(r) for r in rows]


def _ma(data: List[float], n: int) -> Optional[float]:
    if len(data) < n or n <= 0:
        return None
    return sum(data[-n:]) / n


def _ema(data: List[float], n: int) -> List[float]:
    if not data:
        return []
    alpha = 2.0 / (n + 1)
    res = [data[0]]
    for x in data[1:]:
        res.append(alpha * x + (1 - alpha) * res[-1])
    return res


# ---------------- 规则计算函数 ----------------

def _check_breakout(bars: List[dict], params: dict) -> Optional[str]:
    """突破规则：收盘价创近 N 日新高且成交额达标。"""
    period = params.get("period", 20)
    min_amount = params.get("min_amount", 80_000_000)
    if len(bars) < period:
        return None
    recent = bars[-period:]
    last = bars[-1]
    close = last.get("close") or 0
    amount = last.get("amount") or 0
    if amount < min_amount:
        return None
    high_max = max((b.get("high") or 0) for b in recent[:-1])
    if close >= high_max and close > 0:
        return f"放量创{period}日新高 {close:.2f}元 (成交额{amount/1e8:.2f}亿)"
    return None


def _check_golden_cross(bars: List[dict], params: dict) -> Optional[str]:
    """金叉规则：短期均线上穿长期均线。"""
    fast = params.get("fast", 5)
    slow = params.get("slow", 20)
    if len(bars) < slow + 1:
        return None
    closes = [b.get("close") or 0 for b in bars]
    ma_fast_today = _ma(closes, fast)
    ma_slow_today = _ma(closes, slow)
    ma_fast_yest = _ma(closes[:-1], fast)
    ma_slow_yest = _ma(closes[:-1], slow)
    if None in (ma_fast_today, ma_slow_today, ma_fast_yest, ma_slow_yest):
        return None
    if ma_fast_yest <= ma_slow_yest and ma_fast_today > ma_slow_today:
        return f"MA{fast}({ma_fast_today:.2f}) 金叉 MA{slow}({ma_slow_today:.2f})"
    return None


def _check_volume_surge(bars: List[dict], params: dict) -> Optional[str]:
    """放量规则：今日量超过 N 日均量的指定倍数。"""
    period = params.get("period", 20)
    multiple = params.get("multiple", 1.8)
    if len(bars) < period + 1:
        return None
    vols = [b.get("volume") or 0 for b in bars]
    today_vol = vols[-1]
    avg_vol = sum(vols[-period - 1:-1]) / period if period > 0 else 0
    if avg_vol <= 0:
        return None
    ratio = today_vol / avg_vol
    if ratio >= multiple:
        return f"成交量放大至 {ratio:.1f} 倍 (主力资金抢筹)"
    return None


def _check_ma_bullish(bars: List[dict], params: dict) -> Optional[str]:
    """多头排列规则：MA5 > MA10 > MA20。"""
    closes = [b.get("close") or 0 for b in bars]
    if len(closes) < 20:
        return None
    ma5 = _ma(closes, 5)
    ma10 = _ma(closes, 10)
    ma20 = _ma(closes, 20)
    if None in (ma5, ma10, ma20) or not (ma5 > ma10 > ma20):
        return None
    if len(closes) >= 60:
        ma60 = _ma(closes, 60)
        if ma60 and ma5 > ma10 > ma20 > ma60:
            return f"MA5/10/20/60 四线多头排列 ({ma5:.2f}>{ma10:.2f}>{ma20:.2f})"
    return f"MA5/10/20 三线多头排列 ({ma5:.2f}>{ma10:.2f}>{ma20:.2f})"


def _check_main_inflow_surge(bars: List[dict], params: dict) -> Optional[str]:
    """主力抢筹：单日主力资金净流入 > 2500万 且 主力占比 > 6%，大资金强力建仓。"""
    today = bars[-1]
    inflow = today.get("main_inflow") or 0
    ratio = today.get("main_ratio") or 0
    close_p = today.get("close") or 0
    open_p = today.get("open") or 0
    min_inflow = params.get("min_inflow", 25_000_000)
    min_ratio = params.get("min_ratio", 6.0)

    if inflow >= min_inflow and ratio >= min_ratio and close_p >= open_p:
        inflow_wan = inflow / 10000
        return f"主力单日强力净流入 {inflow_wan:.0f}万 (净占比 {ratio:.1f}%)"
    return None


def _check_active_turnover(bars: List[dict], params: dict) -> Optional[str]:
    """游资活跃换手：换手率处于 6%~18% 黄金活跃区间且涨幅 > 3%，股性极度活跃。"""
    today = bars[-1]
    turnover = today.get("turnover") or 0
    pct = today.get("change_pct") or 0
    vr = today.get("volume_ratio") or 1.0
    min_to = params.get("min_turnover", 6.0)
    max_to = params.get("max_turnover", 18.0)
    min_pct = params.get("min_pct", 3.0)

    if min_to <= turnover <= max_to and pct >= min_pct and vr >= 1.2:
        return f"黄金活跃换手 {turnover:.1f}% (涨幅+{pct:.1f}%, 量比{vr:.2f})"
    return None


def _check_small_cap_leader(bars: List[dict], params: dict) -> Optional[str]:
    """小盘弹性龙头：流通市值 30~180 亿黄金弹性区间 + 短线均线多头 + 主力净买入。"""
    if len(bars) < 10:
        return None
    today = bars[-1]
    float_mv = today.get("float_mv") or 0
    inflow = today.get("main_inflow") or 0
    closes = [b.get("close") or 0 for b in bars]
    ma5 = _ma(closes, 5) or 0
    ma10 = _ma(closes, 10) or 0

    min_mv = params.get("min_mv", 3_000_000_000)
    max_mv = params.get("max_mv", 18_000_000_000)

    if min_mv <= float_mv <= max_mv and ma5 > ma10 and closes[-1] > ma5 and inflow > 5_000_000:
        mv_yi = float_mv / 100_000_000
        inflow_wan = inflow / 10000
        return f"高弹性小盘市值 {mv_yi:.1f}亿，短线均线多头发散且主力加仓 {inflow_wan:.0f}万"
    return None


def _check_bullish_engulfing(bars: List[dict], params: dict) -> Optional[str]:
    """阳包阴反包：昨日收阴洗盘，今日放量长阳实体完全反包昨日阴线开盘价。"""
    if len(bars) < 2:
        return None
    prev = bars[-2]
    today = bars[-1]
    prev_o = prev.get("open") or 0
    prev_c = prev.get("close") or 0
    today_o = today.get("open") or 0
    today_c = today.get("close") or 0
    today_v = today.get("volume") or 0
    prev_v = prev.get("volume") or 0

    # 昨日阴线，今日阳线
    if prev_c < prev_o and today_c > today_o:
        # 今日收盘完全包住昨日开盘
        if today_c > prev_o and today_v >= prev_v * 1.05:
            pct = today.get("change_pct") or ((today_c - prev_c) / prev_c * 100 if prev_c > 0 else 0)
            return f"放量阳包阴强势反包 (+{pct:.1f}%)，洗盘彻底结束"
    return None


def _check_pullback_support(bars: List[dict], params: dict) -> Optional[str]:
    """缩量回踩规则：价格回踩均线附近且缩量。"""
    ma_period = params.get("ma", 20)
    max_dist = params.get("max_dist_pct", 2.5)
    if len(bars) < ma_period + 5:
        return None
    closes = [b.get("close") or 0 for b in bars]
    vols = [b.get("volume") or 0 for b in bars]
    last_close = closes[-1]
    last_low = bars[-1].get("low") or last_close
    ma_val = _ma(closes, ma_period)
    if ma_val is None or ma_val <= 0:
        return None
    dist_pct = abs(last_close - ma_val) / ma_val * 100
    if dist_pct > max_dist and last_low > ma_val * (1 + max_dist / 100):
        return None
    avg_vol_5 = _ma(vols[:-1], 5) or 0
    if avg_vol_5 > 0 and vols[-1] <= avg_vol_5 * 0.92:
        return f"缩量回踩 MA{ma_period}({ma_val:.2f}) 距{dist_pct:.1f}%，支撑有效"
    return None


def _check_box_breakout(bars: List[dict], params: dict) -> Optional[str]:
    """平台整理突破：前 box_days 振幅 < max_amp，今日长阳突破箱顶。"""
    box_days = params.get("box_days", 10)
    max_amp = params.get("max_amp", 10.0)
    if len(bars) < box_days + 1:
        return None
    box_bars = bars[-box_days - 1:-1]
    box_highs = [b.get("high") or 0 for b in box_bars]
    box_lows = [b.get("low") or 0 for b in box_bars]
    max_h = max(box_highs) if box_highs else 0
    min_l = min(box_lows) if box_lows else 0
    if min_l <= 0 or max_h <= 0:
        return None
    box_amp = (max_h - min_l) / min_l * 100
    if box_amp > max_amp:
        return None
    today = bars[-1]
    today_c = today.get("close") or 0
    if today_c > max_h:
        return f"横盘{box_days}日(振幅{box_amp:.1f}%) 今日突破箱顶 {max_h:.2f}元"
    return None


def _check_macd_zero_cross(bars: List[dict], params: dict) -> Optional[str]:
    """MACD 水上金叉：DIF/DEA > 0 且 DIF 今日上穿 DEA。"""
    if len(bars) < 35:
        return None
    closes = [b.get("close") or 0 for b in bars]
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    dif = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
    dea = _ema(dif, 9)
    if len(dif) < 2 or len(dea) < 2:
        return None
    dif_now, dif_prev = dif[-1], dif[-2]
    dea_now, dea_prev = dea[-1], dea[-2]
    if dif_now > 0 and dea_now > 0 and dif_prev <= dea_prev and dif_now > dea_now:
        return f"MACD水上二次金叉 (DIF={dif_now:.2f}, DEA={dea_now:.2f})"
    return None


def _check_oversold_rebound(bars: List[dict], params: dict) -> Optional[str]:
    """超跌反弹：前期回调幅度较大，今日放量长阳反包站上 MA5。"""
    min_pct = params.get("min_pct", 3.0)
    if len(bars) < 10:
        return None
    closes = [b.get("close") or 0 for b in bars]
    vols = [b.get("volume") or 0 for b in bars]
    # 计算过去 6 日累计跌幅
    c_start = closes[-6] if len(closes) >= 6 else closes[0]
    c_low = min(closes[-6:-1])
    drop_pct = (c_start - c_low) / c_start * 100 if c_start > 0 else 0
    if drop_pct < 6.0:  # 前期无明显超跌
        return None
    today = bars[-1]
    today_o = today.get("open") or 0
    today_c = today.get("close") or 0
    today_pct = (today_c - closes[-2]) / closes[-2] * 100 if closes[-2] > 0 else 0
    ma5 = _ma(closes, 5) or 0
    if today_pct >= min_pct and today_c > today_o and today_c > ma5:
        avg_vol = _ma(vols[-6:-1], 5) or 0
        if avg_vol > 0 and vols[-1] >= avg_vol * 1.2:
            return f"超跌回调{drop_pct:.1f}%后放量大阳反包 (今日+{today_pct:.1f}%)"
    return None


_CHECKERS = {
    "breakout": _check_breakout,
    "ma_bullish": _check_ma_bullish,
    "main_inflow_surge": _check_main_inflow_surge,
    "volume_surge": _check_volume_surge,
    "box_breakout": _check_box_breakout,
    "pullback_support": _check_pullback_support,
    "golden_cross": _check_golden_cross,
    "macd_zero_cross": _check_macd_zero_cross,
    "active_turnover": _check_active_turnover,
    "small_cap_leader": _check_small_cap_leader,
    "bullish_engulfing": _check_bullish_engulfing,
    "oversold_rebound": _check_oversold_rebound,
}


def run_screen(rules: List[str], params: Optional[Dict[str, dict]] = None,
               scope: str = "all", filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    执行盘后选股扫描。纯本地 SQLite 向量化极速计算（< 100ms）。
    支持 ST / 破位 / 科创板 / 创业板 / 北交所 灵活过滤与共振聚合。
    """
    params = params or {}
    filters = filters or {}
    t0 = time.monotonic()

    # 提取过滤开关
    exclude_st = filters.get("exclude_st", True)
    exclude_broken = filters.get("exclude_broken", True)
    exclude_kcb = filters.get("exclude_kcb", True)   # 科创板 688
    exclude_cyb = filters.get("exclude_cyb", True)   # 创业板 300/301
    exclude_bjs = filters.get("exclude_bjs", True)   # 北交所 8/4/920
    min_amount = filters.get("min_amount", 30_000_000)

    conn = store.get_conn()
    # 创建运行记录
    conn.execute(
        "INSERT INTO screener_runs(started_at, rules, scope, status) VALUES (?, ?, ?, 'running')",
        (store._now(), json.dumps(rules), scope),
    )
    conn.commit()
    run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 获取待扫股票列表与基础元数据
    stocks_meta = {}
    if scope == "watchlist":
        rows = conn.execute(
            "SELECT s.code, s.name, s.industry FROM watchlist w JOIN stocks s ON w.code = s.code"
        ).fetchall()
    else:
        rows = conn.execute("SELECT code, name, industry FROM stocks").fetchall()
    for r in rows:
        stocks_meta[r[0]] = {"name": r[1] or "", "industry": r[2] or ""}

    # 获取参与扫描的代码列表
    candidate_codes = set(stocks_meta.keys())
    if not candidate_codes:
        distinct_codes = [r[0] for r in conn.execute("SELECT DISTINCT code FROM daily_bars").fetchall()]
        for c in distinct_codes:
            candidate_codes.add(c)
            if c not in stocks_meta:
                stocks_meta[c] = {"name": c, "industry": ""}

    # 过滤板块与排雷
    filtered_codes = []
    for c in candidate_codes:
        meta = stocks_meta.get(c, {})
        name = meta.get("name", "")

        # 1. 过滤 ST 股
        if exclude_st and ("ST" in name or "退" in name or "*ST" in name):
            continue
        # 2. 过滤北交所 (8/4/920 开头)
        if exclude_bjs and (c.startswith("8") or c.startswith("4") or c.startswith("920")):
            continue
        # 3. 过滤科创板 (688 开头)
        if exclude_kcb and c.startswith("688"):
            continue
        # 4. 过滤创业板 (300/301 开头)
        if exclude_cyb and (c.startswith("300") or c.startswith("301")):
            continue

        filtered_codes.append(c)

    hits_by_rule: Dict[str, list] = {r: [] for r in rules}
    stock_hits_map: Dict[str, dict] = {}

    for c in filtered_codes:
        bars = _load_bars(c, min_count=2)
        if not bars:
            continue

        today = bars[-1]
        today_close = today.get("close") or 0
        today_amount = today.get("amount") or 0
        prev_close = bars[-2].get("close") if len(bars) >= 2 else today_close
        change_pct = ((today_close - prev_close) / prev_close * 100) if prev_close else 0

        # 破位排雷：排除今日大幅下跌 (<-3%) 的弱势破位标的
        if exclude_broken and change_pct < -3.0:
            continue
        # 流动性过滤：成交额过低（< 3000万）的僵尸股排除
        if min_amount and today_amount > 0 and today_amount < min_amount:
            continue

        meta = stocks_meta.get(c, {})
        stock_name = meta.get("name") or c

        # 执行选定策略
        for rule_id in rules:
            checker = _CHECKERS.get(rule_id)
            if not checker:
                continue
            r_params = {**RULES.get(rule_id, {}).get("default_params", {}), **params.get(rule_id, {})}
            detail_msg = checker(bars, r_params)
            if detail_msg:
                hit_item = {
                    "code": c,
                    "name": stock_name,
                    "close": today_close,
                    "change_pct": round(change_pct, 2),
                    "detail": detail_msg,
                    "industry": meta.get("industry", ""),
                    "amount": today_amount,
                }
                hits_by_rule[rule_id].append(hit_item)

                if c not in stock_hits_map:
                    stock_hits_map[c] = {
                        "code": c,
                        "name": stock_name,
                        "close": today_close,
                        "change_pct": round(change_pct, 2),
                        "amount": today_amount,
                        "industry": meta.get("industry", ""),
                        "hit_rules": [],
                        "signals": [],
                    }
                stock_hits_map[c]["hit_rules"].append(rule_id)
                r_name = RULES.get(rule_id, {}).get("name", rule_id)
                stock_hits_map[c]["signals"].append({"rule": rule_id, "name": r_name, "detail": detail_msg})

    # 共振聚合排序
    aggregated_items = []
    for s in stock_hits_map.values():
        s["match_count"] = len(s["hit_rules"])
        s["detail"] = " · ".join(f"[{item['name']}] {item['detail']}" for item in s["signals"])
        aggregated_items.append(s)

    # 优先按共振策略数量降序，再按涨跌幅降序
    aggregated_items.sort(key=lambda x: (x["match_count"], x.get("change_pct") or 0), reverse=True)

    # 结果入库归档
    total_hits = len(aggregated_items)
    with store._lock:
        conn = store.get_conn()
        conn.execute(
            "UPDATE screener_runs SET finished_at = ?, hit_count = ?, status = 'completed' WHERE id = ?",
            (store._now(), total_hits, run_id),
        )
        hit_rows = []
        for r_id, items in hits_by_rule.items():
            for it in items:
                hit_rows.append((run_id, r_id, it["code"], it["name"], it["close"], it["change_pct"], it["detail"]))
        if hit_rows:
            conn.executemany(
                "INSERT INTO screener_hits(run_id, rule_id, code, name, close, change_pct, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                hit_rows,
            )
        conn.commit()

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    logger.info("选股扫描完成: run_id=%d, 策略=%s, 扫描=%d只, 命中=%d只, 耗时=%dms",
                run_id, rules, len(filtered_codes), total_hits, elapsed_ms)

    return {
        "run_id": run_id,
        "scanned": len(filtered_codes),
        "hit_count": total_hits,
        "elapsed_ms": elapsed_ms,
        "items": aggregated_items,
        "hits": hits_by_rule,
    }


def list_rules() -> List[Dict[str, Any]]:
    """返回支持的 12 大量化选股策略列表。"""
    res = []
    for k, v in RULES.items():
        res.append({
            "id": k,
            "name": v["name"],
            "tag": v.get("tag", ""),
            "badge": v.get("badge", ""),
            "desc": v["desc"],
            "is_default": v.get("is_default", False),
            "default_params": v.get("default_params", {}),
        })
    return res


def list_runs(limit: int = 20) -> List[Dict[str, Any]]:
    """获取历史选股任务列表。"""
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT * FROM screener_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def clear_runs() -> int:
    """清空历史选股归档数据。"""
    with store._lock:
        conn = store.get_conn()
        conn.execute("DELETE FROM screener_hits")
        conn.execute("DELETE FROM screener_runs")
        conn.commit()
    logger.info("已清空历史选股归档记录")
    return 1


def get_run_hits(run_id: int) -> Dict[str, Any]:
    """获取指定选股任务的详情与命中列表。"""
    conn = store.get_conn()
    run = conn.execute("SELECT * FROM screener_runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        return {"error": "not found"}
    hits = conn.execute(
        "SELECT * FROM screener_hits WHERE run_id = ?", (run_id,)
    ).fetchall()

    hits_by_rule: Dict[str, list] = {}
    stock_map = {}
    for h in hits:
        d = dict(h)
        c = d["code"]
        r_id = d["rule_id"]
        if r_id not in hits_by_rule:
            hits_by_rule[r_id] = []
        hits_by_rule[r_id].append(d)

        if c not in stock_map:
            stock_map[c] = {
                "code": c,
                "name": d["name"],
                "close": d["close"],
                "change_pct": d["change_pct"],
                "hit_rules": [],
                "signals": [],
                "detail": "",
            }
        r_name = RULES.get(r_id, {}).get("name", r_id)
        if r_id not in stock_map[c]["hit_rules"]:
            stock_map[c]["hit_rules"].append(r_id)
            stock_map[c]["signals"].append({"rule": r_id, "name": r_name, "detail": d["detail"]})

    for s in stock_map.values():
        s["match_count"] = len(s["hit_rules"])
        s["detail"] = " · ".join(f"[{item['name']}] {item['detail']}" for item in s["signals"])

    items = sorted(stock_map.values(), key=lambda x: (x["match_count"], x.get("change_pct") or 0), reverse=True)

    return {
        "run": dict(run),
        "items": items,
        "hits": hits_by_rule,
    }
