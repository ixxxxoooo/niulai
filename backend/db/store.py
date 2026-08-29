"""SQLite 存储：股票列表 / 自选 / 设置 / 日志
@author ygw
"""
import os
import queue
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .. import config
from .pinyin import pinyin_initials, pinyin_full
from .tags import infer_board

TZ_CN = timezone(timedelta(hours=8))
DATA_DIR = config.BASE_DIR / "data"

# 测试环境使用临时数据库，避免 pytest 与运行中的容器并发写真实 data/stock.db 造成 WAL 损坏
if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
    import tempfile
    DB_PATH = Path(tempfile.gettempdir()) / "niulai_test_stock.db"
else:
    DB_PATH = DATA_DIR / "stock.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stocks (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    market INTEGER,
    pinyin TEXT,
    pinyin_full TEXT,
    classify TEXT DEFAULT 'AStock',
    board TEXT,
    is_st INTEGER DEFAULT 0,
    industry TEXT,
    concepts TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_stocks_name ON stocks(name);
CREATE INDEX IF NOT EXISTS idx_stocks_pinyin ON stocks(pinyin);
CREATE INDEX IF NOT EXISTS idx_stocks_classify ON stocks(classify);

CREATE TABLE IF NOT EXISTS watchlist_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS watchlist (
    code TEXT NOT NULL,
    group_id INTEGER NOT NULL DEFAULT 1,
    added_at TEXT,
    PRIMARY KEY (code, group_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS api_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    method TEXT,
    path TEXT,
    query TEXT,
    status INTEGER,
    duration_ms REAL,
    size_bytes INTEGER,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS user_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    action TEXT,
    target TEXT,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS ds_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    source TEXT,
    host TEXT,
    path TEXT,
    ok INTEGER,
    duration_ms REAL,
    error TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    code TEXT PRIMARY KEY,
    shares REAL NOT NULL DEFAULT 0,
    cost REAL NOT NULL DEFAULT 0,
    note TEXT DEFAULT '',
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS position_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    code TEXT,
    action TEXT,
    shares REAL,
    cost REAL,
    price REAL,
    amount REAL,
    pnl REAL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS pnl_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    kind TEXT,
    market_value REAL,
    cost_value REAL,
    pnl REAL,
    pnl_pct REAL
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL DEFAULT 'stock',
    code TEXT NOT NULL,
    name TEXT DEFAULT '',
    metric TEXT NOT NULL DEFAULT 'price',
    op TEXT NOT NULL DEFAULT 'lte',
    threshold REAL NOT NULL,
    enabled INTEGER DEFAULT 1,
    cooldown_sec INTEGER DEFAULT 300,
    last_triggered_at TEXT,
    note TEXT DEFAULT '',
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_enabled ON price_alerts(enabled);

CREATE TABLE IF NOT EXISTS lhb_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL,
    seat_name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'broker',
    nickname TEXT NOT NULL DEFAULT '',
    premium TEXT DEFAULT 'neutral',
    buy REAL DEFAULT 0,
    sell REAL DEFAULT 0,
    net REAL DEFAULT 0,
    reason TEXT DEFAULT '',
    UNIQUE(date, code, side, seat_name)
);
CREATE INDEX IF NOT EXISTS idx_lhb_records_date ON lhb_records(date);
CREATE INDEX IF NOT EXISTS idx_lhb_records_nick ON lhb_records(nickname, date);

CREATE TABLE IF NOT EXISTS lhb_dates (
    date TEXT PRIMARY KEY,
    stock_count INTEGER DEFAULT 0,
    record_count INTEGER DEFAULT 0,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS ai_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    reasoning TEXT,
    content TEXT,
    result TEXT,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_ai_history_code ON ai_history(code, id DESC);
"""

_lock = threading.RLock()
_tls = threading.local()
_log_q: "queue.SimpleQueue" = queue.SimpleQueue()
_writer_started = False


def _now() -> str:
    return datetime.now(TZ_CN).strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    """每线程独立连接（WAL）。共享连接 + check_same_thread=False 会在并发读写时 SIGSEGV。"""
    conn = getattr(_tls, "conn", None)
    if conn is None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        _tls.conn = conn
    return conn


def _migrate_stock_columns(conn: sqlite3.Connection) -> None:
    """给已有 stocks 表补标签列（旧库升级）。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(stocks)").fetchall()}
    alters = [
        ("board", "TEXT"),
        ("is_st", "INTEGER DEFAULT 0"),
        ("industry", "TEXT"),
        ("concepts", "TEXT"),
        ("pinyin_full", "TEXT"),
    ]
    for col, spec in alters:
        if col not in cols:
            conn.execute(f"ALTER TABLE stocks ADD COLUMN {col} {spec}")
    # 全拼索引（新列补齐后）
    conn.execute("CREATE INDEX IF NOT EXISTS idx_stocks_pinyin_full ON stocks(pinyin_full)")


def _migrate_watchlist_schema(conn: sqlite3.Connection) -> None:
    """自选股多分组迁移。"""
    conn.execute("""
    CREATE TABLE IF NOT EXISTS watchlist_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT
    )
    """)
    # 清理历史可能存在的"默认自选"虚拟分组
    conn.execute("DELETE FROM watchlist_groups WHERE name IN ('默认自选', '默认')")

    # 检查 watchlist 是否已有 group_id 列
    cols = {r[1] for r in conn.execute("PRAGMA table_info(watchlist)").fetchall()}
    if "group_id" not in cols:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_new (
            code TEXT NOT NULL,
            group_id INTEGER NOT NULL DEFAULT 0,
            added_at TEXT,
            PRIMARY KEY (code, group_id)
        )
        """)
        conn.execute("""
        INSERT OR IGNORE INTO watchlist_new(code, group_id, added_at)
        SELECT code, 0, added_at FROM watchlist
        """)
        conn.execute("DROP TABLE watchlist")
        conn.execute("ALTER TABLE watchlist_new RENAME TO watchlist")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_group ON watchlist(group_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_code ON watchlist(code)")


_LOG_TABLE_SCHEMAS = {
    "api_logs": """
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            method TEXT,
            path TEXT,
            query TEXT,
            status INTEGER,
            duration_ms REAL,
            size_bytes INTEGER,
            detail TEXT
        );
    """,
    "user_actions": """
        CREATE TABLE IF NOT EXISTS user_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            action TEXT,
            target TEXT,
            detail TEXT
        );
    """,
    "ds_logs": """
        CREATE TABLE IF NOT EXISTS ds_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            source TEXT,
            host TEXT,
            path TEXT,
            ok INTEGER,
            duration_ms REAL,
            error TEXT
        );
    """,
}


def _repair_log_table(table_name: str) -> None:
    """自愈损坏或缺失的日志表，避免阻断服务与后台线程。"""
    schema = _LOG_TABLE_SCHEMAS.get(table_name)
    if not schema:
        return
    try:
        conn = get_conn()
        with _lock:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.executescript(schema)
            conn.commit()
    except Exception:
        pass


def _check_log_tables(conn: sqlite3.Connection) -> None:
    """启动时检查日志表完整性，如有损坏则自动重置。"""
    for table, schema in _LOG_TABLE_SCHEMAS.items():
        try:
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        except sqlite3.DatabaseError:
            try:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
                conn.executescript(schema)
                conn.commit()
            except Exception:
                pass


def init_db() -> None:
    """建表并启动异步日志写入线程。"""
    global _writer_started
    with _lock:
        conn = get_conn()
        # 先建表；全拼索引放在迁移里，避免旧库尚无 pinyin_full 列时 CREATE INDEX 失败
        conn.executescript(_SCHEMA)
        _check_log_tables(conn)
        _migrate_stock_columns(conn)
        _migrate_watchlist_schema(conn)
        _init_preset_groups_if_needed(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stocks_board ON stocks(board)")
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if not _writer_started:
            t = threading.Thread(target=_log_writer, name="sqlite-log", daemon=True)
            t.start()
            t2 = threading.Thread(target=_wal_checkpointer, name="sqlite-wal-ckpt", daemon=True)
            t2.start()
            _writer_started = True


def _wal_checkpointer() -> None:
    """每60秒执行 WAL checkpoint，确保设置等数据持久化到主DB文件。"""
    while True:
        time.sleep(60)
        try:
            conn = get_conn()
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
        except Exception:
            pass


def _log_writer() -> None:
    """后台批量写入日志，带有顶级异常保护，避免守护线程崩溃。"""
    buf: List[tuple] = []
    last_flush = time.monotonic()
    last_cleanup = time.monotonic()
    while True:
        try:
            try:
                item = _log_q.get(timeout=1.0)
                buf.append(item)
            except queue.Empty:
                item = None
            now = time.monotonic()
            if buf and (len(buf) >= 20 or now - last_flush >= 1.0 or item is None):
                _flush_logs(buf)
                buf = []
                last_flush = now
            # 定期清理（每 120 秒），避免高频执行 DELETE 子查询造成的锁竞争
            if now - last_cleanup >= 120.0:
                _cleanup_old_logs()
                last_cleanup = now
        except Exception:
            time.sleep(0.5)


def _flush_logs(items: List[tuple]) -> None:
    if not items:
        return
    conn = get_conn()
    with _lock:
        try:
            for kind, payload in items:
                try:
                    if kind == "api":
                        conn.execute(
                            "INSERT INTO api_logs(ts,method,path,query,status,duration_ms,size_bytes,detail) "
                            "VALUES (?,?,?,?,?,?,?,?)",
                            payload,
                        )
                    elif kind == "action":
                        conn.execute(
                            "INSERT INTO user_actions(ts,action,target,detail) VALUES (?,?,?,?)",
                            payload,
                        )
                    elif kind == "ds":
                        conn.execute(
                            "INSERT INTO ds_logs(ts,source,host,path,ok,duration_ms,error) VALUES (?,?,?,?,?,?,?)",
                            payload,
                        )
                except sqlite3.DatabaseError:
                    if kind == "api":
                        _repair_log_table("api_logs")
                    elif kind == "action":
                        _repair_log_table("user_actions")
                    elif kind == "ds":
                        _repair_log_table("ds_logs")
                except sqlite3.Error:
                    continue
            conn.commit()
        except sqlite3.DatabaseError:
            try:
                conn.rollback()
            except Exception:
                pass
        except Exception:
            pass


def _cleanup_old_logs() -> None:
    """控制体积：各表保留最近 8000 条。"""
    conn = get_conn()
    with _lock:
        for table in ("api_logs", "user_actions", "ds_logs"):
            try:
                conn.execute(
                    f"DELETE FROM {table} WHERE id < (SELECT COALESCE(MAX(id),0) FROM {table}) - 8000"
                )
                conn.commit()
            except sqlite3.DatabaseError:
                _repair_log_table(table)
            except Exception:
                pass


# ------------------------------------------------------------------ 股票列表
def upsert_stocks(rows: Sequence[Dict[str, Any]]) -> int:
    """批量写入/更新股票基础信息（含板块/行业标签）。"""
    if not rows:
        return 0
    now = _now()
    payload = []
    for r in rows:
        code = str(r.get("code") or "").strip()
        if not code:
            continue
        name = str(r.get("name") or "")
        classify = r.get("classify") or "AStock"
        board, is_st = infer_board(code, name, classify)
        if r.get("board"):
            board = r.get("board")
        if r.get("is_st") is not None:
            is_st = int(r.get("is_st") or 0)
        payload.append((
            code, name, r.get("market"),
            pinyin_initials(name),
            pinyin_full(name),
            classify,
            board,
            is_st,
            r.get("industry") or "",
            r.get("concepts") or "",
            now,
        ))
    conn = get_conn()
    with _lock:
        conn.executemany(
            "INSERT INTO stocks(code,name,market,pinyin,pinyin_full,classify,board,is_st,industry,concepts,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(code) DO UPDATE SET name=excluded.name, market=excluded.market, "
            "pinyin=excluded.pinyin, pinyin_full=excluded.pinyin_full, "
            "classify=excluded.classify, board=excluded.board, "
            "is_st=excluded.is_st, updated_at=excluded.updated_at, "
            "industry=COALESCE(NULLIF(excluded.industry,''), stocks.industry), "
            "concepts=COALESCE(NULLIF(excluded.concepts,''), stocks.concepts)",
            payload,
        )
        conn.commit()
    return len(payload)


def get_stock(code: str) -> Optional[Dict[str, Any]]:
    """按代码取本地标签。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT code,name,market,classify,board,is_st,industry,concepts FROM stocks WHERE code=?",
        (code,),
    ).fetchone()
    return dict(row) if row else None


