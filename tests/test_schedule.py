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


def test_lhb_multi_slot_auto_sync():
    from unittest import mock
    from backend.db import store
    from backend.db.lhb_moves import auto_sync_today_if_needed

    store.init_db()
    store.set_setting("lhbAutoSync", "1")
    today = "2026-08-10"  # 周一
    store.set_setting(f"lhbSyncedSlots_{today}", "")

    # 1. 16:00 未到达任何槽位，不触发
    with mock.patch("backend.db.lhb_moves.sync_records_for_dates") as mock_sync:
        now_1600 = datetime.datetime(2026, 8, 10, 16, 0)
        auto_sync_today_if_needed(now_1600)
        mock_sync.assert_not_called()

    # 2. 16:45 到达第一批槽位，触发 16:45
    with mock.patch("backend.db.lhb_moves.sync_records_for_dates", return_value={"written": 10}) as mock_sync:
        now_1645 = datetime.datetime(2026, 8, 10, 16, 45)
        auto_sync_today_if_needed(now_1645)
        mock_sync.assert_called_once_with([today])
        slots = store.get_setting(f"lhbSyncedSlots_{today}")
        assert "16:45" in slots

    # 3. 再次 16:50 运行，已记录 16:45，未到 17:05，不重复触发
    with mock.patch("backend.db.lhb_moves.sync_records_for_dates") as mock_sync:
        now_1650 = datetime.datetime(2026, 8, 10, 16, 50)
        auto_sync_today_if_needed(now_1650)
        mock_sync.assert_not_called()

    # 4. 到达 17:05，触发第二批槽位
    with mock.patch("backend.db.lhb_moves.sync_records_for_dates", return_value={"written": 30}) as mock_sync:
        now_1705 = datetime.datetime(2026, 8, 10, 17, 5)
        auto_sync_today_if_needed(now_1705)
        mock_sync.assert_called_once_with([today])
        slots = store.get_setting(f"lhbSyncedSlots_{today}")
        assert "17:05" in slots and "16:45" in slots
