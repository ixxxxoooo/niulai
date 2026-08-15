"""盘后选股路由：日 K 同步 + 选股执行 + 结果查询
@author ygw
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


class SyncBarsBody(BaseModel):
    """日 K 同步参数"""
    lookback_days: int = Field(default=120, ge=30, le=500)
    scope: str = Field(default="all", pattern="^(all|watchlist)$")


class ScreenRunBody(BaseModel):
    """选股执行参数"""
    rules: List[str] = Field(default=["breakout", "golden_cross", "volume_surge"])
    scope: str = Field(default="all", pattern="^(all|watchlist)$")
    params: Optional[dict] = None
    notify_feishu: bool = False


class SeatSyncBody(BaseModel):
    """席位同步参数"""
    force: bool = False


# ── 日 K 同步 ──

@router.post("/screener/sync-bars")
def screener_sync_bars(body: SyncBarsBody):
    """触发日 K 线后台同步任务。"""
    from ...db.daily_sync import start_daily_sync_job
    return {"ok": True, **start_daily_sync_job(body.lookback_days, body.scope)}


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
    rules: ["breakout", "golden_cross", "volume_surge"] 中的子集。
    """
    from ...analyzer.screener import RULES, run_screen
    valid_rules = [r for r in body.rules if r in RULES]
    if not valid_rules:
        raise HTTPException(status_code=400, detail="请至少选择一条有效规则")

    result = run_screen(valid_rules, body.params, body.scope)

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
        {"id": k, "name": v["name"], "desc": v["desc"], "default_params": v["default_params"]}
        for k, v in RULES.items()
    ]}


@router.get("/screener/runs")
def screener_runs(limit: int = Query(20, ge=1, le=100)):
    """历史选股任务列表。"""
    from ...analyzer.screener import list_runs
    return {"runs": list_runs(limit)}


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
    """席位标签库列表。"""
    from ...db.lhb_seats import list_seats, seat_count
    return {"count": seat_count(), "seats": list_seats()}


@router.post("/lhb/seats/sync")
def lhb_seats_sync(body: SeatSyncBody):
    """重置/更新席位标签库。"""
    from ...db.lhb_seats import init_builtin_seats, seat_count
    n = init_builtin_seats(force=body.force)
    return {"ok": True, "count": seat_count(), "written": n}
