"""腾讯行情解析单元测试（mock httpx 响应）"""
from unittest import mock

from backend.datasource import tencent

# 模拟腾讯返回（GBK 编码）
FAKE_RESP = (
    'v_sh600519="1~贵州茅台~600519~1341.99~1355.29~1355.00~29853~12760~17093~'
    '1341.98~1~1341.90~2~1341.69~1~1341.68~1~1341.62~3~'
    '1341.99~283~1342.00~23~1342.01~1~1342.02~2~1342.06~3~~'
    '20260814161443~-13.30~-0.98~1359.00~1338.14~1341.99/29853/4024065608~'
    '29853~402407~0.24~20.60~~1359.00~1338.14~1.54~16775.97~16775.97~7.20~'
    '1490.82~1219.76~0.82~-304~1347.95~18.84~20.38";'
)


class _FakeResp:
    status_code = 200

    def raise_for_status(self):
        pass

    @property
    def content(self):
        return FAKE_RESP.encode("gbk")


def test_tencent_quote_parsing():
    client = tencent.TencentClient()
    with mock.patch.object(client._http, "get", return_value=_FakeResp()):
        quotes = client.fetch_quotes(["600519"])
    q = quotes["600519"]
    assert q["name"] == "贵州茅台"
    assert q["price"] == 1341.99
    assert q["prev_close"] == 1355.29
    assert q["outer"] == 12760.0
    assert q["inner"] == 17093.0
    assert q["volume_ratio"] == 0.82
    assert q["weicha"] == -304.0
    assert q["limit_up"] == 1490.82
    assert q["limit_down"] == 1219.76
    # 五档
    assert q["orderbook"]["bid"][0] == {"price": 1341.98, "volume": 1.0}
    assert q["orderbook"]["ask"][0] == {"price": 1341.99, "volume": 283.0}
    assert len(q["orderbook"]["bid"]) == 5
    assert len(q["orderbook"]["ask"]) == 5
    # 时间
    assert q["time"] == "2026-08-14 16:14:43"


def test_to_tencent_symbol():
    assert tencent.to_tencent_symbol("600519") == "sh600519"
    assert tencent.to_tencent_symbol("000001") == "sz000001"
    assert tencent.to_tencent_symbol("300750") == "sz300750"
    assert tencent.to_tencent_symbol("688981") == "sh688981"
    assert tencent.to_tencent_symbol("830799") == "bj830799"


def test_tencent_failure_returns_empty():
    client = tencent.TencentClient()
    with mock.patch.object(client._http, "get", side_effect=Exception("network")):
        assert client.fetch_quotes(["600519"]) == {}
        assert client.minute_quotes("600519") is None
