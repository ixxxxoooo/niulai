"""交易与财经日历事件算法推算引擎

实现国家级与交易所标准规则事件的 100% 确定性纯算法推算：
- 股指期货/期权交割日（中金所 IF/IC/IH/IM）：每月第 3 个星期五
- ETF期权到期交割日（上交所/深交所 50ETF/300ETF 等）：每月第 4 个星期三
- 美股四巫日（指数/个股期货期权同日交割）：每年 3/6/9/12 月第 3 个星期五
- 央行 LPR 贷款市场报价利率发布：每月 20 日 09:00
- 官方制造业 PMI 发布：每月最后一天 09:30
- A 股法定节假日休市与调休

@author ygw
"""
import calendar
import datetime
from typing import Any, Dict, List, Optional

from . import schedule
from .. import config


def _get_nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> datetime.date:
    """获取某年某月的第 n 个特定星期几（weekday: 0=周一, 4=周五, 2=周三）。"""
    cal = calendar.monthcalendar(year, month)
    count = 0
    for week in cal:
        day = week[weekday]
        if day != 0:
            count += 1
            if count == n:
                return datetime.date(year, month, day)
    # 理论上不会发生，兜底返回月末
    last_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, last_day)


def _adjust_to_next_trading_day(d: datetime.date) -> datetime.date:
    """若指定日期非交易日（周末或法定节假日），则依次顺延至下一个交易日。"""
    cur = d
    for _ in range(30):
        if schedule.is_trading_day(cur):
            return cur
        cur += datetime.timedelta(days=1)
    return d


def _generate_events_for_month(year: int, month: int) -> List[Dict[str, Any]]:
    """生成指定年月的关键日历事件。"""
    events = []

    # 1. 中金所股指期货/期权交割日（每月第 3 个星期五）
    raw_if_date = _get_nth_weekday_of_month(year, month, 4, 3)
    if_date = _adjust_to_next_trading_day(raw_if_date)
    is_delayed_if = if_date != raw_if_date
    events.append({
        "id": f"futures_{year}_{month:02d}",
        "date": if_date.isoformat(),
        "raw_date": raw_if_date.isoformat(),
        "type": "derivative",
        "type_label": "衍生品交割",
        "badge_color": "danger",
        "title": f"{month}月 股指期货/期权交割日",
        "target": "IF / IH / IC / IM 股指合约",
        "time_desc": "全天交易 · 14:00~15:00 尾盘多空决战",
        "summary": "中金所沪深300(IF)、上证50(IH)、中证500(IC)、中证1000(IM)期货与期权主力合约最后交易日与交割日。"
                   + (" (因节假日顺延)" if is_delayed_if else ""),
        "tips": "交割日效应：主力资金移仓换月或平仓，尾盘极易出现多空博弈导致标的指数放量波动。短线选手宜轻仓防范异动。",
    })

    # 2. ETF 期权 / 股票期权到期日（每月第 4 个星期三）
    raw_etf_date = _get_nth_weekday_of_month(year, month, 2, 4)
    etf_date = _adjust_to_next_trading_day(raw_etf_date)
    is_delayed_etf = etf_date != raw_etf_date
    events.append({
        "id": f"etf_opt_{year}_{month:02d}",
        "date": etf_date.isoformat(),
        "raw_date": raw_etf_date.isoformat(),
        "type": "derivative",
        "type_label": "衍生品交割",
        "badge_color": "danger",
        "title": f"{month}月 ETF/股票期权行权交割日",
        "target": "50ETF / 300ETF / 500ETF / 创业板ETF期权",
        "time_desc": "行权日 · 现货收盘后进行清算",
        "summary": "上交所/深交所股票期权与 ETF 期权合约到期日与行权日。" + (" (因节假日顺延)" if is_delayed_etf else ""),
        "tips": "期权末日轮：虚值期权时间价值归零，平值/实值期权围绕行权价博弈剧烈，标的 ETF 常出现压盘或磁吸现象。",
    })

    # 3. 美股四巫日（3/6/9/12 月第 3 个星期五）
    if month in (3, 6, 9, 12):
        quad_date = _get_nth_weekday_of_month(year, month, 4, 3)
        events.append({
            "id": f"quad_{year}_{month:02d}",
            "date": quad_date.isoformat(),
            "raw_date": quad_date.isoformat(),
            "type": "global",
            "type_label": "国际大事件",
            "badge_color": "warning",
            "title": f"{month}月 美股四巫日 (Quadruple Witching)",
            "target": "美股股指期货/期权 + 个股期货/期权",
            "time_desc": "美东时间 16:00 (北京时间次日凌晨 04:00)",
            "summary": "美股四大衍生品同日到期清算，全球金融资产成交量激增。",
            "tips": "美股单日成交额与波动率往往创季度峰值，需关注次日早盘 A 股开盘情绪联动。",
        })

    # 4. 央行 LPR 贷款市场报价利率（每月 20 日）
    raw_lpr_date = datetime.date(year, month, 20)
    lpr_date = _adjust_to_next_trading_day(raw_lpr_date)
    events.append({
        "id": f"lpr_{year}_{month:02d}",
        "date": lpr_date.isoformat(),
        "raw_date": raw_lpr_date.isoformat(),
        "type": "macro",
        "type_label": "央行与利率",
        "badge_color": "primary",
        "title": f"{month}月 央行 LPR 报价利率发布",
        "target": "1年期 LPR / 5年期以上 LPR",
        "time_desc": "09:00 准时发布",
        "summary": "中国人民银行授权全国银行间同业拆借中心公布最新贷款市场报价利率。",
        "tips": "5年期 LPR 直接锚定房贷利率，1年期锚定企业贷款利率。降息或维持不变直接影响银行、地产与大金融板块。",
    })

    # 5. 官方制造业 PMI（每月最后一天）
    last_day = calendar.monthrange(year, month)[1]
    raw_pmi_date = datetime.date(year, month, last_day)
    # PMI 通常在月末最后一天或顺延至次月首个工作日
    events.append({
        "id": f"pmi_{year}_{month:02d}",
        "date": raw_pmi_date.isoformat(),
        "raw_date": raw_pmi_date.isoformat(),
        "type": "macro",
        "type_label": "宏观景气",
        "badge_color": "success",
        "title": f"{month}月 官方制造业/非制造业 PMI",
        "target": "国家统计局 制造业经理指数",
        "time_desc": "09:30 准时发布",
        "summary": "国家统计局公布当月中采购经理指数，50% 为荣枯分界线。",
        "tips": "PMI>50% 扩张、<50% 收缩。超预期景气度通常对有色、化工、工程机械等顺周期品种形成直接催化。",
    })

    return events


