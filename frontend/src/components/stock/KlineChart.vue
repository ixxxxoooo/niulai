<template>
  <div ref="el" style="width: 100%; height: 460px"></div>
</template>

<script setup>
/**
 * 日/周/月 K 线图
 * @author ygw
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { themeColors, isLightTheme } from '../../utils.js'
import { calcKlineYRange } from '../../utils/chartScale.js'
import { ensureIndicators } from '../../chartIndicators.js'
import { settingsState } from '../../composables/useSettings.js'
import { subPanel, tripleAxis, calcMA, buildMarkLines, formatKlineTooltip } from './chartCommon.js'

const props = defineProps({
  period: { type: String, default: 'day' },
  kline: { type: Object, default: null },
  detail: { type: Object, default: () => ({}) },
  subInd: { type: String, default: 'macd' },
  srOptions: { type: Array, default: () => [] },
  selectedSet: { type: Object, default: () => new Set() },
})

const el = ref(null)
let chart = null

function render() {
  if (!chart) return
  const cw = el.value?.clientWidth || 0
  const ch = el.value?.clientHeight || 0
  if (cw > 0 && (cw !== chart.getWidth() || ch !== chart.getHeight())) chart.resize()
  const k = props.kline
  if (!k || !k.points || !k.points.length) return
  const tc = themeColors()
  const pts = k.points
  const ind = ensureIndicators(pts, k.indicators)
  const dates = pts.map(p => p.date)
  const kdata = pts.map(p => [p.open, p.close, p.low, p.high])
  const vols = pts.map(p => p.volume)
  const ma5 = ind.ma5 || calcMA(pts, 5)
  const ma10 = ind.ma10 || calcMA(pts, 10)
  const ma20 = ind.ma20 || calcMA(pts, 20)
  const ma60 = ind.ma60 || []
  const volMa5 = ind.vol_ma5 || []
  const boll = ind.boll || {}
  const hasSub = !!props.subInd
  const sub = subPanel(ind, tc, props.subInd)
  const priceRange = calcKlineYRange({
    mode: settingsState.klineYScale || 'auto',
    highs: pts.map(p => p.high),
    lows: pts.map(p => p.low),
    overlays: [ma5, ma10, ma20, ma60, boll.upper || [], boll.lower || []],
    base: pts[0].close,
  })
  const axis = tripleAxis(dates, tc, priceRange, hasSub)
  const markLines = buildMarkLines(tc, props.srOptions, props.selectedSet)
  const zoomAxes = hasSub ? [0, 1, 2] : [0, 1]
  const lastDate = pts[pts.length - 1]?.date
  const turnoverHint = lastDate ? props.detail.turnover : null

  chart.setOption({
    animation: false,
    dataZoom: [{ type: 'inside', xAxisIndex: zoomAxes, filterMode: 'filter', zoomOnMouseWheel: true }],
    ...axis,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: isLightTheme() ? 'rgba(255,255,255,0.96)' : 'rgba(22,24,32,0.96)',
      borderColor: tc.split,
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: tc.axis, fontSize: 12 },
      extraCssText: 'box-shadow:0 6px 20px rgba(0,0,0,.18);border-radius:8px;',
      formatter: (ps) => {
        const i = ps[0].dataIndex
        const lastClose = pts[pts.length - 1]?.close ?? null
        return formatKlineTooltip(pts[i], pts[i - 1], tc, turnoverHint, lastClose)
      },
    },
    legend: {
      data: ['MA5', 'MA10', 'MA20', 'MA60', 'BOLL'], top: 0, right: 0,
      textStyle: { color: tc.axis, fontSize: 10 }, itemWidth: 12, itemHeight: 6,
    },
    series: [
      {
        name: 'K线', type: 'candlestick', data: kdata,
        itemStyle: { color: tc.up, color0: tc.down, borderColor: tc.up, borderColor0: tc.down },
        markLine: markLines.length ? {
          silent: true, symbol: 'none',
          data: markLines.map(l => ({
            yAxis: l.yAxis, name: l.name, lineStyle: l.lineStyle, label: { show: false },
          })),
        } : undefined,
      },
      { name: 'MA5', type: 'line', data: ma5, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' }, itemStyle: { color: '#f5a623' } },
      { name: 'MA10', type: 'line', data: ma10, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' }, itemStyle: { color: '#4c9aff' } },
      { name: 'MA20', type: 'line', data: ma20, showSymbol: false, lineStyle: { width: 1, color: '#f04444' }, itemStyle: { color: '#f04444' } },
      { name: 'MA60', type: 'line', data: ma60, showSymbol: false, lineStyle: { width: 1, color: '#2fbf8f' }, itemStyle: { color: '#2fbf8f' } },
      { name: 'BOLL', type: 'line', data: boll.upper || [], showSymbol: false, lineStyle: { width: 1, color: '#8b949e', type: 'dotted' }, itemStyle: { color: '#8b949e' } },
      { name: 'BOLL', type: 'line', data: boll.lower || [], showSymbol: false, lineStyle: { width: 1, color: '#8b949e', type: 'dotted' }, itemStyle: { color: '#8b949e' } },
      {
        name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, barWidth: '60%',
        data: vols.map((v, i) => ({
          value: v,
          itemStyle: { color: pts[i].close >= pts[i].open ? tc.up + '8c' : tc.down + '8c' },
        })),
      },
      { name: 'VOL MA5', type: 'line', data: volMa5, xAxisIndex: 1, yAxisIndex: 1, showSymbol: false, lineStyle: { width: 1, color: '#f5a623', type: 'dashed' }, itemStyle: { color: '#f5a623' } },
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

watch(() => [props.kline, props.period, props.subInd, props.selectedSet], () => render(), { deep: true })

defineExpose({ render, resize: onResize, getChart: () => chart })
</script>
