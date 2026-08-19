"""全 A 日 K 线增量同步到 SQLite（用于盘后选股）
支持全市场 1.5 秒极速批量打包同步与历史多日回溯
@author ygw
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from .. import config
from ..logging_config import logger
from . import store

TZ_CN = store.TZ_CN

_job_lock = threading.Lock()
_job: Dict[str, Any] = {
    "running": False,
    "scope": "daily_bars",
    "mode": "today_bulk",
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
    """返回当前日 K 同步任务状态（前端轮询用）。"""
    with _job_lock:
        st = dict(_job)
    conn = store.get_conn()
    try:
        row = conn.execute("SELECT COUNT(DISTINCT code) AS cnt FROM daily_bars").fetchone()
        stock_cnt = row["cnt"] if row else 0
        st["stock_count"] = stock_cnt
        row2 = conn.execute("SELECT MAX(trade_date) AS d FROM daily_bars").fetchone()
        st["latest_date"] = row2["d"] if row2 else None
        row3 = conn.execute("SELECT COUNT(*) AS total_bars FROM daily_bars").fetchone()
        st["total_bars"] = row3["total_bars"] if row3 else 0

        # 统计已具备 120 天完整日 K 的股票数量与覆盖率
        row4 = conn.execute(
            "SELECT COUNT(*) AS full_cnt FROM (SELECT code FROM daily_bars GROUP BY code HAVING COUNT(*) >= 120)"
        ).fetchone()
        full_cnt = row4["full_cnt"] if row4 else 0
        st["full_bars_count"] = full_cnt
        st["full_bars_pct"] = round(full_cnt / stock_cnt * 100, 1) if stock_cnt > 0 else 0.0
    except Exception:
        st["stock_count"] = 0
        st["latest_date"] = None
        st["total_bars"] = 0
        st["full_bars_count"] = 0
        st["full_bars_pct"] = 0.0
    return st


def get_latest_completed_trade_date(now_dt: Optional[datetime] = None) -> str:
    """
    计算最新已收盘归档的交易日 YYYY-MM-DD。
    - 若当前处于周一至周五且时间 >= 15:00，则收盘归档日为当天；
    - 若时间 < 15:00（如凌晨、清晨、盘前盘中），则收盘归档日为上一个交易日；
    - 若当前为周六/周日，则收盘归档日为周五。
    """
    if now_dt is None:
        now_dt = datetime.now(TZ_CN)
    d = now_dt.date()
    # 如果是交易日且已经过了 15:00 收盘
    if now_dt.weekday() < 5 and (now_dt.hour > 15 or (now_dt.hour == 15 and now_dt.minute >= 0)):
        return d.strftime("%Y-%m-%d")

    # 否则取上一个交易日（往前找最近的周一至周五）
    d = d - timedelta(days=1)
    while d.weekday() >= 5:  # 5 是周六，6 是周日
        d = d - timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def sync_today_bars_bulk(trade_date: Optional[str] = None,
                         progress: Optional[Callable] = None) -> int:
    """
    使用东财全市场 clist 批量打包接口，1.5 秒极速同步全市场 5400+ 只 A 股最新收盘日 K。
    杜绝逐只股票连续请求导致的频控与封禁。

    参数:
        trade_date: 目标日期 YYYY-MM-DD（默认最新已收盘交易日）
        progress: 进度回调 (percent, message, done, total)

    返回:
        写入的日 K 记录数
    """
    from .lhb_seats import ensure_tables
    ensure_tables()

    now = datetime.now(TZ_CN)
    today_str = trade_date or get_latest_completed_trade_date(now)

    if progress:
        progress(10, "正在批量拉取全市场 A 股收盘数据（约 1.5 秒）…", 0, 5400)

    t0 = time.monotonic()
    from ..datasource import eastmoney
    client = eastmoney.get_client()

    fields = "f12,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f15,f16,f17,f18,f20,f21,f23,f62,f184"
    diff_list = client._clist_all_pages(config.FS_ALL_A, fields=fields, concurrency=6)

    if not diff_list:
        if progress:
            progress(100, "未获取到全市场行情数据", 0, 0)
        return 0

    if progress:
        progress(60, f"已获取 {len(diff_list)} 只股票数据，正在批量写入数据库…", len(diff_list), len(diff_list))

    def _sf(v, d=0.0):
        if v is None or v == "-":
            return d
        try:
            return float(v)
        except (ValueError, TypeError):
            return d

    rows_data: List[tuple] = []
    for it in diff_list:
        code = str(it.get("f12") or "").strip()
        if not code:
            continue
        close_p = it.get("f2")
        vol = it.get("f5")
        if close_p is None or close_p == "-" or (isinstance(close_p, (int, float)) and close_p <= 0):
            continue
        try:
            c = float(close_p)
            o = _sf(it.get("f17"), c)
            h = _sf(it.get("f15"), c)
            l = _sf(it.get("f16"), c)
            v = _sf(vol, 0.0)
            a = _sf(it.get("f6"), 0.0)
            turnover = _sf(it.get("f8"), 0.0)
            volume_ratio = _sf(it.get("f10"), 0.0)
            amplitude = _sf(it.get("f7"), 0.0)
            change_pct = _sf(it.get("f3"), 0.0)
            main_inflow = _sf(it.get("f62"), 0.0)
            main_ratio = _sf(it.get("f184"), 0.0)
            float_mv = _sf(it.get("f21"), 0.0)
            total_mv = _sf(it.get("f20"), 0.0)
            pe = _sf(it.get("f9"), 0.0)
            pb = _sf(it.get("f23"), 0.0)

            rows_data.append((
                code, today_str, o, h, l, c, v, a,
                turnover, volume_ratio, amplitude, change_pct,
                main_inflow, main_ratio, float_mv, total_mv, pe, pb
            ))
        except (ValueError, TypeError):
            continue

    written = 0
    if rows_data:
        with store._lock:
            conn = store.get_conn()
            conn.executemany(
                "INSERT OR REPLACE INTO daily_bars"
                "(code, trade_date, open, high, low, close, volume, amount, "
                "turnover, volume_ratio, amplitude, change_pct, "
                "main_inflow, main_ratio, float_mv, total_mv, pe, pb) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows_data,
            )
            stocks_tuples = [
                (str(it.get("f12")).strip(), str(it.get("f14")).strip())
                for it in diff_list if it.get("f12") and it.get("f14")
            ]
            if stocks_tuples:
                conn.executemany(
                    "INSERT OR IGNORE INTO stocks (code, name) VALUES (?, ?)",
                    stocks_tuples,
                )
            conn.commit()
            written = len(rows_data)

    dur_ms = (time.monotonic() - t0) * 1000
    logger.info("全市场日K极速批量同步完成: %d 只, 日期: %s (耗时 %.0fms)", written, today_str, dur_ms)

    if progress:
        progress(100, f"极速同步完成，写入 {written} 只股票全维日K (耗时 {dur_ms:.0f}ms)", written, written)

    return written


def _fetch_kline_single(client, code: str, lookback: int) -> List[tuple]:
    """拉取单只股票历史日 K 线"""
    results = []
    try:
        kl = client.kline(code, period="day", limit=lookback)
        if not kl or not kl.get("points"):
            return []
        for p in kl["points"]:
            d = p.get("date") or ""
            if not d:
                continue
            results.append((
                code, d,
                p.get("open"), p.get("high"), p.get("low"), p.get("close"),
                p.get("volume"), p.get("amount"),
            ))
    except Exception as e:
        logger.debug("历史日K拉取失败 %s: %s", code, e)
    return results


def sync_historical_bars(lookback_days: int = 120, scope: str = "watchlist",
                         progress: Optional[Callable] = None) -> int:
    """
    同步历史日 K 线（用于补齐前 N 天均线多空数据）。
    性能优化：
    1. 智能增量跳过：已具备完整 120 天且达到最新收盘日的标的直接跳过，0 网络开销；
    2. 并发数提升至 12~16，批量事务提交（500 条/批），极大减少 SQLite 锁竞争与 I/O 等待。
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

    target_date = get_latest_completed_trade_date()

    # 查本地现有数据状态 (code -> (max_date, count))
    existing_stats = {}
    stat_rows = conn.execute(
        "SELECT code, MAX(trade_date) as max_d, COUNT(*) as cnt FROM daily_bars GROUP BY code"
    ).fetchall()
    for r in stat_rows:
        existing_stats[r["code"]] = (r["max_d"] or "", r["cnt"] or 0)

    # 过滤出真正需要补齐历史的股票
    need_sync_codes = []
    for c in codes:
        max_d, cnt = existing_stats.get(c, ("", 0))
        if cnt >= lookback_days and max_d >= target_date:
            continue
        need_sync_codes.append(c)

    total_codes = len(codes)
    need_total = len(need_sync_codes)

    if need_total == 0:
        if progress:
            progress(100, f"所有 {total_codes} 只股票历史 K 线已是最新完整状态（已自动极速跳过）", total_codes, total_codes)
        return 0

    if progress:
        progress(2, f"增量补齐 {need_total} 只股票历史 K 线（已智能跳过 {total_codes - need_total} 只完整标的）…", 0, need_total)

    from ..datasource import eastmoney
    client = eastmoney.get_client()

    written = 0
    done_count = 0
    batch_size = 500
    concurrency = 12 if scope == "watchlist" else 16

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(_fetch_kline_single, client, code, lookback_days): code for code in need_sync_codes}
        pending_rows = []
        for fut in as_completed(futures):
            code = futures[fut]
            done_count += 1
            try:
                rows = fut.result()
                if rows:
                    pending_rows.extend(rows)
            except Exception:
                pass

            if len(pending_rows) >= batch_size or done_count == need_total:
                if pending_rows:
                    with store._lock:
                        conn2 = store.get_conn()
                        conn2.executemany(
                            "INSERT OR REPLACE INTO daily_bars"
                            "(code, trade_date, open, high, low, close, volume, amount) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            pending_rows,
                        )
                        conn2.commit()
                        written += len(pending_rows)
                        pending_rows = []

            if progress and (done_count % 15 == 0 or done_count == need_total):
                pct = max(3, min(99, int(done_count / need_total * 96) + 3))
                progress(pct, f"已增量补齐 {done_count}/{need_total} 只历史 K 线…", done_count, need_total)

    if progress:
        progress(100, f"历史 K 线增量同步完成，写入 {written} 条数据", total_codes, total_codes)

    logger.info("历史K线同步完成: scope=%s, 扫描 %d 只, 增量更新 %d 只, 写入 %d 条", scope, total_codes, need_total, written)
    return written


