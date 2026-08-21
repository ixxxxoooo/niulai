from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ...db import store as db

from .common import (
    ttl_cache, WatchBody, WatchImportBody, PositionBody,
    WatchGroupCreateBody, WatchGroupUpdateBody, WatchGroupReorderBody, WatchStockGroupsBody,
)

router = APIRouter()

@router.get("/watchlist")
def watchlist_get(group_id: Optional[int] = Query(None)):
    """自选股代码列表（支持按分组过滤，并返回分组元数据）"""
    return {
        "codes": db.watchlist_codes(group_id),
        "groups": db.list_watchlist_groups(),
        "current_group_id": group_id,
    }


@router.get("/watchlist/groups")
def watchlist_groups_get():
    """自选分组列表及各组股票数量"""
    return {"groups": db.list_watchlist_groups()}


@router.post("/watchlist/groups")
def watchlist_group_create(body: WatchGroupCreateBody):
    """新建自选分组"""
    try:
        grp = db.create_watchlist_group(body.name)
        return {"ok": True, "group": grp, "groups": db.list_watchlist_groups()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/watchlist/groups/{group_id}")
def watchlist_group_update(group_id: int, body: WatchGroupUpdateBody):
    """重命名自选分组或修改排序"""
    try:
        db.update_watchlist_group(group_id, name=body.name, sort_order=body.sort_order)
        return {"ok": True, "groups": db.list_watchlist_groups()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/watchlist/groups/{group_id}")
def watchlist_group_delete(group_id: int):
    """删除自选分组"""
    try:
        db.delete_watchlist_group(group_id)
        return {"ok": True, "groups": db.list_watchlist_groups()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/watchlist/groups/reorder")
def watchlist_groups_reorder(body: WatchGroupReorderBody):
    """批量调整自选分组顺序"""
    db.reorder_watchlist_groups(body.group_ids)
    return {"ok": True, "groups": db.list_watchlist_groups()}


@router.get("/watchlist/stock-groups/{code}")
def watchlist_stock_groups_get(code: str):
    """获取某只股票所属的分组 ID 列表"""
    return {"code": code, "group_ids": db.get_stock_group_ids(code)}


@router.post("/watchlist/stock-groups")
def watchlist_stock_groups_set(body: WatchStockGroupsBody):
    """设置某只股票所属的分组列表（支持批量归属多分组）"""
    code = body.code.strip()
    if not code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码须为 6 位数字")
    db.set_stock_groups(code, body.group_ids)
    return {"ok": True, "code": code, "group_ids": db.get_stock_group_ids(code), "groups": db.list_watchlist_groups()}


@router.post("/watchlist/init-presets")
def watchlist_init_presets():
    """重新初始化/补充热门预设分组及成分股"""
    res = db.init_preset_groups()
    return {"ok": True, "groups": res.get("groups", []), "codes": db.watchlist_codes()}


@router.post("/watchlist")
def watchlist_post(body: WatchBody):
    """添加自选股（可指定分组，默认归入默认自选）"""
    code = body.code.strip()
    if not code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码须为 6 位数字")
    db.watchlist_add(code, body.group_id)
    return {"ok": True, "codes": db.watchlist_codes(body.group_id), "groups": db.list_watchlist_groups()}


@router.delete("/watchlist/{code}")
def watchlist_delete(code: str, group_id: Optional[int] = Query(None)):
    """删除自选股（若传 group_id 则仅从该分组移出，不传则从全部自选及持仓中删除）"""
    db.watchlist_remove(code, group_id)
    return {"ok": True, "codes": db.watchlist_codes(group_id), "groups": db.list_watchlist_groups()}


@router.post("/watchlist/import")
def watchlist_import(body: WatchImportBody):
    """批量导入自选股"""
    codes = [str(c).strip() for c in (body.codes or []) if str(c).strip().isdigit() and len(str(c).strip()) == 6]
    n = db.watchlist_import(codes, body.group_id)
    return {"ok": True, "count": n, "codes": db.watchlist_codes(body.group_id), "groups": db.list_watchlist_groups()}


@router.post("/watchlist/clear")
def watchlist_clear(group_id: Optional[int] = Query(None)):
    """清空自选股"""
    db.watchlist_clear(group_id)
    return {"ok": True, "codes": [], "groups": db.list_watchlist_groups()}


def _is_etf_row(d: dict) -> bool:
    name = str(d.get("name") or "")
    code = str(d.get("code") or "")
    return d.get("classify") == "Fund" or d.get("type") == "ETF" or "ETF" in name.upper() or bool(
        code.startswith(("15", "16", "51", "56", "58"))
    )


def _pnl_bucket(items: list) -> dict:
    mv = sum(float(x.get("market_value") or 0) for x in items)
    cv = sum(float(x.get("cost_value") or 0) for x in items)
    pnl = mv - cv
    pct = (pnl / cv * 100.0) if cv else None
    return {
        "market_value": mv,
        "cost_value": cv,
        "pnl": pnl,
        "pnl_pct": pct,
        "count": len(items),
    }


@router.get("/positions")
def positions_get():
    """持仓列表。"""
    return {"items": db.list_positions()}


@router.put("/positions")
def positions_put(body: PositionBody):
    """录入/更新持仓（shares=0 清空）。同时确保在自选中。"""
    code = body.code.strip()
    if not code.isdigit():
        raise HTTPException(status_code=400, detail="股票代码须为 6 位数字")
    if body.shares < 0 or body.cost < 0:
        raise HTTPException(status_code=400, detail="数量和成本价不能为负")
    db.watchlist_add(code)
    row = db.upsert_position(code, body.shares, body.cost, body.note or "")
    return {"ok": True, "item": row, "codes": db.watchlist_codes()}


@router.delete("/positions/snapshots")
def positions_snapshots_clear():
    """清空全部收益记录快照。"""
    db.clear_pnl_snapshots()
    return {"ok": True}


@router.delete("/positions/snapshots/{snapshot_id}")
def positions_snapshot_delete(snapshot_id: int):
    """删除指定收益记录快照。"""
    db.delete_pnl_snapshot(snapshot_id)
    return {"ok": True}


@router.delete("/positions/{code}")
def positions_delete(code: str):
    """清空该标的持仓（仍保留自选）。"""
    db.delete_position(code)
    return {"ok": True, "items": db.list_positions()}


@router.get("/positions/summary")
def positions_summary():
    """持仓浮动盈亏（个股/ETF 分计 + 合计），并按日落快照。"""
    pos = db.list_positions()
    pos = [p for p in pos if float(p.get("shares") or 0) > 0]
    if not pos:
        empty = _pnl_bucket([])
        return {
            "all": empty, "stock": empty, "etf": empty,
            "items": [], "snapshots": db.list_pnl_snapshots(14),
        }
    codes = [p["code"] for p in pos]
    from .stocks import stocks_batch
    quotes = {r.get("code"): r for r in stocks_batch(",".join(codes))}
    items = []
    for p in pos:
        q = quotes.get(p["code"]) or {}
        price = q.get("price")
        shares = float(p.get("shares") or 0)
        cost = float(p.get("cost") or 0)
        mv = (price if price is not None else 0) * shares
        cv = cost * shares
        pnl = mv - cv if price is not None else None
        pct = (pnl / cv * 100.0) if (pnl is not None and cv) else None
        row = {
            **p,
            "name": q.get("name") or p["code"],
            "price": price,
            "change_pct": q.get("change_pct"),
            "market_value": mv,
            "cost_value": cv,
            "pnl": pnl,
            "pnl_pct": pct,
            "classify": q.get("classify"),
            "board": q.get("board"),
            "is_st": q.get("is_st"),
            "industry": q.get("industry"),
        }
        items.append(row)
    stocks = [x for x in items if not _is_etf_row(x)]
    etfs = [x for x in items if _is_etf_row(x)]
    summary = {
        "all": _pnl_bucket(items),
        "stock": _pnl_bucket(stocks),
        "etf": _pnl_bucket(etfs),
        "items": items,
        "snapshots": db.list_pnl_snapshots(14),
    }
    db.maybe_daily_snapshot([
        {"kind": "all", **summary["all"]},
        {"kind": "stock", **summary["stock"]},
        {"kind": "etf", **summary["etf"]},
    ])
    summary["snapshots"] = db.list_pnl_snapshots(14)
    return summary


@router.get("/positions/ledger")
def positions_ledger(code: str = Query("", max_length=6), limit: int = Query(80, ge=1, le=300)):
    """持仓流水。"""
    return db.list_ledger(code or None, limit)
