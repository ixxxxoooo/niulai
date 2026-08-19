"""后端 API 测试：默认 mock 外部数据源，不连东财/腾讯
@author ygw
"""
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.datasource.models import (
    IndexQuote, OrderBook, SectorQuote, StockDetail, IntradayTrend, TrendPoint,
    MarketOverview,
)


@pytest.fixture(scope="module")
def client():
    from backend.app import create_app
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_trading_time(client):
    r = client.get("/api/trading/time")
    assert r.status_code == 200
    d = r.json()
    assert "is_trading_time" in d
    assert "session" in d


def _fake_overview():
    return MarketOverview(
        indices=[
            IndexQuote(code="000001", name="上证指数", price=3000, change_pct=0.5,
                       high=3010, low=2990, amplitude=0.67),
            IndexQuote(code="399001", name="深证成指", price=10000, change_pct=0.3,
                       high=10010, low=9990, amplitude=0.2),
            IndexQuote(code="399006", name="创业板指", price=2000, change_pct=-0.1,
                       high=2010, low=1990, amplitude=1.0),
            IndexQuote(code="000688", name="科创50", price=1000, change_pct=0.2,
                       high=1010, low=990, amplitude=2.0),
        ],
        total_amount=1.2e12,
        up_count=2000,
        down_count=1500,
        flat_count=100,
        limit_up_count=40,
        quote_time="15:00:00",
    )


def test_market_overview_mocked(client):
    with mock.patch("backend.analyzer.market.market_overview", return_value=_fake_overview()):
        from backend.api.routes.common import clear_cache
        clear_cache()
        r = client.get("/api/market/overview")
    assert r.status_code == 200
    d = r.json()
    assert len(d["indices"]) >= 4
    assert d["total_amount"] > 0
    assert d["up_count"] and d["down_count"]
    assert d["quote_time"]


def test_sectors_mocked(client):
    fake = [
        SectorQuote(code="BK0001", name="白酒", change_pct=2.0, amount=1e10),
        SectorQuote(code="BK0002", name="银行", change_pct=1.0, amount=2e10),
        SectorQuote(code="BK0003", name="半导体", change_pct=0.5, amount=3e10),
        SectorQuote(code="BK0004", name="新能源", change_pct=-0.5, amount=1e10),
        SectorQuote(code="BK0005", name="医药", change_pct=0.2, amount=1e10),
    ]
    with mock.patch("backend.analyzer.sector.sector_list", return_value=fake):
        from backend.api.routes.common import clear_cache
        clear_cache()
        r = client.get("/api/sectors?type=industry&limit=5")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 5
    assert all(s["code"].startswith("BK") for s in items)


def test_stock_detail_mocked(client):
    detail = StockDetail(
        code="600519", name="贵州茅台", price=1600.0, prev_close=1580.0,
        open=1590, high=1610, low=1585, change=20, change_pct=1.27,
        limit_up=1738, limit_down=1422, concepts="白酒",
        orderbook=OrderBook(bid=[{"price": 1599, "volume": 10}], ask=[{"price": 1601, "volume": 8}]),
        data_source="东财+腾讯", fetched_at="10:00:00", main_inflow=1e8,
    )
    with mock.patch("backend.api.routes.stocks._merge_stock_detail", return_value=detail):
        with mock.patch("backend.datasource.eastmoney.get_client") as gc:
            gc.return_value.stock_f10_boards.return_value = {}
            gc.return_value.moneyflow_history.return_value = []
            from backend.api.routes.common import clear_cache
            clear_cache()
            r = client.get("/api/stocks/600519")
    assert r.status_code == 200
    d = r.json()
    assert d["name"] == "贵州茅台"
    assert d["price"] > 0
    assert d["orderbook"]["bid"] and d["orderbook"]["ask"]
    assert d["limit_up"] > d["limit_down"]
    assert d.get("data_source")


