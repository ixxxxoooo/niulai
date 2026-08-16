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
# 106=纽交所、107=美交所、176=日股、177=韩股；期货/现货：101=COMEX、109=LME、
# 122=伦敦现货、118=上金所。region 用于前端分组（us/jp/kr/metal）。
GLOBAL_THEME_SECTORS = [
    # ---------------- 美股（US） ----------------
    {"key": "us_ai", "name": "AI算力", "region": "us",
     "secids": ["105.NVDA", "105.AMD", "105.AVGO", "105.ARM", "105.MRVL"]},
    {"key": "us_cpo", "name": "CPO·光模块", "region": "us",
     "secids": ["106.COHR", "105.LITE", "105.AAOI", "106.GLW", "106.CIEN"]},
    {"key": "us_memory", "name": "半导体存储", "region": "us",
     "secids": ["105.MU", "105.WDC", "105.STX", "105.SNDK", "105.SIMO"]},
    {"key": "us_datacenter", "name": "数据中心", "region": "us",
     "secids": ["106.DELL", "105.SMCI", "106.VRT", "105.MRVL", "105.AMD"]},
    {"key": "us_cloud", "name": "云计算", "region": "us",
     "secids": ["105.MSFT", "105.AMZN", "105.GOOGL", "106.ORCL", "106.SNOW", "106.CRM"]},
    {"key": "us_space", "name": "商业航天", "region": "us",
     "secids": ["105.RKLB", "105.LUNR", "106.RTX", "106.LMT"]},
    {"key": "us_satellite", "name": "卫星", "region": "us",
     "secids": ["105.ASTS", "105.RKLB", "106.LMT", "106.NOC"]},
    {"key": "us_robot", "name": "机器人", "region": "us",
     "secids": ["105.ISRG", "105.TER", "106.ROK", "105.NVDA"]},
    {"key": "us_auto_drive", "name": "自动驾驶", "region": "us",
     "secids": ["105.TSLA", "105.GOOGL", "106.UBER", "105.AUR"]},
    {"key": "us_grid", "name": "电网", "region": "us",
     "secids": ["106.ETN", "106.GEV", "106.VRT"]},
    {"key": "us_defense", "name": "军工", "region": "us",
     "secids": ["106.RTX", "106.LMT", "106.NOC", "106.GD"]},
    {"key": "us_newenergy", "name": "新能源", "region": "us",
     "secids": ["105.ENPH", "105.FSLR", "106.ALB", "105.PLUG"]},
    {"key": "us_battery", "name": "锂电池", "region": "us",
     "secids": ["105.ENVX", "106.ALB", "105.TSLA"]},
    {"key": "us_solar", "name": "光伏", "region": "us",
     "secids": ["105.FSLR", "105.ENPH", "105.RUN", "105.ARRY"]},
    {"key": "us_pharma", "name": "生物制药", "region": "us",
     "secids": ["106.LLY", "106.NVO", "105.AMGN", "106.ABBV", "106.UNH"]},
    {"key": "us_consumer", "name": "消费", "region": "us",
     "secids": ["105.WMT", "106.PG", "106.KO", "106.MCD", "106.NKE", "105.PEP"]},
    {"key": "us_banks", "name": "银行", "region": "us",
     "secids": ["106.JPM", "106.BAC", "106.GS", "106.MS", "106.WFC"]},
    # ---------------- 日股（JP） ----------------
    {"key": "jp_semi_equip", "name": "半导体设备", "region": "jp",
     "secids": ["176.2760", "176.6857", "176.6146"]},
    {"key": "jp_industrial_auto", "name": "工业自动化", "region": "jp",
     "secids": ["176.6954", "176.6506", "176.6861"]},
    {"key": "jp_precision", "name": "精密制造", "region": "jp",
     "secids": ["176.6594", "176.6902", "176.7259"]},
    {"key": "jp_auto_chain", "name": "汽车产业链", "region": "jp",
     "secids": ["176.7203", "176.7267", "176.7201", "176.6902"]},
    {"key": "jp_optics", "name": "光学·影像", "region": "jp",
     "secids": ["176.7751", "176.7731"]},
    {"key": "jp_elec_ent", "name": "消费电子·娱乐", "region": "jp",
     "secids": ["176.6758", "176.7974"]},
    # ---------------- 韩股（KR） ----------------
    {"key": "kr_memory", "name": "存储", "region": "kr",
     "secids": ["177.005930", "177.000660"]},
    {"key": "kr_semis", "name": "半导体", "region": "kr",
     "secids": ["177.005930", "177.000660", "177.000990"]},
    {"key": "kr_battery", "name": "电池", "region": "kr",
     "secids": ["177.373220", "177.006400", "177.096770", "177.051910"]},
    {"key": "kr_consumer_elec", "name": "消费电子", "region": "kr",
     "secids": ["177.005930", "177.066570"]},
    {"key": "kr_internet", "name": "互联网·平台", "region": "kr",
     "secids": ["177.035420", "177.035720"]},
    # ---------------- 贵金属 / 工业金属（metal，期货/现货） ----------------
    {"key": "metal_precious", "name": "黄金白银", "region": "metal",
     "secids": ["101.GC00Y", "101.SI00Y", "122.XAU"]},
    {"key": "metal_industrial", "name": "工业金属", "region": "metal",
     "secids": ["109.LCPT", "109.LALT", "109.LZNT", "109.LNKT", "109.LTNT", "101.HG00Y"]},
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
