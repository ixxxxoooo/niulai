"""7x24 实时财经电报与快讯单元测试。
@author ygw
"""

from unittest import mock
import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.datasource.telegraph import get_cls_sign, TelegraphClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_cls_sign_calculation():
    """验证财联社 SHA1 -> MD5 签名生成。"""
    params = {
        "app": "CailianpressWeb",
        "os": "web",
        "sv": "8.7.9",
        "rn": 20,
    }
    sign = get_cls_sign(params)
    assert isinstance(sign, str)
    assert len(sign) == 32  # 32 位 MD5 字符串


def test_telegraph_api_endpoint(client):
    """测试 /api/telegraph 接口返回结构。"""
    r = client.get("/api/telegraph?category=all&rn=10")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "category" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        assert "id" in item
        assert "content" in item
        assert "time" in item
        assert "source" in item
        assert "is_red" in item


def test_telegraph_category_filter(client):
    """测试不同分类下的电报拉取。"""
    for cat in ["red", "company", "watch", "hk_us", "fund"]:
        r = client.get(f"/api/telegraph?category={cat}&rn=10")
        assert r.status_code == 200
        data = r.json()
        assert data["category"] == cat


def test_telegraph_failover():
    """测试财联社异常时自动降级到东财快讯。"""
    tc = TelegraphClient()
    with mock.patch.object(tc, "fetch_cls", return_value=[]):
        with mock.patch.object(tc, "fetch_eastmoney", return_value=[{
            "id": "12345",
            "title": "测试东财降级快讯",
            "content": "测试东财降级快讯内容",
            "time": "12:00:00",
            "source": "东财快讯",
            "is_red": False,
        }]):
            res = tc.fetch_telegraph(category="all", rn=10)
            assert len(res) == 1
            assert res[0]["source"] == "东财快讯"