def test_stock_trends_mocked(client):
    pts = []
    for i in range(120):
        m = 30 + i
        hh, mm = 9 + m // 60, m % 60
        pts.append(TrendPoint(
            time=f"{hh:02d}:{mm:02d}", price=100+i*0.1, avg=100, volume=100,
            amount=10000, high=101, low=99,
        ))
    td = IntradayTrend(code="600519", name="贵州茅台", pre_close=100.0, points=pts)
    with mock.patch("backend.datasource.eastmoney.get_client") as gc:
        gc.return_value.intraday_trends.return_value = td
        from backend.api.routes.common import clear_cache
        clear_cache()
        r = client.get("/api/stocks/600519/trends")
    assert r.status_code == 200
    d = r.json()
    assert d["pre_close"] > 0
    assert len(d["points"]) > 100


def test_stock_kline_mocked(client):
    points = [
        {"date": f"2026-01-{i+1:02d}", "open": 10, "close": 11, "high": 12, "low": 9, "volume": 1000}
        for i in range(30)
    ]
    k = {"points": points, "name": "贵州茅台"}
    with mock.patch("backend.datasource.eastmoney.get_client") as gc:
        gc.return_value.kline.return_value = k
        with mock.patch("backend.api.routes.stocks._merge_baidu_kline_fields"):
            from backend.api.routes.common import clear_cache
            clear_cache()
            r = client.get("/api/stocks/600519/kline?period=day&limit=30")
    assert r.status_code == 200
    d = r.json()
    assert len(d["points"]) > 0
    p = d["points"][0]
    for key in ("date", "open", "close", "high", "low", "volume"):
        assert key in p
    assert "macd" in (d.get("indicators") or {})


