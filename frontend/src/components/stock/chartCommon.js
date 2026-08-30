/**
 * 个股分时/K线公共绘制辅助
 * @author ygw
 */
import { fmtAmount, fmtPrice, fmtNum } from '../../utils.js'

export function findCrossPoints(lineA, lineB, tc) {
  const marks = []
  if (!lineA || !lineB || lineA.length < 2) return marks
  for (let i = 1; i < lineA.length; i++) {
    if (lineA[i] == null || lineB[i] == null || lineA[i-1] == null || lineB[i-1] == null) continue
    const prevDiff = lineA[i-1] - lineB[i-1]
    const currDiff = lineA[i] - lineB[i]
    if (prevDiff <= 0 && currDiff > 0) {
      marks.push({ coord: [i, lineA[i]], value: '金', itemStyle: { color: tc.up }, symbol: 'circle', symbolSize: 8,
        label: { show: true, formatter: '金叉', color: tc.up, fontSize: 9, position: 'top' } })
    } else if (prevDiff >= 0 && currDiff < 0) {
      marks.push({ coord: [i, lineA[i]], value: '死', itemStyle: { color: tc.down }, symbol: 'circle', symbolSize: 8,
        label: { show: true, formatter: '死叉', color: tc.down, fontSize: 9, position: 'bottom' } })
    }
  }
  return marks
}

/** 副图系列（MACD/KDJ/RSI） */
export function subPanel(ind, tc, subInd, showCross = true) {
  const type = subInd
  if (!type) return { legend: [], series: [] }
  if (type === 'kdj' && ind.kdj) {
    const crossMarks = showCross ? findCrossPoints(ind.kdj.k, ind.kdj.d, tc) : []
    return {
      legend: ['K', 'D', 'J'],
      series: [
        { name: 'K', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: ind.kdj.k, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' }, itemStyle: { color: '#f5a623' },
          markPoint: crossMarks.length ? { data: crossMarks, animation: false } : undefined },
        { name: 'D', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: ind.kdj.d, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' }, itemStyle: { color: '#4c9aff' } },
        { name: 'J', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: ind.kdj.j, showSymbol: false, lineStyle: { width: 1, color: '#f04444' }, itemStyle: { color: '#f04444' } },
      ],
    }
  }
  if (type === 'rsi' && ind.rsi) {
    return {
      legend: ['RSI'],
      series: [{ name: 'RSI', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: ind.rsi, showSymbol: false, lineStyle: { width: 1, color: '#e3b341' }, itemStyle: { color: '#e3b341' } }],
    }
  }
  if (type !== 'macd') return { legend: [], series: [] }
  const macd = ind.macd || { dif: [], dea: [], hist: [] }
  const macdCross = showCross ? findCrossPoints(macd.dif, macd.dea, tc) : []
  return {
    legend: ['DIF', 'DEA', 'MACD'],
    series: [
      { name: 'DIF', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: macd.dif, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' }, itemStyle: { color: '#4c9aff' },
        markPoint: macdCross.length ? { data: macdCross, animation: false } : undefined },
      { name: 'DEA', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: macd.dea, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' }, itemStyle: { color: '#f5a623' } },
      {
        name: 'MACD', type: 'bar', xAxisIndex: 2, yAxisIndex: 2, barWidth: '55%',
        data: (macd.hist || []).map(v => ({ value: v, itemStyle: { color: (v || 0) >= 0 ? tc.up + '99' : tc.down + '99' } })),
      },
    ],
  }
}

export function tripleAxis(times, tc, priceRange = null, withSub = true) {
  const y0 = {
    type: 'value', gridIndex: 0, scale: true,
    splitLine: { lineStyle: { color: tc.split } },
    axisLabel: { color: tc.axis, fontSize: 11 },
  }
  if (priceRange) {
    y0.min = priceRange.yMin
    y0.max = priceRange.yMax
    y0.scale = false
  }
  const rightPad = priceRange ? 56 : 16
  const grids = withSub
    ? [
      { left: 64, right: rightPad, top: 26, height: '52%' },
      { left: 64, right: rightPad, top: '61%', height: '14%' },
      { left: 64, right: rightPad, top: '78%', height: '17%' },
    ]
    : [
      { left: 64, right: rightPad, top: 26, height: '67%' },
      { left: 64, right: rightPad, top: '75%', height: '19%' },
    ]
  const xAxes = [
    { type: 'category', data: times, gridIndex: 0, axisLabel: { color: tc.axis, fontSize: 11 }, axisLine: { lineStyle: { color: tc.split } } },
    { type: 'category', data: times, gridIndex: 1, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
  ]
  const yAxes = [
    y0,
    { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { color: tc.axis, fontSize: 10 } },
  ]
  if (withSub) {
    xAxes.push({ type: 'category', data: times, gridIndex: 2, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } } })
    yAxes.push({ type: 'value', gridIndex: 2, scale: true, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axis, fontSize: 10 } })
  }
  if (priceRange) {
    yAxes.push({
      type: 'value', gridIndex: 0, position: 'right',
      min: priceRange.pctMin, max: priceRange.pctMax,
      splitLine: { show: false },
      axisLabel: {
        color: tc.axis, fontSize: 10,
        formatter: (v) => (v > 0 ? '+' : '') + Number(v).toFixed(1) + '%',
      },
    })
  }
  return { grid: grids, xAxis: xAxes, yAxis: yAxes }
}

