"""标的板块/ST 标签推断
@author ygw
"""
from typing import Tuple


def infer_board(code: str, name: str = "", classify: str = "AStock") -> Tuple[str, int]:
    """根据代码/名称推断板块标签与是否 ST。

    返回 (board, is_st)。board ∈ MAIN/KCB/CYB/BSE/ETF。
    """
    code = (code or "").strip()
    name = name or ""
    is_st = 1 if "ST" in name.upper() else 0
    if classify == "Fund" or "ETF" in name.upper():
        return "ETF", is_st
    if code.startswith(("688", "689")):
        return "KCB", is_st
    if code.startswith(("300", "301")):
        return "CYB", is_st
    if code.startswith(("43", "83", "87", "88", "92")):
        return "BSE", is_st
    return "MAIN", is_st
