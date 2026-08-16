"""龙虎榜席位标签库：游资/机构/北向识别（参考 UZI seat_db.py 精简版）
@author ygw
"""
import threading
from typing import Dict, List, Optional, Sequence

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
    source TEXT DEFAULT 'builtin',
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

# ── 内置游资席位种子（仅用于首次建库/恢复出厂；运行期数据以 lhb_seats 表为准） ──
DEFAULT_SEATS: List[dict] = [
    # ── 殿堂级游资 ──
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
        "中信证券股份有限公司佛山桂澜中路证券营业部",
    ]},
    {"nickname": "炒股养家", "real_name": "", "tier": "legend", "style": "情绪揣摩，通道排板", "premium": "positive", "seats": [
        "华鑫证券有限责任公司上海红宝石路证券营业部",
        "华鑫证券有限责任公司上海宛平南路证券营业部",
    ]},
    {"nickname": "金田路", "real_name": "", "tier": "legend", "style": "深圳一线老牌游资，龙头激进打板", "premium": "positive", "seats": [
        "国信证券股份有限公司深圳泰然九路证券营业部",
        "中国银河证券股份有限公司深圳民田路证券营业部",
    ]},
    {"nickname": "欢乐海岸", "real_name": "", "tier": "legend", "style": "核心资产趋势，大资金运作", "premium": "neutral", "seats": [
        "华泰证券股份有限公司深圳益田路荣超商务中心证券营业部",
    ]},
    {"nickname": "葵花宝典", "real_name": "", "tier": "legend", "style": "超短龙头打板", "premium": "positive", "seats": [
        "国海证券股份有限公司广州东风东路证券营业部",
    ]},
    {"nickname": "葛老大", "real_name": "", "tier": "legend", "style": "大资金趋势，主升浪重仓", "premium": "neutral_positive", "seats": [
        "国泰君安证券股份有限公司上海分公司",
    ]},
    {"nickname": "淮海中路", "real_name": "", "tier": "legend", "style": "龙头启动点，热点发动机", "premium": "positive", "seats": [
        "中信证券股份有限公司上海淮海中路证券营业部",
    ]},
    {"nickname": "清扬路", "real_name": "", "tier": "legend", "style": "连板敢死队，主板低位打板", "premium": "neutral", "seats": [
        "中国中投证券有限责任公司无锡清扬路证券营业部",
    ]},
    {"nickname": "宁波解放南", "real_name": "马信琪", "tier": "legend", "style": "敢死队，万手连板排单", "premium": "neutral", "seats": [
        "光大证券股份有限公司宁波解放南路证券营业部",
    ]},
    {"nickname": "徐留胜", "real_name": "", "tier": "legend", "style": "牛散顶级游资，波段锁仓", "premium": "neutral_positive", "seats": [
        "华泰证券股份有限公司深圳益田路证券营业部",
    ]},
    {"nickname": "徐晓", "real_name": "", "tier": "legend", "style": "老牌游资，波段运作", "premium": "neutral", "seats": [
        "国元证券股份有限公司上海虹桥路证券营业部",
    ]},

    # ── 新生代游资 ──
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
    {"nickname": "紫阳东路", "real_name": "", "tier": "new_gen", "style": "武汉一线游资，高位接力", "premium": "neutral", "seats": [
        "国泰海通证券股份有限公司武汉紫阳东路证券营业部",
        "海通证券股份有限公司武汉紫阳东路证券营业部",
        "国泰君安证券股份有限公司武汉紫阳东路证券营业部",
    ]},
    {"nickname": "著名刺客", "real_name": "", "tier": "new_gen", "style": "精准低吸+龙头接力", "premium": "positive", "seats": [
        "中信证券股份有限公司北京望京证券营业部",
    ]},
    {"nickname": "北京炸板哥", "real_name": "", "tier": "new_gen", "style": "强势股博弈，次日竞价", "premium": "neutral", "seats": [
        "华泰证券股份有限公司北京西三环北路证券营业部",
        "中信证券股份有限公司北京东三环中路证券营业部",
    ]},
    {"nickname": "涅槃重升", "real_name": "查一丁", "tier": "new_gen", "style": "超短龙头，半路+打板，情绪流", "premium": "positive", "seats": [
        "上海证券有限责任公司苏州太湖西路证券营业部",
        "长城证券股份有限公司资阳娇子大道证券营业部",
    ]},
    {"nickname": "职业炒手", "real_name": "", "tier": "new_gen", "style": "量化辅助打板", "premium": "neutral", "seats": [
        "国金证券股份有限公司上海奉贤区金碧路证券营业部",
    ]},
    {"nickname": "无锡马夫", "real_name": "", "tier": "new_gen", "style": "趋势股波段，龙头锁仓", "premium": "neutral", "seats": [
        "华泰证券股份有限公司无锡解放西路证券营业部",
    ]},
    {"nickname": "宁波桑田路", "real_name": "", "tier": "new_gen", "style": "一线游资，龙头战法", "premium": "positive", "seats": [
        "银河证券股份有限公司宁波桑田路证券营业部",
        "中国银河证券股份有限公司宁波桑田路证券营业部",
    ]},
    {"nickname": "首板客", "real_name": "", "tier": "new_gen", "style": "首板排单，竞价博弈", "premium": "neutral", "seats": [
        "华泰证券股份有限公司成都蜀金路证券营业部",
    ]},
    {"nickname": "乔帮主", "real_name": "", "tier": "new_gen", "style": "强势股低吸，下午板", "premium": "neutral_positive", "seats": [
        "招商证券股份有限公司深圳蛇口工业七路证券营业部",
        "招商证券股份有限公司深圳蛇口工业三路证券营业部",
    ]},
    {"nickname": "瑞鹤仙", "real_name": "", "tier": "new_gen", "style": "独来独往，趋势波段", "premium": "neutral", "seats": [
        "中信建投证券股份有限公司宜昌解放路证券营业部",
        "中国银河证券股份有限公司宜昌新世纪证券营业部",
    ]},
    {"nickname": "上塘路", "real_name": "", "tier": "new_gen", "style": "扫板封板率最高，节奏大师", "premium": "positive", "seats": [
        "财通证券股份有限公司杭州上塘路证券营业部",
    ]},
    {"nickname": "流沙河", "real_name": "", "tier": "new_gen", "style": "题材潜伏，人气股狙击", "premium": "neutral", "seats": [
        "招商证券股份有限公司北京车公庄西路证券营业部",
        "华泰证券股份有限公司上海武定路证券营业部",
    ]},
    {"nickname": "列夫", "real_name": "", "tier": "new_gen", "style": "市场龙头主做，情绪洞察", "premium": "neutral", "seats": [
        "海通证券股份有限公司绍兴劳动路证券营业部",
    ]},
    {"nickname": "屠文斌", "real_name": "", "tier": "new_gen", "style": "板块中军偏好，大流通票", "premium": "neutral", "seats": [
        "中国银河证券股份有限公司上海杨浦区靖宇东路证券营业部",
    ]},
    {"nickname": "和平路", "real_name": "", "tier": "new_gen", "style": "妖股龙头重仓，波段操作", "premium": "neutral", "seats": [
        "东兴证券股份有限公司晋江和平路证券营业部",
    ]},
    {"nickname": "北京炒家", "real_name": "", "tier": "new_gen", "style": "超短博弈，题材热点", "premium": "neutral", "seats": [
        "长城证券股份有限公司绵阳飞云大道证券营业部",
    ]},
    {"nickname": "玉兰路", "real_name": "", "tier": "new_gen", "style": "龙头锁仓，激进接力", "premium": "neutral_positive", "seats": [
        "东莞证券股份有限公司南京分公司",
    ]},
    {"nickname": "小棉袄", "real_name": "", "tier": "new_gen", "style": "价值投机，逻辑牛股", "premium": "neutral", "seats": [
        "上海证券有限责任公司上海分公司",
    ]},
    {"nickname": "东北猛男", "real_name": "", "tier": "new_gen", "style": "风格激进果断", "premium": "neutral", "seats": [
        "广发证券股份有限公司辽阳民主路证券营业部",
    ]},
    {"nickname": "ASKing", "real_name": "邱宝裕", "tier": "new_gen", "style": "老牌短线，龙头运作", "premium": "neutral", "seats": [
        "兴业证券股份有限公司福州湖东路证券营业部",
    ]},
    {"nickname": "落升", "real_name": "", "tier": "new_gen", "style": "江南神鹰，波段高手", "premium": "neutral", "seats": [
        "光大证券股份有限公司金华宾虹路证券营业部",
    ]},
    {"nickname": "华鑫宁波分", "real_name": "", "tier": "new_gen", "style": "主线热点低吸+打板锁仓", "premium": "neutral_positive", "seats": [
        "华鑫证券有限责任公司宁波分公司",
    ]},
    {"nickname": "宁波和源路", "real_name": "", "tier": "new_gen", "style": "高位接力敢重仓，通道排板", "premium": "neutral", "seats": [
        "甬兴证券有限公司宁波和源路证券营业部",
    ]},
    {"nickname": "北京中关村", "real_name": "", "tier": "new_gen", "style": "竞价抢筹，分歧回暖扫货", "premium": "neutral", "seats": [
        "中国银河证券股份有限公司北京中关村大街证券营业部",
    ]},
    {"nickname": "92科比", "real_name": "", "tier": "new_gen", "style": "龙头理解超越常人，实盘冠军", "premium": "positive", "seats": [
        "兴业证券股份有限公司南京天元东路证券营业部",
        "兴业证券股份有限公司南京分公司",
    ]},
    {"nickname": "歌神", "real_name": "", "tier": "new_gen", "style": "风格凌厉，强势龙头接力", "premium": "neutral_positive", "seats": [
        "中信证券股份有限公司杭州金城路证券营业部",
        "中信证券股份有限公司杭州市心南路证券营业部",
    ]},
    {"nickname": "湖州劳动路", "real_name": "", "tier": "new_gen", "style": "超短博弈，题材挖掘", "premium": "neutral", "seats": [
        "华鑫证券有限责任公司湖州劳动路浙北金融中心证券营业部",
    ]},
    {"nickname": "涪陵广场路", "real_name": "", "tier": "new_gen", "style": "重仓连板封神，激进打板", "premium": "neutral", "seats": [
        "方正证券股份有限公司重庆金开大道证券营业部",
    ]},
    {"nickname": "一瞬流光", "real_name": "", "tier": "new_gen", "style": "超短打板，题材波段", "premium": "neutral", "seats": [
        "浙商证券股份有限公司海宁水月亭西路证券营业部",
    ]},

    # ── 地方帮派 ──
    {"nickname": "拉萨天团", "real_name": "", "tier": "regional", "style": "群狼一日游，反向指标", "premium": "negative", "seats": [
        "东方财富证券股份有限公司拉萨",
    ]},
    {"nickname": "成都帮", "real_name": "", "tier": "regional", "style": "底部黑马点火", "premium": "neutral", "seats": [
        "华泰证券股份有限公司成都南一环路第二证券营业部",
        "华泰证券股份有限公司成都蜀锦路证券营业部",
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
    {"nickname": "厦门帮", "real_name": "", "tier": "regional", "style": "控盘庄股、左侧埋伏", "premium": "neutral", "seats": [
        "国泰君安证券股份有限公司厦门夏禾路证券营业部",
    ]},
    {"nickname": "温州帮", "real_name": "", "tier": "regional", "style": "多席位合力拉高出货", "premium": "negative", "seats": [
        "华鑫证券有限责任公司温州飞霞南路证券营业部",
    ]},
    {"nickname": "北京帮", "real_name": "", "tier": "regional", "style": "大格局资金，题材运作", "premium": "neutral", "seats": [
        "海通证券股份有限公司北京知春路证券营业部",
        "中国银河证券股份有限公司北京朝阳门北大街证券营业部",
        "广发证券股份有限公司潮州潮枫路证券营业部",
    ]},
    {"nickname": "上海超短帮", "real_name": "", "tier": "regional", "style": "超短线快进快出", "premium": "neutral", "seats": [
        "国泰君安证券股份有限公司上海新闸路证券营业部",
        "东方证券股份有限公司上海浦东新区银城中路证券营业部",
    ]},
    {"nickname": "苏州帮", "real_name": "", "tier": "regional", "style": "江浙联动，短线波段", "premium": "neutral", "seats": [
        "华泰证券股份有限公司苏州人民路证券营业部",
        "东吴证券股份有限公司苏州西北街证券营业部",
        "广发证券股份有限公司吴江仲英大道证券营业部",
    ]},
    {"nickname": "保定游资", "real_name": "", "tier": "regional", "style": "低位启动，题材博弈", "premium": "neutral", "seats": [
        "中信证券股份有限公司保定东风中路证券营业部",
        "浙商证券股份有限公司保定复兴中路证券营业部",
    ]},
]

# ── 内存缓存（启动/同步后从 SQLite 加载） ──
_seat_cache: List[dict] = []
_cache_lock = threading.Lock()


def ensure_tables() -> None:
    """确保新表已建 + lhb_seats 补 source 列（旧库迁移）。"""
    conn = store.get_conn()
    for stmt in _EXTRA_SCHEMA.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                conn.execute(stmt)
            except Exception:
                pass
    cols = {r[1] for r in conn.execute("PRAGMA table_info(lhb_seats)").fetchall()}
    if "source" not in cols:
        conn.execute("ALTER TABLE lhb_seats ADD COLUMN source TEXT DEFAULT 'builtin'")
    conn.commit()


def init_builtin_seats(force: bool = False) -> int:
    """
    用内置种子 DEFAULT_SEATS 初始化 lhb_seats 表（种子只用于首次建库/恢复出厂）。

    参数:
        force: True 时仅重建内置条目（删除 source='builtin' 后重灌，保留自定义）；
               False 时仅补内置缺位

    返回:
        写入行数
    """
    ensure_tables()
    conn = store.get_conn()
    if force:
        with store._lock:
            conn.execute("DELETE FROM lhb_seats WHERE source='builtin'")
    count = 0
    with store._lock:
        for youzi in DEFAULT_SEATS:
            nick = youzi["nickname"]
            for seat in youzi["seats"]:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO lhb_seats(nickname, real_name, tier, style, premium, seat_name, source) "
                        "VALUES (?, ?, ?, ?, ?, ?, 'builtin')",
                        (nick, youzi.get("real_name", ""), youzi["tier"],
                         youzi.get("style", ""), youzi.get("premium", "neutral"), seat),
                    )
                    count += 1
                except Exception:
                    pass
        conn.commit()
    _reload_cache()
    logger.info("席位字典初始化 %d 条", count)
    return count


