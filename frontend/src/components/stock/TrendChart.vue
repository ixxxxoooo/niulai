<template>
  <div ref="el" style="width: 100%; height: 500px"></div>
</template>

<script setup>
/**
 * 分时走势图
 * @author ygw
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { fmtAmount, fmtPrice, fmtNum, themeColors, isLightTheme } from '../../utils.js'
import { calcTrendYRange, inferLimitPct } from '../../utils/chartScale.js'
import { settingsState } from '../../composables/useSettings.js'
import { trendIndicators } from '../../chartIndicators.js'
import { subPanel, buildMarkLines } from './chartCommon.js'

const props = defineProps({
  trend: { type: Object, default: null },
  detail: { type: Object, default: () => ({}) },
  code: { type: String, default: '' },
  subInd: { type: String, default: 'macd' },
  showBuySell: { type: Boolean, default: true },
  srOptions: { type: Array, default: () => [] },
  selectedSet: { type: Object, default: () => new Set() },
})

const el = ref(null)
let chart = null

function buildBuySellMarks(tc) {
  if (!props.showBuySell) return []
  const t = props.trend
  if (!t || !t.points || t.points.length < 10) return []
  const pts = t.points
  const marks = []
  const avgVol = pts.reduce((s, p) => s + (p.volume || 0), 0) / pts.length
  for (let i = 5; i < pts.length - 1; i++) {
    const vol = pts[i].volume || 0
    const price = pts[i].price
    const nextPrice = pts[i + 1].price
    if (vol < avgVol * 2) continue
    const isLow = price <= Math.min(...pts.slice(Math.max(0, i - 5), i).map(p => p.price))
    const isHigh = price >= Math.max(...pts.slice(Math.max(0, i - 5), i).map(p => p.price))
    if (isLow && nextPrice > price) {
      marks.push({
        coord: [pts[i].time, price], value: '买', itemStyle: { color: tc.up },
        symbol: 'triangle', symbolSize: 10, symbolRotate: 0,
        label: { show: true, formatter: '买', color: tc.up, fontSize: 10, position: 'bottom' },
      })
    } else if (isHigh && nextPrice < price) {
      marks.push({
        coord: [pts[i].time, price], value: '卖', itemStyle: { color: tc.down },
        symbol: 'triangle', symbolSize: 10, symbolRotate: 180,
        label: { show: true, formatter: '卖', color: tc.down, fontSize: 10, position: 'top' },
      })
    }
  }
  return marks
}

/**
 * 生成 A 股全天分时时间轴：09:30~11:30 + 13:00~15:00，每分钟一个点。
 * @returns {string[]} ['09:30', '09:31', ...]
 * @author ygw
 */
