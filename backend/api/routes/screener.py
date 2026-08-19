"""盘后选股路由：日 K 同步 + 选股执行 + 结果查询
@author ygw
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class SyncBarsBody(BaseModel):
    """日 K 同步参数"""
    lookback_days: int = Field(default=120, ge=1, le=500)
    scope: str = Field(default="all", pattern="^(all|watchlist)$")
    mode: str = Field(default="today_bulk", pattern="^(today_bulk|history)$")


class ScreenRunBody(BaseModel):
    """选股执行参数"""
    rules: List[str] = Field(default=["breakout", "golden_cross", "volume_surge"])
    scope: str = Field(default="all", pattern="^(all|watchlist)$")
    params: Optional[dict] = None
    filters: Optional[dict] = None
    notify_feishu: bool = False


class SeatSyncBody(BaseModel):
    """席位同步参数"""
    force: bool = False


class SeatGroupBody(BaseModel):
    """新增一个游资（含席位列表）"""
    nickname: str = Field(..., min_length=1, max_length=32)
    real_name: str = ""
    tier: str = Field("new_gen", pattern="^(legend|new_gen|regional|broker)$")
    style: str = ""
    premium: str = Field("neutral", pattern="^(positive|neutral_positive|neutral|negative)$")
    seats: List[str] = Field(..., min_length=1)


class SeatGroupPatchBody(BaseModel):
    """更新一个游资（nickname 不可改，其余整体替换）"""
    real_name: str = ""
    tier: str = Field("new_gen", pattern="^(legend|new_gen|regional|broker)$")
    style: str = ""
    premium: str = Field("neutral", pattern="^(positive|neutral_positive|neutral|negative)$")
    seats: List[str] = Field(..., min_length=1)


# ── 日 K 同步 ──

@router.post("/screener/sync-bars")
def screener_sync_bars(body: SyncBarsBody):
    """触发日 K 线后台同步任务。"""
    from ...db.daily_sync import start_daily_sync_job
    return {"ok": True, **start_daily_sync_job(body.lookback_days, body.scope, body.mode)}


@router.get("/screener/sync-status")
def screener_sync_status():
    """日 K 同步进度轮询。"""
    from ...db.daily_sync import daily_sync_status
    return daily_sync_status()


# ── 选股执行 ──

@router.post("/screener/run")
def screener_run(body: ScreenRunBody):
    """
    执行盘后选股扫描。
    rules: ["breakout", "golden_cross", "volume_surge"] 等。
    """
    from ...analyzer.screener import RULES, run_screen
    valid_rules = [r for r in body.rules if r in RULES]
    if not valid_rules:
        raise HTTPException(status_code=400, detail="请至少选择一条有效规则")

    result = run_screen(valid_rules, body.params, body.scope, body.filters)

    # 可选飞书推送
    if body.notify_feishu:
        try:
            from ...notify.feishu import send_screener_result
            for rule_id, hits in result.get("hits", {}).items():
                if hits:
                    rule_name = RULES.get(rule_id, {}).get("name", rule_id)
                    send_screener_result(rule_name, hits)
        except Exception:
            pass

    return result


@router.get("/screener/rules")
def screener_rules():
    """可用的选股规则列表。"""
    from ...analyzer.screener import RULES
    return {"rules": [
        {
            "id": k,
            "name": v["name"],
            "tag": v.get("tag", "量化策略"),
            "badge": v.get("badge", ""),
            "desc": v["desc"],
            "default_params": v["default_params"],
        }
        for k, v in RULES.items()
    ]}


@router.get("/screener/runs")
def screener_runs(limit: int = Query(20, ge=1, le=100)):
    """历史选股任务列表。"""
    from ...analyzer.screener import list_runs
    return {"runs": list_runs(limit)}


@router.delete("/screener/runs")
def screener_clear_runs():
    """清空历史选股归档。"""
    from ...analyzer.screener import clear_runs
    clear_runs()
    return {"ok": True}


@router.get("/screener/runs/{run_id}")
def screener_run_detail(run_id: int):
    """某次选股的命中结果。"""
    from ...analyzer.screener import get_run_hits
    data = get_run_hits(run_id)
    if not data.get("run"):
        raise HTTPException(status_code=404, detail="任务不存在")
    return data


# ── 席位管理 ──

@router.get("/lhb/seats")
def lhb_seats_list():
    """席位标签库列表（含近期活跃度 + 实际出现过的营业部）。"""
    from ...db.lhb_seats import list_seats, seat_count
    seats = list_seats()
    activity: dict = {}
    real_seats: dict = {}
    try:
        from ...db import store
        conn = store.get_conn()
        rows = conn.execute(
            "SELECT nickname, COUNT(*) AS c FROM lhb_records "
            "WHERE nickname != '' AND date >= date('now', '-30 day') GROUP BY nickname"
        ).fetchall()
        activity = {r["nickname"]: r["c"] for r in rows}
        rrows = conn.execute(
            "SELECT nickname, seat_name, MAX(date) AS last_date FROM lhb_records "
            "WHERE nickname != '' AND seat_name != '' GROUP BY nickname, seat_name"
        ).fetchall()
        real_seats = {}
        for r in rrows:
            real_seats.setdefault(r["nickname"], []).append({
                "name": r["seat_name"], "last_date": r["last_date"],
            })
    except Exception:
        pass
    for s in seats:
        s["activity"] = activity.get(s["nickname"], 0)
        s["real_seats"] = real_seats.get(s["nickname"], [])
    return {"count": seat_count(), "seats": seats}


@router.post("/lhb/seats")
def lhb_seats_create(body: SeatGroupBody):
    """新增一个游资（多席位）。"""
    from ...db.lhb_seats import add_seat_group, seat_group_exists, seat_count
    nick = body.nickname.strip()
    if seat_group_exists(nick):
        raise HTTPException(status_code=409, detail=f"游资「{nick}」已存在")
    n = add_seat_group(nick, body.real_name, body.tier, body.style, body.premium, body.seats)
    return {"ok": True, "written": n, "count": seat_count()}


@router.put("/lhb/seats/{nickname}")
def lhb_seats_update(nickname: str, body: SeatGroupPatchBody):
    """整体更新一个游资（席位整体替换，改动标记自定义）。"""
    from ...db.lhb_seats import seat_group_exists, update_seat_group, seat_count
    if not seat_group_exists(nickname):
        raise HTTPException(status_code=404, detail=f"游资「{nickname}」不存在")
    n = update_seat_group(nickname, body.real_name, body.tier, body.style, body.premium, body.seats)
    return {"ok": True, "written": n, "count": seat_count()}


@router.delete("/lhb/seats/{nickname}")
def lhb_seats_delete(nickname: str):
    """删除一个游资（该昵称所有席位）。"""
    from ...db.lhb_seats import delete_seat_group, seat_group_exists, seat_count
    if not seat_group_exists(nickname):
        raise HTTPException(status_code=404, detail=f"游资「{nickname}」不存在")
    n = delete_seat_group(nickname)
    return {"ok": True, "deleted": n, "count": seat_count()}


@router.post("/lhb/seats/sync")
def lhb_seats_sync(body: SeatSyncBody):
    """同步席位标签库：force=True 重建内置种子（保留自定义），False 仅补内置缺位。"""
    from ...db.lhb_seats import init_builtin_seats, seat_count
    n = init_builtin_seats(force=body.force)
    return {"ok": True, "count": seat_count(), "written": n}