def test_stock_moneyflow_graceful_mocked(client):
    with mock.patch("backend.datasource.eastmoney.get_client") as gc:
        gc.return_value.moneyflow_history.return_value = []
        from backend.api.routes.common import clear_cache
        clear_cache()
        r = client.get("/api/stocks/600519/moneyflow?days=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_sector_moves_mocked(client):
    fake = [
        SectorQuote(code="BK0001", name="白酒", zhangsu=1.5, change_pct=2.0),
        SectorQuote(code="BK0002", name="银行", zhangsu=0.8, change_pct=1.0),
    ]
    with mock.patch("backend.datasource.eastmoney.get_client") as gc:
        gc.return_value.sector_moves.return_value = fake
        from backend.api.routes.common import clear_cache
        clear_cache()
        r = client.get("/api/sector-moves?dir=up&limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_alerts_crud(client):
    """监控 CRUD + 涨速指标（本地 SQLite，不连外网）"""
    r = client.post("/api/alerts", json={
        "target_type": "stock", "code": "600519", "name": "贵州茅台",
        "metric": "zhangsu", "op": "gte", "threshold": 1.5, "note": "涨速测试",
    })
    assert r.status_code == 200
    alert = r.json()["alert"]
    aid = alert["id"]
    assert alert["metric"] == "zhangsu"

    lst = client.get("/api/alerts")
    assert lst.status_code == 200
    assert any(a["id"] == aid for a in lst.json())

    upd = client.put(f"/api/alerts/{aid}", json={"enabled": False})
    assert upd.status_code == 200
    assert upd.json()["alert"]["enabled"] in (0, False)

    dlt = client.delete(f"/api/alerts/{aid}")
    assert dlt.status_code == 200


def test_pinyin_full_and_search_local():
    """拼音全拼写入 + 本地搜索 maotai（不启 FastAPI，避免外网）"""
    from backend.db import store as db
    from backend.db.pinyin import pinyin_full, pinyin_initials

    db.init_db()
    full = pinyin_full("贵州茅台")
    assert "maotai" in full or "mao" in full
    assert pinyin_initials("贵州茅台") == "gzmt"

    db.upsert_stocks([{
        "code": "600519", "name": "贵州茅台", "market": 1, "classify": "AStock",
    }])
    hits = db.search_stocks_local("maotai", 5)
    assert any(h["code"] == "600519" for h in hits), hits

    hits2 = db.search_stocks_local("zmt", 5)
    assert any(h["code"] == "600519" for h in hits2)


def test_ttl_offhours_multiplier():
    """休市时 TTL 至少抬到 CACHE_TTL_OFFHOURS"""
    from backend import config
    from backend.api.routes.common import ttl_cache, clear_cache, _cache

    calls = {"n": 0}

    @ttl_cache(ttl=2)
    def _probe():
        calls["n"] += 1
        return {"ok": True}

    clear_cache()
    with mock.patch("backend.analyzer.schedule.is_trading_time", return_value=False):
        _probe()
        _probe()
    assert calls["n"] == 1
    assert _cache
    assert config.CACHE_TTL_OFFHOURS >= config.CACHE_TTL


def test_meta_lookup(client):
    r = client.get("/api/meta/lookup/600519")
    assert r.status_code == 200
    assert r.json()["code"] == "600519"


def test_positions_roundtrip(client):
    existed = "600519" in (client.get("/api/watchlist").json().get("codes") or [])
    r = client.put("/api/positions", json={"code": "600519", "shares": 100, "cost": 1400})
    assert r.status_code == 200
    assert r.json()["item"]["shares"] == 100
    try:
        with mock.patch("backend.api.routes.stocks.stocks_batch", return_value=[
            {"code": "600519", "name": "贵州茅台", "price": 1600, "change_pct": 1.0}
        ]):
            s = client.get("/api/positions/summary")
        assert s.status_code == 200
        assert s.json()["all"]["count"] >= 1
        dlt = client.delete("/api/positions/600519")
        assert dlt.status_code == 200
    finally:
        if not existed:
            client.delete("/api/watchlist/600519")


def test_merge_stock_detail_flatline_zero():
    """验证腾讯返回 change=0.0 / change_pct=0.0 时能够保留 0.0 而不是被 None 覆盖"""
    from backend.api.routes.common import _merge_stock_detail
    from backend.datasource.models import StockDetail

    fake_em = StockDetail(
        code="600519", name="贵州茅台", price=100.0, prev_close=100.0,
        change=None, change_pct=None,
    )
    fake_tx = {
        "600519": {
            "name": "贵州茅台", "price": 100.0, "prev_close": 100.0,
            "change": 0.0, "change_pct": 0.0,
        }
    }
    with mock.patch("backend.datasource.eastmoney.get_client") as gem, \
         mock.patch("backend.datasource.tencent.get_client") as gtx:
        gem.return_value.stock_snapshot.return_value = fake_em
        gtx.return_value.fetch_quotes.return_value = fake_tx
        merged = _merge_stock_detail("600519")
        assert merged.change == 0.0
        assert merged.change_pct == 0.0


def test_ai_history_store(client):
    """验证 AI 历史记录存储与读取（上限 5 条）"""
    from backend.db import store as db
    db.init_db()

    for i in range(7):
        client.post("/api/ai/save", json={
            "code": "600519",
            "reasoning": f"think {i}",
            "content": f"content {i}",
            "result": {"score": i},
        })

    resp = client.get("/api/ai/history/600519")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 5
    assert items[0]["content"] == "content 6"
    assert items[0]["result"]["score"] == 6


def test_market_volume_date_alignment():
    """验证两市量能按共同交易日对齐"""
    from backend.analyzer import market as market_an

    fake_hist = {
        "sh000001": {"2026-08-15": 50000, "2026-08-16": 60000},
        "sz399001": {"2026-08-14": 40000, "2026-08-15": 50000, "2026-08-16": 60000},
    }
    with mock.patch("backend.analyzer.market._fetch_amount_history", return_value=fake_hist):
        v = market_an.market_volume()
        assert v is not None
        assert v["today_amount"] == (60000 + 60000) * 1e4
        assert v["prev_amount"] == (50000 + 50000) * 1e4
        assert v["label"] == "放量"


def test_rsi_flatline():
    """验证价格无波动时 RSI 计算结果为 50.0"""
    from backend.analyzer.indicators import _rsi

    flat_closes = [10.0] * 30
    res = _rsi(flat_closes, period=14)
    assert res[14] == 50.0
    assert res[-1] == 50.0


def test_backup_import_clear_empty_table():
    """验证备份导入空表能够正确清空数据"""
    from backend.db import store as db
    db.init_db()

    db.watchlist_add("600519")
    assert "600519" in db.watchlist_codes()

    # 导入空的 watchlist
    payload = {"tables": {"watchlist": []}}
    db.import_user_backup(payload)
    assert len(db.watchlist_codes()) == 0


def test_trading_day_and_custom_holidays():
    """验证节假日判断与动态自定义休市日生效"""
    import datetime
    from backend.analyzer import schedule as sch
    from backend.db import store as db

    # 元旦法定节假日
    assert not sch.is_trading_day(datetime.date(2026, 1, 1))

    # 普通周三 (非节假日)
    normal_day = datetime.date(2026, 8, 19)
    assert sch.is_trading_day(normal_day)

    # 动态添加自定义休市日
    db.set_setting("custom_holidays", "2026-08-19")
    try:
        assert not sch.is_trading_day(normal_day)
    finally:
        db.set_setting("custom_holidays", "")


def test_stocks_batch_multi_batch(client):
    """验证自选股超过50只时分批并发拉取"""
    from backend.datasource.models import StockBrief

    codes = [f"60{i:04d}" for i in range(1, 65)]  # 64 只股票
    fake_briefs = [StockBrief(code=c, name=f"测试{c}", price=10.0, change_pct=1.5) for c in codes]

    with mock.patch("backend.datasource.eastmoney.get_client") as gem:
        gem.return_value.ulist_briefs.side_effect = lambda batch, markets: [
            StockBrief(code=c, name=f"测试{c}", price=10.0, change_pct=1.5) for c in batch
        ]
        resp = client.get(f"/api/stocks/batch?codes={','.join(codes)}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 64
        assert data[0]["code"] == "600001"
        assert data[-1]["code"] == "600064"


def test_calendar_events_api(client):
    """验证交易日历与交割日推算接口"""
    resp = client.get("/api/calendar/events?months=4")
    assert resp.status_code == 200
    data = resp.json()
    assert "hero_cards" in data
    assert "events" in data
    assert len(data["hero_cards"]) >= 2
    assert len(data["events"]) >= 10
    # 验证包含股指期货与ETF期权事件
    types = [e["type"] for e in data["events"]]
    assert "derivative" in types
    assert "macro" in types


def test_unlock_calendar_api(client):
    """验证限售股解禁日历接口"""
    with mock.patch("backend.datasource.eastmoney.get_client") as gem:
        gem.return_value.restricted_unlock_list.return_value = [
            {"code": "600519", "name": "贵州茅台", "date": "2026-08-25", "ratio_total": 6.5, "market_cap": 2000000000}
        ]
        resp = client.get("/api/calendar/unlocks?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["heavy_count"] == 1
        assert data["items"][0]["code"] == "600519"


def test_stock_risk_diagnosis_api(client):
    """验证个股排雷诊断接口"""
    with mock.patch("backend.datasource.eastmoney.get_client") as gem:
        gem.return_value.stock_unlock_detail.return_value = [
            {"code": "000001", "name": "平安银行", "date": "2026-08-20", "ratio_total": 8.0}
        ]
        gem.return_value.stock_performance_forecast.return_value = [
            {"code": "000001", "predict_type": "首亏", "content": "受行业周期影响", "report_date": "2026-06-30"}
        ]
        resp = client.get("/api/stocks/000001/risk-diagnosis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risk_level"] == "high"
        assert len(data["risk_tags"]) >= 2


def test_watchlist_groups_and_presets(client):
    """验证自选股分组 CRUD、预设热门赛道与股票归属"""
    # 1. 验证获取分组列表及初始化预设
    r = client.get("/api/watchlist/groups")
    assert r.status_code == 200
    groups = r.json().get("groups") or []
    assert len(groups) >= 1
    assert any(g["name"] in ("光通信", "PCB", "先进封装", "存储芯片") for g in groups)

    # 2. 重新初始化预设
    r_pre = client.post("/api/watchlist/init-presets")
    assert r_pre.status_code == 200
    assert any(g["name"] == "光通信" for g in r_pre.json()["groups"])

    # 3. 创建自定义分组
    test_group_name = "测试芯片"
    r_create = client.post("/api/watchlist/groups", json={"name": test_group_name})
    assert r_create.status_code == 200
    grp = r_create.json()["group"]
    gid = grp["id"]
    assert grp["name"] == test_group_name

    # 4. 添加股票到新分组
    r_add = client.post("/api/watchlist", json={"code": "688008", "group_id": gid})
    assert r_add.status_code == 200
    assert "688008" in r_add.json()["codes"]

    # 5. 查询该分组的自选股票
    r_get = client.get(f"/api/watchlist?group_id={gid}")
    assert r_get.status_code == 200
    assert "688008" in r_get.json()["codes"]

    # 6. 查询股票所属分组
    r_sg = client.get("/api/watchlist/stock-groups/688008")
    assert r_sg.status_code == 200
    assert gid in r_sg.json()["group_ids"]

    # 7. 修改分组名称
    r_upd = client.put(f"/api/watchlist/groups/{gid}", json={"name": "测试芯片2"})
    assert r_upd.status_code == 200
    assert any(g["id"] == gid and g["name"] == "测试芯片2" for g in r_upd.json()["groups"])

    # 8. 从指定分组移出股票
    r_del_stock = client.delete(f"/api/watchlist/688008?group_id={gid}")
    assert r_del_stock.status_code == 200
    assert "688008" not in r_del_stock.json()["codes"]

    # 9. 删除该自定义分组
    r_del_grp = client.delete(f"/api/watchlist/groups/{gid}")
    assert r_del_grp.status_code == 200
    assert not any(g["id"] == gid for g in r_del_grp.json()["groups"])


def test_market_heatmap_api(client):
    """验证大盘热力云图数据接口"""
    from backend.datasource.models import SectorQuote, StockBrief
    with mock.patch("backend.datasource.eastmoney.get_client") as gem:
        gem.return_value.sector_list.return_value = [
            SectorQuote(code="BK0420", name="半导体", price=100.0, change_pct=2.5, amount=5000000000.0, main_inflow=100000000.0, leader_name="中芯国际", leader_code="688981", leader_pct=4.2)
        ]
        gem.return_value.sector_stocks.return_value = [
            StockBrief(code="688981", name="中芯国际", price=50.0, change_pct=4.2, amount=2000000000.0, main_inflow=50000000.0)
        ]
        gem.return_value._q.get.return_value = {
            "data": {
                "diff": [
                    {"f12": "688981", "f14": "中芯国际", "f2": 50.0, "f3": 4.2, "f6": 2000000000.0, "f8": 1.5, "f20": 400000000000.0, "f21": 200000000000.0, "f100": "半导体", "f62": 50000000.0}
                ]
            }
        }
        resp = client.get("/api/market/heatmap?scope=all_top300&size_by=amount")
        assert resp.status_code == 200
        data = resp.json()
        assert data["scope"] == "all_top300"
        assert data["count"] >= 1
        assert data["items"][0]["name"] == "半导体"
        assert "children" in data["items"][0]
        assert data["items"][0]["children"][0]["name"] == "中芯国际"






