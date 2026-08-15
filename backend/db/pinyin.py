"""中文拼音首字母 + 全拼（全拼优先 pypinyin，缺失时仅首字母）
@author ygw
"""
from typing import List, Tuple

# GBK 双字节区间 → 声母首字母（不含 I/U/V）
_GBK_RANGES: List[Tuple[int, int, str]] = [
    (0xB0A1, 0xB0C4, "a"),
    (0xB0C5, 0xB2C0, "b"),
    (0xB2C1, 0xB4ED, "c"),
    (0xB4EE, 0xB6E9, "d"),
    (0xB6EA, 0xB7A1, "e"),
    (0xB7A2, 0xB8C0, "f"),
    (0xB8C1, 0xB9FD, "g"),
    (0xB9FE, 0xBBF6, "h"),
    (0xBBF7, 0xBFA5, "j"),
    (0xBFA6, 0xC0AB, "k"),
    (0xC0AC, 0xC2E7, "l"),
    (0xC2E8, 0xC4C2, "m"),
    (0xC4C3, 0xC5B5, "n"),
    (0xC5B6, 0xC5BD, "o"),
    (0xC5BE, 0xC6D9, "p"),
    (0xC6DA, 0xC8BA, "q"),
    (0xC8BB, 0xC8F5, "r"),
    (0xC8F6, 0xCBF9, "s"),
    (0xCBFA, 0xCDD9, "t"),
    (0xCDDA, 0xCEF3, "w"),
    (0xCEF4, 0xD1B8, "x"),
    (0xD1B9, 0xD4D0, "y"),
    (0xD4D1, 0xD7F9, "z"),
]


def _letter_of(ch: str) -> str:
    """单个字符转拼音首字母；ASCII 原样小写，无法识别则空。"""
    if "a" <= ch.lower() <= "z" or ch.isdigit():
        return ch.lower()
    try:
        raw = ch.encode("gbk")
    except UnicodeEncodeError:
        return ""
    if len(raw) == 1:
        return ch.lower()
    code = raw[0] * 256 + raw[1]
    for lo, hi, letter in _GBK_RANGES:
        if lo <= code <= hi:
            return letter
    return ""


def pinyin_initials(text: str) -> str:
    """名称 → 拼音首字母串，如 贵州茅台 → gzmt。"""
    if not text:
        return ""
    return "".join(_letter_of(ch) for ch in text)


def pinyin_full(text: str) -> str:
    """
    名称 → 全拼无空格小写，如 贵州茅台 → guizhoumaotai。
    优先 pypinyin；未安装时回退为空（搜索仍可用首字母）。
    """
    if not text:
        return ""
    try:
        from pypinyin import lazy_pinyin
        return "".join(lazy_pinyin(text)).lower()
    except Exception:
        return ""
