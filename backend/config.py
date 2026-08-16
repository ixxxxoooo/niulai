"""全局配置"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------- 数据源节点 ----------
# 东方财富行情主节点（按优先级排列，自动故障转移）
# push2 主域名经常断连(RemoteProtocolError)，优先使用 delay/子域
EASTMONEY_HOSTS = [
    "push2delay.eastmoney.com",
    "1.push2delay.eastmoney.com",
    "push2.eastmoney.com",
]
# 资金流：push2 主节点常被掐，delay 节点实测可用
EASTMONEY_FFLOW_HOSTS = [
    "push2delay.eastmoney.com",
    "1.push2delay.eastmoney.com",
]
# 东方财富历史数据节点（push2his2 实测稳定；主节点会间歇性拒连）
EASTMONEY_HIS_HOSTS = [
    "push2his2.eastmoney.com",
    "push2his.eastmoney.com",
    "42.push2his.eastmoney.com",
    "21.push2his.eastmoney.com",
]
# 东方财富涨停池节点
EASTMONEY_EX_HOSTS = ["push2ex.eastmoney.com"]
# 东方财富股票搜索接口（suggest）
EASTMONEY_SEARCH_HOSTS = ["searchapi.eastmoney.com"]
SEARCH_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
# 腾讯行情（个股详情/五档盘口）
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
TENCENT_REFERER = "https://gu.qq.com/"

# ---------- 请求参数 ----------
REQUEST_TIMEOUT = 8          # 交易时段单请求超时（秒）
REQUEST_TIMEOUT_OFFHOURS = 3 # 非交易时段超时，减少无效等待
REQUEST_RETRIES = 2          # 单节点重试次数（多节点故障转移已覆盖）
NODE_FAIL_COOLDOWN = 20      # 节点失败后冷却秒数，期间优先跳过
CACHE_TTL = 2.0              # 交易时段后端接口缓存（秒）
CACHE_TTL_OFFHOURS = 60.0    # 非交易时段缓存（数据不再变化）
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# ---------- 大盘指数 ----------
INDEX_SECIDS = [
    ("1.000001", "上证指数"),
    ("0.399001", "深证成指"),
    ("0.399006", "创业板指"),
    ("1.000688", "科创50"),
    ("1.000300", "沪深300"),
]

# 全 A 股 fs 参数（clist 用）
FS_ALL_A = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
# 行业板块 / 概念板块
FS_SECTOR_INDUSTRY = "m:90+t:2"
FS_SECTOR_CONCEPT = "m:90+t:3"
FS_SECTOR_AREA = "m:90+t:1"

# ---------- 全球题材板块 ----------
# 东财无海外题材板块接口（仅科技/金融等大类），采用「代表股 → 板块涨跌幅」方案：
# 每个板块配若干代表股 secid，涨跌幅取成分股简单平均。secid 前缀：105=纳斯达克、
# 106=纽交所、107=美交所、176=日股、177=韩股。region 用于前端分组（us/jp/kr）。
GLOBAL_THEME_SECTORS = [
    # ---------------- 美股（US） ----------------
    {"key": "us_memory", "name": "存储芯片", "region": "us",
     "secids": ["105.MU", "105.WDC", "105.STX", "105.SIMO", "105.SNDK"]},
    {"key": "us_cpo", "name": "CPO·光模块", "region": "us",
     "secids": ["106.COHR", "105.LITE", "105.AAOI", "106.GLW", "106.CIEN"]},
    {"key": "us_gpu", "name": "AI算力·GPU", "region": "us",
     "secids": ["105.NVDA", "105.AMD", "105.AVGO", "105.ARM", "106.TSM"]},
    {"key": "us_semi_equip", "name": "半导体设备", "region": "us",
     "secids": ["105.AMAT", "105.LRCX", "105.KLAC", "105.ASML", "105.TER"]},
    {"key": "us_ai_software", "name": "AI软件", "region": "us",
     "secids": ["106.MSFT", "105.GOOGL", "105.META", "105.PLTR", "105.CRWD"]},
    {"key": "us_megacap", "name": "科技七巨头", "region": "us",
     "secids": ["106.MSFT", "105.AAPL", "105.GOOGL", "105.META", "105.NVDA", "105.AMZN", "105.TSLA"]},
    {"key": "us_semis", "name": "芯片设计", "region": "us",
     "secids": ["105.NVDA", "105.AMD", "105.AVGO", "105.QCOM", "105.INTC", "105.TXN"]},
    {"key": "us_cloud", "name": "云计算·SaaS", "region": "us",
     "secids": ["106.MSFT", "105.AMZN", "105.GOOGL", "106.ORCL", "106.SNOW", "106.CRM"]},
    {"key": "us_cyber", "name": "网络安全", "region": "us",
     "secids": ["105.CRWD", "105.PANW", "105.ZS", "105.FTNT", "105.OKTA"]},
    {"key": "us_crypto", "name": "加密货币", "region": "us",
     "secids": ["105.COIN", "105.MSTR", "105.MARA", "105.RIOT", "105.CLSK", "105.HOOD"]},
    {"key": "us_nuclear", "name": "核电", "region": "us",
     "secids": ["106.OKLO", "106.SMR", "106.VST", "105.CEG", "106.CCJ"]},
    {"key": "us_glp1", "name": "减肥药", "region": "us",
     "secids": ["106.LLY", "106.NVO"]},
    {"key": "us_biotech", "name": "生物医药", "region": "us",
     "secids": ["106.LLY", "106.PFE", "106.MRK", "106.ABBV", "106.UNH"]},
    {"key": "us_ev", "name": "新能源车", "region": "us",
     "secids": ["105.TSLA", "105.RIVN", "105.LCID"]},
    {"key": "us_robotics", "name": "医疗机器人", "region": "us",
     "secids": ["105.ISRG"]},
    {"key": "us_consumer", "name": "消费电子", "region": "us",
     "secids": ["105.AAPL", "105.QCOM", "105.TXN", "105.MU"]},
    {"key": "us_streaming", "name": "流媒体", "region": "us",
     "secids": ["105.NFLX", "105.META", "106.DIS", "106.SNAP"]},
    {"key": "us_defense", "name": "军工航天", "region": "us",
     "secids": ["106.RTX", "106.LMT", "106.NOC"]},
    {"key": "us_banks", "name": "银行", "region": "us",
     "secids": ["106.JPM", "106.BAC", "106.GS", "106.MS", "106.WFC"]},
    # ---------------- 日股（JP） ----------------
    {"key": "jp_semi_equip", "name": "半导体设备", "region": "jp",
     "secids": ["176.2760", "176.6857", "176.6146"]},
    {"key": "jp_auto", "name": "汽车", "region": "jp",
     "secids": ["176.7203", "176.7267"]},
    {"key": "jp_consumer_elec", "name": "消费电子·娱乐", "region": "jp",
     "secids": ["176.6758", "176.7974"]},
    {"key": "jp_internet", "name": "互联网", "region": "jp",
     "secids": ["176.9984"]},
    {"key": "jp_banks", "name": "银行", "region": "jp",
     "secids": ["176.8306", "176.8316", "176.8411"]},
    {"key": "jp_materials", "name": "材料·消费", "region": "jp",
     "secids": ["176.4063", "176.4452"]},
    # ---------------- 韩股（KR） ----------------
    {"key": "kr_memory", "name": "存储芯片", "region": "kr",
     "secids": ["177.005930", "177.000660"]},
    {"key": "kr_battery", "name": "动力电池", "region": "kr",
     "secids": ["177.373220", "177.006400", "177.096770"]},
    {"key": "kr_auto", "name": "汽车", "region": "kr",
     "secids": ["177.005380", "177.000270"]},
    {"key": "kr_internet", "name": "互联网·平台", "region": "kr",
     "secids": ["177.035420", "177.035720"]},
    {"key": "kr_biotech", "name": "生物制药", "region": "kr",
     "secids": ["177.207940", "177.068270"]},
    {"key": "kr_industrial", "name": "造船·工业", "region": "kr",
     "secids": ["177.009540", "177.028260"]},
    {"key": "kr_steel", "name": "钢铁", "region": "kr",
     "secids": ["177.005490"]},
]

# ---------- 交易时段 ----------
# 节假日休市日（YYYY-MM-DD）。未列到的法定假日可自行补充；
# 默认至少排除周末。这里预置 2025~2026 主要节假日（供参考，请按交易所公告核对）。
TRADING_HOLIDAYS = {
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-02-03", "2025-02-04", "2025-04-04", "2025-05-01", "2025-05-02",
    "2025-05-05", "2025-06-02", "2025-10-01", "2025-10-02", "2025-10-03",
    "2025-10-06", "2025-10-07", "2025-10-08",
    "2026-01-01", "2026-01-02",
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-02-23", "2026-02-24",
    "2026-04-06",
    "2026-05-01",
    "2026-06-19",
    "2026-09-25",
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07",
    "2026-10-08",
}
# 盘中时间区间（含集合竞价 9:15 起）
TRADING_SESSIONS = [("09:15", "11:30"), ("13:00", "15:00")]

# ---------- 服务 ----------
HOST = "0.0.0.0"
PORT = 8088

# ---------- 开盘啦（kaipanla） ----------
# 抓包私有接口：仅个人研究、低频调用；关闭后相关区块自动隐藏，不影响现有功能
KAIPANLA_ENABLED = True
