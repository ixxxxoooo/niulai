"""东财板块表（行业 + 概念）入库：统一板块查询口径

数据源：东方财富公开接口（sector_list），行业约 90 个、概念 500+ 个。
板块成分股不重复落库（现有 /api/sectors/{code} 实时拉取），此表存板块元数据，
供板块页统一使用，并可关联申万行业（sw_stocks.sw1/sw2/sw3_name）。
@author ygw
"""
import time
from typing import List

from . import store

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sectors (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,          -- industry / concept
    synced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sectors_type ON sectors(type);
"""


def ensure_tables() -> None:
    """建板块表。"""
    conn = store.get_conn()
    conn.executescript(_SCHEMA)
    conn.commit()


def sync_sectors() -> dict:
    """全量同步东财行业 + 概念板块元数据。"""
    from ..datasource import eastmoney

    ensure_tables()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    client = eastmoney.get_client()
    payload = []
    for stype, limit in (("industry", 200), ("concept", 500)):
        try:
            for s in client.sector_list(stype, limit, sort_by="main_inflow"):
                name = (s.name or "").strip()
                if name:
                    payload.append((s.code, name, stype, now))
        except Exception:
            continue
    conn = store.get_conn()
    with store._lock:
        conn.executemany(
            "INSERT OR REPLACE INTO sectors(code,name,type,synced_at) VALUES (?,?,?,?)",
            payload,
        )
        conn.commit()
    return {"ok": True, "count": len(payload)}


def sector_count() -> int:
    """板块总数。"""
    try:
        conn = store.get_conn()
        row = conn.execute("SELECT COUNT(*) AS c FROM sectors").fetchone()
        return int(row["c"] or 0)
    except Exception:
        return 0


def list_sectors(stype: str = "") -> List[dict]:
    """板块列表，按类型过滤（industry/concept，空=全部）。"""
    ensure_tables()
    conn = store.get_conn()
    if stype in ("industry", "concept"):
        rows = conn.execute(
            "SELECT code,name,type FROM sectors WHERE type=? ORDER BY name", (stype,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT code,name,type FROM sectors ORDER BY type,name").fetchall()
    return [dict(r) for r in rows]
