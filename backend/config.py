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
