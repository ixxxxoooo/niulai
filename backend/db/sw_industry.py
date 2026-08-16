"""申万行业分类（2021 版）入库：行业字典（一级/二级/三级）+ 股票映射

数据源（均免费无需 token）：
- 行业字典：AKShare sw_index_first/second/third_info（一级31/二级131/三级335）
- 成分股：申万宏源官网 API（swsresearch.com，JSON 直取，快且稳定）
@author ygw
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import httpx

from . import store

_SW_STATUS: Dict = {"running": False, "percent": 0, "message": "", "error": ""}
_lock = threading.Lock()

_SW_API = "https://www.swsresearch.com/institute-sw/api/index_publish/details/component_stocks/"
_SW_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Referer": "https://www.swsresearch.com/",
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sw_industries (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    level INTEGER NOT NULL,
    parent_name TEXT DEFAULT '',
    parent_code TEXT DEFAULT '',
    stock_count INTEGER DEFAULT 0,
    synced_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sw_industries_level ON sw_industries(level);
CREATE INDEX IF NOT EXISTS idx_sw_industries_parent ON sw_industries(parent_code);

CREATE TABLE IF NOT EXISTS sw_stocks (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT DEFAULT '',
    sw3_code TEXT DEFAULT '',
    sw3_name TEXT DEFAULT '',
    sw2_name TEXT DEFAULT '',
    sw1_name TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_sw_stocks_sw3 ON sw_stocks(sw3_code);
"""


def ensure_tables() -> None:
    """建申万行业相关表。"""
    conn = store.get_conn()
    conn.executescript(_SCHEMA)
    conn.commit()


def sync_status() -> Dict:
    """同步进度状态。"""
    with _lock:
        return dict(_SW_STATUS)


def start_sw_sync() -> Dict:
    """后台启动申万行业同步（非阻塞）。"""
    with _lock:
        if _SW_STATUS.get("running"):
            return {"started": False, "message": "申万行业正在同步中"}
    t = threading.Thread(target=sync_sw_industry, daemon=True)
    t.start()
    return {"started": True, "message": "已启动申万行业同步"}

def _set_status(**kw) -> None:
    with _lock:
        _SW_STATUS.update(kw)


def _fetch_cons(code: str) -> List[dict]:
    """拉某申万行业（纯数字代码）成分股：[{stockcode, stockname}]，失败返回 []。"""
    try:
        r = httpx.get(
            _SW_API,
            params={"swindexcode": code, "page": "1", "page_size": "10000"},
            headers=_SW_HEADERS, timeout=15, verify=False,
        )
        r.raise_for_status()
        return (r.json().get("data") or {}).get("results") or []
    except Exception:
        return []


def sw_count() -> int:
    """已同步的股票映射数。"""
    try:
        conn = store.get_conn()
        row = conn.execute("SELECT COUNT(*) AS c FROM sw_stocks").fetchone()
        return int(row["c"] or 0)
    except Exception:
        return 0


