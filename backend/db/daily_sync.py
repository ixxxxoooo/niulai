"""全 A 日 K 线增量同步到 SQLite（用于盘后选股）
@author ygw
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Optional

from ..logging_config import logger
from . import store

_job_lock = threading.Lock()
_job: Dict[str, Any] = {
    "running": False,
    "scope": "daily_bars",
    "percent": 0,
    "message": "空闲",
    "total": 0,
    "done": 0,
    "error": "",
    "started_at": "",
    "finished_at": "",
    "result": None,
}


def _set_progress(percent: int, message: str, done: int = 0, total: int = 0) -> None:
    """更新同步进度（线程安全）。"""
    with _job_lock:
        _job["percent"] = max(0, min(100, int(percent)))
        _job["message"] = message
        if done:
            _job["done"] = done
        if total:
            _job["total"] = total


def daily_sync_status() -> Dict[str, Any]:
    """
    返回当前日 K 同步任务状态（前端轮询用）。

    返回:
        包含 running/percent/message/done/total/error 等字段的字典
    """
    with _job_lock:
        st = dict(_job)
    conn = store.get_conn()
    try:
        row = conn.execute("SELECT COUNT(DISTINCT code) AS cnt FROM daily_bars").fetchone()
        st["stock_count"] = row["cnt"] if row else 0
        row2 = conn.execute("SELECT MAX(trade_date) AS d FROM daily_bars").fetchone()
        st["latest_date"] = row2["d"] if row2 else None
    except Exception:
        st["stock_count"] = 0
        st["latest_date"] = None
    return st


def _fetch_kline_batch(codes: list, lookback: int) -> list:
    """
    批量拉取一组股票日 K 线。

    参数:
        codes: 股票代码列表
        lookback: 拉取的 K 线条数

    返回:
        [(code, date, open, high, low, close, volume, amount), ...]
    """
    from ..datasource import eastmoney
    results = []
    client = eastmoney.get_client()
    for code in codes:
        try:
            kl = client.kline(code, period="day", limit=lookback)
            if not kl or not kl.get("points"):
                continue
            for p in kl["points"]:
                results.append((
                    code,
                    p.get("date") or "",
                    p.get("open"),
                    p.get("high"),
                    p.get("low"),
                    p.get("close"),
                    p.get("volume"),
                    p.get("amount"),
                ))
        except Exception as e:
            logger.debug("日K拉取失败 %s: %s", code, e)
    return results


def sync_daily_bars(lookback_days: int = 120, scope: str = "all",
                    progress: Optional[Callable] = None) -> int:
    """
    全 A 日 K 增量同步到 SQLite daily_bars 表。

    参数:
        lookback_days: 每只拉取的 K 线条数（默认 120 个交易日）
        scope: "all" 全 A 股 / "watchlist" 仅自选
        progress: 进度回调 (percent, message, done, total)

    返回:
        写入总行数
    """
    from .lhb_seats import ensure_tables
    ensure_tables()

    conn = store.get_conn()
    if scope == "watchlist":
        codes = store.watchlist_codes()
    else:
        rows = conn.execute("SELECT code FROM stocks WHERE classify IN ('AStock','ETF')").fetchall()
        codes = [r["code"] for r in rows]

    if not codes:
        if progress:
            progress(100, "无股票可同步", 0, 0)
        return 0

    total = len(codes)
    if progress:
        progress(1, f"准备同步 {total} 只…", 0, total)

    # 检查每只的最新日期，决定是否需要更新
    today_str = time.strftime("%Y-%m-%d")
    need_update = []
    for code in codes:
        row = conn.execute(
            "SELECT MAX(trade_date) AS d FROM daily_bars WHERE code = ?", (code,)
        ).fetchone()
        last = row["d"] if row else None
        if not last or last < today_str:
            need_update.append(code)

    if not need_update:
        if progress:
            progress(100, f"全部 {total} 只已是最新", total, total)
        return 0

    total_need = len(need_update)
    if progress:
        progress(2, f"需更新 {total_need} 只…", 0, total_need)

    batch_size = 50
    batches = [need_update[i:i + batch_size] for i in range(0, total_need, batch_size)]
    written = 0
    done_count = 0

    for bi, batch in enumerate(batches):
        try:
            rows_data = _fetch_kline_batch(batch, lookback_days)
            if rows_data:
                with store._lock:
                    conn2 = store.get_conn()
                    conn2.executemany(
                        "INSERT OR REPLACE INTO daily_bars"
                        "(code, trade_date, open, high, low, close, volume, amount) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        rows_data,
                    )
                    conn2.commit()
                written += len(rows_data)
        except Exception as e:
            logger.warning("日K批次写入失败 batch=%d: %s", bi, e)

        done_count += len(batch)
        pct = max(3, min(99, int(done_count / total_need * 97) + 3))
        if progress:
            progress(pct, f"已完成 {done_count}/{total_need}", done_count, total_need)

        time.sleep(0.3)

    if progress:
        progress(100, f"同步完成，写入 {written} 条", total_need, total_need)

    logger.info("日K同步完成: 更新 %d 只, 写入 %d 条", total_need, written)
    return written


def _run_daily_job(lookback_days: int, scope: str) -> None:
    """后台线程执行日 K 同步。"""
    try:
        result = sync_daily_bars(lookback_days, scope, progress=_set_progress)
        with _job_lock:
            _job["result"] = result
            _job["error"] = ""
    except Exception as e:
        logger.exception("日K同步任务失败")
        with _job_lock:
            _job["error"] = str(e)
            _job["message"] = "同步失败：" + str(e)
    finally:
        with _job_lock:
            _job["running"] = False
            _job["finished_at"] = store._now()
            if not _job["error"]:
                _job["percent"] = 100


def start_daily_sync_job(lookback_days: int = 120, scope: str = "all") -> Dict[str, Any]:
    """
    启动后台日 K 同步任务。已在跑则返回当前状态。

    参数:
        lookback_days: 拉取条数
        scope: "all" / "watchlist"

    返回:
        任务状态字典
    """
    with _job_lock:
        if _job["running"]:
            return dict(_job)
        _job.update({
            "running": True,
            "scope": scope,
            "percent": 1,
            "message": "已启动",
            "total": 0,
            "done": 0,
            "error": "",
            "started_at": store._now(),
            "finished_at": "",
            "result": None,
        })
    threading.Thread(
        target=_run_daily_job, args=(lookback_days, scope),
        name="daily-sync", daemon=True,
    ).start()
    with _job_lock:
        return dict(_job)
