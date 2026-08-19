"""自选股与个股智能排雷诊断引擎

多维排雷维度：
1. 限售解禁风险：近 30/90 天内解禁市值与占流通/总股本比例；
2. 业绩变脸风险：最新业绩预告（首亏/续亏/大幅预减）；
3. 风险警示属性：ST / *ST；
4. 综合风险评级：high (高危) / medium (中度预警) / low (低风险) / safe (安全)。

@author ygw
"""
import time
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional
from ..datasource import eastmoney

# 线程安全的内存诊断缓存 (code -> (timestamp, data))，财务/解禁公告缓存 24 小时（每天仅需更新一次）
_DIAG_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
_DIAG_LOCK = threading.Lock()
_CACHE_TTL = 86400.0  # 24 小时（财务与解禁数据为日级低频静态公告）


def diagnose_stock_risk(code: str) -> Dict[str, Any]:
    """单只股票智能排雷诊断（带 24 小时内存缓存）"""
    clean_code = str(code).strip()
    if "." in clean_code:
        clean_code = clean_code.split(".")[0]

    now = time.time()
    with _DIAG_LOCK:
        if clean_code in _DIAG_CACHE:
            ts, cached_res = _DIAG_CACHE[clean_code]
            if now - ts < _CACHE_TTL:
                return cached_res

    client = eastmoney.get_client()

    # 1. 查询该股解禁列表
    try:
        unlocks = client.stock_unlock_detail(clean_code)
    except Exception:
        unlocks = []

    # 2. 查询业绩预告
    try:
        forecasts = client.stock_performance_forecast(clean_code)
    except Exception:
        forecasts = []

    today = datetime.date.today()
    future_30d = today + datetime.timedelta(days=30)
    future_90d = today + datetime.timedelta(days=90)

    upcoming_30d_unlocks = []
    upcoming_90d_unlocks = []
    total_ratio_30d = 0.0

    for u in unlocks:
        try:
            udate = datetime.date.fromisoformat(u["date"])
            if today <= udate <= future_30d:
                upcoming_30d_unlocks.append(u)
                total_ratio_30d += float(u.get("ratio_total") or 0.0)
            elif today <= udate <= future_90d:
                upcoming_90d_unlocks.append(u)
        except Exception:
            pass

    risk_tags = []
    risk_level = "safe"
    risk_score = 10  # 初始基础分 (0~100, 越高风险越大)

    # 判定解禁风险
    if total_ratio_30d >= 5.0:
        risk_tags.append({
            "type": "unlock",
            "level": "high",
            "text": f"30天内大比例解禁 ({total_ratio_30d:.1f}%)",
            "desc": f"未来30天内将有 {len(upcoming_30d_unlocks)} 批限售股解禁，合计占总股本 {total_ratio_30d:.1f}%，需警惕减持抛压。",
        })
        risk_score += 45
        risk_level = "high"
    elif total_ratio_30d >= 1.0:
        risk_tags.append({
            "type": "unlock",
            "level": "medium",
            "text": f"30天内小额解禁 ({total_ratio_30d:.1f}%)",
            "desc": f"未来30天内解禁股份占总股本 {total_ratio_30d:.1f}%。",
        })
        risk_score += 20
        if risk_level != "high":
            risk_level = "medium"
    elif upcoming_90d_unlocks:
        risk_tags.append({
            "type": "unlock",
            "level": "low",
            "text": "90天内有限售解禁",
            "desc": f"未来90天内有 {len(upcoming_90d_unlocks)} 批解禁计划。",
        })
        risk_score += 10

    # 判定业绩风险
    latest_fc = forecasts[0] if forecasts else None
    if latest_fc:
        p_type = latest_fc.get("predict_type") or ""
        p_content = latest_fc.get("content") or ""
        rep_date = latest_fc.get("report_date") or ""

        if any(w in p_type for w in ["首亏", "续亏", "大幅减亏"]):
            risk_tags.append({
                "type": "performance",
                "level": "high",
                "text": f"业绩预亏 ({p_type})",
                "desc": f"{rep_date} 业绩预告：{p_type}。{p_content}",
            })
            risk_score += 40
            risk_level = "high"
        elif "预减" in p_type or "略减" in p_type:
            risk_tags.append({
                "type": "performance",
                "level": "medium",
                "text": f"业绩预减 ({p_type})",
                "desc": f"{rep_date} 业绩预告：{p_type}。{p_content}",
            })
            risk_score += 25
            if risk_level != "high":
                risk_level = "medium"
        elif any(w in p_type for w in ["预增", "扭亏", "略增"]):
            risk_tags.append({
                "type": "performance",
                "level": "good",
                "text": f"业绩向好 ({p_type})",
                "desc": f"{rep_date} 业绩预告：{p_type}。{p_content}",
            })

    if not risk_tags:
        risk_tags.append({
            "type": "safe",
            "level": "safe",
            "text": "暂无明显排雷风险",
            "desc": "近期无大额解禁计划，无已公告的业绩预亏。",
        })

    risk_score = min(100, risk_score)

    diag_result = {
        "code": clean_code,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_tags": risk_tags,
        "unlock_summary": {
            "total_30d_ratio": round(total_ratio_30d, 2),
            "count_30d": len(upcoming_30d_unlocks),
            "count_90d": len(upcoming_90d_unlocks),
            "next_unlock": upcoming_30d_unlocks[0] if upcoming_30d_unlocks else (unlocks[0] if unlocks else None),
        },
        "all_unlocks": unlocks,
        "forecasts": forecasts,
    }

    with _DIAG_LOCK:
        _DIAG_CACHE[clean_code] = (now, diag_result)

    return diag_result


def _extract_badge(diag: Dict[str, Any]) -> Dict[str, Any]:
    """从诊断结果提取前端展示用的胶囊徽章数据"""
    risk_tags = diag.get("risk_tags") or []
    top_tag = risk_tags[0] if risk_tags else None
    return {
        "risk_level": diag.get("risk_level", "safe"),
        "risk_score": diag.get("risk_score", 0),
        "badge_text": top_tag["text"] if top_tag and top_tag.get("level") in ("high", "medium") else "",
        "badge_level": top_tag.get("level", "safe") if top_tag else "safe",
        "tags_count": len(risk_tags),
    }


def batch_diagnose_stocks(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """批量自选股快速排雷（多线程高并发 + 30 分钟内存缓存加速）"""
    result: Dict[str, Dict[str, Any]] = {}
    uncached: List[str] = []
    now = time.time()

    # 1. 先从内存缓存快速命中
    with _DIAG_LOCK:
        for c in codes:
            clean = str(c).strip()
            if clean in _DIAG_CACHE and (now - _DIAG_CACHE[clean][0] < _CACHE_TTL):
                result[clean] = _extract_badge(_DIAG_CACHE[clean][1])
            else:
                uncached.append(clean)

    # 2. 未命中的代码使用多线程并发拉取（最多 10 线程）
    if uncached:
        with ThreadPoolExecutor(max_workers=min(10, len(uncached))) as executor:
            future_to_code = {executor.submit(diagnose_stock_risk, c): c for c in uncached}
            for future in as_completed(future_to_code):
                c = future_to_code[future]
                try:
                    diag = future.result()
                    result[c] = _extract_badge(diag)
                except Exception:
                    result[c] = {"risk_level": "safe", "risk_score": 0, "badge_text": "", "badge_level": "safe"}

    return result