def sync_sw_industry() -> Dict:
    """全量同步申万行业分类（行业字典 + 股票映射），后台执行约 1 分钟。

    行业字典优先复用库中已有（缺失时才用 AKShare 拉取，legulegu 源不稳定会重试）；
    成分股走申万宏源官网 API（稳定）。

    返回:
        {"ok", "industries", "stocks"} 同步统计
    """
    _set_status(running=True, percent=0, message="检查申万行业字典…", error="")
    ensure_tables()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    conn = store.get_conn()

    # ── 1. 行业字典（复用库中 / 缺失时 AKShare 拉取，重试 3 次） ──
    existing = int(conn.execute("SELECT COUNT(*) AS c FROM sw_industries").fetchone()["c"] or 0)
    name_to1: Dict[str, str] = {}   # 二级名 → 一级名
    name_to2: Dict[str, str] = {}   # 三级名 → 二级名
    code_to_name: Dict[str, str] = {}

    if existing > 0:
        rows = conn.execute(
            "SELECT code,name,level,parent_name FROM sw_industries ORDER BY level"
        ).fetchall()
        rows1 = [{"行业代码": r["code"], "行业名称": r["name"]} for r in rows if r["level"] == 1]
        rows2 = [{"行业代码": r["code"], "行业名称": r["name"], "上级行业": r["parent_name"]} for r in rows if r["level"] == 2]
        rows3 = [{"行业代码": r["code"], "行业名称": r["name"], "上级行业": r["parent_name"]} for r in rows if r["level"] == 3]
    else:
        import akshare as ak
        last_err = ""
        for _ in range(3):
            try:
                df1 = ak.sw_index_first_info()
                df2 = ak.sw_index_second_info()
                df3 = ak.sw_index_third_info()
                break
            except Exception as e:
                last_err = str(e)
                time.sleep(2)
        else:
            _set_status(running=False, error=f"拉取申万行业字典失败：{last_err}")
            return {"ok": False, "error": last_err}

        rows1 = df1[["行业代码", "行业名称"]].to_dict("records")
        rows2 = df2[["行业代码", "行业名称", "上级行业"]].to_dict("records")
        rows3 = df3[["行业代码", "行业名称", "上级行业"]].to_dict("records")

        with store._lock:
            for r in rows1:
                conn.execute(
                    "INSERT OR REPLACE INTO sw_industries(code,name,level,parent_name,synced_at) VALUES (?,?,1,'',?)",
                    (r["行业代码"], r["行业名称"], now),
                )
            for r in rows2:
                conn.execute(
                    "INSERT OR REPLACE INTO sw_industries(code,name,level,parent_name,synced_at) VALUES (?,?,2,?,?)",
                    (r["行业代码"], r["行业名称"], r["上级行业"] or "", now),
                )
            for r in rows3:
                conn.execute(
                    "INSERT OR REPLACE INTO sw_industries(code,name,level,parent_name,synced_at) VALUES (?,?,3,?,?)",
                    (r["行业代码"], r["行业名称"], r["上级行业"] or "", now),
                )
            conn.commit()

    for r in rows1:
        code_to_name[r["行业代码"]] = r["行业名称"]
    for r in rows2:
        code_to_name[r["行业代码"]] = r["行业名称"]
        name_to1[r["行业名称"]] = r["上级行业"] or ""
    for r in rows3:
        code_to_name[r["行业代码"]] = r["行业名称"]
        name_to2[r["行业名称"]] = r["上级行业"] or ""

    # 二级/三级的 parent_code 关联
    code_to_parent = {}
    for r in rows2:
        code_to_parent[r["行业代码"]] = name_to1.get(r["行业名称"], "")
    for r in rows3:
        code_to_parent[r["行业代码"]] = name_to2.get(r["行业名称"], "")
    name_to_code = {}
    for r in rows2:
        name_to_code.setdefault(r["行业名称"], r["行业代码"])
    for r in rows3:
        name_to_code.setdefault(r["行业名称"], r["行业代码"])
    for code, pname in code_to_parent.items():
        pcode = ""
        if pname:
            for c, n in code_to_name.items():
                if n == pname:
                    pcode = c
                    break
        conn.execute("UPDATE sw_industries SET parent_code=? WHERE code=?", (pcode, code))
    conn.commit()

    # ── 2. 成分股（遍历三级行业）──
    conn.execute("DELETE FROM sw_stocks")
    conn.commit()

    total = len(rows3)
    mapping: Dict[str, tuple] = {}
    failed: List[str] = []

    def _one(r: dict):
        code, name = r["行业代码"], r["行业名称"]
        sw2 = r["上级行业"] or ""
        sw1 = name_to1.get(sw2, "") or (name_to2.get(sw2, "") and name_to1.get(name_to2[sw2], "")) or ""
        for attempt in range(4):
            cons = _fetch_cons(code.split(".")[0])
            if cons:
                return code, name, sw2, sw1, cons
            time.sleep(0.5)
        failed.append(code)
        return None

    _set_status(percent=5, message=f"拉取三级行业成分（0/{total}）…")
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, res in enumerate(ex.map(_one, rows3)):
            if res:
                code, name, sw2, sw1, cons = res
                mapping[code] = (name, sw2, sw1, cons)
            if i % 20 == 0:
                _set_status(percent=5 + int(i / total * 85), message=f"拉取三级行业成分（{i}/{total}）…")

    # 失败的行业再重试（串行）
    for code in failed:
        for _ in range(3):
            try:
                cons = _fetch_cons(code.split(".")[0])
                r = next(x for x in rows3 if x["行业代码"] == code)
                if cons:
                    mapping[code] = (r["行业名称"], r["上级行业"] or "",
                                     name_to1.get(r["上级行业"] or "", ""), cons)
                    break
            except Exception:
                pass
            time.sleep(1)

    _set_status(percent=92, message="写入股票行业映射…")
    total_stocks = 0
    with store._lock:
        for code, (name, sw2, sw1, cons) in mapping.items():
            conn.execute("UPDATE sw_industries SET stock_count=? WHERE code=?", (len(cons), code))
            for row in cons:
                scode = str(row.get("stockcode") or "").strip()
                if not scode:
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO sw_stocks(stock_code,stock_name,sw3_code,sw3_name,sw2_name,sw1_name) "
                    "VALUES (?,?,?,?,?,?)",
                    (scode, str(row.get("stockname") or "").strip(), code, name, sw2, sw1),
                )
                total_stocks += 1
        # 二级/一级股票数 = 子级之和
        conn.execute(
            "UPDATE sw_industries SET stock_count=(SELECT COALESCE(SUM(stock_count),0) FROM sw_industries c "
            "WHERE c.parent_code=sw_industries.code) WHERE level=2"
        )
        conn.execute(
            "UPDATE sw_industries SET stock_count=(SELECT COALESCE(SUM(stock_count),0) FROM sw_industries c "
            "WHERE c.parent_code=sw_industries.code) WHERE level=1"
        )
        conn.commit()

    _set_status(running=False, percent=100, message=f"完成：行业 {len(rows1)+len(rows2)+len(rows3)} 个，股票 {total_stocks} 只")
    return {"ok": True, "industries": len(rows1) + len(rows2) + len(rows3), "stocks": total_stocks}