def sync_daily_bars(lookback_days: int = 120, scope: str = "all", mode: str = "today_bulk",
                    progress: Optional[Callable] = None) -> int:
    """
    全 A 日 K 增量同步入口。
    mode: "today_bulk"（默认：全市场 1.5 秒极速今日日 K 批量同步） / "history"（历史多日回溯）
    """
    if mode == "today_bulk":
        return sync_today_bars_bulk(progress=progress)
    return sync_historical_bars(lookback_days=lookback_days, scope=scope, progress=progress)


def _run_daily_job(lookback_days: int, scope: str, mode: str = "today_bulk") -> None:
    """后台线程执行日 K 同步。"""
    try:
        result = sync_daily_bars(lookback_days, scope, mode, progress=_set_progress)
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


def start_daily_sync_job(lookback_days: int = 120, scope: str = "all",
                         mode: str = "today_bulk") -> Dict[str, Any]:
    """启动后台日 K 同步任务。"""
    with _job_lock:
        if _job["running"]:
            return dict(_job)
        _job.update({
            "running": True,
            "scope": scope,
            "mode": mode,
            "percent": 1,
            "message": "极速批量打包拉取中…" if mode == "today_bulk" else f"正在同步 {scope} 历史K线…",
            "total": 0,
            "done": 0,
            "error": "",
            "started_at": store._now(),
            "finished_at": "",
            "result": None,
        })
    threading.Thread(
        target=_run_daily_job,
        args=(lookback_days, scope, mode),
        name="daily-bars-sync",
        daemon=True,
    ).start()
    with _job_lock:
        return dict(_job)


def auto_sync_daily_bars_if_needed(now_dt: Optional[datetime] = None) -> None:
    """每日收盘 15:30 自动极速同步全市场当日收盘日 K（供后台线程定时调用）。"""
    enabled = store.get_setting("dailyBarsAutoSync")
    if enabled == "0":
        return
    now = now_dt or datetime.now(TZ_CN)
    if now.weekday() >= 5:  # 周末跳过
        return
    # 收盘后 15:30 之后触发
    if now.hour < 15 or (now.hour == 15 and now.minute < 30):
        return

    today = now.strftime("%Y-%m-%d")
    synced_key = f"dailyBarsSynced_{today}"
    if store.get_setting(synced_key):
        return

    try:
        logger.info("触发每日收盘全市场日K极速同步: %s", today)
        n = sync_today_bars_bulk(today)
        if n > 0:
            store.set_setting(synced_key, store._now())
            logger.info("每日收盘全市场日K同步成功: %s (%d 只)", today, n)
    except Exception as e:
        logger.warning("每日收盘全市场日K同步失败: %s", e)
