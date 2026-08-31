"""龙虎榜席位买入记录：全市场明细同步入库 + 游资动向查询
@author ygw
"""
import threading
import time
from datetime import date as _date, datetime, timedelta
from typing import Any, Dict, List, Optional

from ..logging_config import logger
from . import store

TZ_CN = store.TZ_CN

# 东财明细接口里的散户统计席位（非营业部，会污染游资/机构动向）
_SKIP_SEAT_NAMES = {"自然人", "其他自然人", "中小投资者", "机构"}

_job_lock = threading.Lock()
_job: Dict[str, Any] = {
    "running": False,
    "scope": "lhb",
    "percent": 0,
    "message": "空闲",
    "total": 0,
    "done": 0,
    "error": "",
    "started_at": "",
    "finished_at": "",
    "result": None,
    "dates": [],
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


def _dc_paged(report: str, columns: str, filt: str, page_size: int = 500) -> List[dict]:
    """东财 datacenter 列表接口（分页拉全，避免单页条数上限截断）。"""
    import httpx
    from .. import config
    from ..datasource import lhb
    out: List[dict] = []
    page = 1
    while True:
        params = {
            "reportName": report,
            "columns": columns,
            "filter": filt,
            "pageNumber": str(page),
            "pageSize": str(page_size),
            "source": "WEB",
            "client": "WEB",
        }
        try:
            resp = httpx.get(
                lhb.DC_URL, params=params,
                headers={"User-Agent": config.USER_AGENT, "Referer": "https://data.eastmoney.com/"},
                timeout=config.REQUEST_TIMEOUT, follow_redirects=True,
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            logger.info("龙虎榜明细拉取失败 %s %s: %s", report, filt, e)
            break
        rows = ((body or {}).get("result") or {}).get("data") or []
        out.extend(rows)
        if len(rows) < page_size:
            break
        page += 1
    return out


# 东财可转债板块（118/123/127 等）与北交所（920 等），均不在本地股票池
_CB_FS = "b:MK0354"
_BJ_FS = "m:0+t:81+s:2048"
_CB_CACHE: Dict[str, Any] = {"ts": 0.0, "map": {}}
_BJ_CACHE: Dict[str, Any] = {"ts": 0.0, "map": {}}


def _sector_name_map(fs: str, cache: Dict[str, Any], label: str) -> Dict[str, str]:
    """东财板块列表名称映射（一次拉全），模块级缓存 6 小时。

    用途:
        龙虎榜上榜的可转债/北交所等证券不在本地股票池 stocks 表，
        名称会存空导致前端退显代码，此处用板块列表批量补名。

    参数:
        fs: 东财 clist 板块筛选参数
        cache: 模块级缓存（{"ts": float, "map": dict}）
        label: 日志标签

    返回:
        code -> 名称（如 {"118064": "联瑞转债", "920059": "双英集团"}）
    """
    now = time.monotonic()
    if cache["map"] and now - cache["ts"] < 6 * 3600:
        return cache["map"]
    out: Dict[str, str] = {}
    try:
        from ..datasource import eastmoney
        items = eastmoney.get_client()._clist_all_pages(fs, "f12,f14", max_pages=5)
        for it in items:
            code = str(it.get("f12") or "")
            name = it.get("f14") or ""
            if code and name:
                out[code] = name
        if out:
            cache.update({"ts": now, "map": out})
            logger.info("%s名称映射已刷新: %d 只", label, len(out))
    except Exception:
        logger.debug("%s名称拉取失败", label, exc_info=True)
    return out


def _cb_name_map() -> Dict[str, str]:
    """可转债板块名称映射（东财 b:MK0354），缓存 6 小时。"""
    return _sector_name_map(_CB_FS, _CB_CACHE, "可转债板块")


def _bj_name_map() -> Dict[str, str]:
    """北交所板块名称映射（东财 m:0+t:81+s:2048），缓存 6 小时。"""
    return _sector_name_map(_BJ_FS, _BJ_CACHE, "北交所")


def _ulist_name_map(codes: List[str]) -> Dict[str, str]:
    """对本地股票池查不到的代码用东财 ulist 批量补名（B股等）。

    参数:
        codes: 待补名代码列表

    返回:
        code -> 名称（如 {"200521": "虹美菱B"}）
    """
    codes = [c for c in codes if c]
    if not codes:
        return {}
    out: Dict[str, str] = {}
    try:
        from ..datasource import eastmoney
        briefs = eastmoney.get_client().ulist_briefs(codes, {})
        for b in briefs:
            if b.code and b.name:
                out[b.code] = b.name
    except Exception:
        logger.debug("龙虎榜 ulist 补名失败", exc_info=True)
    return out


def sync_records_for_dates(dates: List[str], progress: Optional[Any] = None) -> Dict[str, Any]:
    """
    按日期同步龙虎榜全市场席位（买入+卖出）入库，含游资/机构/北向/普通全部席位。

    参数:
        dates: 交易日列表 YYYY-MM-DD（非交易日接口返回空，自动跳过）
        progress: 进度回调 (percent, message, done, total)

    返回:
        {"dates": 成功同步的日期列表, "written": 写入条数}
    """
    from ..datasource import lhb
    from .lhb_seats import classify_seat

    cols = "SECURITY_CODE,OPERATEDEPT_NAME,BUY,SELL,NET,EXPLANATION"
    total = len(dates)
    written = 0
    done_dates: List[str] = []

    for i, d in enumerate(dates, 1):
        rows = []
        for side, report in (
            ("buy", "RPT_BILLBOARD_DAILYDETAILSBUY"),
            ("sell", "RPT_BILLBOARD_DAILYDETAILSSELL"),
        ):
            for it in _dc_paged(report, cols, f"(TRADE_DATE='{d}')"):
                seat_name = it.get("OPERATEDEPT_NAME") or ""
                if seat_name in _SKIP_SEAT_NAMES:
                    continue
                cls = classify_seat(seat_name)
                rows.append((
                    d,
                    str(it.get("SECURITY_CODE") or ""),
                    side,
                    seat_name,
                    cls["type"],
                    cls.get("nickname") or "",
                    cls.get("premium") or "",
                    it.get("BUY"),
                    it.get("SELL"),
                    it.get("NET"),
                    (it.get("EXPLANATION") or "")[:120],
                ))
        if not rows:
            continue

        codes = {r[1] for r in rows if r[1]}
        name_map = store.get_stocks_map(list(codes))
        cb_map = _cb_name_map()   # 可转债不在本地股票池，板块列表兜底补名
        bj_map = _bj_name_map()   # 北交所不在本地股票池，板块列表兜底补名
        missing = [c for c in codes
                   if not (name_map.get(c, {}).get("name") or cb_map.get(c) or bj_map.get(c))]
        ul_map = _ulist_name_map(missing)  # B股等其他证券批量补名
        conn = store.get_conn()
        with store._lock:
            for r in rows:
                nm = (name_map.get(r[1], {}).get("name") or cb_map.get(r[1])
                      or bj_map.get(r[1]) or ul_map.get(r[1]) or "")
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO lhb_records"
                        "(date, code, name, side, seat_name, type, nickname, premium, buy, sell, net, reason) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (r[0], r[1], nm, r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10]),
                    )
                except Exception:
                    pass
            conn.execute(
                "INSERT INTO lhb_dates(date, stock_count, record_count, synced_at) VALUES (?,?,?,?) "
                "ON CONFLICT(date) DO UPDATE SET "
                "stock_count=excluded.stock_count, record_count=excluded.record_count, "
                "synced_at=excluded.synced_at",
                (d, len(codes), len(rows), store._now()),
            )
            conn.commit()
        written += len(rows)
        done_dates.append(d)

        if progress:
            progress(int(i / total * 100) if total else 100, f"已同步 {i}/{total} 天（{d}）", i, total)

    logger.info("龙虎榜同步完成: %d 天, 写入 %d 条", len(done_dates), written)
    return {"dates": done_dates, "written": written}


# ------------------------------------------------------------------ 后台任务
def _run_job(dates: List[str]) -> None:
    try:
        result = sync_records_for_dates(dates, progress=_set_progress)
        with _job_lock:
            _job["result"] = result
            _job["error"] = ""
    except Exception as e:
        logger.exception("龙虎榜同步任务失败")
        with _job_lock:
            _job["error"] = str(e)
            _job["message"] = "同步失败：" + str(e)
    finally:
        with _job_lock:
            _job["running"] = False
            _job["finished_at"] = store._now()
            if not _job["error"]:
                _job["percent"] = 100


def start_moves_sync(start: str, end: str) -> Dict[str, Any]:
    """
    启动后台龙虎榜同步任务（已同步日期自动跳过）。已在跑则返回当前状态。

    参数:
        start/end: 日期区间 YYYY-MM-DD（含）

    返回:
        任务状态字典
    """
    dates = []
    d = _date.fromisoformat(start)
    end_d = _date.fromisoformat(end)
    while d <= end_d:
        dates.append(d.isoformat())
        d += timedelta(days=1)

    conn = store.get_conn()
    have = {r["date"] for r in conn.execute("SELECT date FROM lhb_dates").fetchall()}
    pending = [x for x in dates if x not in have]

    with _job_lock:
        if _job["running"]:
            return dict(_job)
        _job.update({
            "running": True,
            "scope": "lhb",
            "percent": 0,
            "message": f"待同步 {len(pending)} 天",
            "total": len(pending),
            "done": 0,
            "error": "",
            "started_at": store._now(),
            "finished_at": "",
            "result": None,
            "dates": pending[:5],
        })

    if not pending:
        with _job_lock:
            _job["running"] = False
            _job["percent"] = 100
            _job["message"] = "所选日期均已同步"
            _job["finished_at"] = store._now()
        return dict(_job)

    threading.Thread(target=_run_job, args=(pending,), name="lhb-moves-sync", daemon=True).start()
    with _job_lock:
        return dict(_job)


def moves_sync_status() -> Dict[str, Any]:
    """返回当前龙虎榜同步任务状态。"""
    with _job_lock:
        return dict(_job)


# 交易日多波段定时同步时间节点: (小时, 分钟, 节点名称, 阶段说明)
LHB_SYNC_SLOTS = [
    (16, 45, "16:45", "初榜尝鲜（交易所第一批数据）"),
    (17, 5,  "17:05", "全市场放榜（营业部及游资打标全面更新）"),
    (18, 0,  "18:00", "晚间复核（补齐晚间修正与深港通席位）"),
    (19, 0,  "19:00", "夜间归档（最终收盘席位汇总）"),
]


def auto_sync_today_if_needed(now_dt: Optional[datetime] = None) -> None:
    """每日收盘后多时间点自动梯次同步当天龙虎榜（供后台线程定时调用）。"""
    enabled = store.get_setting("lhbAutoSync")
    if enabled == "0":
        return
    now = now_dt or datetime.now(TZ_CN)
    if now.weekday() >= 5:  # 周末休市不执行
        return
    today = now.strftime("%Y-%m-%d")
    current_hm = (now.hour, now.minute)

    # 获取今日已完成同步的时间槽集合
    synced_key = f"lhbSyncedSlots_{today}"
    raw_synced = store.get_setting(synced_key) or ""
    synced_slots = set(filter(None, raw_synced.split(",")))

    # 按时间顺序检查已到达且未执行的同步槽位
    for hour, minute, slot_name, desc in LHB_SYNC_SLOTS:
        if current_hm >= (hour, minute) and slot_name not in synced_slots:
            try:
                logger.info("触发龙虎榜梯次同步 [%s · %s]: %s", slot_name, desc, today)
                res = sync_records_for_dates([today])
                synced_slots.add(slot_name)
                store.set_setting(synced_key, ",".join(sorted(synced_slots)))
                logger.info("龙虎榜 [%s · %s] 同步完成: %s (写入/更新 %s 条)",
                            slot_name, desc, today, res.get("written", 0))
            except Exception as e:
                logger.warning("龙虎榜 [%s · %s] 同步异常: %s", slot_name, desc, e)


# ------------------------------------------------------------------ 查询
def list_dates() -> List[Dict[str, Any]]:
    """已同步交易日列表（含股票/记录数，按日期倒序）。"""
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT date, stock_count, record_count FROM lhb_dates ORDER BY date DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def moves_by_date(trade_date: str, side: str = "buy", nickname: str = "",
                  limit: int = 100) -> List[Dict[str, Any]]:
    """
    当日某方向席位记录，按股票聚合（含参与的游资）。

    返回:
        每只股票一行: code/name/buy/sell/net/reason/seats（游资席位列表）
    """
    conn = store.get_conn()
    where = "date=? AND side=?"
    args: List[Any] = [trade_date, side]
    if nickname:
        where += " AND nickname=?"
        args.append(nickname)
    rows = conn.execute(
        f"SELECT code, name, seat_name, type, nickname, premium, buy, sell, net, reason "
        f"FROM lhb_records WHERE {where} ORDER BY net DESC",
        args,
    ).fetchall()

    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        d = dict(r)
        k = d["code"]
        g = agg.get(k)
        if g is None:
            g = agg[k] = {
                "code": k, "name": d["name"], "reason": d["reason"] or "",
                "buy": 0.0, "sell": 0.0, "net": 0.0, "seats": [],
            }
        g["buy"] += d["buy"] or 0
        g["sell"] += d["sell"] or 0
        g["net"] += d["net"] or 0
        if d["nickname"]:
            g["seats"].append({
                "nickname": d["nickname"], "type": d["type"],
                "premium": d["premium"], "seat_name": d["seat_name"],
            })
    out = sorted(agg.values(), key=lambda x: x["net"], reverse=True)
    return out[:limit]


def moves_by_nick(nickname: str) -> List[Dict[str, Any]]:
    """
    某游资买入过的股票汇总。

    返回:
        每只股票一行: code/name/first_date/last_date/count/total_buy/total_net/reason/records
    """
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT date, code, name, buy, sell, net, reason FROM lhb_records "
        "WHERE nickname=? AND side='buy' ORDER BY date",
        (nickname,),
    ).fetchall()

    agg: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        k = r["code"]
        g = agg.get(k)
        if g is None:
            g = agg[k] = {
                "code": k, "name": r["name"] or "", "reason": r["reason"] or "",
                "first_date": r["date"], "last_date": r["date"],
                "count": 0, "total_buy": 0.0, "total_net": 0.0, "records": [],
            }
        g["count"] += 1
        g["total_buy"] += r["buy"] or 0
        g["total_net"] += r["net"] or 0
        if r["date"] < g["first_date"]:
            g["first_date"] = r["date"]
        if r["date"] > g["last_date"]:
            g["last_date"] = r["date"]
        if r["reason"]:
            g["reason"] = r["reason"]
        g["records"].append({"date": r["date"], "buy": r["buy"], "sell": r["sell"], "net": r["net"]})
    for g in agg.values():
        g["records"].sort(key=lambda x: x["date"], reverse=True)
    out = sorted(agg.values(), key=lambda x: x["last_date"], reverse=True)
    return out