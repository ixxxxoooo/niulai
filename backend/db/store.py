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
from typing import Any, Dict, List, Optional, Sequence

from .. import config
from .pinyin import pinyin_initials, pinyin_full
from .tags import infer_board

TZ_CN = timezone(timedelta(hours=8))
DATA_DIR = config.BASE_DIR / "data"
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

CREATE TABLE IF NOT EXISTS watchlist (
    code TEXT PRIMARY KEY,
    added_at TEXT
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

_lock = threading.Lock()
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
        conn = sqlite3.connect(str(DB_PATH), timeout=8)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
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


def init_db() -> None:
    """建表并启动异步日志写入线程。"""
    global _writer_started
    with _lock:
        conn = get_conn()
        # 先建表；全拼索引放在迁移里，避免旧库尚无 pinyin_full 列时 CREATE INDEX 失败
        conn.executescript(_SCHEMA)
        _migrate_stock_columns(conn)
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
    """后台批量写入日志，避免阻塞请求线程。"""
    buf: List[tuple] = []
    last_flush = time.monotonic()
    while True:
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


def _flush_logs(items: List[tuple]) -> None:
    conn = get_conn()
    with _lock:
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
            except sqlite3.Error:
                continue
        conn.commit()
        # 控制体积：各表保留最近 8000 条
        for table in ("api_logs", "user_actions", "ds_logs"):
            conn.execute(
                f"DELETE FROM {table} WHERE id < (SELECT COALESCE(MAX(id),0) FROM {table}) - 8000"
            )
        conn.commit()


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


# ------------------------------------------------------------------ 自选
def watchlist_codes() -> List[str]:
    conn = get_conn()
    rows = conn.execute("SELECT code FROM watchlist ORDER BY added_at").fetchall()
    return [r["code"] for r in rows]


def watchlist_add(code: str) -> bool:
    code = (code or "").strip()
    if not code:
        return False
    conn = get_conn()
    with _lock:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist(code, added_at) VALUES (?, ?)",
            (code, _now()),
        )
        conn.commit()
    return True


def watchlist_remove(code: str) -> None:
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        conn.execute("DELETE FROM positions WHERE code = ?", (code,))
        conn.commit()


def watchlist_clear() -> None:
    conn = get_conn()
    with _lock:
        conn.execute("DELETE FROM watchlist")
        conn.execute("DELETE FROM positions")
        conn.commit()


def watchlist_import(codes: Sequence[str]) -> int:
    """批量导入自选（去重）。返回导入后总数。"""
    now = _now()
    payload = [(c.strip(), now) for c in codes if c and str(c).strip()]
    if payload:
        conn = get_conn()
        with _lock:
            conn.executemany(
                "INSERT OR IGNORE INTO watchlist(code, added_at) VALUES (?, ?)",
                payload,
            )
            conn.commit()
    return len(watchlist_codes())


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
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts, method, path, query, status, duration_ms, size_bytes, detail "
        "FROM api_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_action_logs(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts, action, target, detail FROM user_actions ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_ds_logs(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts, source, host, path, ok, duration_ms, error "
        "FROM ds_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


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
