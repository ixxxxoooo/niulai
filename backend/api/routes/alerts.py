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
    # 飞书双通道推送
    for item in triggered:
        try:
            from ...notify.feishu import send_alert
            send_alert(item)
        except Exception:
            pass

    return {"triggered": triggered, "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}


# ── 持仓股异动监控 ──

_change_notified: dict = {}  # {code:type_code: last_ts} 避免重复通知
_CHANGE_COOLDOWN = 120       # 同一只股票同类异动冷却 120 秒


@router.get("/alerts/check-changes")
def alerts_check_changes():
    """
    检查持仓股是否出现异动（大笔买卖/急速拉升跳水等），
    命中后返回 + 飞书推送。前端轮询调用。
    @author ygw
    """
    enabled = db.get_setting("changes_monitor_enabled", "1")
    if enabled != "1":
        return {"changes": [], "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 取持仓代码集合
    positions = db.list_positions()
    if not positions:
        return {"changes": [], "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    pos_codes = {p["code"] for p in positions}

    # 关注的异动类型（可配置，默认只关注大笔和急速类）
    watch_types_str = db.get_setting("changes_watch_types",
                                     "8201,8202,8193,8204,8203,8211,8212,4,64,8208,8210")
    watch_types = set(watch_types_str.split(",")) if watch_types_str else set()

    # 拉取最新异动
    all_changes = eastmoney.get_client().stock_changes(200)

    now_ts = time.time()
    matched = []
    for c in all_changes:
        code = c.get("code") or ""
        if code not in pos_codes:
            continue
        type_code = c.get("type_code") or ""
        if watch_types and type_code not in watch_types:
            continue

        # 冷却判断
        ck = f"{code}:{type_code}"
        last = _change_notified.get(ck, 0)
        if now_ts - last < _CHANGE_COOLDOWN:
            continue
        _change_notified[ck] = now_ts

        matched.append(c)

    # 清理过期冷却记录
    for k in list(_change_notified):
        if now_ts - _change_notified[k] > 600:
            del _change_notified[k]

    # 飞书推送
    if matched:
        try:
            from ...notify.feishu import send_card, _get_webhook, _base_url
            webhook = _get_webhook()
            if webhook:
                base = _base_url()
                fields = []
                for m in matched[:10]:
                    name = m.get("name") or m.get("code")
                    code = m.get("code") or ""
                    pct = m.get("change_pct")
                    pct_str = f" ({pct}%)" if pct is not None else ""
                    fields.append({
                        "label": m.get("type_name") or "异动",
                        "value": f"[{name}]({base}/#/stock/{code}){pct_str}  {m.get('time', '')}",
                    })
                if len(matched) > 10:
                    fields.append({"label": "更多", "value": f"共 {len(matched)} 条异动"})
                send_card(webhook, "盯盘 · 持仓异动提醒", fields,
                          link=f"{base}/#/rank/changes", color="red")
        except Exception:
            pass

    return {"changes": matched, "checked_at": time.strftime("%Y-%m-%d %H:%M:%S")}