def _reload_cache() -> None:
    """从 SQLite 加载全部席位到内存。"""
    conn = store.get_conn()
    rows = conn.execute(
        "SELECT nickname, real_name, tier, style, premium, seat_name, source "
        "FROM lhb_seats ORDER BY id"
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


def seat_group_exists(nickname: str) -> bool:
    """按昵称判断游资是否存在。"""
    with _cache_lock:
        return any(s["nickname"] == nickname for s in _seat_cache)


def add_seat_group(nickname: str, real_name: str, tier: str, style: str,
                   premium: str, seats: Sequence[str], source: str = "custom") -> int:
    """新增一个游资（含多个席位），写库后重载内存缓存。返回写入行数。"""
    seats = [str(s).strip() for s in seats if s and str(s).strip()]
    if not nickname or not seats:
        raise ValueError("昵称和席位不能为空")
    ensure_tables()
    conn = store.get_conn()
    with store._lock:
        for seat in seats:
            conn.execute(
                "INSERT OR IGNORE INTO lhb_seats(nickname, real_name, tier, style, premium, seat_name, source) "
                "VALUES (?,?,?,?,?,?,?)",
                (nickname, real_name or "", tier or "new_gen", style or "",
                 premium or "neutral", seat, source),
            )
        conn.commit()
    _reload_cache()
    return len(seats)


def update_seat_group(nickname: str, real_name: str, tier: str, style: str,
                      premium: str, seats: Sequence[str]) -> int:
    """整体更新一个游资：删除原席位后重写。改动一律标记自定义，避免被恢复出厂覆盖。"""
    seats = [str(s).strip() for s in seats if s and str(s).strip()]
    if not nickname or not seats:
        raise ValueError("昵称和席位不能为空")
    ensure_tables()
    conn = store.get_conn()
    with store._lock:
        conn.execute("DELETE FROM lhb_seats WHERE nickname=?", (nickname,))
        for seat in seats:
            conn.execute(
                "INSERT INTO lhb_seats(nickname, real_name, tier, style, premium, seat_name, source) "
                "VALUES (?,?,?,?,?,?,'custom')",
                (nickname, real_name or "", tier or "new_gen", style or "",
                 premium or "neutral", seat),
            )
        conn.commit()
    _reload_cache()
    return len(seats)


def delete_seat_group(nickname: str) -> int:
    """删除一个游资（该昵称所有席位），写库后重载内存缓存。返回删除行数。"""
    ensure_tables()
    conn = store.get_conn()
    with store._lock:
        cur = conn.execute("DELETE FROM lhb_seats WHERE nickname=?", (nickname,))
        conn.commit()
    _reload_cache()
    return cur.rowcount


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

    # 游资匹配：精确包含 + 关键地址模糊匹配
    with _cache_lock:
        for seat in _seat_cache:
            matched = False
            sn = seat["seat_name"]
            if sn in name or name in sn:
                matched = True
            elif len(sn) > 6:
                # 券商改名兼容：提取地址关键词（如"武汉紫阳东路"）
                # 去掉常见券商前缀后比较剩余地址部分
                addr_parts = sn.split("公司", 1)
                if len(addr_parts) > 1:
                    addr = addr_parts[-1]
                    # 去掉机构后缀，避免「上海分公司」「浙江分公司」等泛化地址误配其他游资
                    core = addr
                    for suffix in ("证券营业部", "营业部", "分公司", "证券部", "营业部分部", "分部"):
                        if core.endswith(suffix):
                            core = core[:-len(suffix)]
                            break
                    if len(core) >= 4 and core in name:
                        matched = True
            if matched:
                tier = seat["tier"]
                nick = seat["nickname"]
                label = f"游资·{nick}"
                return {
                    "type": tier,
                    "nickname": nick,
                    "style": seat.get("style"),
                    "premium": seat.get("premium"),
                    "label": label,
                }

    return {"type": "broker", "nickname": None, "style": None, "premium": None, "label": "营业部"}
