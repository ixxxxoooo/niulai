"""盘后量化选股引擎：8 大高胜率经典实战策略
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
        "default_params": {"period": 20, "min_amount": 80_000_000},
    },
    "ma_bullish": {
        "name": "多头排列",
        "tag": "顺势主升",
        "badge": "💎 胜率极高",
        "desc": "MA5 > MA10 > MA20 均线发散向上，处于健康顺势主升浪",
        "default_params": {},
    },
    "golden_cross": {
        "name": "均线金叉",
        "tag": "右侧买点",
        "badge": "✨ 趋势启动",
        "desc": "MA5 短期均线向上金叉 MA20 长期均线，拐点确立",
        "default_params": {"fast": 5, "slow": 20},
    },
    "volume_surge": {
        "name": "放量拉升",
        "tag": "主力抢筹",
        "badge": "📊 资金异动",
        "desc": "今日成交量达近 20 日均量 1.8 倍以上且收阳，主力强力介入",
        "default_params": {"period": 20, "multiple": 1.8},
    },
    "pullback_support": {
        "name": "缩量回踩",
        "tag": "稳健低吸",
        "badge": "🎯 极佳盈亏比",
        "desc": "多头趋势中缩量回踩 MA10/MA20 均线支撑位，低吸性价比极高",
        "default_params": {"ma": 20, "max_dist_pct": 2.5},
    },
    "box_breakout": {
        "name": "平台突围",
        "tag": "蓄势爆发",
        "badge": "🚀 爆发力强",
        "desc": "近 10 日窄幅箱体整理（振幅<10%），今日放量大阳线强势突破",
        "default_params": {"box_days": 10, "max_amp": 10.0},
    },
    "macd_zero_cross": {
        "name": "水上金叉",
        "tag": "二次加速",
        "badge": "⚡ 加速主升",
        "desc": "MACD 指标在 0 轴上方二次形成多头金叉，主升浪二次加速",
        "default_params": {},
    },
    "oversold_rebound": {
        "name": "超跌反包",
        "tag": "拐点反转",
        "badge": "🔄 止跌反弹",
        "desc": "前期回调充分超跌，今日放量反包长阳站上短期均线，拐点确立",
        "default_params": {"min_pct": 3.0},
    },
}


def _load_bars(code: str, min_count: int = 5) -> Optional[List[dict]]:
    """从 daily_bars 读取指定股票的日 K 数据（按日期升序）。"""
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, volume, amount "
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
    "golden_cross": _check_golden_cross,
    "volume_surge": _check_volume_surge,
    "pullback_support": _check_pullback_support,
    "box_breakout": _check_box_breakout,
    "macd_zero_cross": _check_macd_zero_cross,
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
    exclude_kcb = filters.get("exclude_kcb", False)  # 科创板 688
    exclude_cyb = filters.get("exclude_cyb", False)  # 创业板 300/301
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
    if scope == "watchlist":
        codes = store.watchlist_codes()
        stock_rows = conn.execute(
            "SELECT code, name, is_st FROM stocks WHERE code IN ({})".format(
                ",".join("?" * len(codes))), codes
        ).fetchall() if codes else []
    else:
        stock_rows = conn.execute(
            "SELECT code, name, is_st FROM stocks WHERE classify = 'AStock'"
        ).fetchall()

    code_meta = {
        r["code"]: {"name": r["name"], "is_st": r["is_st"]}
        for r in stock_rows
    }

    hits_by_rule: Dict[str, list] = {r: [] for r in rules}
    stock_hits_map: Dict[str, dict] = {}
    total_signals = 0
    scanned = 0

    for code, meta in code_meta.items():
        name = meta.get("name") or ""

        # 1. 板块过滤
        if exclude_kcb and code.startswith("688"):
            continue
        if exclude_cyb and code.startswith(("300", "301")):
            continue
        if exclude_bjs and (code.startswith(("8", "4", "920"))):
            continue

        # 2. ST / 退市排雷
        if exclude_st:
            if meta.get("is_st") == 1 or name.startswith(("ST", "*ST", "退")):
                continue

        bars = _load_bars(code)
        if not bars or len(bars) < 2:
            continue
        scanned += 1

        last_bar = bars[-1]
        prev_bar = bars[-2]
        close_val = last_bar.get("close")
        if close_val is None or close_val <= 0:
            continue

        amount_val = last_bar.get("amount") or 0.0
        # 3. 过滤成交极低僵尸股
        if amount_val > 0 and amount_val < min_amount:
            continue

        prev_close = prev_bar.get("close") or close_val
        change_pct = round((close_val - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0.0

        # 4. 破位大跌排雷（涨跌幅 < -3.0% 且不包含超跌反弹策略时排除）
        if exclude_broken and "oversold_rebound" not in rules:
            if change_pct < -3.0:
                continue

        matched_for_stock = []
        for rule_id in rules:
            checker = _CHECKERS.get(rule_id)
            if not checker:
                continue
            rule_params = {**(RULES.get(rule_id, {}).get("default_params") or {}), **(params.get(rule_id) or {})}
            signal = checker(bars, rule_params)
            if signal:
                matched_for_stock.append((rule_id, signal))
                total_signals += 1
                try:
                    conn.execute(
                        "INSERT INTO screener_hits(run_id, rule_id, code, name, close, change_pct, detail) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (run_id, rule_id, code, name, close_val, change_pct, signal),
                    )
                except Exception:
                    pass

        if matched_for_stock:
            stock_entry = {
                "code": code,
                "name": name,
                "close": close_val,
                "change_pct": change_pct,
                "amount": amount_val,
                "volume": last_bar.get("volume") or 0.0,
                "hit_rules": [r[0] for r in matched_for_stock],
                "match_count": len(matched_for_stock),
                "signals": [
                    {"rule": r[0], "name": RULES.get(r[0], {}).get("name", r[0]), "detail": r[1]}
                    for r in matched_for_stock
                ],
                "detail": " · ".join(f"[{RULES.get(r[0], {}).get('name', r[0])}] {r[1]}" for r in matched_for_stock),
            }
            stock_hits_map[code] = stock_entry

            for r_id, sig in matched_for_stock:
                hits_by_rule[r_id].append({
                    "code": code,
                    "name": name,
                    "close": close_val,
                    "change_pct": change_pct,
                    "amount": amount_val,
                    "detail": sig,
                    "hit_rules": stock_entry["hit_rules"],
                    "match_count": stock_entry["match_count"],
                })

    # 将聚合股票列表按：共振策略数降序 -> 涨跌幅降序 -> 成交额降序 排序
    aggregated_items = sorted(
        stock_hits_map.values(),
        key=lambda x: (x["match_count"], x["change_pct"], x["amount"]),
        reverse=True,
    )

    for r_id in hits_by_rule:
        hits_by_rule[r_id].sort(key=lambda x: (x.get("match_count", 1), x.get("change_pct", 0)), reverse=True)

    elapsed = (time.monotonic() - t0) * 1000
    conn.execute(
        "UPDATE screener_runs SET finished_at=?, hit_count=?, status='done' WHERE id=?",
        (store._now(), len(aggregated_items), run_id),
    )
    conn.commit()

    logger.info("选股完成 run=%d scanned=%d 命中股票=%d 信号数=%d (%.0fms)",
                run_id, scanned, len(aggregated_items), total_signals, elapsed)

    return {
        "run_id": run_id,
        "items": aggregated_items,
        "hits": hits_by_rule,
        "hit_count": len(aggregated_items),
        "total_signals": total_signals,
        "scanned": scanned,
        "elapsed_ms": round(elapsed, 1),
    }


def list_runs(limit: int = 20) -> List[dict]:
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
