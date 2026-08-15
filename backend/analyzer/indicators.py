"""K 线技术指标：MA / MACD / KDJ / RSI / BOLL
@author ygw
"""
from typing import List, Optional


def _ma(data: List[float], period: int) -> List[Optional[float]]:
    """简单移动平均。"""
    n = len(data)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n < period:
        return result
    s = sum(data[:period])
    result[period - 1] = round(s / period, 4)
    for i in range(period, n):
        s += data[i] - data[i - period]
        result[i] = round(s / period, 4)
    return result


def _ema(data: List[Optional[float]], period: int) -> List[Optional[float]]:
    """指数移动平均；跳过序列前部的空值。"""
    n = len(data)
    result: List[Optional[float]] = [None] * n
    if period <= 0 or n == 0:
        return result
    k = 2.0 / (period + 1)
    seed = 0.0
    count = 0
    start = None
    for i, v in enumerate(data):
        if v is None:
            continue
        seed += float(v)
        count += 1
        if count == period:
            start = i
            break
    if start is None:
        return result
    prev = seed / period
    result[start] = round(prev, 4)
    for i in range(start + 1, n):
        v = data[i]
        if v is None:
            result[i] = result[i - 1]
            continue
        prev = float(v) * k + prev * (1 - k)
        result[i] = round(prev, 4)
    return result


def _macd(closes: List[float]) -> dict:
    """MACD：DIF / DEA / 柱（国内习惯柱 = (DIF-DEA)*2）。"""
    as_opt: List[Optional[float]] = list(closes)
    dif = []
    ema12 = _ema(as_opt, 12)
    ema26 = _ema(as_opt, 26)
    for a, b in zip(ema12, ema26):
        if a is None or b is None:
            dif.append(None)
        else:
            dif.append(round(a - b, 4))
    dea = _ema(dif, 9)
    hist = []
    for a, b in zip(dif, dea):
        if a is None or b is None:
            hist.append(None)
        else:
            hist.append(round((a - b) * 2, 4))
    return {"dif": dif, "dea": dea, "hist": hist}


def _kdj(highs: List[float], lows: List[float], closes: List[float], n: int = 9) -> dict:
    """KDJ（9,3,3）。"""
    size = len(closes)
    k_list: List[Optional[float]] = [None] * size
    d_list: List[Optional[float]] = [None] * size
    j_list: List[Optional[float]] = [None] * size
    k_val, d_val = 50.0, 50.0
    for i in range(size):
        start = max(0, i - n + 1)
        hh = max(highs[start:i + 1])
        ll = min(lows[start:i + 1])
        rsv = 50.0 if hh == ll else (closes[i] - ll) / (hh - ll) * 100.0
        k_val = 2 / 3 * k_val + 1 / 3 * rsv
        d_val = 2 / 3 * d_val + 1 / 3 * k_val
        j_val = 3 * k_val - 2 * d_val
        if i >= n - 1:
            k_list[i] = round(k_val, 4)
            d_list[i] = round(d_val, 4)
            j_list[i] = round(j_val, 4)
    return {"k": k_list, "d": d_list, "j": j_list}


def _rsi(closes: List[float], period: int = 14) -> List[Optional[float]]:
    """RSI。"""
    n = len(closes)
    result: List[Optional[float]] = [None] * n
    if n <= period:
        return result
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    result[period] = round(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss), 4)
    for i in range(period + 1, n):
        diff = closes[i] - closes[i - 1]
        gain = diff if diff > 0 else 0.0
        loss = -diff if diff < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[i] = round(100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss), 4)
    return result


def _boll(closes: List[float], period: int = 20, k: float = 2.0) -> dict:
    """布林带。"""
    n = len(closes)
    mid = _ma(closes, period)
    upper: List[Optional[float]] = [None] * n
    lower: List[Optional[float]] = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        mean = mid[i]
        if mean is None:
            continue
        var = sum((x - mean) ** 2 for x in window) / period
        std = var ** 0.5
        upper[i] = round(mean + k * std, 4)
        lower[i] = round(mean - k * std, 4)
    return {"mid": mid, "upper": upper, "lower": lower}


def calc_indicators(points: list) -> dict:
    """基于 K 线点计算常用指标。points 项含 close，可选 high/low/volume。"""
    if not points:
        return {}
    closes = [float(p.get("close") or 0) for p in points]
    highs = [float(p.get("high") if p.get("high") is not None else p.get("close") or 0) for p in points]
    lows = [float(p.get("low") if p.get("low") is not None else p.get("close") or 0) for p in points]
    volumes = [float(p.get("volume") or 0) for p in points]
    return {
        "ma5": _ma(closes, 5),
        "ma10": _ma(closes, 10),
        "ma20": _ma(closes, 20),
        "ma60": _ma(closes, 60),
        "vol_ma5": _ma(volumes, 5),
        "vol_ma10": _ma(volumes, 10),
        "macd": _macd(closes),
        "kdj": _kdj(highs, lows, closes),
        "rsi": _rsi(closes),
        "boll": _boll(closes),
    }
