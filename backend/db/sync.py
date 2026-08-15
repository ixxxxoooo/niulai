"""全 A 股 + ETF 基础信息 / 概念标签同步到 SQLite
@author ygw
"""
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from ..logging_config import logger
from . import store

_job_lock = threading.Lock()
_job: Dict[str, Any] = {
    "running": False,
    "scope": "",
    "percent": 0,
    "message": "空闲",
    "error": "",
    "started_at": "",
    "finished_at": "",
    "result": None,
}


def _set_progress(percent: int, message: str) -> None:
    with _job_lock:
        _job["percent"] = max(0, min(100, int(percent)))
        _job["message"] = message


def sync_status() -> Dict[str, Any]:
    """当前同步任务状态（前端进度条轮询）。"""
    with _job_lock:
        return dict(_job)


def is_stale(max_hours: float = 24.0) -> bool:
    """股票列表为空或超过 max_hours 未更新。"""
    if store.stock_count() < 100:
        return True
    ts = store.stocks_updated_at()
    if not ts:
        return True
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - dt).total_seconds() > max_hours * 3600
    except ValueError:
        return True


def sync_stock_list(force: bool = False,
                    progress: Optional[Callable[[int, str], None]] = None) -> int:
    """从东财拉取全 A + ETF 名称/行业写入 SQLite。返回写入条数。"""
    if store.in_pytest() and not force:
        return 0
    if not force and not is_stale():
        logger.info("股票列表仍新鲜 count=%s updated=%s，跳过同步",
                    store.stock_count(), store.stocks_updated_at())
        return 0
    from ..datasource import eastmoney
    if progress:
        progress(8, "正在拉取全 A + ETF 列表…")
    t0 = time.monotonic()
    client = eastmoney.get_client()
    rows = client.list_instruments()
    if progress:
        progress(70, f"写入本地 {len(rows)} 条…")
    n = store.upsert_stocks(rows)
    store.set_setting("lastStockSyncAt", store._now())
    logger.info("股票列表同步完成 %s 条 (%.0fms)", n, (time.monotonic() - t0) * 1000)
    if progress:
        progress(100, f"名称/行业已更新 {n} 条")
    return n


def sync_concept_tags(force: bool = False,
                      progress: Optional[Callable[[int, str], None]] = None) -> int:
    """按概念板块成分反查，把概念名写入 stocks.concepts。"""
    if store.in_pytest() and not force:
        return 0
    from .. import config
    from ..datasource import eastmoney
    t0 = time.monotonic()
    client = eastmoney.get_client()
    if progress:
        progress(5, "拉取概念板块列表…")
    sectors = client.clist(config.FS_SECTOR_CONCEPT, "f3", 300, fields="f12,f14")
    mapping: dict = defaultdict(list)
    n_sec = max(len(sectors), 1)

    def _one(it: dict):
        bk = str(it.get("f12") or "")
        name = (it.get("f14") or "").strip()
        if not bk or not name:
            return []
        try:
            members = client.clist(f"b:{bk}", "f3", 100, fields="f12")
        except Exception:
            return []
        return [(str(m.get("f12") or ""), name) for m in members if m.get("f12")]

    done = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(_one, it) for it in sectors]
        for fut in as_completed(futs):
            done += 1
            if progress:
                progress(8 + int(done / n_sec * 85), f"概念板块 {done}/{n_sec}")
            try:
                pairs = fut.result()
            except Exception:
                pairs = []
            for code, name in pairs:
                if name not in mapping[code]:
                    mapping[code].append(name)
    if progress:
        progress(95, "写入概念标签…")
    n = store.merge_concepts(mapping)
    store.set_setting("lastConceptSyncAt", store._now())
    logger.info("概念标签同步完成 %s 只 (%.0fms)", n, (time.monotonic() - t0) * 1000)
    if progress:
        progress(100, f"概念标签已更新 {n} 只")
    return n


def tags_incomplete() -> bool:
    """行业标签尚未写入（升级后的旧库）。"""
    try:
        conn = store.get_conn()
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM stocks WHERE industry IS NOT NULL AND industry != ''"
        ).fetchone()
        return int(row["c"] if row else 0) < 100
    except Exception:
        return True


def _run_job(scope: str) -> None:
    """后台执行同步，更新进度。"""
    result = {"stocks": 0, "concepts": 0}
    try:
        if scope in ("stocks", "all"):
            _set_progress(3, "同步名称 / 行业…")
            result["stocks"] = sync_stock_list(force=True, progress=_set_progress)
        if scope in ("concepts", "all"):
            _set_progress(5, "同步概念标签…")
            result["concepts"] = sync_concept_tags(force=True, progress=_set_progress)
        _set_progress(100, "同步完成")
        with _job_lock:
            _job["result"] = result
            _job["error"] = ""
    except Exception as e:
        logger.exception("同步任务失败")
        with _job_lock:
            _job["error"] = str(e)
            _job["message"] = "同步失败：" + str(e)
            _job["result"] = result
    finally:
        with _job_lock:
            _job["running"] = False
            _job["finished_at"] = store._now()
            _job["percent"] = 100 if not _job["error"] else _job["percent"]


def start_sync_job(scope: str = "stocks") -> Dict[str, Any]:
    """启动后台同步。已在跑则返回当前状态。"""
    if scope not in ("stocks", "concepts", "all"):
        scope = "stocks"
    with _job_lock:
        if _job["running"]:
            return dict(_job)
        _job.update({
            "running": True,
            "scope": scope,
            "percent": 1,
            "message": "已启动",
            "error": "",
            "started_at": store._now(),
            "finished_at": "",
            "result": None,
        })
    threading.Thread(target=_run_job, args=(scope,), name="meta-sync", daemon=True).start()
    with _job_lock:
        return dict(_job)


def start_background_sync() -> None:
    """启动后台线程：启动时同步列表，并按设置间隔定时刷新。"""
    if store.in_pytest():
        return

    def _run():
        try:
            store.init_db()
            sync_stock_list(force=tags_incomplete())
        except Exception:
            logger.exception("股票列表后台同步失败")
        while True:
            time.sleep(600)
            try:
                hours = float(store.get_setting("autoSyncHours") or 0)
                if hours <= 0:
                    continue
                if is_stale(hours):
                    sync_stock_list(force=True)
                last_c = store.get_setting("lastConceptSyncAt") or ""
                need_c = True
                if last_c:
                    try:
                        dt = datetime.strptime(last_c, "%Y-%m-%d %H:%M:%S")
                        need_c = (datetime.now() - dt).total_seconds() > hours * 3600
                    except ValueError:
                        need_c = True
                if need_c:
                    sync_concept_tags()
            except Exception:
                logger.exception("定时同步失败")

    threading.Thread(target=_run, name="stock-sync", daemon=True).start()
