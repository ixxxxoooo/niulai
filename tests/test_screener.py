"""量化选股与日 K 极速批量同步测试"""
import datetime
from unittest import mock
import pytest

from backend.db import store
from backend.db.daily_sync import (
    sync_today_bars_bulk,
    auto_sync_daily_bars_if_needed,
    daily_sync_status,
)
from backend.analyzer.screener import RULES, run_screen


def test_screener_rules_list():
    assert "breakout" in RULES
    assert "golden_cross" in RULES
    assert "volume_surge" in RULES
    assert "ma_bullish" in RULES
    assert "pullback_support" in RULES


def test_sync_today_bars_bulk_mocked():
    store.init_db()
    fake_clist = [
        {"f12": "600519", "f14": "贵州茅台", "f2": 1800.0, "f17": 1790.0, "f15": 1810.0, "f16": 1785.0, "f5": 50000, "f6": 900000000},
        {"f12": "000001", "f14": "平安银行", "f2": 12.5, "f17": 12.3, "f15": 12.6, "f16": 12.2, "f5": 1000000, "f6": 125000000},
    ]
    with mock.patch("backend.datasource.eastmoney.EastMoneyClient._clist_all_pages", return_value=fake_clist):
        written = sync_today_bars_bulk(trade_date="2026-08-19")
        assert written == 2
        st = daily_sync_status()
        assert st["stock_count"] >= 2
        assert st["latest_date"] == "2026-08-19"


def test_auto_sync_daily_bars_schedule():
    store.init_db()
    store.set_setting("dailyBarsAutoSync", "1")
    today = "2026-08-10"  # 周一
    store.set_setting(f"dailyBarsSynced_{today}", "")

    # 1. 14:00 盘中未收盘，不触发
    with mock.patch("backend.db.daily_sync.sync_today_bars_bulk") as mock_sync:
        now_1400 = datetime.datetime(2026, 8, 10, 14, 0)
        auto_sync_daily_bars_if_needed(now_1400)
        mock_sync.assert_not_called()

    # 2. 15:30 达到收盘时间点，触发批量同步并写入 settings 标记
    with mock.patch("backend.db.daily_sync.sync_today_bars_bulk", return_value=5000) as mock_sync:
        now_1530 = datetime.datetime(2026, 8, 10, 15, 30)
        auto_sync_daily_bars_if_needed(now_1530)
        mock_sync.assert_called_once_with(today)
        assert store.get_setting(f"dailyBarsSynced_{today}") is not None

    # 3. 15:35 再次运行，已标记今日完成，不重复触发
    with mock.patch("backend.db.daily_sync.sync_today_bars_bulk") as mock_sync:
        now_1535 = datetime.datetime(2026, 8, 10, 15, 35)
        auto_sync_daily_bars_if_needed(now_1535)
        mock_sync.assert_not_called()


def test_run_screen_local_engine():
    store.init_db()
    conn = store.get_conn()
    
    # 构造模拟股票与 30 日模拟日 K
    code = "600999"
    conn.execute("INSERT OR REPLACE INTO stocks(code, name, classify) VALUES (?, ?, 'AStock')", (code, "测试牛股"))
    
    # 模拟均线多头上升形态且成交量/额达标（>1亿）
    bars = []
    base_date = datetime.date(2026, 7, 1)
    for i in range(30):
        d_str = (base_date + datetime.timedelta(days=i)).isoformat()
        close = 10.0 + i * 0.2  # 稳步上升
        vol = 10_000_000 + (20_000_000 if i == 29 else 0)
        amount = close * vol  # > 1 亿
        bars.append((code, d_str, close - 0.1, close + 0.2, close - 0.2, close, vol, amount))

    conn.executemany(
        "INSERT OR REPLACE INTO daily_bars(code, trade_date, open, high, low, close, volume, amount) VALUES (?,?,?,?,?,?,?,?)",
        bars,
    )
    conn.commit()

    # 运行选股
    res = run_screen(["breakout", "volume_surge", "ma_bullish"], scope="all")
    assert res["scanned"] >= 1
    assert "hits" in res
    assert len(res["hits"].get("breakout", [])) >= 1
    assert len(res["hits"].get("volume_surge", [])) >= 1
    assert len(res["hits"].get("ma_bullish", [])) >= 1
