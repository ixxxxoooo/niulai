"""价格监控路由
@author ygw
"""
from typing import Optional
import time

from fastapi import APIRouter, HTTPException

from ...datasource import eastmoney
from ...db import store as db

from .common import AlertBody, AlertPatchBody

router = APIRouter()

# ------------------------------------------------------------------ 价格监控
def _alert_current_value(alert: dict) -> Optional[dict]:
    """取监控目标当前价/涨跌幅。"""
    code = (alert.get("code") or "").strip()
    ttype = alert.get("target_type") or "stock"
    if not code:
        return None
    try:
        if ttype == "index":
            secid = code if "." in code else None
            if not secid:
                # 兼容纯代码：000001 → 1.000001
                secid = f"1.{code}" if code.startswith("000") else f"0.{code}"
            qs = eastmoney.get_client().index_quotes([secid])
            if not qs:
                return None
            q = qs[0]
            return {
                "price": q.price,
                "points": q.price,
                "change_pct": q.change_pct,
                "zhangsu": getattr(q, "zhangsu", None),
                "name": q.name or alert.get("name") or "",
                "secid": q.secid or secid,
            }
        snap = eastmoney.get_client().stock_snapshot(code)
        if snap is None:
            return None
        return {
            "price": snap.price,
            "points": snap.price,
            "change_pct": snap.change_pct,
            "zhangsu": getattr(snap, "zhangsu", None),
            "name": snap.name or alert.get("name") or "",
        }
    except Exception:
        return None


def _alert_hit(alert: dict, cur: dict) -> bool:
    """判断是否触发：lte=≤阈值，gte=≥阈值。"""
    metric = alert.get("metric") or "price"
    val = cur.get(metric)
    if val is None and metric == "points":
        val = cur.get("price")
    if val is None:
        return False
    thr = float(alert.get("threshold") or 0)
    op = alert.get("op") or "lte"
    if op == "gte":
        return float(val) >= thr
    return float(val) <= thr


def _in_cooldown(alert: dict) -> bool:
    """冷却期内不再重复触发。"""
    last = alert.get("last_triggered_at") or ""
    if not last:
        return False
    try:
        from datetime import datetime
        t0 = datetime.strptime(last[:19], "%Y-%m-%d %H:%M:%S")
        cool = int(alert.get("cooldown_sec") or 300)
        return (datetime.now() - t0).total_seconds() < cool
    except Exception:
        return False


@router.get("/alerts")
def alerts_list():
    """全部监控规则。"""
    return db.list_alerts()


@router.post("/alerts")
def alerts_create(body: AlertBody):
    """新建监控。metric=price/points/change_pct/zhangsu；op=lte(跌到)/gte(涨到)。"""
    code = body.code.strip().upper()
    if body.target_type == "stock" and (len(code) != 6 or not code.isdigit()):
        raise HTTPException(status_code=400, detail="个股代码须为 6 位数字")
    row = db.create_alert(
        body.target_type, code, body.name.strip(), body.metric, body.op,
        body.threshold, body.cooldown_sec, body.note.strip(),
    )
    return {"ok": True, "alert": row}


@router.put("/alerts/{alert_id}")
def alerts_update(alert_id: int, body: AlertPatchBody):
    """更新监控规则。"""
    if not db.get_alert(alert_id):
        raise HTTPException(status_code=404, detail="监控不存在")
    fields = body.model_dump(exclude_none=True)
    if "enabled" in fields:
        fields["enabled"] = 1 if fields["enabled"] else 0
    row = db.update_alert(alert_id, **fields)
    return {"ok": True, "alert": row}


@router.delete("/alerts/{alert_id}")
def alerts_delete(alert_id: int):
    """删除监控。"""
    db.delete_alert(alert_id)
    return {"ok": True}


@router.get("/alerts/check")
def alerts_check():
    """检查已启用监控是否触发，返回需通知的列表。"""
    triggered = []
    for alert in db.list_alerts(enabled_only=True):
        if _in_cooldown(alert):
            continue
        cur = _alert_current_value(alert)
        if not cur:
            continue
        if not _alert_hit(alert, cur):
            continue
        db.mark_alert_triggered(alert["id"])
        metric = alert.get("metric") or "price"
        val = cur.get(metric if metric != "points" else "price")
        triggered.append({
            "id": alert["id"],
            "target_type": alert["target_type"],
            "code": alert["code"],
            "name": cur.get("name") or alert.get("name") or alert["code"],
            "metric": metric,
            "op": alert["op"],
            "threshold": alert["threshold"],
            "current": val,
            "change_pct": cur.get("change_pct"),
            "price": cur.get("price"),
            "note": alert.get("note") or "",
        })
    return {"triggered": triggered, "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}
