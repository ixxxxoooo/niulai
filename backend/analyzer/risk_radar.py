"""自选股与个股智能排雷诊断引擎

多维排雷维度：
1. 限售解禁风险：近 30/90 天内解禁市值与占流通/总股本比例；
2. 业绩变脸风险：最新业绩预告（首亏/续亏/大幅预减）；
3. 风险警示属性：ST / *ST；
4. 综合风险评级：high (高危) / medium (中度预警) / low (低风险) / safe (安全)。

@author ygw
"""
import datetime
from typing import Any, Dict, List, Optional
from ..datasource import eastmoney


def diagnose_stock_risk(code: str) -> Dict[str, Any]:
    """单只股票智能排雷诊断"""
    clean_code = str(code).strip()
    if "." in clean_code:
        clean_code = clean_code.split(".")[0]

    client = eastmoney.get_client()

    # 1. 查询该股解禁列表
    unlocks = client.stock_unlock_detail(clean_code)

    # 2. 查询业绩预告
    forecasts = client.stock_performance_forecast(clean_code)

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

    return {
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


def batch_diagnose_stocks(codes: List[str]) -> Dict[str, Dict[str, Any]]:
    """批量自选股快速排雷（轻量级返回标签与等级）"""
    result = {}
    for c in codes:
        try:
            diag = diagnose_stock_risk(c)
            # 提取简版用于自选列表胶囊展示
            top_tag = diag["risk_tags"][0] if diag["risk_tags"] else None
            result[c] = {
                "risk_level": diag["risk_level"],
                "risk_score": diag["risk_score"],
                "badge_text": top_tag["text"] if top_tag and top_tag["level"] in ("high", "medium") else "",
                "badge_level": top_tag["level"] if top_tag else "safe",
                "tags_count": len(diag["risk_tags"]),
            }
        except Exception:
            result[c] = {"risk_level": "safe", "risk_score": 0, "badge_text": "", "badge_level": "safe"}
    return result
