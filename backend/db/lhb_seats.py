"""龙虎榜席位标签库：游资/机构/北向识别（参考 UZI seat_db.py 精简版）
@author ygw
"""
import threading
from typing import Dict, List, Optional

from ..logging_config import logger
from . import store

_EXTRA_SCHEMA = """
CREATE TABLE IF NOT EXISTS lhb_seats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL,
    real_name TEXT DEFAULT '',
    tier TEXT DEFAULT 'broker',
    style TEXT DEFAULT '',
    premium TEXT DEFAULT 'neutral',
    seat_name TEXT NOT NULL,
    UNIQUE(nickname, seat_name)
);
CREATE INDEX IF NOT EXISTS idx_lhb_seats_name ON lhb_seats(seat_name);

CREATE TABLE IF NOT EXISTS daily_bars (
    code TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    amount REAL,
    PRIMARY KEY(code, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_bars_date ON daily_bars(trade_date);

CREATE TABLE IF NOT EXISTS screener_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT,
    finished_at TEXT,
    rules TEXT,
    scope TEXT DEFAULT 'all',
    hit_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS screener_hits (
    run_id INTEGER,
    rule_id TEXT,
    code TEXT,
    name TEXT DEFAULT '',
    close REAL,
    change_pct REAL,
    detail TEXT DEFAULT '',
    FOREIGN KEY(run_id) REFERENCES screener_runs(id)
);
"""

# ── 内置游资席位字典（精简版，约 25 位知名游资） ──
_BUILTIN_SEATS: List[dict] = [
    {"nickname": "章盟主", "real_name": "章建平", "tier": "legend", "style": "大资金趋势波段，格局锁仓", "premium": "neutral", "seats": [
        "国泰君安证券股份有限公司上海江苏路证券营业部",
        "国泰君安证券股份有限公司宁波彩虹北路证券营业部",
        "中信证券股份有限公司杭州延安路证券营业部",
    ]},
    {"nickname": "孙哥", "real_name": "孙煜", "tier": "legend", "style": "板块引导，波段锁仓", "premium": "neutral_positive", "seats": [
        "中信证券股份有限公司上海溧阳路证券营业部",
        "中信证券股份有限公司上海古北路证券营业部",
        "中信证券股份有限公司上海分公司",
    ]},
    {"nickname": "赵老哥", "real_name": "赵强", "tier": "legend", "style": "打板，二板定龙头", "premium": "positive", "seats": [
        "浙商证券股份有限公司绍兴解放北路证券营业部",
        "中国银河证券股份有限公司绍兴证券营业部",
        "中国银河证券股份有限公司北京阜成路证券营业部",
    ]},
    {"nickname": "佛山无影脚", "real_name": "廖国沛", "tier": "legend", "style": "一日游，翘板，砸盘王", "premium": "negative", "seats": [
        "光大证券股份有限公司佛山绿景路证券营业部",
        "光大证券股份有限公司佛山季华六路证券营业部",
        "湘财证券股份有限公司佛山祖庙路证券营业部",
    ]},
    {"nickname": "炒股养家", "real_name": "", "tier": "legend", "style": "情绪揣摩，通道排板", "premium": "positive", "seats": [
        "华鑫证券有限责任公司上海红宝石路证券营业部",
        "华鑫证券有限责任公司上海宛平南路证券营业部",
    ]},
    {"nickname": "陈小群", "real_name": "陈宴群", "tier": "new_gen", "style": "龙头接力、一线天", "premium": "positive", "seats": [
        "中国银河证券股份有限公司大连黄河路证券营业部",
    ]},
    {"nickname": "呼家楼", "real_name": "", "tier": "new_gen", "style": "多席位协同、板块平铺扫货", "premium": "neutral", "seats": [
        "中信证券股份有限公司上海凯滨路证券营业部",
        "中信证券股份有限公司北京总部",
        "中信建投证券股份有限公司北京朝外大街证券营业部",
    ]},
    {"nickname": "方新侠", "real_name": "", "tier": "new_gen", "style": "大成交趋势票、格局锁仓", "premium": "neutral", "seats": [
        "兴业证券股份有限公司陕西分公司",
        "中信证券股份有限公司西安朱雀大街证券营业部",
    ]},
    {"nickname": "作手新一", "real_name": "严冬", "tier": "new_gen", "style": "龙头战法，连板+趋势", "premium": "positive", "seats": [
        "国泰君安证券股份有限公司南京太平南路证券营业部",
    ]},
    {"nickname": "小鳄鱼", "real_name": "", "tier": "new_gen", "style": "基本面辅助选股", "premium": "neutral", "seats": [
        "南京证券股份有限公司南京大钟亭证券营业部",
        "中金财富证券有限公司南京龙蟠中路证券营业部",
    ]},
    {"nickname": "交易猿", "real_name": "", "tier": "new_gen", "style": "大容量票锁仓、龙头加速", "premium": "neutral", "seats": [
        "华泰证券股份有限公司天津东丽开发区二纬路证券营业部",
        "招商证券股份有限公司福州六一中路证券营业部",
    ]},
    {"nickname": "毛老板", "real_name": "", "tier": "new_gen", "style": "AI主线大资金重仓", "premium": "neutral", "seats": [
        "国泰君安证券股份有限公司北京光华路证券营业部",
        "方正证券股份有限公司乐山龙游路证券营业部",
        "广发证券股份有限公司上海东方路证券营业部",
    ]},
    {"nickname": "消闲派", "real_name": "", "tier": "new_gen", "style": "满仓满融极致进攻", "premium": "neutral", "seats": [
        "华泰证券股份有限公司浙江分公司",
    ]},
    {"nickname": "拉萨天团", "real_name": "", "tier": "regional", "style": "群狼一日游，反向指标", "premium": "negative", "seats": [
        "东方财富证券股份有限公司拉萨",
    ]},
    {"nickname": "成都帮", "real_name": "", "tier": "regional", "style": "底部黑马点火", "premium": "neutral", "seats": [
        "华泰证券股份有限公司成都南一环路第二证券营业部",
    ]},
    {"nickname": "深圳帮", "real_name": "", "tier": "regional", "style": "龙头接力", "premium": "neutral", "seats": [
        "华鑫证券有限责任公司深圳分公司",
        "东亚前海证券有限责任公司深圳分公司",
    ]},
    {"nickname": "上海帮", "real_name": "", "tier": "regional", "style": "大资金运作", "premium": "neutral", "seats": [
        "东方证券股份有限公司上海浦东新区源深路证券营业部",
    ]},
    {"nickname": "杭州帮", "real_name": "", "tier": "regional", "style": "题材股短线", "premium": "neutral", "seats": [
        "中信证券股份有限公司杭州凤起路证券营业部",
    ]},
]

