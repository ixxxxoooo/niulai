// K 线附图指标（后端未带时前端兜底）
// @author ygw

function ma(data, period) {
  const n = data.length
  const out = Array(n).fill(null)
  if (n < period) return out
  let s = 0
  for (let i = 0; i < n; i++) {
    s += data[i]
    if (i >= period) s -= data[i - period]
    if (i >= period - 1) out[i] = +(s / period).toFixed(4)
  }
  return out
}

function ema(data, period) {
  const n = data.length
  const out = Array(n).fill(null)
  const k = 2 / (period + 1)
  let seed = 0, count = 0, start = -1
  for (let i = 0; i < n; i++) {
    if (data[i] == null) continue
    seed += data[i]
    count++
    if (count === period) { start = i; break }
  }
  if (start < 0) return out
  let prev = seed / period
  out[start] = +prev.toFixed(4)
  for (let i = start + 1; i < n; i++) {
    if (data[i] == null) { out[i] = out[i - 1]; continue }
    prev = data[i] * k + prev * (1 - k)
    out[i] = +prev.toFixed(4)
  }
  return out
}

function macd(closes) {
  const e12 = ema(closes, 12)
  const e26 = ema(closes, 26)
  const dif = closes.map((_, i) => (e12[i] == null || e26[i] == null) ? null : +(e12[i] - e26[i]).toFixed(4))
  const dea = ema(dif, 9)
  const hist = dif.map((a, i) => (a == null || dea[i] == null) ? null : +((a - dea[i]) * 2).toFixed(4))
  return { dif, dea, hist }
}

function kdj(highs, lows, closes, n = 9) {
  const size = closes.length
  const kArr = Array(size).fill(null)
  const dArr = Array(size).fill(null)
  const jArr = Array(size).fill(null)
  let k = 50, d = 50
  for (let i = 0; i < size; i++) {
    const start = Math.max(0, i - n + 1)
    let hh = -Infinity, ll = Infinity
    for (let j = start; j <= i; j++) {
      if (highs[j] > hh) hh = highs[j]
      if (lows[j] < ll) ll = lows[j]
    }
    const rsv = hh === ll ? 50 : (closes[i] - ll) / (hh - ll) * 100
    k = 2 / 3 * k + 1 / 3 * rsv
    d = 2 / 3 * d + 1 / 3 * k
    if (i >= n - 1) {
      kArr[i] = +k.toFixed(4)
      dArr[i] = +d.toFixed(4)
      jArr[i] = +(3 * k - 2 * d).toFixed(4)
    }
  }
  return { k: kArr, d: dArr, j: jArr }
}

function rsi(closes, period = 14) {
  const n = closes.length
  const out = Array(n).fill(null)
  if (n <= period) return out
  let gains = 0, losses = 0
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1]
    if (diff >= 0) gains += diff
    else losses -= diff
  }
  let avgG = gains / period, avgL = losses / period
  out[period] = +(avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL)).toFixed(4)
  for (let i = period + 1; i < n; i++) {
    const diff = closes[i] - closes[i - 1]
    const gain = diff > 0 ? diff : 0
    const loss = diff < 0 ? -diff : 0
    avgG = (avgG * (period - 1) + gain) / period
    avgL = (avgL * (period - 1) + loss) / period
    out[i] = +(avgL === 0 ? 100 : 100 - 100 / (1 + avgG / avgL)).toFixed(4)
  }
  return out
}

function boll(closes, period = 20, k = 2) {
  const mid = ma(closes, period)
  const n = closes.length
  const upper = Array(n).fill(null)
  const lower = Array(n).fill(null)
  for (let i = period - 1; i < n; i++) {
    const m = mid[i]
    if (m == null) continue
    let v = 0
    for (let j = i - period + 1; j <= i; j++) v += (closes[j] - m) ** 2
    const std = Math.sqrt(v / period)
    upper[i] = +(m + k * std).toFixed(4)
    lower[i] = +(m - k * std).toFixed(4)
  }
  return { mid, upper, lower }
}

/**
 * 补全指标对象
 * @param {Array} points
 * @param {object} ind
 */
export function ensureIndicators(points, ind) {
  const src = ind || {}
  if (src.macd && src.kdj && src.rsi) return src
  const closes = points.map(p => p.close)
  const highs = points.map(p => p.high ?? p.close)
  const lows = points.map(p => p.low ?? p.close)
  const vols = points.map(p => p.volume || 0)
  return {
    ma5: src.ma5 || ma(closes, 5),
    ma10: src.ma10 || ma(closes, 10),
    ma20: src.ma20 || ma(closes, 20),
    ma60: src.ma60 || ma(closes, 60),
    vol_ma5: src.vol_ma5 || ma(vols, 5),
    macd: src.macd || macd(closes),
    kdj: src.kdj || kdj(highs, lows, closes),
    rsi: src.rsi || rsi(closes),
    boll: src.boll || boll(closes),
  }
}

/** 分时价格序列上的 MACD/KDJ/RSI */
export function trendIndicators(points) {
  const closes = points.map(p => p.price)
  const highs = points.map(p => p.high ?? p.price)
  const lows = points.map(p => p.low ?? p.price)
  return { macd: macd(closes), kdj: kdj(highs, lows, closes), rsi: rsi(closes) }
}
