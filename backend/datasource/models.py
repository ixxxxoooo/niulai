"""统一数据模型（Pydantic）"""
from typing import Optional, List
from pydantic import BaseModel


class IndexQuote(BaseModel):
    """大盘/全球指数"""
    code: str
    name: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    amount: Optional[float] = None          # 成交额（元）
    volume: Optional[float] = None          # 成交量（手）
    high: Optional[float] = None            # 当日最高
    low: Optional[float] = None             # 当日最低
    amplitude: Optional[float] = None       # 振幅 %
    up_count: Optional[int] = None          # 上涨家数
    down_count: Optional[int] = None        # 下跌家数
    flat_count: Optional[int] = None        # 平盘家数
    secid: Optional[str] = None             # 东财 secid（如 1.000001 / 100.N225）
    region: Optional[str] = None            # 全球指数区域（日韩/亚太/美股）


class StockBrief(BaseModel):
    """个股简要行情（榜单/板块成分用）"""
    code: str
    name: str
    market: Optional[int] = None            # 1=沪 0=深
    price: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None          # 成交量（手）
    amount: Optional[float] = None          # 成交额（元）
    turnover: Optional[float] = None        # 换手率 %
    volume_ratio: Optional[float] = None    # 量比
    amplitude: Optional[float] = None       # 振幅 %
    zhangsu: Optional[float] = None         # 涨速 %（5分钟）
    industry: Optional[str] = None          # 所属行业
    classify: Optional[str] = None          # AStock / Fund
    board: Optional[str] = None             # MAIN/KCB/CYB/BSE/ETF
    is_st: Optional[int] = None
    main_inflow: Optional[float] = None     # 主力净流入（元）
    main_inflow_pct: Optional[float] = None # 主力净流入占比 %
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    prev_close: Optional[float] = None


class SectorQuote(BaseModel):
    """板块行情"""
    code: str
    name: str
    price: Optional[float] = None
    change_pct: Optional[float] = None
    amount: Optional[float] = None          # 成交额（元）
    main_inflow: Optional[float] = None     # 主力净流入（元）
    zhangsu: Optional[float] = None         # 5 分钟板块涨速 %
    up_count: Optional[int] = None
    down_count: Optional[int] = None
    flat_count: Optional[int] = None
    leader_code: Optional[str] = None       # 领涨股代码
    leader_name: Optional[str] = None       # 领涨股名称
    leader_pct: Optional[float] = None      # 领涨股涨跌幅 %


class OrderBook(BaseModel):
    """五档盘口"""
    bid: List[dict] = []                    # [{price, volume}, ...] 买一~买五
    ask: List[dict] = []                    # [{price, volume}, ...] 卖一~卖五


class StockDetail(BaseModel):
    """个股实时详情（东财快照 + 腾讯盘口合并）"""
    code: str
    name: str
    market: Optional[int] = None
    price: Optional[float] = None
    prev_close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    amplitude: Optional[float] = None
    volume: Optional[float] = None          # 成交量（手）
    amount: Optional[float] = None          # 成交额（元）
    turnover: Optional[float] = None        # 换手率 %
    volume_ratio: Optional[float] = None    # 量比
    pe: Optional[float] = None              # 市盈率（动）
    pb: Optional[float] = None              # 市净率
    total_mv: Optional[float] = None        # 总市值（元）
    float_mv: Optional[float] = None        # 流通市值（元）
    limit_up: Optional[float] = None        # 涨停价
    limit_down: Optional[float] = None      # 跌停价
    outer: Optional[float] = None           # 外盘（手）
    inner: Optional[float] = None           # 内盘（手）
    weicha: Optional[float] = None          # 委差（手）
    avg_price: Optional[float] = None       # 均价
    orderbook: Optional[OrderBook] = None
    industry: Optional[str] = None
    concepts: Optional[str] = None           # 概念标签，逗号分隔
    classify: Optional[str] = None
    board: Optional[str] = None
    is_st: Optional[int] = None
    zhangsu: Optional[float] = None          # 5分钟涨速 %
    main_inflow: Optional[float] = None
    main_inflow_pct: Optional[float] = None
    time: Optional[str] = None              # 行情时间
    data_source: Optional[str] = None       # 东财 / 腾讯 / 东财+腾讯
    fetched_at: Optional[str] = None        # 本次成功拉取时间


class TrendPoint(BaseModel):
    """分时点"""
    time: str                               # HH:MM
    price: float
    avg: float                              # 均价
    volume: float                           # 成交量（手）
    amount: float                           # 成交额（元）
    high: float
    low: float


class IntradayTrend(BaseModel):
    """分时数据"""
    code: str
    name: str
    pre_close: float
    points: List[TrendPoint] = []


class Tick(BaseModel):
    """成交明细"""
    time: str
    price: float
    volume: float                           # 手
    amount: float
    direction: int                          # 1=买盘 2=卖盘 0=中性


class MoneyFlowDay(BaseModel):
    """单日资金流（历史）"""
    date: str
    main_inflow: float                      # 主力净流入（元）
    small: float
    medium: float
    large: float
    extra_large: float
    main_pct: float = 0.0                   # 主力净占比(%)
    small_pct: float = 0.0
    medium_pct: float = 0.0
    large_pct: float = 0.0
    extra_large_pct: float = 0.0
    main_in: float = 0.0                    # 主力流入（元）＝超大单流入+大单流入
    main_out: float = 0.0                   # 主力流出（元）


class LimitUpStock(BaseModel):
    """涨停/炸板股"""
    code: str
    name: str
    price: float
    change_pct: float
    seal_amount: float = 0.0                # 封单额（元）
    lbc: int = 0                            # 连板数
    first_time: str = ""                    # 首次封板时间 HH:MM
    last_time: str = ""                     # 最后封板时间 HH:MM
    zb_count: int = 0                       # 炸板次数
    industry: str = ""                      # 所属行业（涨停池 hybk）
    amount: Optional[float] = None
    turnover: Optional[float] = None
    kind: str = "zt"                        # zt=涨停 zb=炸板
    board: Optional[str] = None
    is_st: Optional[int] = None


class MarketOverview(BaseModel):
    """大盘概况"""
    indices: List[IndexQuote] = []
    total_amount: Optional[float] = None    # 两市总成交额（元）
    up_count: Optional[int] = None
    down_count: Optional[int] = None
    flat_count: Optional[int] = None
    limit_up_count: Optional[int] = None    # 涨停家数
    limit_down_count: Optional[int] = None  # 跌停家数
    index_volume: Optional[dict] = None     # 上证指数量能 {ratio, label, today, avg5}
    is_trading_time: bool = False
    quote_time: Optional[str] = None        # 数据时间
    source: str = "eastmoney"