# ── 查询 ──
def list_sw_industries(level: int = 1, parent: str = "") -> List[dict]:
    """行业字典：按级别/父级过滤，按股票数降序。"""
    ensure_tables()
    conn = store.get_conn()
    sql = "SELECT code,name,level,parent_name,parent_code,stock_count FROM sw_industries WHERE level=?"
    args: List[object] = [level]
    if parent:
        sql += " AND parent_code=?"
        args.append(parent)
    sql += " ORDER BY stock_count DESC"
    rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]


def get_sw_industry(code: str) -> Optional[dict]:
    """单个行业字典。"""
    conn = store.get_conn()
    row = conn.execute(
        "SELECT code,name,level,parent_name,parent_code,stock_count FROM sw_industries WHERE code=?",
        (code,),
    ).fetchone()
    return dict(row) if row else None


def list_sw_stocks(code: str, limit: int = 500) -> List[dict]:
    """某申万行业（一级/二级/三级 code 或名称均可）的成分股。"""
    conn = store.get_conn()
    # 解析传入 code → 行业级别与名称
    ind = get_sw_industry(code)
    if ind:
        name, level = ind["name"], ind["level"]
        if level == 3:
            cond = "s.sw3_code=? OR s.sw3_name=?"
            args = [code, name]
        elif level == 2:
            cond = "s.sw2_name=?"
            args = [name]
        else:
            cond = "s.sw1_name=?"
            args = [name]
    else:
        cond = "s.sw3_name=? OR s.sw2_name=? OR s.sw1_name=?"
        args = [code, code, code]
    rows = conn.execute(
        f"SELECT s.stock_code AS code, s.stock_name AS name, s.sw3_name, s.sw2_name, s.sw1_name, "
        f"COALESCE(m.industry,'') AS industry, COALESCE(m.concepts,'') AS concepts "
        f"FROM sw_stocks s LEFT JOIN stocks m ON m.code = s.stock_code "
        f"WHERE {cond} ORDER BY s.stock_code LIMIT ?",
        args + [limit],
    ).fetchall()
    return [dict(r) for r in rows]


def stock_sw(code: str) -> Optional[dict]:
    """个股申万行业映射。"""
    conn = store.get_conn()
    row = conn.execute(
        "SELECT stock_code AS code, stock_name AS name, sw3_code, sw3_name, sw2_name, sw1_name "
        "FROM sw_stocks WHERE stock_code=?",
        (code,),
    ).fetchone()
    return dict(row) if row else None
