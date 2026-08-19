"""盘后选股引擎：突破 / 金叉 / 放量 三规则扫描
@author ygw
"""
import json
import time
from typing import Any, Dict, List, Optional

from ..logging_config import logger
from ..db import store

RULES = {
    "breakout": {
        "name": "突破",
        "desc": "收盘 = 近 N 日最高且成交额 > 阈值",
        "default_params": {"period": 20, "min_amount": 100_000_000},
    },
    "golden_cross": {
        "name": "金叉",
        "desc": "MA5 上穿 MA20",
        "default_params": {"fast": 5, "slow": 20},
    },
    "volume_surge": {
        "name": "放量",
        "desc": "今日量 > N 日均量 × 倍数",
        "default_params": {"period": 20, "multiple": 1.5},
    },
}


def _load_bars(code: str, min_count: int = 25) -> Optional[List[dict]]:
    """
    从 daily_bars 读取指定股票的日 K 数据。

    参数:
        code: 股票代码
        min_count: 最少需要的数据条数

    返回:
        按日期升序排列的 K 线列表，不足时返回 None
    """
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, volume, amount "
        "FROM daily_bars WHERE code = ? ORDER BY trade_date",
        (code,),
    ).fetchall()
    if len(rows) < min_count:
        return None
    return [dict(r) for r in rows]


def _check_breakout(bars: List[dict], params: dict) -> Optional[str]:
    """
    突破规则：收盘价 = 近 N 日最高且成交额达标。

    参数:
        bars: K 线数据
        params: {"period": 20, "min_amount": 100000000}

    返回:
        命中时返回信号描述，未命中返回 None
    """
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
    high_max = max((b.get("high") or 0) for b in recent)
    if close >= high_max and close > 0:
        return f"{period}日新高 {close:.2f}，成交额 {amount / 1e8:.1f}亿"
    return None


def _check_golden_cross(bars: List[dict], params: dict) -> Optional[str]:
    """
    金叉规则：短期均线上穿长期均线。

    参数:
        bars: K 线数据
        params: {"fast": 5, "slow": 20}

    返回:
        命中时返回信号描述，未命中返回 None
    """
    fast = params.get("fast", 5)
    slow = params.get("slow", 20)
    if len(bars) < slow + 1:
        return None
    closes = [b.get("close") or 0 for b in bars]

    def _ma(data, n):
        if len(data) < n:
            return None
        return sum(data[-n:]) / n

    ma_fast_today = _ma(closes, fast)
    ma_slow_today = _ma(closes, slow)
    ma_fast_yest = _ma(closes[:-1], fast)
    ma_slow_yest = _ma(closes[:-1], slow)
    if None in (ma_fast_today, ma_slow_today, ma_fast_yest, ma_slow_yest):
        return None
    if ma_fast_yest <= ma_slow_yest and ma_fast_today > ma_slow_today:
        return f"MA{fast}({ma_fast_today:.2f}) 上穿 MA{slow}({ma_slow_today:.2f})"
    return None


def _check_volume_surge(bars: List[dict], params: dict) -> Optional[str]:
    """
    放量规则：今日量超过 N 日均量的指定倍数。

    参数:
        bars: K 线数据
        params: {"period": 20, "multiple": 1.5}

    返回:
        命中时返回信号描述，未命中返回 None
    """
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
        return f"量比 {ratio:.1f} 倍（>{multiple}倍）"
    return None


_CHECKERS = {
    "breakout": _check_breakout,
    "golden_cross": _check_golden_cross,
    "volume_surge": _check_volume_surge,
}


def run_screen(rules: List[str], params: Optional[Dict[str, dict]] = None,
               scope: str = "all") -> Dict[str, Any]:
    """
    执行盘后选股扫描。

    参数:
        rules: 规则 ID 列表，如 ["breakout", "golden_cross"]
        params: 每条规则的参数覆盖，如 {"breakout": {"period": 30}}
        scope: "all" 全 A / "watchlist" 仅自选

    返回:
        {
            "run_id": int,
            "hits": {"breakout": [...], "golden_cross": [...]},
            "hit_count": int,
            "elapsed_ms": float
        }
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
            rule_params = {**RULES[rule_id]["default_params"], **(params.get(rule_id) or {})}
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
    """
    获取历史选股任务列表。

    参数:
        limit: 返回条数

    返回:
        任务列表（新→旧）
    """
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT * FROM screener_runs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_run_hits(run_id: int) -> Dict[str, Any]:
    """
    获取某次选股的命中结果。

    参数:
        run_id: 任务 ID

    返回:
        {"run": {...}, "hits": {"rule_id": [...]}}
    """
    conn = store.get_conn()
    run = conn.execute("SELECT * FROM screener_runs WHERE id = ?", (run_id,)).fetchone()
    if not run:
        return {"run": None, "hits": {}}
    hit_rows = conn.execute(
        "SELECT * FROM screener_hits WHERE run_id = ?", (run_id,)
    ).fetchall()
    hits: Dict[str, list] = {}
    for h in hit_rows:
        h = dict(h)
        rid = h.get("rule_id") or "unknown"
        hits.setdefault(rid, []).append(h)
    return {"run": dict(run), "hits": hits}
