"""交易时段与节假日判断测试"""
import datetime

from backend.analyzer import schedule


def test_weekday_morning_session():
    # 2026-08-10 是周一
    now = datetime.datetime(2026, 8, 10, 10, 0)
    assert schedule.is_trading_day(now.date())
    assert schedule.is_trading_time(now)
    assert schedule.session_label(now) == "上午盘中"


def test_weekend_not_trading():
    # 2026-08-15 周六
    now = datetime.datetime(2026, 8, 15, 10, 0)
    assert not schedule.is_trading_day(now.date())
    assert not schedule.is_trading_time(now)
    assert schedule.session_label(now) == "休市"


def test_lunch_break():
    now = datetime.datetime(2026, 8, 10, 12, 0)
    assert not schedule.is_trading_time(now)
    assert schedule.session_label(now) == "午间休市"


def test_afternoon_session():
    now = datetime.datetime(2026, 8, 10, 14, 30)
    assert schedule.is_trading_time(now)
    assert schedule.session_label(now) == "下午盘中"


def test_closed_after_1500():
    now = datetime.datetime(2026, 8, 10, 15, 30)
    assert not schedule.is_trading_time(now)
    assert schedule.session_label(now) == "已收盘"


def test_holiday_config():
    # 配置中的节假日（2026-01-01 元旦）
    assert not schedule.is_trading_day(datetime.date(2026, 1, 1))
    # 未配置的普通工作日
    assert schedule.is_trading_day(datetime.date(2026, 8, 14))