def get_stocks_map(codes: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    """批量取本地标签。"""
    codes = [c for c in codes if c]
    if not codes:
        return {}
    conn = get_conn()
    qs = ",".join("?" * len(codes))
    rows = conn.execute(
        f"SELECT code,name,market,classify,board,is_st,industry,concepts FROM stocks WHERE code IN ({qs})",
        list(codes),
    ).fetchall()
    return {r["code"]: dict(r) for r in rows}


def merge_concepts(mapping: Dict[str, List[str]]) -> int:
    """把概念名合并进 stocks.concepts（逗号分隔、去重）。"""
    if not mapping:
        return 0
    conn = get_conn()
    n = 0
    with _lock:
        for code, names in mapping.items():
            if not code or not names:
                continue
            row = conn.execute("SELECT concepts FROM stocks WHERE code=?", (code,)).fetchone()
            old = [x for x in str(row["concepts"] if row and row["concepts"] else "").split(",") if x]
            merged = []
            seen = set()
            for x in old + list(names):
                x = str(x).strip()
                if x and x not in seen:
                    seen.add(x)
                    merged.append(x)
            conn.execute(
                "UPDATE stocks SET concepts=? WHERE code=?",
                (",".join(merged), code),
            )
            n += 1
        conn.commit()
    return n


def update_stock_tags(code: str, industry: str = "", concepts: Optional[List[str]] = None) -> None:
    """写入单只股票的行业/概念（详情页即时补全）。"""
    if not code:
        return
    conn = get_conn()
    with _lock:
        if industry:
            conn.execute(
                "UPDATE stocks SET industry=COALESCE(NULLIF(?, ''), industry) WHERE code=?",
                (industry, code),
            )
        if concepts is not None:
            conn.execute("UPDATE stocks SET concepts=? WHERE code=?", (",".join(concepts), code))
        conn.commit()


def stock_count() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS c FROM stocks").fetchone()
    return int(row["c"] if row else 0)


def stocks_updated_at() -> Optional[str]:
    conn = get_conn()
    row = conn.execute("SELECT MAX(updated_at) AS t FROM stocks").fetchone()
    return row["t"] if row and row["t"] else None


def search_stocks_local(keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    本地模糊搜索：代码 / 名称 / 拼音首字母 / 全拼（支持前缀与中间匹配，如 gzmt、zmt、maotai）。
    @author ygw
    """
    q = (keyword or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    prefix = f"{q}%"
    py = q.lower().replace(" ", "")
    py_like = f"%{py}%"
    py_prefix = f"{py}%"
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT code, name, market, classify, pinyin, pinyin_full FROM stocks
        WHERE code = ? OR code LIKE ? OR name LIKE ?
           OR pinyin = ? OR pinyin LIKE ? OR pinyin LIKE ?
           OR pinyin_full = ? OR pinyin_full LIKE ? OR pinyin_full LIKE ?
        ORDER BY
          CASE
            WHEN code = ? THEN 0
            WHEN code LIKE ? THEN 1
            WHEN name LIKE ? THEN 2
            WHEN pinyin = ? OR pinyin_full = ? THEN 3
            WHEN pinyin LIKE ? OR pinyin_full LIKE ? THEN 4
            ELSE 5
          END,
          length(name), code
        LIMIT ?
        """,
        (
            q, prefix, like,
            py, py_prefix, py_like,
            py, py_prefix, py_like,
            q, prefix, like, py, py, py_prefix, py_prefix,
            limit,
        ),
    ).fetchall()
    out = []
    for r in rows:
        classify = r["classify"] or "AStock"
        out.append({
            "code": r["code"],
            "name": r["name"],
            "market": r["market"],
            "type": "ETF" if classify == "Fund" else "A股",
            "pinyin": r["pinyin"] or "",
            "pinyin_full": r["pinyin_full"] or "",
        })
    return out


# ------------------------------------------------------------------ 热门预设分组定义
PRESET_POPULAR_GROUPS = [
    {
        "name": "ETF",
        "stocks": [
            ("510300", "沪深300ETF"),
            ("510500", "中证500ETF"),
            ("512100", "中证1000ETF"),
            ("510050", "上证50ETF"),
            ("159915", "创业板ETF"),
            ("159949", "创业板50ETF"),
            ("588000", "科创50ETF"),
            ("588100", "科创100ETF"),
            ("512480", "半导体ETF"),
            ("588170", "科创芯片ETF"),
            ("515880", "通信ETF"),
            ("159819", "人工智能ETF"),
            ("159852", "软件ETF"),
            ("561600", "消费电子ETF"),
            ("516630", "云计算50ETF"),
            ("159755", "电池ETF"),
            ("515790", "光伏ETF"),
            ("562500", "机器人ETF"),
            ("562550", "绿电ETF"),
            ("515220", "煤炭ETF"),
            ("512880", "证券ETF"),
            ("512800", "银行ETF"),
            ("159992", "创新药ETF"),
            ("512690", "酒ETF"),
            ("512660", "军工ETF"),
            ("512400", "有色金属ETF"),
            ("518880", "黄金ETF"),
            ("513130", "恒生科技ETF"),
            ("159530", "港股通科技ETF"),
        ],
    },
    {
        "name": "光通信",
        "stocks": [
            ("300308", "中际旭创"),
            ("300502", "新易盛"),
            ("300394", "天孚通信"),
            ("688498", "源杰科技"),
            ("300570", "太辰光"),
            ("002281", "光迅科技"),
            ("000988", "华工科技"),
            ("603083", "剑桥科技"),
            ("301205", "联特科技"),
            ("688313", "仕佳光子"),
            ("300620", "光库科技"),
            ("003031", "中瓷电子"),
            ("002902", "铭普光磁"),
            ("300548", "博创科技"),
            ("600487", "亨通光电"),
            ("600522", "中天科技"),
            ("601869", "长飞光纤"),
        ],
    },
    {
        "name": "PCB",
        "stocks": [
            ("002463", "沪电股份"),
            ("300476", "胜宏科技"),
            ("688183", "生益电子"),
            ("600183", "生益科技"),
            ("002916", "深南电路"),
            ("001389", "广合科技"),
            ("603228", "景旺电子"),
            ("002938", "鹏鼎控股"),
            ("603920", "世运电路"),
            ("002913", "奥士康"),
            ("603186", "华正新材"),
            ("688519", "南亚新材"),
        ],
    },
    {
        "name": "先进封装",
        "stocks": [
            ("002156", "通富微电"),
            ("600584", "长电科技"),
            ("002185", "华天科技"),
            ("688362", "甬矽电子"),
            ("603005", "晶方科技"),
            ("600520", "文一科技"),
            ("301348", "蓝箭电子"),
            ("300398", "飞凯材料"),
            ("688535", "华海诚科"),
            ("688403", "汇成股份"),
            ("688035", "德邦科技"),
            ("300429", "强力新材"),
        ],
    },
    {
        "name": "存储芯片",
        "stocks": [
            ("688008", "澜起科技"),
            ("603986", "兆易创新"),
            ("301308", "江波龙"),
            ("001309", "德明利"),
            ("688525", "佰维存储"),
            ("688766", "普冉股份"),
            ("688123", "聚辰股份"),
            ("300223", "北京君正"),
            ("688110", "东芯股份"),
            ("300042", "朗科科技"),
            ("300475", "香农芯创"),
            ("688416", "恒烁股份"),
        ],
    },
    {
        "name": "半导体自主可控",
        "stocks": [
            ("002371", "北方华创"),
            ("688012", "中微公司"),
            ("688041", "海光信息"),
            ("688256", "寒武纪"),
            ("688047", "龙芯中科"),
            ("688072", "拓荆科技"),
            ("688120", "华海清科"),
            ("688981", "中芯国际"),
            ("688347", "华虹公司"),
            ("688082", "盛美上海"),
            ("688037", "芯源微"),
            ("300474", "景嘉微"),
            ("300567", "精测电子"),
        ],
    },
    {
        "name": "AI硬件基础设施",
        "stocks": [
            ("601138", "工业富联"),
            ("000977", "浪潮信息"),
            ("603019", "中科曙光"),
            ("000938", "紫光股份"),
            ("002837", "英维克"),
            ("002130", "沃尔核材"),
            ("300563", "神宇股份"),
            ("300870", "欧陆通"),
            ("688629", "华丰科技"),
            ("688668", "鼎通科技"),
            ("300499", "高澜股份"),
            ("300602", "飞荣达"),
        ],
    },
    {
        "name": "算力租赁",
        "stocks": [
            ("603629", "利通电子"),
            ("300442", "润泽科技"),
            ("603220", "中贝通信"),
            ("002261", "拓维信息"),
            ("002229", "鸿博股份"),
            ("603985", "恒润股份"),
            ("603019", "中科曙光"),
            ("002602", "世纪华通"),
            ("300857", "协创数据"),
            ("300657", "弘信电子"),
            ("301085", "亚康股份"),
            ("603881", "数据港"),
            ("300067", "安诺其"),
            ("300846", "首都在线"),
            ("000628", "高新发展"),
            ("002929", "润建股份"),
            ("688158", "优刻得"),
        ],
    },
    {
        "name": "AI软件",
        "stocks": [
            ("002230", "科大讯飞"),
            ("688111", "金山办公"),
            ("300033", "同花顺"),
            ("601360", "三六零"),
            ("300418", "昆仑万维"),
            ("300624", "万兴科技"),
            ("300229", "拓尔思"),
            ("301236", "软通动力"),
            ("300339", "润和软件"),
            ("300634", "彩讯股份"),
            ("002315", "焦点科技"),
        ],
    },
    {
        "name": "消费电子",
        "stocks": [
            ("002475", "立讯精密"),
            ("002241", "歌尔股份"),
            ("002600", "领益智造"),
            ("300433", "蓝思科技"),
            ("002273", "水晶光电"),
            ("002938", "鹏鼎控股"),
            ("002456", "欧菲光"),
            ("002384", "东山精密"),
            ("688036", "传音控股"),
            ("300207", "欣旺达"),
        ],
    },
    {
        "name": "锂电池",
        "stocks": [
            ("300750", "宁德时代"),
            ("002594", "比亚迪"),
            ("300014", "亿纬锂能"),
            ("002074", "国轩高科"),
            ("002460", "赣锋锂业"),
            ("002466", "天齐锂业"),
            ("002709", "天赐材料"),
            ("002812", "恩捷股份"),
            ("603659", "璞泰来"),
            ("002407", "多氟多"),
            ("603799", "华友钴业"),
        ],
    },
    {
        "name": "电网设备",
        "stocks": [
            ("600406", "国电南瑞"),
            ("600089", "特变电工"),
            ("000400", "许继电气"),
            ("601179", "中国西电"),
            ("002028", "思源电气"),
            ("600312", "平高电气"),
            ("601567", "三星医疗"),
            ("688676", "金盘科技"),
            ("600550", "保变电气"),
            ("601126", "四方股份"),
        ],
    },
    {
        "name": "光伏储能",
        "stocks": [
            ("300274", "阳光电源"),
            ("601012", "隆基绿能"),
            ("600438", "通威股份"),
            ("002129", "TCL中环"),
            ("002459", "晶澳科技"),
            ("688223", "晶科能源"),
            ("300763", "锦浪科技"),
            ("605117", "德业股份"),
            ("600732", "爱旭股份"),
            ("002865", "钧达股份"),
            ("688390", "固德威"),
        ],
    },
    {
        "name": "券商",
        "stocks": [
            ("300059", "东方财富"),
            ("600030", "中信证券"),
            ("601688", "华泰证券"),
            ("601211", "国泰君安"),
            ("601878", "浙商证券"),
            ("601818", "光大证券"),
            ("601995", "中金公司"),
            ("601377", "中信建投"),
            ("300803", "指南针"),
            ("000776", "广发证券"),
        ],
    },
    {
        "name": "商业航天",
        "stocks": [
            ("600879", "航天电子"),
            ("600118", "中国卫星"),
            ("002465", "海格通信"),
            ("300045", "华力创通"),
            ("300762", "上海瀚讯"),
            ("002544", "普天科技"),
            ("300455", "航天智装"),
            ("300342", "天银机电"),
            ("300102", "乾照光电"),
            ("301517", "陕西华达"),
        ],
    },
    {
        "name": "国防军工",
        "stocks": [
            ("600760", "中航沈飞"),
            ("000768", "中航西飞"),
            ("600893", "航发动力"),
            ("002179", "中航光电"),
            ("600765", "中航重机"),
            ("600862", "中航高科"),
            ("600150", "中国船舶"),
            ("601989", "中国重工"),
            ("600316", "洪都航空"),
            ("002389", "航天彩虹"),
        ],
    },
    {
        "name": "贵金属与小金属",
        "stocks": [
            ("601899", "紫金矿业"),
            ("600547", "山东黄金"),
            ("600489", "中金黄金"),
            ("600988", "赤峰黄金"),
            ("002155", "湖南黄金"),
            ("603993", "洛阳钼业"),
            ("000657", "中钨高新"),
            ("600549", "厦门钨业"),
            ("600111", "北方稀土"),
            ("000831", "中国稀土"),
            ("002428", "云南锗业"),
            ("000960", "锡业股份"),
        ],
    },
    {
        "name": "基础化工",
        "stocks": [
            ("600309", "万华化学"),
            ("600426", "华鲁恒升"),
            ("600160", "巨化股份"),
            ("603379", "三美股份"),
            ("601058", "赛轮轮胎"),
            ("601966", "玲珑轮胎"),
            ("600346", "恒力石化"),
            ("000301", "东方盛虹"),
            ("002601", "龙佰集团"),
            ("600486", "扬农化工"),
        ],
    },
    {
        "name": "创新药",
        "stocks": [
            ("688235", "百济神州"),
            ("600276", "恒瑞医药"),
            ("603259", "药明康德"),
            ("688331", "荣昌生物"),
            ("002422", "科伦药业"),
            ("301333", "诺思格"),
            ("688192", "迪哲医药"),
            ("688180", "君实生物"),
            ("002294", "信立泰"),
            ("300759", "康龙化成"),
        ],
    },
    {
        "name": "白酒",
        "stocks": [
            ("600519", "贵州茅台"),
            ("000858", "五粮液"),
            ("000568", "泸州老窖"),
            ("600809", "山西汾酒"),
            ("000596", "古井贡酒"),
            ("002304", "洋河股份"),
            ("603369", "今世缘"),
            ("600702", "舍得酒业"),
            ("000799", "酒鬼酒"),
            ("603198", "迎驾贡酒"),
        ],
    },
    {
        "name": "银行",
        "stocks": [
            ("601398", "工商银行"),
            ("601939", "建设银行"),
            ("601288", "农业银行"),
            ("601988", "中国银行"),
            ("600036", "招商银行"),
            ("601328", "交通银行"),
            ("600919", "江苏银行"),
            ("601838", "成都银行"),
            ("600926", "杭州银行"),
            ("002142", "宁波银行"),
        ],
    },
    {
        "name": "能源",
        "stocks": [
            ("600938", "中国海油"),
            ("601857", "中国石油"),
            ("600028", "中国石化"),
            ("600256", "广汇能源"),
            ("600803", "新奥股份"),
            ("605090", "九丰能源"),
            ("601808", "中海油服"),
            ("601088", "中国神华"),
            ("601225", "陕西煤业"),
            ("600188", "兖矿能源"),
            ("601898", "中煤能源"),
            ("000983", "山西焦煤"),
            ("601699", "潞安环能"),
            ("600900", "长江电力"),
            ("601985", "中国核电"),
            ("003816", "中国广核"),
            ("600011", "华能国际"),
            ("600886", "国投电力"),
        ],
    },
    {
        "name": "电力",
        "stocks": [
            ("600900", "长江电力"),
            ("601985", "中国核电"),
            ("003816", "中国广核"),
            ("600905", "三峡能源"),
            ("600011", "华能国际"),
            ("600886", "国投电力"),
            ("600795", "国电电力"),
            ("600027", "华电国际"),
            ("600023", "浙能电力"),
            ("600674", "川投能源"),
            ("600642", "申能股份"),
            ("001289", "龙源电力"),
        ],
    },
    {
        "name": "人形机器人",
        "stocks": [
            ("603728", "鸣志电器"),
            ("002050", "三花智控"),
            ("601689", "拓普集团"),
            ("688017", "绿的谐波"),
            ("002472", "双环传动"),
            ("603009", "北特科技"),
            ("300580", "贝斯特"),
            ("603662", "柯力传感"),
            ("002896", "中大力德"),
            ("601100", "恒立液压"),
            ("688160", "步科股份"),
        ],
    },
    {
        "name": "低空经济",
        "stocks": [
            ("002085", "万丰奥威"),
            ("000099", "中信海直"),
            ("001696", "宗申动力"),
            ("688631", "莱斯信息"),
            ("600990", "四创电子"),
            ("600580", "卧龙电驱"),
            ("002389", "航天彩虹"),
            ("688522", "纳睿雷达"),
            ("002097", "山河智能"),
            ("300542", "新晨科技"),
            ("300699", "光威复材"),
        ],
    },
]


def _init_preset_groups_if_needed(conn: sqlite3.Connection) -> None:
    """如果当前暂无分组，自动初始化热门预设分组及成分股。"""
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM watchlist_groups").fetchone()
        count = row["c"] if row else 0
        if count == 0:
            _populate_presets(conn)
    except Exception:
        pass


def _populate_presets(conn: sqlite3.Connection) -> None:
    """初始化写入预设热门分组及成分股。"""
    now = _now()
    stock_payload = []
    watch_payload = []
    for idx, g in enumerate(PRESET_POPULAR_GROUPS):
        gname = g["name"]
        sort_order = idx * 10
        conn.execute(
            "INSERT OR IGNORE INTO watchlist_groups(name, sort_order, created_at) VALUES (?, ?, ?)",
            (gname, sort_order, now),
        )
        grow = conn.execute("SELECT id FROM watchlist_groups WHERE name = ?", (gname,)).fetchone()
        if not grow:
            continue
        gid = grow["id"]
        for code, name in g["stocks"]:
            watch_payload.append((code, gid, now))
            classify = "Fund" if code.startswith(("15", "16", "51", "56", "58")) else "AStock"
            board, is_st = infer_board(code, name, classify)
            stock_payload.append((
                code, name, 1 if code.startswith(("6", "5", "9")) else 0,
                pinyin_initials(name), pinyin_full(name), classify, board, is_st,
                gname, gname, now,
            ))

    if stock_payload:
        conn.executemany(
            "INSERT INTO stocks(code,name,market,pinyin,pinyin_full,classify,board,is_st,industry,concepts,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(code) DO UPDATE SET name=CASE WHEN stocks.name='' THEN excluded.name ELSE stocks.name END, "
            "industry=COALESCE(NULLIF(stocks.industry,''), excluded.industry), "
            "concepts=COALESCE(NULLIF(stocks.concepts,''), excluded.concepts)",
            stock_payload,
        )
    if watch_payload:
        conn.executemany(
            "INSERT OR IGNORE INTO watchlist(code, group_id, added_at) VALUES (?, ?, ?)",
            watch_payload,
        )


def init_preset_groups(presets: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """手动重新初始化/补全热门预设分组。"""
    conn = get_conn()
    with _lock:
        _populate_presets(conn)
        conn.commit()
    return {"ok": True, "groups": list_watchlist_groups()}


# ------------------------------------------------------------------ 自选分组管理
def list_watchlist_groups() -> List[Dict[str, Any]]:
    """获取所有自选分组、各自分组股票数量及股票代码列表。"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT g.id, g.name, g.sort_order, g.created_at,
               COUNT(w.code) AS count
        FROM watchlist_groups g
        LEFT JOIN watchlist w ON g.id = w.group_id
        GROUP BY g.id, g.name, g.sort_order, g.created_at
        ORDER BY g.sort_order ASC, g.id ASC
    """).fetchall()

    group_map: Dict[int, List[str]] = {}
    for r in conn.execute("SELECT group_id, code FROM watchlist ORDER BY added_at ASC, code ASC").fetchall():
        group_map.setdefault(r["group_id"], []).append(r["code"])

    result = []
    for r in rows:
        d = dict(r)
        d["codes"] = group_map.get(r["id"], [])
        result.append(d)
    return result


def create_watchlist_group(name: str) -> Dict[str, Any]:
    """创建新自选分组。"""
    name = (name or "").strip()
    if not name:
        raise ValueError("分组名称不能为空")
    conn = get_conn()
    with _lock:
        existing = conn.execute("SELECT id FROM watchlist_groups WHERE name = ?", (name,)).fetchone()
        if existing:
            raise ValueError(f"分组「{name}」已存在")
        r = conn.execute("SELECT COALESCE(MAX(sort_order), 0) AS max_s FROM watchlist_groups").fetchone()
        next_sort = (r["max_s"] if r else 0) + 10
        now = _now()
        cur = conn.execute(
            "INSERT INTO watchlist_groups(name, sort_order, created_at) VALUES (?, ?, ?)",
            (name, next_sort, now),
        )
        conn.commit()
        gid = cur.lastrowid
    return {"id": gid, "name": name, "sort_order": next_sort, "count": 0, "codes": [], "created_at": now}


def update_watchlist_group(group_id: int, name: Optional[str] = None, sort_order: Optional[int] = None) -> bool:
    """重命名分组或更新排序。"""
    conn = get_conn()
    updates = []
    params = []
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("分组名称不能为空")
        updates.append("name = ?")
        params.append(name)
    if sort_order is not None:
        updates.append("sort_order = ?")
        params.append(int(sort_order))
    if not updates:
        return False
    params.append(group_id)
    with _lock:
        conn.execute(f"UPDATE watchlist_groups SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    return True


def delete_watchlist_group(group_id: int) -> bool:
    """删除自选分组（不影响其他分组内的股票）。"""
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM watchlist WHERE group_id = ?", (group_id,))
        conn.execute("DELETE FROM watchlist_groups WHERE id = ?", (group_id,))
        conn.commit()
    return True


def reorder_watchlist_groups(group_ids: List[int]) -> bool:
    """批量调整分组排序。"""
    if not group_ids:
        return False
    conn = get_conn()
    with _lock:
        for idx, gid in enumerate(group_ids):
            conn.execute("UPDATE watchlist_groups SET sort_order = ? WHERE id = ?", (idx * 10, gid))
        conn.commit()
    return True


# ------------------------------------------------------------------ 自选股
def watchlist_codes(group_id: Optional[int] = None) -> List[str]:
    """查询自选股代码列表。若 group_id 为空则返回全量去重列表。"""
    conn = get_conn()
    if group_id is not None:
        rows = conn.execute(
            "SELECT code FROM watchlist WHERE group_id = ? ORDER BY added_at ASC, code ASC",
            (group_id,),
        ).fetchall()
        return [r["code"] for r in rows]
    # 全量去重自选（按最早添加时间排序）
    rows = conn.execute(
        "SELECT code, MIN(added_at) as min_added FROM watchlist GROUP BY code ORDER BY min_added ASC, code ASC"
    ).fetchall()
    return [r["code"] for r in rows]


def watchlist_add(code: str, group_id: Optional[int] = None) -> bool:
    """添加股票到自选（若指定 group_id 则加入对应分组，否则 group_id=0）。"""
    code = (code or "").strip()
    if not code:
        return False
    gid = group_id if group_id is not None else 0
    conn = get_conn()
    with _lock:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist(code, group_id, added_at) VALUES (?, ?, ?)",
            (code, gid, _now()),
        )
        conn.commit()
    return True


def watchlist_remove(code: str, group_id: Optional[int] = None) -> None:
    """从指定分组移出股票；若未指定 group_id，则从所有自选分组与持仓中彻底移除。"""
    code = (code or "").strip()
    if not code:
        return
    conn = get_conn()
    with _lock:
        if group_id is not None:
            conn.execute("DELETE FROM watchlist WHERE code = ? AND group_id = ?", (code, group_id))
        else:
            conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
            conn.execute("DELETE FROM positions WHERE code = ?", (code,))
        conn.commit()


def watchlist_clear(group_id: Optional[int] = None) -> None:
    """清空指定分组或全部自选股。"""
    conn = get_conn()
    with _lock:
        if group_id is not None:
            conn.execute("DELETE FROM watchlist WHERE group_id = ?", (group_id,))
        else:
            conn.execute("DELETE FROM watchlist")
            conn.execute("DELETE FROM positions")
        conn.commit()


def watchlist_import(codes: Sequence[str], group_id: Optional[int] = None) -> int:
    """批量导入自选股到指定分组。"""
    now = _now()
    gid = group_id if group_id is not None else 0
    payload = [(c.strip(), gid, now) for c in codes if c and str(c).strip()]
    if payload:
        conn = get_conn()
        with _lock:
            conn.executemany(
                "INSERT OR IGNORE INTO watchlist(code, group_id, added_at) VALUES (?, ?, ?)",
                payload,
            )
            conn.commit()
    return len(watchlist_codes(group_id))


def get_stock_group_ids(code: str) -> List[int]:
    """获取某只股票所属的所有有效分组 ID。"""
    code = (code or "").strip()
    if not code:
        return []
    conn = get_conn()
    rows = conn.execute("SELECT group_id FROM watchlist WHERE code = ? AND group_id > 0", (code,)).fetchall()
    return [r["group_id"] for r in rows]


def set_stock_groups(code: str, group_ids: List[int]) -> None:
    """设置某只股票所属的分组列表（覆盖更新）。"""
    code = (code or "").strip()
    if not code:
        return
    now = _now()
    valid_gids = [int(gid) for gid in group_ids if gid is not None and int(gid) > 0]
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        if valid_gids:
            payload = [(code, gid, now) for gid in valid_gids]
            conn.executemany(
                "INSERT OR IGNORE INTO watchlist(code, group_id, added_at) VALUES (?, ?, ?)",
                payload,
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO watchlist(code, group_id, added_at) VALUES (?, 0, ?)",
                (code, now),
            )
        conn.commit()


# ------------------------------------------------------------------ 设置
def get_settings() -> Dict[str, str]:
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        conn.commit()


def set_settings(items: Dict[str, Any]) -> None:
    for k, v in items.items():
        if k:
            set_setting(k, "" if v is None else str(v))


# ------------------------------------------------------------------ 日志入队
def log_api(method: str, path: str, query: str, status: int,
            duration_ms: float, size_bytes: int = 0, detail: str = "") -> None:
    try:
        _log_q.put_nowait(("api", (
            _now(), method, path, query or "", int(status),
            round(duration_ms, 1), int(size_bytes or 0), (detail or "")[:300],
        )))
    except Exception:
        pass


def log_action(action: str, target: str = "", detail: str = "", ts: str = "") -> None:
    try:
        _log_q.put_nowait(("action", (ts or _now(), action, target or "", (detail or "")[:500])))
    except Exception:
        pass


def log_ds(source: str, host: str, path: str, ok: bool,
           duration_ms: float, error: str = "") -> None:
    try:
        _log_q.put_nowait(("ds", (
            _now(), source, host or "", path or "", 1 if ok else 0,
            round(duration_ms, 1), (error or "")[:300],
        )))
    except Exception:
        pass


def list_api_logs(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ts, method, path, query, status, duration_ms, size_bytes, detail "
            "FROM api_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.DatabaseError:
        _repair_log_table("api_logs")
        return []
    except Exception:
        return []


def list_action_logs(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ts, action, target, detail FROM user_actions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.DatabaseError:
        _repair_log_table("user_actions")
        return []
    except Exception:
        return []


def list_ds_logs(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        conn = get_conn()
        rows = conn.execute(
            "SELECT ts, source, host, path, ok, duration_ms, error "
            "FROM ds_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.DatabaseError:
        _repair_log_table("ds_logs")
        return []
    except Exception:
        return []


def in_pytest() -> bool:
    return "pytest" in sys.modules or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def list_positions() -> List[Dict[str, Any]]:
    """全部持仓。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT code, shares, cost, note, updated_at FROM positions ORDER BY updated_at"
    ).fetchall()
    return [dict(r) for r in rows]


def get_position(code: str) -> Optional[Dict[str, Any]]:
    """单只持仓。"""
    conn = get_conn()
    row = conn.execute(
        "SELECT code, shares, cost, note, updated_at FROM positions WHERE code=?",
        (code,),
    ).fetchone()
    return dict(row) if row else None


def upsert_position(code: str, shares: float, cost: float, note: str = "",
                    price: Optional[float] = None) -> Dict[str, Any]:
    """录入/更新持仓，并写流水。shares=0 视为清空。"""
    code = (code or "").strip()
    if not code:
        raise ValueError("代码不能为空")
    shares = float(shares or 0)
    cost = float(cost or 0)
    note = note or ""
    if shares < 0 or cost < 0:
        raise ValueError("数量和成本价不能为负")
    conn = get_conn()
    now = _now()
    amount = shares * cost
    with _lock:
        if shares <= 0:
            conn.execute("DELETE FROM positions WHERE code=?", (code,))
            action = "clear"
            shares = 0
            cost = 0
            amount = 0
        else:
            conn.execute(
                "INSERT INTO positions(code, shares, cost, note, updated_at) VALUES (?,?,?,?,?) "
                "ON CONFLICT(code) DO UPDATE SET shares=excluded.shares, cost=excluded.cost, "
                "note=excluded.note, updated_at=excluded.updated_at",
                (code, shares, cost, note, now),
            )
            action = "set"
        conn.execute(
            "INSERT INTO position_ledger(ts, code, action, shares, cost, price, amount, pnl, note) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now, code, action, shares, cost, price, amount, None, note),
        )
        conn.commit()
    return get_position(code) or {"code": code, "shares": 0, "cost": 0, "note": "", "updated_at": now}


def delete_position(code: str) -> None:
    """删除持仓。"""
    upsert_position(code, 0, 0)


def import_positions(items: List[Dict[str, Any]]) -> int:
    """批量导入持仓（覆盖写入，不写流水）。返回导入条数。
    @param items: [{code, shares, cost, note?}]
    @author ygw
    """
    conn = get_conn()
    now = _now()
    n = 0
    with _lock:
        for it in items or []:
            code = str(it.get("code") or "").strip()
            if not code.isdigit() or len(code) != 6:
                continue
            shares = float(it.get("shares") or 0)
            cost = float(it.get("cost") or 0)
            if shares < 0 or cost < 0:
                continue
            note = str(it.get("note") or "")
            if shares <= 0:
                conn.execute("DELETE FROM positions WHERE code=?", (code,))
            else:
                conn.execute(
                    "INSERT INTO positions(code, shares, cost, note, updated_at) VALUES (?,?,?,?,?) "
                    "ON CONFLICT(code) DO UPDATE SET shares=excluded.shares, cost=excluded.cost, "
                    "note=excluded.note, updated_at=excluded.updated_at",
                    (code, shares, cost, note, now),
                )
            n += 1
        conn.commit()
    return n


def list_ledger(code: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """持仓流水。"""
    conn = get_conn()
    if code:
        rows = conn.execute(
            "SELECT ts, code, action, shares, cost, price, amount, pnl, note "
            "FROM position_ledger WHERE code=? ORDER BY id DESC LIMIT ?",
            (code, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ts, code, action, shares, cost, price, amount, pnl, note "
            "FROM position_ledger ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def list_pnl_snapshots(limit: int = 30) -> List[Dict[str, Any]]:
    """历史盈亏快照。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, ts, kind, market_value, cost_value, pnl, pnl_pct "
        "FROM pnl_snapshots ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_pnl_snapshot(snapshot_id: int) -> None:
    """删除指定收益记录快照。"""
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM pnl_snapshots WHERE id=?", (int(snapshot_id),))
        conn.commit()


def clear_pnl_snapshots() -> None:
    """清空全部收益记录快照。"""
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM pnl_snapshots")
        conn.commit()


def maybe_daily_snapshot(rows: Sequence[Dict[str, Any]]) -> None:
    """每个自然日只记一组分快照（all/stock/etf）。"""
    if not rows:
        return
    today = _now()[:10]
    conn = get_conn()
    hit = conn.execute(
        "SELECT id FROM pnl_snapshots WHERE ts LIKE ? LIMIT 1",
        (today + "%",),
    ).fetchone()
    if hit:
        return
    now = _now()
    with _lock:
        for r in rows:
            conn.execute(
                "INSERT INTO pnl_snapshots(ts, kind, market_value, cost_value, pnl, pnl_pct) "
                "VALUES (?,?,?,?,?,?)",
                (
                    now,
                    r.get("kind") or "all",
                    float(r.get("market_value") or 0),
                    float(r.get("cost_value") or 0),
                    float(r.get("pnl") or 0),
                    float(r.get("pnl_pct") or 0) if r.get("pnl_pct") is not None else None,
                ),
            )
        conn.commit()


# ------------------------------------------------------------------ 价格监控
def list_alerts(enabled_only: bool = False) -> List[Dict[str, Any]]:
    """列出价格/跌幅监控规则。"""
    conn = get_conn()
    if enabled_only:
        rows = conn.execute(
            "SELECT * FROM price_alerts WHERE enabled=1 ORDER BY id DESC"
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM price_alerts ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_alert(alert_id: int) -> Optional[Dict[str, Any]]:
    """按 id 取监控规则。"""
    conn = get_conn()
    row = conn.execute("SELECT * FROM price_alerts WHERE id=?", (alert_id,)).fetchone()
    return dict(row) if row else None


def create_alert(
    target_type: str,
    code: str,
    name: str,
    metric: str,
    op: str,
    threshold: float,
    cooldown_sec: int = 300,
    note: str = "",
) -> Dict[str, Any]:
    """新建监控规则，返回完整记录。"""
    conn = get_conn()
    with _lock:
        cur = conn.execute(
            "INSERT INTO price_alerts(target_type, code, name, metric, op, threshold, "
            "enabled, cooldown_sec, note, created_at) VALUES (?,?,?,?,?,?,1,?,?,?)",
            (
                target_type, code, name or "", metric, op, float(threshold),
                int(cooldown_sec), note or "", _now(),
            ),
        )
        conn.commit()
        aid = cur.lastrowid
    return get_alert(aid) or {}


def update_alert(alert_id: int, **fields) -> Optional[Dict[str, Any]]:
    """更新监控规则可写字段。"""
    allowed = {
        "name", "metric", "op", "threshold", "enabled",
        "cooldown_sec", "note", "last_triggered_at",
    }
    patch = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not patch:
        return get_alert(alert_id)
    cols = ", ".join(f"{k}=?" for k in patch)
    vals = list(patch.values()) + [alert_id]
    conn = get_conn()
    with _lock:
        conn.execute(f"UPDATE price_alerts SET {cols} WHERE id=?", vals)
        conn.commit()
    return get_alert(alert_id)


def delete_alert(alert_id: int) -> None:
    """删除监控规则。"""
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM price_alerts WHERE id=?", (alert_id,))
        conn.commit()


def mark_alert_triggered(alert_id: int) -> None:
    """标记刚触发时间，用于冷却。"""
    update_alert(alert_id, last_triggered_at=_now())


# ── 用户数据备份 / 恢复（iCloud 多设备同步用） ──
# 仅含用户产生/关心的数据表；stocks / daily_bars / lhb_records（可从接口重建）/
# 日志等可重建数据不导出。
USER_BACKUP_TABLES = [
    "watchlist_groups", "watchlist", "settings", "positions", "position_ledger", "pnl_snapshots",
    "price_alerts", "lhb_seats", "lhb_dates",
    "screener_runs", "screener_hits", "ai_history",
]


def export_user_backup() -> Dict[str, Any]:
    """导出全部用户数据，返回 {表名: [行...]}。
    生成一个导出时间戳，供导入方展示。
    @author ygw
    """
    conn = get_conn()
    data = {}
    for table in USER_BACKUP_TABLES:
        try:
            rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
            data[table] = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            # 表不存在（早期库可能缺），跳过
            data[table] = []
    return {
        "version": 1,
        "exported_at": _now(),
        "app": "niulai",
        "tables": data,
    }


def import_user_backup(payload: Dict[str, Any]) -> Dict[str, int]:
    """恢复用户数据：整体替换（先清空对应表再写入）。
    仅处理已知的用户表；新行自增主键 id 保留原值（lhb_records 有唯一约束，防止重复）。
    @param payload: {tables: {表名: [行...]}}
    @return: {表名: 导入行数}
    @author ygw
    """
    tables = (payload or {}).get("tables") or {}
    conn = get_conn()
    result: Dict[str, int] = {}
    with _lock:
        for table in USER_BACKUP_TABLES:
            if table not in tables:
                continue
            rows = tables.get(table) or []
            # 清空旧数据后整体写入（id 自增主键：保留原 id 以维持流水/快照/选股外键一致）
            conn.execute(f'DELETE FROM "{table}"')
            if rows:
                cols = list(rows[0].keys())
                placeholders = ", ".join(["?"] * len(cols))
                col_sql = ", ".join(f'"{c}"' for c in cols)
                conn.executemany(
                    f'INSERT INTO "{table}"({col_sql}) VALUES ({placeholders})',
                    [tuple(r.get(c) for c in cols) for r in rows],
                )
            result[table] = len(rows)
        conn.commit()
    return result


# ------------------------------------------------------------------ AI 分析历史
def save_ai_history(code: str, reasoning: str, content: str,
                    result: Optional[Dict[str, Any]] = None) -> None:
    """保存一条 AI 分析历史，仅保留该股票最近 5 条（倒序）。线程安全。"""
    import json
    code = (code or "").strip()
    if not code:
        return
    conn = get_conn()
    with _lock:
        conn.execute(
            "INSERT INTO ai_history (code, reasoning, content, result, created_at) VALUES (?,?,?,?,?)",
            (code, reasoning or "", content or "",
             json.dumps(result, ensure_ascii=False) if result else None,
             _now()),
        )
        conn.execute(
            "DELETE FROM ai_history WHERE code=? AND id NOT IN "
            "(SELECT id FROM ai_history WHERE code=? ORDER BY id DESC LIMIT 5)",
            (code, code),
        )
        conn.commit()


def get_ai_history(code: str, limit: int = 5) -> List[Dict[str, Any]]:
    """读取某股票 AI 分析历史（倒序，最多 limit 条）。"""
    import json
    code = (code or "").strip()
    if not code:
        return []
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, code, reasoning, content, result, created_at "
        "FROM ai_history WHERE code=? ORDER BY id DESC LIMIT ?",
        (code, limit),
    ).fetchall()
    items = []
    for r in rows:
        res = {}
        if r["result"]:
            try:
                res = json.loads(r["result"])
            except Exception:
                res = {}
        items.append({
            "id": r["id"],
            "code": r["code"],
            "reasoning": r["reasoning"] or "",
            "content": r["content"] or "",
            "result": res,
            "created_at": r["created_at"] or "",
        })
    return items

