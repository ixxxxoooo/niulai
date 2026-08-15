"""飞书自定义机器人 Webhook 推送（交互卡片）
@author ygw
"""
import httpx
from typing import List, Dict, Optional

from ..logging_config import logger
from ..db import store as db

_TIMEOUT = 5.0


def _get_webhook() -> Optional[str]:
    """从 settings 读取飞书 Webhook URL，未配置或关闭则返回 None。"""
    enabled = db.get_setting("feishu_enabled", "0")
    if enabled != "1":
        return None
    url = (db.get_setting("feishu_webhook") or "").strip()
    if not url:
        return None
    return url


def _base_url() -> str:
    """卡片中跳转链接的基址。"""
    return (db.get_setting("public_base_url") or "http://127.0.0.1:8088").rstrip("/")


def send_card(webhook_url: str, title: str, fields: List[Dict[str, str]],
              link: str = "", color: str = "red") -> bool:
    """
    向飞书 Webhook 发送交互卡片消息。

    参数:
        webhook_url: 飞书机器人 Webhook 地址
        title: 卡片标题
        fields: 字段列表，每项 {"label": "标的", "value": "贵州茅台 600519"}
        link: 可选跳转链接
        color: 卡片颜色模板（red/blue/green/yellow）

    返回:
        是否发送成功
    """
    elements = []
    for f in fields:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**{f['label']}**：{f['value']}",
            },
        })
    if link:
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": "查看详情"},
                "url": link,
                "type": "primary",
            }],
        })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": elements,
        },
    }

    try:
        resp = httpx.post(webhook_url, json=payload, timeout=_TIMEOUT)
        body = resp.json()
        if body.get("code") != 0 and body.get("StatusCode") != 0:
            logger.warning("飞书推送响应异常: %s", body)
            return False
        logger.info("飞书推送成功: %s", title)
        return True
    except Exception as e:
        logger.warning("飞书推送失败: %s %s", title, e)
        return False


def send_alert(item: dict) -> bool:
    """
    推送监控告警到飞书。

    参数:
        item: alerts_check 返回的 triggered 项
              包含 code, name, metric, op, threshold, current, change_pct, note
    返回:
        是否成功
    """
    webhook = _get_webhook()
    if not webhook:
        return False

    metric_labels = {
        "price": "价格", "points": "点数",
        "change_pct": "涨跌幅", "zhangsu": "涨速",
    }
    metric = item.get("metric") or "price"
    op_label = "≥" if item.get("op") == "gte" else "≤"
    name = item.get("name") or item.get("code") or ""
    code = item.get("code") or ""

    fields = [
        {"label": "标的", "value": f"{name}（{code}）"},
        {"label": "触发条件", "value": f"{metric_labels.get(metric, metric)} {op_label} {item.get('threshold')}"},
        {"label": "当前值", "value": str(item.get("current", ""))},
    ]
    if item.get("change_pct") is not None:
        fields.append({"label": "涨跌幅", "value": f"{item['change_pct']}%"})
    if item.get("note"):
        fields.append({"label": "备注", "value": item["note"]})

    target_type = item.get("target_type") or "stock"
    base = _base_url()
    if target_type == "index":
        link = f"{base}/#/index/{code}"
    else:
        link = f"{base}/#/stock/{code}"

    return send_card(webhook, f"盯盘提醒 · {name}", fields, link=link)


def send_screener_result(rule_name: str, hits: List[dict]) -> bool:
    """
    盘后选股结果推送飞书。

    参数:
        rule_name: 规则名（如"突破"、"金叉"）
        hits: 命中列表，每项含 code, name, close, change_pct

    返回:
        是否成功
    """
    webhook = _get_webhook()
    if not webhook:
        return False

    if not hits:
        return True

    base = _base_url()
    lines = []
    for h in hits[:20]:
        name = h.get("name") or h.get("code")
        code = h.get("code") or ""
        close = h.get("close", "")
        pct = h.get("change_pct", "")
        pct_str = f" {pct}%" if pct else ""
        lines.append(f"[{name}]({base}/#/stock/{code})  {close}{pct_str}")

    more = f"\n\n共 {len(hits)} 只" if len(hits) > 20 else ""

    fields = [
        {"label": "命中数", "value": str(len(hits))},
        {"label": "个股", "value": "\n".join(lines) + more},
    ]

    return send_card(webhook, f"盯盘选股 · {rule_name}", fields,
                     link=f"{base}/#/screener", color="blue")


def send_test() -> dict:
    """
    发送测试卡片，用于设置页验证 Webhook 配置。

    返回:
        {"ok": bool, "message": str}
    """
    webhook = _get_webhook()
    if not webhook:
        return {"ok": False, "message": "未配置或未启用飞书 Webhook"}

    ok = send_card(
        webhook,
        "盯盘 · 测试推送",
        [{"label": "状态", "value": "Webhook 配置正确，推送通道正常"}],
        link=_base_url(),
        color="green",
    )
    return {"ok": ok, "message": "发送成功" if ok else "发送失败，请检查 Webhook URL"}
