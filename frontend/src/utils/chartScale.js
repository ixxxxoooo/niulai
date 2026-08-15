/**
 * 分时 / K 线 Y 轴缩放（对齐同花顺/东财/TradingView 惯例）
 * @author ygw
 */

/** 默认上下边距比例 */
export const DEFAULT_PAD = 0.08

/**
 * 从数组中取有效数值的最小/最大
 * @param {number[]} arr
 * @returns {{ lo: number, hi: number } | null}
 */
function minMax(arr) {
  let lo = Infinity
  let hi = -Infinity
  for (const v of arr) {
    if (v == null || Number.isNaN(v)) continue
    if (v < lo) lo = v
    if (v > hi) hi = v
  }
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return null
  return { lo, hi }
}

/**
 * 分时 Y 轴范围
 * @param {object} opts
 * @param {'normal'|'fill'|'limit'} opts.mode 普通/满占/涨停板
 * @param {number[]} opts.prices 分时价格序列
 * @param {number} opts.preClose 昨收
 * @param {number} [opts.limitUp] 涨停价
 * @param {number} [opts.limitDown] 跌停价
 * @param {number} [opts.limitPct] 板块涨跌幅限制（%）
 * @param {number} [opts.pad] 边距比例，默认 0.08
 * @returns {{ yMin: number, yMax: number, pctMin: number, pctMax: number, mode: string }}
 */
export function calcTrendYRange({
  mode = 'normal',
  prices = [],
  preClose,
  limitUp,
  limitDown,
  limitPct,
  pad = DEFAULT_PAD,
} = {}) {
  const pre = Number(preClose)
  if (!pre || !Number.isFinite(pre)) {
    return { yMin: 0, yMax: 1, pctMin: -1, pctMax: 1, mode: 'normal' }
  }

  let m = mode
  const hasLimitPrice = limitUp != null && limitDown != null && Number(limitUp) > pre && Number(limitDown) < pre
  const hasPct = limitPct != null && Number(limitPct) > 0
  // 指数等无涨跌停价且未显式传 limitPct 时，涨停板坐标回退普通坐标
  if (m === 'limit' && !hasLimitPrice && !hasPct) m = 'normal'

  if (m === 'limit') {
    let yMin
    let yMax
    let pct
    if (hasLimitPrice) {
      yMin = Number(limitDown)
      yMax = Number(limitUp)
      pct = ((yMax - pre) / pre) * 100
    } else {
      pct = Number(limitPct) || 10
      yMin = pre * (1 - pct / 100)
      yMax = pre * (1 + pct / 100)
    }
    return { yMin, yMax, pctMin: -pct, pctMax: pct, mode: 'limit' }
  }

  const mm = minMax(prices)
  const lo = mm ? Math.min(mm.lo, pre) : pre
  const hi = mm ? Math.max(mm.hi, pre) : pre

  if (m === 'fill') {
    // 满占：非对称，高低填满 + 边距；需保证含昨收以便 0% 线可见时可落在图内
    let yMin = lo
    let yMax = hi
    if (yMax <= yMin) {
      const eps = Math.abs(pre) * 0.002 || 0.01
      yMin = pre - eps
      yMax = pre + eps
    }
    const span = yMax - yMin
    const p = span * pad || Math.abs(pre) * 0.002
    yMin -= p
    yMax += p
    return {
      yMin,
      yMax,
      pctMin: ((yMin - pre) / pre) * 100,
      pctMax: ((yMax - pre) / pre) * 100,
      mode: 'fill',
    }
  }

  // 普通坐标（业界自适应）：始终包含昨收（0% 线），上下按实际高低独立留白；
  // 单边上涨/下跌不强制对称，避免半屏无数据空白（同花顺「满占」同类思路；对称可用涨停板模式）
  const up = Math.max(0, hi - pre)
  const down = Math.max(0, pre - lo)
  const minHalf = Math.abs(pre) * 0.003 || 0.01
  const yMax = pre + Math.max(up, minHalf) * (1 + pad)
  const yMin = pre - Math.max(down, minHalf) * (1 + pad)
  return {
    yMin,
    yMax,
    pctMin: ((yMin - pre) / pre) * 100,
    pctMax: ((yMax - pre) / pre) * 100,
    mode: 'normal',
  }
}

/**
 * K 线 Y 轴范围（可见高低 + 叠加线 + 边距）
 * @param {object} opts
 * @param {'auto'|'fixed'} opts.mode
 * @param {number[]} opts.highs
 * @param {number[]} opts.lows
 * @param {number[][]} [opts.overlays] 均线/BOLL 等叠加序列
 * @param {number} [opts.base] fixed 模式基准价（首根收盘）
 * @param {number} [opts.pad]
 * @returns {{ yMin: number, yMax: number, pctMin?: number, pctMax?: number, mode: string }}
 */
export function calcKlineYRange({
  mode = 'auto',
  highs = [],
  lows = [],
  overlays = [],
  base,
  pad = DEFAULT_PAD,
} = {}) {
  const vals = [...highs, ...lows]
  for (const series of overlays) {
    if (!Array.isArray(series)) continue
    for (const v of series) {
      if (v != null && Number.isFinite(v)) vals.push(v)
    }
  }
  const mm = minMax(vals)
  if (!mm) {
    const b = Number(base) || 1
    return { yMin: b * 0.95, yMax: b * 1.05, pctMin: -5, pctMax: 5, mode }
  }

  if (mode === 'fixed') {
    const b = Number(base) || mm.lo || 1
    const half = Math.max(b - mm.lo, mm.hi - b) || Math.abs(b) * 0.01
    const yMin = b - half
    const yMax = b + half
    const pct = (half / b) * 100
    return { yMin, yMax, pctMin: -pct, pctMax: pct, mode: 'fixed' }
  }

  // auto：可见极值 + 百分比边距（TradingView scaleMargins 等价）
  let { lo, hi } = mm
  if (hi <= lo) {
    const eps = Math.abs(lo) * 0.002 || 0.01
    lo -= eps
    hi += eps
  }
  const span = hi - lo
  const p = span * pad
  const yMin = lo - p
  const yMax = hi + p
  const mid = (yMin + yMax) / 2 || 1
  const halfPct = ((yMax - yMin) / 2 / mid) * 100
  return { yMin, yMax, pctMin: -halfPct, pctMax: halfPct, mode: 'auto' }
}

/**
 * 根据代码/名称推断涨跌幅限制百分比
 * @param {string} code
 * @param {string} [name]
 * @returns {number}
 */
export function inferLimitPct(code = '', name = '') {
  if (/ST/i.test(name || '')) return 5
  if (/^(300|301|688|689)/.test(code || '')) return 20
  if (/^(43|83|87|88|92)/.test(code || '')) return 30
  return 10
}
