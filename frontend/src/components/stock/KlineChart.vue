<template>
  <div ref="el" style="width: 100%" :style="{ height }"></div>
</template>

<script setup>
/**
 * 日/周/月 K 线图
 * @author ygw
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { api } from '../../api.js'
import { themeColors, isLightTheme } from '../../utils.js'
import { calcKlineYRange } from '../../utils/chartScale.js'
import { ensureIndicators } from '../../chartIndicators.js'
import { settingsState } from '../../composables/useSettings.js'
import { subPanel, tripleAxis, calcMA, buildMarkLines, formatKlineTooltip } from './chartCommon.js'

const props = defineProps({
  code: { type: String, default: '' },
  period: { type: String, default: 'day' },
  kline: { type: Object, default: null },
  detail: { type: Object, default: () => ({}) },
  subInd: { type: String, default: 'macd' },
  srOptions: { type: Array, default: () => [] },
  selectedSet: { type: Object, default: () => new Set() },
  height: { type: String, default: '500px' },
})

const emit = defineEmits(['load-more'])

const el = ref(null)
let chart = null
let currentYAxis = null
let lastData = null

/**
 * 准备渲染所需数据（指标 + 均线 + BOLL），同一数据源缓存复用，避免 datazoom 高频重算
 * @param {Array} pts K 线点
 * @returns {{ ind: object, ov: object }}
 */
function prepareData(pts) {
  if (lastData && lastData.pts === pts) return lastData
  const ind = ensureIndicators(pts, props.kline ? props.kline.indicators : null)
  const ov = {
    ma5: ind.ma5 || calcMA(pts, 5),
    ma10: ind.ma10 || calcMA(pts, 10),
    ma20: ind.ma20 || calcMA(pts, 20),
    ma60: ind.ma60 || calcMA(pts, 60),
    volMa5: ind.vol_ma5 || calcMA(pts.map(p => ({ close: p.volume || 0 })), 5),
    boll: ind.boll || {},
  }
  lastData = { pts, ind, ov }
  return lastData
}

/**
 * 当前 dataZoom 可见区间（按百分比映射到数据下标）
 * @param {number} total
 * @returns {{ startIdx: number, endIdx: number }}
 */
function visibleIndices(total) {
  let s = Math.round((klineZoom.start / 100) * total)
  let e = Math.round((klineZoom.end / 100) * total)
  s = Math.max(0, Math.min(total - 1, s))
  e = Math.max(s + 1, Math.min(total, e))
  return { startIdx: s, endIdx: e }
}

/**
 * 按可见区间计算 Y 轴范围（价格轴 + 右侧百分比轴），实现「随视图动态缩放」
 * @param {Array} pts K 线点
 * @returns {object} calcKlineYRange 结果
 */
function visibleRange(pts) {
  const ov = prepareData(pts).ov
  const { startIdx, endIdx } = visibleIndices(pts.length)
  const sl = (arr) => (Array.isArray(arr) ? arr.slice(startIdx, endIdx) : [])
  return calcKlineYRange({
    mode: settingsState.klineYScale || 'auto',
    highs: pts.slice(startIdx, endIdx).map(p => p.high),
    lows: pts.slice(startIdx, endIdx).map(p => p.low),
    overlays: [sl(ov.ma5), sl(ov.ma10), sl(ov.ma20), sl(ov.ma60), sl(ov.boll.upper), sl(ov.boll.lower)],
    base: pts[startIdx]?.close,
  })
}

/**
 * 依据最新 dataZoom 窗口动态更新左右 Y 轴范围
 */
function applyVisibleYRange() {
  if (!chart || !currentYAxis) return
  const k = props.kline
  if (!k || !k.points || !k.points.length) return
  const range = visibleRange(k.points)
  const yAxis = currentYAxis.map(a => ({ ...a }))
  yAxis[0].min = range.yMin
  yAxis[0].max = range.yMax
  yAxis[0].scale = false
  const ri = yAxis.length - 1
  if (range.pctMin != null) {
    yAxis[ri].min = range.pctMin
    yAxis[ri].max = range.pctMax
  }
  chart.setOption({ yAxis }, false)
}