# ── 内存缓存（启动/同步后从 SQLite 加载） ──
_seat_cache: List[dict] = []
_cache_lock = threading.Lock()


def ensure_tables() -> None:
    """确保新表已建。在 init_db 后调用一次。"""
    conn = store.get_conn()
    for stmt in _EXTRA_SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception:
                pass
    conn.commit()


def init_builtin_seats(force: bool = False) -> int:
    """
    写入内置游资席位字典到 lhb_seats 表。

    参数:
        force: True 时清空重建，False 时仅补缺

    返回:
        写入行数
    """
    ensure_tables()
    conn = store.get_conn()
    if force:
        conn.execute("DELETE FROM lhb_seats")
    count = 0
    for youzi in _BUILTIN_SEATS:
        nick = youzi["nickname"]
        for seat in youzi["seats"]:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO lhb_seats(nickname, real_name, tier, style, premium, seat_name) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (nick, youzi.get("real_name", ""), youzi["tier"],
                     youzi.get("style", ""), youzi.get("premium", "neutral"), seat),
                )
                count += 1
            except Exception:
                pass
    conn.commit()
    _reload_cache()
    logger.info("席位字典已初始化 %d 条", count)
    return count


def _reload_cache() -> None:
    """从 SQLite 加载全部席位到内存。"""
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT nickname, real_name, tier, style, premium, seat_name FROM lhb_seats"
    ).fetchall()
    with _cache_lock:
        _seat_cache.clear()
        for r in rows:
            _seat_cache.append(dict(r))


def seat_count() -> int:
    """内存缓存的席位数。"""
    with _cache_lock:
        return len(_seat_cache)


def list_seats() -> List[dict]:
    """返回所有席位条目。"""
    with _cache_lock:
        return list(_seat_cache)


def classify_seat(name: str) -> Dict[str, Optional[str]]:
    """
    根据营业部名称判断席位类型。

    参数:
        name: 东财返回的 OPERATEDEPT_NAME

    返回:
        {"type": "legend", "nickname": "章盟主", "style": "...", "premium": "...", "label": "游资·章盟主"}
        无匹配时 {"type": "broker", "nickname": None, "style": None, "premium": None, "label": "营业部"}
    """
    if not name:
        return {"type": "broker", "nickname": None, "style": None, "premium": None, "label": "营业部"}

    # 机构专用
    if "机构专用" in name:
        return {"type": "institution", "nickname": None, "style": None, "premium": None, "label": "机构"}

    # 北向资金
    for kw in ("沪股通", "深股通", "港股通"):
        if kw in name:
            return {"type": "northbound", "nickname": None, "style": None, "premium": None, "label": "北向"}

    # 游资匹配（包含即命中）
    with _cache_lock:
        for seat in _seat_cache:
            if seat["seat_name"] in name or name in seat["seat_name"]:
                tier = seat["tier"]
                nick = seat["nickname"]
                tier_labels = {"legend": "殿堂", "new_gen": "新生代", "regional": "地方"}
                label = f"游资·{nick}"
                return {
                    "type": tier,
                    "nickname": nick,
                    "style": seat.get("style"),
                    "premium": seat.get("premium"),
                    "label": label,
                }

    return {"type": "broker", "nickname": None, "style": None, "premium": None, "label": "营业部"}
