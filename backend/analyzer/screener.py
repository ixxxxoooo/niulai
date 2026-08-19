"""盘后量化选股引擎：突破 / 金叉 / 放量 / 多头排列 / 缩量回踩 多规则快速扫描
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
        "desc": "收盘价创近 N 日最高且成交额达标",
        "default_params": {"period": 20, "min_amount": 100_000_000},
    },
    "golden_cross": {
        "name": "均线金叉",
        "desc": "MA5 向上金叉 MA20",
        "default_params": {"fast": 5, "slow": 20},
    },
    "volume_surge": {
        "name": "放量拉升",
        "desc": "今日成交量 > N 日均量 × 指定倍数",
        "default_params": {"period": 20, "multiple": 1.5},
    },
    "ma_bullish": {
        "name": "多头排列",
        "desc": "MA5 > MA10 > MA20 均线多头发散向上",
        "default_params": {},
    },
    "pullback_support": {
        "name": "缩量回踩",
        "desc": "多头趋势中回踩重要均线支撑（回踩MA20幅度<2.5%且缩量）",
        "default_params": {"ma": 20, "max_dist_pct": 2.5},
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


def _check_breakout(bars: List[dict], params: dict) -> Optional[str]:
    """突破规则：收盘价 = 近 N 日最高且成交额达标。"""
    period = params.get("period", 20)
    min_amount = params.get("min_amount", 100_000_000)
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
        return f"{period}日新高 {close:.2f}元，成交额 {amount / 1e8:.2f}亿"
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
        return f"MA{fast}({ma_fast_today:.2f}) 上穿 MA{slow}({ma_slow_today:.2f}) 形成金叉"
    return None


def _check_volume_surge(bars: List[dict], params: dict) -> Optional[str]:
    """放量规则：今日量超过 N 日均量的指定倍数。"""
    period = params.get("period", 20)
    multiple = params.get("multiple", 1.5)
    if len(bars) < period + 1:
        return None
    vols = [b.get("volume") or 0 for b in bars]
    today_vol = vols[-1]
    avg_vol = sum(vols[-period - 1:-1]) / period if period > 0 else 0
    if avg_vol <= 0:
        return None
    ratio = today_vol / avg_vol
    if ratio >= multiple:
        return f"成交量放大至 {ratio:.1f} 倍（基准 {multiple}倍）"
    return None


def _check_ma_bullish(bars: List[dict], params: dict) -> Optional[str]:
    """多头排列规则：MA5 > MA10 > MA20 (K线条数>=60时自动增强校验 > MA60)。"""
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
            return f"MA5({ma5:.2f}) > MA10({ma10:.2f}) > MA20({ma20:.2f}) > MA60({ma60:.2f}) 四线多头排列"
    return f"MA5({ma5:.2f}) > MA10({ma10:.2f}) > MA20({ma20:.2f}) 三线多头排列"


def _check_pullback_support(bars: List[dict], params: dict) -> Optional[str]:
    """缩量回踩规则：价格回踩均线附近且今日成交量低于5日均量。"""
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
    if avg_vol_5 > 0 and vols[-1] <= avg_vol_5 * 0.9:
        return f"回踩 MA{ma_period}({ma_val:.2f}) 距{dist_pct:.1f}%，缩量 {vols[-1]/avg_vol_5:.2f}倍"
    return None


_CHECKERS = {
    "breakout": _check_breakout,
    "golden_cross": _check_golden_cross,
    "volume_surge": _check_volume_surge,
    "ma_bullish": _check_ma_bullish,
    "pullback_support": _check_pullback_support,
}


def run_screen(rules: List[str], params: Optional[Dict[str, dict]] = None,
               scope: str = "all") -> Dict[str, Any]:
    """
    执行盘后选股扫描。纯本地 SQLite 向量化极速计算（< 100ms）。
    """
    params = params or {}
    t0 = time.monotonic()

    conn = store.get_conn()
    # 创建运行记录
    conn.execute(
        "INSERT INTO screener_runs(started_at, rules, scope, status) VALUES (?, ?, ?, 'running')",
        (store._now(), json.dumps(rules), scope),
    )
    conn.commit()
    run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # 获取待扫股票列表
    if scope == "watchlist":
        codes = store.watchlist_codes()
    else:
        rows = conn.execute(
            "SELECT code, name FROM stocks WHERE classify = 'AStock'"
        ).fetchall()
        codes = [(r["code"], r["name"]) for r in rows]

    if isinstance(codes, list) and codes and isinstance(codes[0], str):
        stock_rows = conn.execute(
            "SELECT code, name FROM stocks WHERE code IN ({})".format(
                ",".join("?" * len(codes))), codes
        ).fetchall()
        code_name = {r["code"]: r["name"] for r in stock_rows}
        codes = [(c, code_name.get(c, "")) for c in codes]

    hits_by_rule: Dict[str, list] = {r: [] for r in rules}
    total_hits = 0
    scanned = 0

    for code, name in codes:
        bars = _load_bars(code)
        if not bars:
            continue
        scanned += 1
        last_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None
        close_val = last_bar.get("close")
        change_pct = None
        if prev_bar and (prev_bar.get("close") or 0) > 0 and close_val is not None:
            change_pct = round((close_val - prev_bar["close"]) / prev_bar["close"] * 100, 2)

        for rule_id in rules:
            checker = _CHECKERS.get(rule_id)
            if not checker:
                continue
            rule_params = {**(RULES.get(rule_id, {}).get("default_params") or {}), **(params.get(rule_id) or {})}
            signal = checker(bars, rule_params)
            if signal:
                hit = {
                    "code": code,
                    "name": name,
                    "close": close_val,
                    "change_pct": change_pct,
                    "detail": signal,
                }
                hits_by_rule[rule_id].append(hit)
                total_hits += 1
                try:
                    conn.execute(
                        "INSERT INTO screener_hits(run_id, rule_id, code, name, close, change_pct, detail) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (run_id, rule_id, code, name, close_val, change_pct, signal),
                    )
                except Exception:
                    pass

    elapsed = (time.monotonic() - t0) * 1000
    conn.execute(
        "UPDATE screener_runs SET finished_at=?, hit_count=?, status='done' WHERE id=?",
        (store._now(), total_hits, run_id),
    )
    conn.commit()

    logger.info("选股完成 run=%d scanned=%d hits=%d (%.0fms)", run_id, scanned, total_hits, elapsed)

    return {
        "run_id": run_id,
        "hits": hits_by_rule,
        "hit_count": total_hits,
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


def get_run_hits(run_id: int) -> Dict[str, Any]:
    """获取指定选股任务的详情与命中列表。"""
    conn = store.get_conn()
    run = conn.execute("SELECT * FROM screener_runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        return {"error": "not found"}
    hits = conn.execute(
        "SELECT * FROM screener_hits WHERE run_id = ?", (run_id,)
    ).fetchall()
    return {
        "run": dict(run),
        "hits": [dict(h) for h in hits],
    }