def get_calendar_events(start_date: Optional[datetime.date] = None, months_ahead: int = 4) -> Dict[str, Any]:
    """生成从当前日期起未来若干个月的完整日历事件与焦点倒计时。"""
    today = start_date or datetime.date.today()
    all_events = []

    # 遍历当前月及未来几个月
    cur_year = today.year
    cur_month = today.month

    for _ in range(months_ahead):
        month_events = _generate_events_for_month(cur_year, cur_month)
        all_events.extend(month_events)
        if cur_month == 12:
            cur_year += 1
            cur_month = 1
        else:
            cur_month += 1

    # 补充节假日休市事件
    holidays_set = sorted(list(config.TRADING_HOLIDAYS))
    for h_str in holidays_set:
        try:
            h_date = datetime.date.fromisoformat(h_str)
            if h_date >= today - datetime.timedelta(days=7):
                all_events.append({
                    "id": f"holiday_{h_str}",
                    "date": h_str,
                    "raw_date": h_str,
                    "type": "holiday",
                    "type_label": "节假日休市",
                    "badge_color": "warning",
                    "title": "A 股法定节假日休市",
                    "target": "沪深京全市场休市",
                    "time_desc": "全天休市",
                    "summary": f"A 股证券交易所休市日 ({h_str})，暂停交易。",
                    "tips": "节前资金通常有避险或结算需求，成交量往往提前缩量。",
                })
        except Exception:
            pass

    # 计算倒计时 days_left 并排序
    enriched = []
    for ev in all_events:
        ev_date = datetime.date.fromisoformat(ev["date"])
        diff_days = (ev_date - today).days
        ev["days_left"] = diff_days
        if diff_days == 0:
            ev["status_text"] = "今日发生"
            ev["status_cls"] = "today"
        elif diff_days > 0:
            ev["status_text"] = f"还有 {diff_days} 天"
            ev["status_cls"] = "future"
        else:
            ev["status_text"] = f"已过 {abs(diff_days)} 天"
            ev["status_cls"] = "past"
        enriched.append(ev)

    # 按事件日期升序排列
    enriched.sort(key=lambda x: (x["date"], x["type"]))

    # 提取未来核心焦点倒计时卡片（期货交割、期权行权、LPR、下一休市）
    def _find_next(type_filter, id_filter=None):
        for e in enriched:
            if e["days_left"] >= 0:
                if id_filter and id_filter in e["id"]:
                    return e
                elif not id_filter and e["type"] == type_filter:
                    return e
        return None

    next_futures = _find_next("derivative", "futures")
    next_option = _find_next("derivative", "etf_opt")
    next_lpr = _find_next("macro", "lpr")
    next_holiday = _find_next("holiday")

    hero_cards = []
    if next_futures:
        hero_cards.append({
            "key": "futures",
            "icon": "fire",
            "badge": "重磅交割",
            "badge_color": "danger",
            "title": "股指期货交割日",
            "target": next_futures["target"],
            "date": next_futures["date"],
            "days_left": next_futures["days_left"],
            "status_text": next_futures["status_text"],
            "desc": next_futures["summary"],
            "tip": next_futures["tips"],
        })
    if next_option:
        hero_cards.append({
            "key": "option",
            "icon": "target",
            "badge": "期权行权",
            "badge_color": "warning",
            "title": "ETF期权行权日",
            "target": next_option["target"],
            "date": next_option["date"],
            "days_left": next_option["days_left"],
            "status_text": next_option["status_text"],
            "desc": next_option["summary"],
            "tip": next_option["tips"],
        })
    if next_lpr:
        hero_cards.append({
            "key": "lpr",
            "icon": "bank",
            "badge": "央行利率",
            "badge_color": "primary",
            "title": "LPR 利率发布",
            "target": next_lpr["target"],
            "date": next_lpr["date"],
            "days_left": next_lpr["days_left"],
            "status_text": next_lpr["status_text"],
            "desc": next_lpr["summary"],
            "tip": next_lpr["tips"],
        })
    if next_holiday:
        hero_cards.append({
            "key": "holiday",
            "icon": "calendar",
            "badge": "法定休市",
            "badge_color": "neutral",
            "title": "下一休市日",
            "target": next_holiday["target"],
            "date": next_holiday["date"],
            "days_left": next_holiday["days_left"],
            "status_text": next_holiday["status_text"],
            "desc": next_holiday["summary"],
            "tip": next_holiday["tips"],
        })

    return {
        "today": today.isoformat(),
        "hero_cards": hero_cards,
        "events": enriched,
        "total": len(enriched),
    }