function buildFullTrendTimes() {
  const out = []
  const push = (startH, startM, endH, endM) => {
    for (let m = startH * 60 + startM; m <= endH * 60 + endM; m++) {
      out.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`)
    }
  }
  push(9, 30, 11, 30)
  push(13, 0, 15, 0)
  return out
}

function render() {
  if (!chart) return
  const cw = el.value?.clientWidth || 0
  const ch = el.value?.clientHeight || 0
  if (cw > 0 && (cw !== chart.getWidth() || ch !== chart.getHeight())) chart.resize()
  const t = props.trend
  if (!t || !t.points || !t.points.length) return
  const tc = themeColors()
  // 全天固定时间轴 09:30~11:30 + 13:00~15:00（每分钟），未到的时间点数据置空
  const fullTimes = buildFullTrendTimes()
  const byTime = new Map()
  for (const p of t.points) byTime.set(p.time, p)
  const times = fullTimes
  const prices = fullTimes.map(tt => { const p = byTime.get(tt); return p ? p.price : null })
  const avgs = fullTimes.map(tt => { const p = byTime.get(tt); return p ? p.avg : null })
  const vols = fullTimes.map(tt => { const p = byTime.get(tt); return p ? p.volume : 0 })
  const realPrices = prices.filter(v => v != null)
  const realAvgs = avgs.filter(v => v != null)
  const pre = t.pre_close || props.detail.prev_close
  if (!pre) return
  const last = realPrices[realPrices.length - 1]
  const color = last >= pre ? tc.up : tc.down
  const volColors = prices.map(p => (p == null ? 'transparent' : (p >= pre ? tc.up + '8c' : tc.down + '8c')))
  const ind = trendIndicators(t.points)
  // 指标序列与原始点一一对应；将缺失的尾部时间补 null，对齐全时间轴
  const padTail = (arr) => {
    if (!arr) return arr
    const gap = fullTimes.length - arr.length
    if (gap <= 0) return arr
    return [...arr, ...new Array(gap).fill(null)]
  }
  if (ind.macd) { ind.macd.dif = padTail(ind.macd.dif); ind.macd.dea = padTail(ind.macd.dea); ind.macd.hist = padTail(ind.macd.hist) }
  if (ind.kdj) { ind.kdj.k = padTail(ind.kdj.k); ind.kdj.d = padTail(ind.kdj.d); ind.kdj.j = padTail(ind.kdj.j) }
  if (ind.rsi) ind.rsi = padTail(ind.rsi)
  const hasSub = !!props.subInd
  const sub = subPanel(ind, tc, props.subInd, false)
  const markLines = buildMarkLines(tc, props.srOptions, props.selectedSet)
  const buySellMarks = buildBuySellMarks(tc)
  const { yMin, yMax, pctMin, pctMax } = calcTrendYRange({
    mode: settingsState.trendYScale || 'normal',
    prices: realPrices,
    preClose: pre,
    limitUp: props.detail.limit_up,
    limitDown: props.detail.limit_down,
    limitPct: inferLimitPct(props.code, props.detail.name || ''),
  })
  const gridColor = tc.split
  const zeroColor = isLightTheme() ? 'rgba(0,0,0,0.28)' : 'rgba(255,255,255,0.28)'
  const grids = hasSub
    ? [
      { left: 64, right: 56, top: 26, height: '52%' },
      { left: 64, right: 56, top: '61%', height: '14%' },
      { left: 64, right: 56, top: '78%', height: '17%' },
    ]
    : [
      { left: 64, right: 56, top: 26, height: '67%' },
      { left: 64, right: 56, top: '75%', height: '19%' },
    ]
  const xAxes = [
    { type: 'category', data: times, gridIndex: 0, boundaryGap: false,
      axisLabel: { color: tc.axis, fontSize: 11 }, axisLine: { lineStyle: { color: tc.split } },
      axisTick: { show: false }, splitLine: { show: false } },
    { type: 'category', data: times, gridIndex: 1, boundaryGap: false, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } }, axisTick: { show: false } },
  ]
  const yAxes = [
    { type: 'value', gridIndex: 0, min: yMin, max: yMax,
      splitLine: { show: true, lineStyle: { color: gridColor, width: 1 } },
      axisLabel: { color: tc.axis, fontSize: 11, formatter: v => Number(v).toFixed(2) },
      axisLine: { show: false }, axisTick: { show: false } },
    { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { color: tc.axis, fontSize: 10 } },
    { type: 'value', gridIndex: 0, min: pctMin, max: pctMax,
      position: 'right', splitLine: { show: false },
      axisLabel: {
        color: tc.axis, fontSize: 11,
        formatter: v => (v > 0 ? '+' : '') + Number(v).toFixed(settingsState.trendYScale === 'limit' ? 0 : 1) + '%',
      },
      axisLine: { show: false }, axisTick: { show: false } },
  ]
  if (hasSub) {
    xAxes.push({ type: 'category', data: times, gridIndex: 2, boundaryGap: false, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } }, axisTick: { show: false } })
    yAxes.splice(2, 0, { type: 'value', gridIndex: 2, scale: true, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axis, fontSize: 10 } })
  }

  chart.setOption({
    animation: false,
    dataZoom: [{
      type: 'inside', xAxisIndex: hasSub ? [0, 1, 2] : [0, 1],
      zoomOnMouseWheel: false, moveOnMouseWheel: false, moveOnMouseMove: false,
      preventDefaultMouseMove: false,
    }],
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (ps) => {
        const i = ps[0].dataIndex
        if (prices[i] == null) return null
        const chg = ((prices[i] - pre) / pre * 100)
        const chgColor = chg >= 0 ? tc.up : tc.down
        const amt = vols[i] * (prices[i] || 0) * 100
        let html = `${times[i]}<br/>价格 <b style="color:${chgColor}">${fmtPrice(prices[i])}</b><br/>涨跌幅 <span style="color:${chgColor}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</span><br/>均价 ${fmtPrice(avgs[i])}<br/>成交量 ${fmtNum(vols[i], 0)}手<br/>成交额 ${fmtAmount(amt)}`
        for (const opt of props.srOptions) {
          if (!props.selectedSet.has(opt.id)) continue
          if (Math.abs(prices[i] - opt.price) / pre < 0.008) {
            html += `<br/><span style="color:${opt.side==='r'?tc.down:tc.up}">${opt.label} ${opt.price}</span>`
          }
        }
        return html
      },
    },
    legend: { show: false },
    series: [
      {
        name: '价格', type: 'line', data: prices, showSymbol: false,
        lineStyle: { color, width: 1.6 }, itemStyle: { color },
        markLine: {
          silent: true, symbol: 'none',
          data: [
            { yAxis: pre, lineStyle: { color: zeroColor, width: 1.2, type: 'solid' }, label: { show: false } },
            ...markLines.map(l => ({
              yAxis: l.yAxis, name: l.name, lineStyle: l.lineStyle, label: { show: false },
            })),
          ],
        },
        markPoint: buySellMarks.length ? { data: buySellMarks, animation: false } : undefined,
      },
      { name: '均价', type: 'line', data: avgs, showSymbol: false, lineStyle: { color: '#ffcc00', width: 1.5, type: 'solid' }, itemStyle: { color: '#ffcc00' } },
      {
        name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, barWidth: '60%',
        data: vols.map((v, i) => ({ value: v, itemStyle: { color: volColors[i] } })),
      },
      ...sub.series,
    ],
  }, true)
}

function onResize() { chart && chart.resize() }

onMounted(() => {
  chart = echarts.init(el.value)
  window.addEventListener('resize', onResize)
  render()
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart && chart.dispose()
  chart = null
})

watch(() => [props.trend, props.subInd, props.showBuySell, props.selectedSet], () => render(), { deep: true })

defineExpose({ render, getChart: () => chart })
</script>
