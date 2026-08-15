"""东财数据解析单元测试（mock 数据，不依赖网络）"""
from backend.datasource import eastmoney


def test_num_conversion():
    assert eastmoney._num(123) == 123.0
    assert eastmoney._num("1.23") == 1.23
    assert eastmoney._num("-") is None
    assert eastmoney._num("") is None
    assert eastmoney._num(None) is None
    assert eastmoney._num("abc") is None


def test_secid_of():
    assert eastmoney.secid_of("600519") == "1.600519"
    assert eastmoney.secid_of("000001") == "0.000001"
    assert eastmoney.secid_of("300750") == "0.300750"
    assert eastmoney.secid_of("688981") == "1.688981"
    assert eastmoney.secid_of("000001", market=1) == "1.000001"


def test_brief_parsing():
    client = eastmoney.EastMoneyClient()
    it = {
        "f12": "600519", "f14": "贵州茅台", "f13": 1,
        "f2": 1341.99, "f3": -0.98, "f4": -13.3,
        "f5": 29853, "f6": 4024065608,
        "f8": 0.24, "f10": 0.82, "f22": 0.15,
        "f62": 123456789, "f184": 3.21,
        "f100": "白酒",
    }
    b = client._brief(it)
    assert b.code == "600519"
    assert b.name == "贵州茅台"
    assert b.price == 1341.99
    assert b.change_pct == -0.98
    assert b.main_inflow == 123456789
    assert b.main_inflow_pct == 3.21
    assert b.industry == "白酒"


def test_brief_missing_fields():
    client = eastmoney.EastMoneyClient()
    b = client._brief({"f12": "000001", "f14": "平安银行"})
    assert b.code == "000001"
    assert b.price is None
    assert b.change_pct is None
    assert b.main_inflow is None


def test_index_parsing():
    client = eastmoney.EastMoneyClient()
    # 模拟 ulist 返回（含深市指数 f13=0）
    fake = {"data": {"diff": [
        {"f12": "000001", "f13": 1, "f14": "上证指数", "f2": 3927.18, "f3": 0.01,
         "f6": 9.9e11, "f104": 1012, "f105": 1254, "f106": 85},
        {"f12": "399001", "f13": 0, "f14": "深证成指", "f2": 12000, "f3": -0.2,
         "f6": 1e11, "f104": 800, "f105": 900, "f106": 40},
    ]}}
    client._q.get = lambda *a, **k: fake
    quotes = client.index_quotes()
    assert len(quotes) == 2
    sh = next(q for q in quotes if q.code == "000001")
    sz = next(q for q in quotes if q.code == "399001")
    assert sh.secid == "1.000001"
    assert sz.secid == "0.399001"


def test_search_parsing():
    """搜索解析：只保留 A 股，过滤板块/基金，正确解析市场"""
    client = eastmoney.EastMoneyClient()
    fake = {"QuotationCodeTable": {"Data": [
        {"Code": "600519", "Name": "贵州茅台", "Classify": "AStock",
         "QuoteID": "1.600519", "SecurityTypeName": "沪A"},
        {"Code": "000001", "Name": "平安银行", "Classify": "AStock",
         "QuoteID": "0.000001", "SecurityTypeName": "深A"},
        {"Code": "BK0475", "Name": "银行Ⅱ", "Classify": "BK",
         "QuoteID": "90.BK0475", "SecurityTypeName": "板块"},
        {"Code": "510300", "Name": "沪深300ETF", "Classify": "Fund",
         "QuoteID": "1.510300", "SecurityTypeName": "沪基金"},
    ]}}
    client._search.get = lambda *a, **k: fake
    out = client.search_stocks("测试", 10)
    assert len(out) == 3
    assert out[0] == {"code": "600519", "name": "贵州茅台", "market": 1, "type": "沪A"}
    assert out[1] == {"code": "000001", "name": "平安银行", "market": 0, "type": "深A"}
    assert out[2]["code"] == "510300"


def test_search_missing_quoteid():
    """QuoteID 缺失时用 MktNum 兜底"""
    client = eastmoney.EastMoneyClient()
    fake = {"QuotationCodeTable": {"Data": [
        {"Code": "300750", "Name": "宁德时代", "Classify": "AStock",
         "QuoteID": "", "MktNum": "0", "SecurityTypeName": "创业板"},
    ]}}
    client._search.get = lambda *a, **k: fake
    out = client.search_stocks("宁德", 10)
    assert out[0]["market"] == 0


def test_fmt_hhmmss():
    """涨停池时间 92500（5 位）也要格式化成 09:25。"""
    assert eastmoney.fmt_hhmmss(92500) == "09:25"
    assert eastmoney.fmt_hhmmss(93000) == "09:30"
    assert eastmoney.fmt_hhmmss(105703) == "10:57"
    assert eastmoney.fmt_hhmmss("09:25:00") == "09:25"
    assert eastmoney.fmt_hhmmss("") == ""
    assert eastmoney.fmt_hhmmss(None) == ""


def test_tencent_symbol_of_indices():
    c = eastmoney.EastMoneyClient()
    assert c._tencent_symbol_of("1.000001") == "sh000001"
    assert c._tencent_symbol_of("0.399001") == "sz399001"
    assert c._tencent_symbol_of("0.399006") == "sz399006"
    assert c._tencent_symbol_of("1.000300") == "sh000300"
    assert c._tencent_symbol_of("0.000001") is None  # 平安银行不是指数

