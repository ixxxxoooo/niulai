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