export function calcMA(points, n) {
  if (!points || !points.length) return []
  return points.map((_, i) => {
    const start = Math.max(0, i - n + 1)
    const count = i - start + 1
    const s = points.slice(start, i + 1).reduce((sum, p) => sum + (p.close != null ? p.close : (p.price != null ? p.price : (typeof p === 'number' ? p : 0))), 0)
    return +(s / count).toFixed(2)
  })
}

export function buildMarkLines(tc, srOptions, selectedSR) {
  const selected = selectedSR
  if (!selected || !selected.size) return []
  const lines = []
  for (const opt of srOptions) {
    if (!selected.has(opt.id)) continue
    const isRes = opt.side === 'r'
    lines.push({
      yAxis: opt.price,
      name: `${opt.label} ${opt.price}`,
      lineStyle: { color: isRes ? tc.down : tc.up, width: 1.2, type: 'dashed' },
      label: { show: false },
    })
  }
  return lines
}

/**
 * 日/周/月 K 悬浮窗（双列排版）
 * @param {object} p 当前 K
 * @param {object|null} prev 前一根
 * @param {object} tc 主题色
 * @param {number|null} turnoverHint 当日换手兜底
 * @param {number|null} lastClose 最后一根 K 的收盘价（用于计算「至今涨跌幅」）
 */
export function formatKlineTooltip(p, prev, tc, turnoverHint = null, lastClose = null) {
  const pre = (p.change_pct != null && p.change_amount != null)
    ? null
    : (prev ? prev.close : null)
  let chgAmt = p.change_amount
  let chgPct = p.change_pct
  if (chgAmt == null && pre != null) chgAmt = +(p.close - pre).toFixed(2)
  if (chgPct == null && pre) chgPct = +((p.close - pre) / pre * 100).toFixed(2)
  const sign = (v) => (v > 0 ? '+' : '')
  const col = (v) => (v > 0 ? tc.up : v < 0 ? tc.down : tc.axis)
  const vsPre = (v) => {
    const base = pre != null ? pre : (chgPct != null ? (chgPct >= 0 ? p.close - Math.abs(chgAmt || 0) : p.close + Math.abs(chgAmt || 0)) : null)
    if (base == null || v == null) return tc.axis
    return v >= base ? tc.up : tc.down
  }
  const row = (label, valHtml) =>
    `<div style="display:flex;justify-content:space-between;gap:28px;line-height:1.7"><span style="color:${tc.axis};opacity:.75">${label}</span><span>${valHtml}</span></div>`
  const volText = (() => {
    const v = p.volume
    if (v == null) return '-'
    if (v >= 1e4) return (v / 1e4).toFixed(2) + '万手'
    return fmtNum(v, 0) + '手'
  })()
  // 至今涨跌幅：选中的那天 → 最新一根 K 的收盘价
  const sinceChgPct = (lastClose != null && p.close != null)
    ? +((lastClose - p.close) / p.close * 100).toFixed(2)
    : null
  let html = `<div style="min-width:168px;font-size:12px">`
  html += row('时间', `<b>${p.date}</b>`)
  html += row('开盘', `<b style="color:${vsPre(p.open)}">${fmtPrice(p.open)}</b>`)
  html += row('收盘', `<b style="color:${vsPre(p.close)}">${fmtPrice(p.close)}</b>`)
  html += row('最高', `<b style="color:${vsPre(p.high)}">${fmtPrice(p.high)}</b>`)
  html += row('最低', `<b style="color:${vsPre(p.low)}">${fmtPrice(p.low)}</b>`)
  if (chgAmt != null) html += row('涨跌额', `<b style="color:${col(chgAmt)}">${sign(chgAmt)}${fmtPrice(Math.abs(chgAmt))}</b>`)
  if (chgPct != null) html += row('涨跌幅', `<b style="color:${col(chgPct)}">${sign(chgPct)}${Number(chgPct).toFixed(2)}%</b>`)
  if (sinceChgPct != null) html += row('至今涨跌幅', `<b style="color:${col(sinceChgPct)}">${sign(sinceChgPct)}${sinceChgPct.toFixed(2)}%</b>`)
  html += row('成交量', volText)
  if (p.amount != null) html += row('成交额', fmtAmount(p.amount))
  const turnVal = p.turnover != null ? p.turnover : turnoverHint
  if (turnVal != null) html += row('换手率', Number(turnVal).toFixed(2) + '%')
  html += `</div>`
  return html
}
