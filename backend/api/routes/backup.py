"""用户数据备份 / 恢复路由（iCloud 多设备同步用）
@author ygw
"""
from typing import Optional

from fastapi import APIRouter

from ...db import store as db

from .common import BackupBody

router = APIRouter()


@router.get("/backup/export")
def backup_export():
    """导出全部用户数据（自选/持仓/监控/设置/流水/游资/选股/AI历史）。"""
    return db.export_user_backup()


@router.post("/backup/import")
def backup_import(body: BackupBody):
    """整体恢复用户数据（先清空对应表再写入）。"""
    result = db.import_user_backup(body.payload or {})
    return {"ok": True, "imported": result}