function render() {
  if (!chart) return
  const cw = el.value?.clientWidth || 0
  const ch = el.value?.clientHeight || 0
  if (cw > 0 && (cw !== chart.getWidth() || ch !== chart.getHeight())) chart.resize()
  const k = props.kline
  if (!k || !k.points || !k.points.length) return
  const tc = themeColors()
  const pts = k.points
  const { ind, ov } = prepareData(pts)
  const dates = pts.map(p => p.date)
  const kdata = pts.map(p => [p.open, p.close, p.low, p.high])
  const vols = pts.map(p => p.volume)
  const hasSub = !!props.subInd
  const sub = subPanel(ind, tc, props.subInd)

  // 初始视图：日周月默认显示最近 60 根蜡烛图（须先设置 zoom，可见区间才能对应）
  if (klineZoom.start === 0 && klineZoom.end === 100 && pts.length > 60) {
    klineZoom.start = Math.max(0, 100 - Math.round(60 / pts.length * 100))
    klineZoom.end = 100
  }

  const priceRange = visibleRange(pts)
  const axis = tripleAxis(dates, tc, priceRange, hasSub)
  currentYAxis = axis.yAxis
  const markLines = buildMarkLines(tc, props.srOptions, props.selectedSet)
  const zoomAxes = hasSub ? [0, 1, 2] : [0, 1]
  const lastDate = pts[pts.length - 1]?.date
  const turnoverHint = lastDate ? props.detail.turnover : null

  chart.setOption({
    animation: false,
    dataZoom: [{
      type: 'inside',
      xAxisIndex: zoomAxes,
      filterMode: 'filter',
      zoomOnMouseWheel: true,
      start: klineZoom.start,
      end: klineZoom.end,
    }],
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
      { name: 'MA5', type: 'line', data: ov.ma5, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' }, itemStyle: { color: '#f5a623' } },
      { name: 'MA10', type: 'line', data: ov.ma10, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' }, itemStyle: { color: '#4c9aff' } },
      { name: 'MA20', type: 'line', data: ov.ma20, showSymbol: false, lineStyle: { width: 1, color: '#f04444' }, itemStyle: { color: '#f04444' } },
      { name: 'MA60', type: 'line', data: ov.ma60, showSymbol: false, lineStyle: { width: 1, color: '#2fbf8f' }, itemStyle: { color: '#2fbf8f' } },
      { name: 'BOLL', type: 'line', data: ov.boll.upper || [], showSymbol: false, lineStyle: { width: 1, color: '#8b949e', type: 'dotted' }, itemStyle: { color: '#8b949e' } },
      { name: 'BOLL', type: 'line', data: ov.boll.lower || [], showSymbol: false, lineStyle: { width: 1, color: '#8b949e', type: 'dotted' }, itemStyle: { color: '#8b949e' } },
      {
        name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, barWidth: '60%',
        data: vols.map((v, i) => ({
          value: v,
          itemStyle: { color: pts[i].close >= pts[i].open ? tc.up + '8c' : tc.down + '8c' },
        })),
      },
      { name: 'VOL MA5', type: 'line', data: ov.volMa5, xAxisIndex: 1, yAxisIndex: 1, showSymbol: false, lineStyle: { width: 1, color: '#f5a623', type: 'dashed' }, itemStyle: { color: '#f5a623' } },
      ...sub.series,
    ],
  }, true)
}

const klineZoom = { start: 0, end: 100 }
let loadingMoreHistory = false

async function maybeLoadMoreHistory() {
  if (loadingMoreHistory || !props.code) return
  const curLen = props.kline?.points?.length || 0
  if (curLen === 0 || curLen >= 800) return

  const targetLimit = Math.min(800, curLen + 120)
  loadingMoreHistory = true
  try {
    const isSecid = String(props.code).includes('.')
    const fresh = isSecid
      ? await api.quoteKline(props.code, props.period, targetLimit)
      : await api.kline(props.code, props.period, targetLimit)
    if (fresh && fresh.points && fresh.points.length > curLen) {
      const added = fresh.points.length - curLen
      const oldVisibleIdx = Math.round((klineZoom.start / 100) * curLen)
      const newVisibleIdx = oldVisibleIdx + added
      klineZoom.start = Math.max(0, +((newVisibleIdx / fresh.points.length) * 100).toFixed(2))
      klineZoom.end = 100
      emit('load-more', { period: props.period, data: fresh })
    }
  } catch (e) {
    /* ignore */
  } finally {
    loadingMoreHistory = false
  }
}

function zoom(dir) {
  if (!chart) return
  if (dir > 0) {
    klineZoom.start = Math.max(0, klineZoom.start - 12)
    klineZoom.end = Math.min(100, klineZoom.end + 4)
    if (klineZoom.start <= 10) {
      maybeLoadMoreHistory()
    }
  } else {
    klineZoom.start = Math.min(klineZoom.end - 10, klineZoom.start + 12)
  }
  chart.dispatchAction({
    type: 'dataZoom',
    start: klineZoom.start,
    end: klineZoom.end,
  })
}

function onResize() { chart && chart.resize() }

onMounted(() => {
  chart = echarts.init(el.value)
  chart.on('datazoom', (params) => {
    if (params.batch && params.batch[0]) {
      klineZoom.start = params.batch[0].start != null ? params.batch[0].start : klineZoom.start
      klineZoom.end = params.batch[0].end != null ? params.batch[0].end : klineZoom.end
    } else if (params.start != null) {
      klineZoom.start = params.start
      klineZoom.end = params.end != null ? params.end : klineZoom.end
    }
    applyVisibleYRange()
    if (klineZoom.start <= 8) {
      maybeLoadMoreHistory()
    }
  })
  window.addEventListener('resize', onResize)
  render()
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chart && chart.dispose()
  chart = null
})

watch(() => [props.kline, props.period, props.subInd, props.selectedSet], () => render(), { deep: true })

defineExpose({ render, resize: onResize, zoom, getChart: () => chart })
</script>
