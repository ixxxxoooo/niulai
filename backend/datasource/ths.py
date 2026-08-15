"""同花顺公开热榜
@author ygw
"""
from typing import Any, Dict, List

import httpx

from .. import config
from ..logging_config import logger

THS_HOT_URL = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"


def fetch_hot_list(kind: str = "hour", limit: int = 50) -> List[Dict[str, Any]]:
    """同花顺 A 股热榜。kind=hour 小时榜 / day 日榜。"""
    kind = "day" if kind == "day" else "hour"
    try:
        resp = httpx.get(
            THS_HOT_URL,
            params={"stock_type": "a", "type": kind, "list_type": "normal"},
            headers={
                "User-Agent": config.USER_AGENT,
                "Referer": "https://eq.10jqka.com.cn/",
            },
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        body = resp.json()
    except Exception as e:
        logger.info("同花顺热榜失败 %s", e)
        return []
    rows = ((body or {}).get("data") or {}).get("stock_list") or []
    out: List[Dict[str, Any]] = []
    for i, it in enumerate(rows[:limit]):
        code = str(it.get("code") or "")
        if not code:
            continue
        analyse = str(it.get("analyse") or "").strip()
        analyse_title = str(it.get("analyse_title") or "").strip()
        # 上游并非每只都有「解读」正文：同花顺只对部分热股配编辑解读。
        # 无正文时依次降级：解读标题 → 概念标签，避免界面大量空白「-」
        if not analyse and analyse_title:
            analyse = analyse_title
        if not analyse:
            tag = it.get("tag") or {}
            if isinstance(tag, str):
                try:
                    import json as _json
                    tag = _json.loads(tag.replace("'", '"'))
                except Exception:
                    tag = {}
            concepts = []
            if isinstance(tag, dict):
                concepts = tag.get("concept_tag") or tag.get("popular_concept_tag") or []
            if isinstance(concepts, list) and concepts:
                analyse = "概念：" + "、".join(str(c) for c in concepts[:4] if c)
        if len(analyse) > 220:
            analyse = analyse[:220] + "…"
        heat = it.get("rate")
        try:
            heat = float(heat) if heat not in (None, "") else None
        except (TypeError, ValueError):
            heat = None
        chg = it.get("rise_and_fall")
        try:
            chg = float(chg) if chg not in (None, "") else None
        except (TypeError, ValueError):
            chg = None
        out.append({
            "rank": i + 1,
            "code": code,
            "name": it.get("name") or "",
            "change_pct": chg,
            "heat": heat,
            "analyse": analyse,
            "analyse_title": analyse_title,
            "source": "ths",
        })
    return out
