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
from backend.analyzer.screener import RULES, run_screen, clear_runs


def test_screener_rules_list():
    assert "breakout" in RULES
    assert "golden_cross" in RULES
    assert "volume_surge" in RULES
    assert "ma_bullish" in RULES
    assert "main_inflow_surge" in RULES
    assert "active_turnover" in RULES
    assert "small_cap_leader" in RULES
    assert "bullish_engulfing" in RULES
    assert "pullback_support" in RULES
    assert "box_breakout" in RULES
    assert "macd_zero_cross" in RULES
    assert "oversold_rebound" in RULES


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


def test_run_screen_local_engine_and_filters():
    store.init_db()
    conn = store.get_conn()

    # 构造模拟股票（主板、科创板、ST股）
    conn.execute("INSERT OR REPLACE INTO stocks(code, name, is_st, classify) VALUES ('600999', '测试牛股', 0, 'AStock')")
    conn.execute("INSERT OR REPLACE INTO stocks(code, name, is_st, classify) VALUES ('688001', '科创龙头', 0, 'AStock')")
    conn.execute("INSERT OR REPLACE INTO stocks(code, name, is_st, classify) VALUES ('600000', '*ST测试', 1, 'AStock')")

    def _make_bars(code, base_p=10.0):
        bars = []
        base_date = datetime.date(2026, 7, 1)
        for i in range(30):
            d_str = (base_date + datetime.timedelta(days=i)).isoformat()
            close = base_p + i * 0.2
            vol = 10_000_000 + (20_000_000 if i == 29 else 0)
            amount = close * vol
            bars.append((code, d_str, close - 0.1, close + 0.2, close - 0.2, close, vol, amount))
        return bars

    all_bars = _make_bars("600999") + _make_bars("688001") + _make_bars("600000")
    conn.executemany(
        "INSERT OR REPLACE INTO daily_bars(code, trade_date, open, high, low, close, volume, amount) VALUES (?,?,?,?,?,?,?,?)",
        all_bars,
    )
    conn.commit()

    # 1. 默认过滤 ST，排除 600000
    res = run_screen(["breakout", "volume_surge", "ma_bullish"], scope="all", filters={"exclude_st": True, "exclude_kcb": False})
    hit_codes = [it["code"] for it in res.get("items", [])]
    assert "600999" in hit_codes
    assert "688001" in hit_codes
    assert "600000" not in hit_codes

    # 2. 开启排除科创板，排除 688001
    res2 = run_screen(["breakout"], scope="all", filters={"exclude_st": True, "exclude_kcb": True})
    hit_codes2 = [it["code"] for it in res2.get("items", [])]
    assert "600999" in hit_codes2
    assert "688001" not in hit_codes2

    # 3. 验证默认交集模式 (match_mode="and") vs 并集模式 (match_mode="or")
    res_and = run_screen(["breakout", "volume_surge"], scope="all", filters={"match_mode": "and", "exclude_st": True, "exclude_kcb": False})
    assert res_and["match_mode"] == "and"
    for it in res_and["items"]:
        assert len(it["hit_rules"]) >= 2

    # 4. 测试清空归档
    clear_runs()
    runs_cnt = conn.execute("SELECT COUNT(*) FROM screener_runs").fetchone()[0]
    assert runs_cnt == 0
