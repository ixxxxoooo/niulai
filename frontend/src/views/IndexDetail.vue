<template>
  <div>
    <div class="stock-head">
      <BackButton label="返回盘面" />
      <button class="btn-nav-idx" @click="prevIndex" title="上一个指数"><UiIcon name="chevronLeft" :size="14" /></button>
      <span class="name">{{ displayName }}</span>
      <button class="btn-nav-idx" @click="nextIndex" title="下一个指数"><UiIcon name="chevronRight" :size="14" /></button>
      <span class="code" style="color:var(--text-dim)">{{ secid }}</span>
      <UiButton variant="subtle" size="sm" @click="showAlert = true"><UiIcon name="plus" :size="13" /> 监控</UiButton>
      <a class="source-link" :href="indexSourceUrl" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
    </div>

    <div class="error-banner" v-if="error">{{ error }}</div>

    <!-- 指数核心行情面板 -->
    <div class="card" v-if="meta.price">
      <div class="index-quote-header">
        <div class="index-quote-main">
          <span class="stock-price" :class="pctClass(meta.change_pct)">{{ fmtPrice(meta.price) }}</span>
          <span class="stock-change" :class="pctClass(meta.change_pct)">
            {{ fmtPct(meta.change_pct) }}
            <span class="change-amt" v-if="meta.change != null">{{ (meta.change > 0 ? '+' : '') + fmtPrice(meta.change) }}</span>
          </span>
        </div>
        <div class="index-quote-sub" v-if="openPrice != null || prevClosePrice != null">
          <span class="sub-item" v-if="openPrice != null">今开 <b :class="vsPreClass(openPrice)">{{ fmtPrice(openPrice) }}</b></span>
          <span class="sub-dot" v-if="openPrice != null && prevClosePrice != null">·</span>
          <span class="sub-item" v-if="prevClosePrice != null">昨收 <b>{{ fmtPrice(prevClosePrice) }}</b></span>
        </div>
        <div class="index-breadth" v-if="hasBreadth">
          <span class="breadth-pill up">涨 {{ meta.up_count }}</span>
          <span class="breadth-pill down">跌 {{ meta.down_count }}</span>
          <span class="breadth-pill flat">平 {{ meta.flat_count }}</span>
        </div>
      </div>

      <div class="index-kv-grid mt12">
        <div class="kv">
          <span class="k">最高</span>
          <span class="v" :class="vsPreClass(meta.high)">{{ fmtPrice(meta.high) }}</span>
        </div>
        <div class="kv">
          <span class="k">最低</span>
          <span class="v" :class="vsPreClass(meta.low)">{{ fmtPrice(meta.low) }}</span>
        </div>
        <div class="kv">
          <span class="k">振幅</span>
          <span class="v">{{ fmtPct(meta.amplitude) }}</span>
        </div>
        <div class="kv">
          <span class="k">成交额</span>
          <span class="v">{{ fmtAmount(meta.amount) }}</span>
        </div>
        <div class="kv">
          <span class="k">成交量</span>
          <span class="v">{{ fmtAmount(meta.volume) }}{{ secid.startsWith('100.') ? '股' : '手' }}</span>
        </div>
        <div class="kv" v-if="hasBreadth">
          <span class="k">涨跌分布</span>
          <span class="v breadth-val">
            <span class="up">{{ meta.up_count }}</span> / <span class="down">{{ meta.down_count }}</span> / <span class="flat">{{ meta.flat_count }}</span>
          </span>
        </div>
      </div>
    </div>

    <!-- 分时 / K线 -->
    <div class="card mt16">
      <div class="card-title">
        <span>{{ chartTitle }}</span>
        <div class="tabs mini-tabs">
          <div class="tab" :class="{ active: period === 'trend' }" @click="switchChart('trend')">分时</div>
          <div class="tab" :class="{ active: period === 'day' }" @click="switchChart('day')">日K</div>
          <div class="tab" :class="{ active: period === 'week' }" @click="switchChart('week')">周K</div>
          <div class="tab" :class="{ active: period === 'month' }" @click="switchChart('month')">月K</div>
        </div>
        <div class="tabs mini-tabs">
          <div class="tab" :class="{ active: subInd === 'macd' }" @click="setSub('macd')">MACD</div>
          <div class="tab" :class="{ active: subInd === 'kdj' }" @click="setSub('kdj')">KDJ</div>
          <div class="tab" :class="{ active: subInd === 'rsi' }" @click="setSub('rsi')">RSI</div>
        </div>
        <div class="tabs mini-tabs" v-if="period !== 'trend'">
          <div class="tab" @click="zoomKline(1)" title="显示更多历史K线 (视野变宽)">拉长K线</div>
          <div class="tab" @click="zoomKline(-1)" title="聚焦近期K线 (蜡烛变粗)">缩短K线</div>
        </div>
        <button class="btn-screenshot" @click="screenshotChart" title="截图到剪贴板"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div ref="chartEl" style="width: 100%; height: 500px"></div>
    </div>

    <AlertQuickModal
      :open="showAlert"
      target-type="index"
      :code="secid"
      :name="displayName"
      :price="meta.price"
      :change-pct="meta.change_pct"
      @close="showAlert = false"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api.js'
import { fmtAmount, fmtPrice, fmtPct, fmtNum, pctClass, themeColors, INDEX_NAMES } from '../utils.js'
import { calcTrendYRange, calcKlineYRange } from '../utils/chartScale.js'
import { settingsState } from '../composables/useSettings.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { getCachedKline } from '../composables/useKlineCache.js'
import { ensureIndicators, trendIndicators } from '../chartIndicators.js'
import { showToast } from '../composables/useToast.js'
import { applyWatermark } from '../composables/useScreenshot.js'
import BackButton from '../components/BackButton.vue'
import AlertQuickModal from '../components/AlertQuickModal.vue'

const props = defineProps({ secid: { type: String, default: '' } })
const secid = ref(props.secid || '')
const meta = reactive({})
const trend = ref(null)
const klineCache = reactive({})
const period = ref('trend')
const subInd = ref('macd')
const klineAvailable = ref(true)
const error = ref('')
const showAlert = ref(false)
const chartEl = ref(null)
let chart = null

const INDEX_LIST = Object.keys(INDEX_NAMES)
const displayName = computed(() => meta.name || INDEX_NAMES[secid.value] || '')
const chartTitle = computed(() => ({ trend: '分时走势', day: '日K线', week: '周K线', month: '月K线' }[period.value]))
const indexSourceUrl = computed(() => {
  const parts = (secid.value || '').split('.')
  const mkt = parts[0]
  const code = parts[1] || parts[0]
  if (mkt === '100' || mkt === '124') {
    return `https://quote.eastmoney.com/gb/zs${code}.html`
  }
  return `https://quote.eastmoney.com/zs${code}.html`
})
const prevClosePrice = computed(() => {
  if (meta.price != null && meta.change != null) {
    return +(meta.price - meta.change).toFixed(2)
  }
  return trend.value?.pre_close ?? null
})

const openPrice = computed(() => {
  if (meta.open != null) return meta.open
  if (trend.value?.points?.length) return trend.value.points[0].price
  return null
})

const hasBreadth = computed(() => {
  return (meta.up_count != null && meta.up_count > 0) || (meta.down_count != null && meta.down_count > 0)
})

function vsPreClass(val) {
  if (val == null || prevClosePrice.value == null) return ''
  if (val > prevClosePrice.value) return 'up'
  if (val < prevClosePrice.value) return 'down'
  return ''
}

function prevIndex() {
  const list = Object.keys(INDEX_NAMES)
  const idx = list.indexOf(secid.value)
  if (idx < 0) {
    navigate('/index/' + list[0])
    return
  }
  const next = idx <= 0 ? list[list.length - 1] : list[idx - 1]
  navigate('/index/' + next)
}
function nextIndex() {
  const list = Object.keys(INDEX_NAMES)
  const idx = list.indexOf(secid.value)
  if (idx < 0) {
    navigate('/index/' + list[0])
    return
  }
  const next = idx >= list.length - 1 ? list[0] : list[idx + 1]
  navigate('/index/' + next)
}

function back() { history.length > 1 ? history.back() : navigate('/') }

async function load() {
  if (!secid.value) return
  try {
    const [q] = await Promise.all([api.indexQuote(secid.value), probeKline()])
    Object.keys(meta).forEach(k => delete meta[k])
    Object.assign(meta, q || { secid: secid.value })
    error.value = ''
    if (period.value === 'trend') {
      loadTrend()
    } else {
      switchChart(period.value)
    }
  } catch (e) {
    error.value = '指数数据加载失败：' + e.message
  }
}

async function loadTrend() {
  try {
    trend.value = await api.quoteTrends(secid.value)
    renderTrend()
  } catch (e) {
    error.value = '分时数据暂不可用：' + e.message
  }
}

async function switchChart(p) {
  period.value = p
  klineZoom.start = 0
  klineZoom.end = 100
  if (p === 'trend') { loadTrend(); return }
  if (klineCache[p]) { renderKline(p); return }
  try {
    const k = await getCachedKline(secid.value, p, 120)
    if (k && k.points && k.points.length) {
      klineCache[p] = k
      error.value = ''
      renderKline(p)
    } else {
      error.value = `${chartTitle.value}暂不可用`
    }
  } catch (e) {
    error.value = 'K线加载失败：' + e.message
  }
}

async function probeKline() {
  try {
    const k = await getCachedKline(secid.value, 'day', 120)
    if (k && k.points && k.points.length) klineCache.day = k
  } catch (e) { /* 探测失败仍保留日K入口 */ }
}

const klineZoom = reactive({ start: 0, end: 100 })
let loadingMoreHistory = false

async function maybeLoadMoreHistory() {
  if (loadingMoreHistory || period.value === 'trend') return
  const currentK = klineCache[period.value]
  const curLen = currentK?.points?.length || 0
  if (curLen === 0 || curLen >= 800) return

  const targetLimit = Math.min(800, curLen + 120)
  loadingMoreHistory = true
  try {
    const fresh = await api.quoteKline(secid.value, period.value, targetLimit)
    if (fresh && fresh.points && fresh.points.length > curLen) {
      const added = fresh.points.length - curLen
      klineCache[period.value] = fresh
      // 重新对齐缩放位置，防止视图跳动
      const oldVisibleIdx = Math.round((klineZoom.start / 100) * curLen)
      const newVisibleIdx = oldVisibleIdx + added
      klineZoom.start = Math.max(0, +((newVisibleIdx / fresh.points.length) * 100).toFixed(2))
      klineZoom.end = 100
      renderKline(period.value)
    }
  } catch (e) {
    /* ignore */
  } finally {
    loadingMoreHistory = false
  }
}

function zoomKline(dir) {
  if (!chart || period.value === 'trend') return
  if (dir > 0) {
    // 拉长K线：视野更宽，看到更多根 K 线
    klineZoom.start = Math.max(0, klineZoom.start - 12)
    klineZoom.end = Math.min(100, klineZoom.end + 4)
    if (klineZoom.start <= 10) {
      maybeLoadMoreHistory()
    }
  } else {
    // 缩短K线：聚焦近期，蜡烛变宽
    klineZoom.start = Math.min(klineZoom.end - 10, klineZoom.start + 12)
  }
  chart.dispatchAction({
    type: 'dataZoom',
    start: klineZoom.start,
    end: klineZoom.end,
  })
}

function setSub(t) {
  subInd.value = subInd.value === t ? '' : t
  if (period.value === 'trend') renderTrend()
  else renderKline(period.value)
}

function subSeries(ind, tc) {
  const type = subInd.value
  if (type === 'kdj' && ind.kdj) {
    return [
      { name: 'K', type: 'line', data: ind.kdj.k, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' } },
      { name: 'D', type: 'line', data: ind.kdj.d, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' } },
      { name: 'J', type: 'line', data: ind.kdj.j, showSymbol: false, lineStyle: { width: 1, color: '#f04444' } },
    ]
  }
  if (type === 'rsi' && ind.rsi) {
    return [{ name: 'RSI', type: 'line', data: ind.rsi, showSymbol: false, lineStyle: { width: 1, color: '#e3b341' } }]
  }
  const macd = ind.macd || { dif: [], dea: [], hist: [] }
  return [
    { name: 'DIF', type: 'line', data: macd.dif, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' } },
    { name: 'DEA', type: 'line', data: macd.dea, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' } },
    { name: 'MACD', type: 'bar', barWidth: '55%', data: (macd.hist || []).map(v => ({ value: v, itemStyle: { color: (v || 0) >= 0 ? tc.up + '99' : tc.down + '99' } })) },
  ]
}

async function screenshotChart() {
  if (!chart) return
  const bg = getComputedStyle(document.body).getPropertyValue('--bg-card').trim() || '#1a1b26'
  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: bg })
  const ok = await captureToClipboard(url, `${displayName.value}_${chartTitle.value}.png`)
  showToast(ok ? '截图成功，已复制到剪贴板' : '截图失败', ok ? 'success' : 'error')
}

async function captureToClipboard(dataUrl, filename) {
  try {
    const img = new Image()
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = dataUrl })
    const canvas = document.createElement('canvas')
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    const ctx = canvas.getContext('2d')
    ctx.drawImage(img, 0, 0)
    await applyWatermark(canvas, { right: 18, bottom: 16, heightRatio: 0.05 })
    dataUrl = canvas.toDataURL('image/png')
  } catch (e) { /* 水印失败仍用原图 */ }
  try {
    const resp = await fetch(dataUrl)
    const blob = await resp.blob()
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    return true
  } catch (e) {
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = filename
    a.click()
    return true
  }
}

/**
 * 生成 A 股全天分时时间轴：09:30~11:30 + 13:00~15:00，每分钟一个点。
 * @returns {string[]}
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

function calcMA(points, n) {
  if (!points || !points.length) return []
  return points.map((_, i) => {
    const start = Math.max(0, i - n + 1)
    const count = i - start + 1
    const s = points.slice(start, i + 1).reduce((sum, p) => sum + (p.close != null ? p.close : (p.price != null ? p.price : (typeof p === 'number' ? p : 0))), 0)
    return +(s / count).toFixed(2)
  })
}

function renderTrend() {
  if (!chart || !trend.value || !trend.value.points || !trend.value.points.length) return
  const tc = themeColors()
  const t = trend.value
  const fullTimes = buildFullTrendTimes()
  const byTime = new Map()
  for (const p of t.points) byTime.set(p.time, p)
  const times = fullTimes
  const prices = fullTimes.map(tt => { const p = byTime.get(tt); return p ? p.price : null })
  const avgs = fullTimes.map(tt => { const p = byTime.get(tt); return p ? p.avg : null })
  const vols = fullTimes.map(tt => { const p = byTime.get(tt); return p ? p.volume : 0 })
  const realPrices = prices.filter(v => v != null)
  const realAvgs = avgs.filter(v => v != null)
  const pre = t.pre_close || (realPrices.length ? realPrices[0] : 1)
  const last = realPrices[realPrices.length - 1]
  const color = last >= pre ? tc.up : tc.down
  const avgOk = realAvgs.length > 0 && Math.abs(realAvgs[0] - pre) / pre < 0.2
  const ind = trendIndicators(t.points)
  const { yMin, yMax, pctMin, pctMax } = calcTrendYRange({
    mode: settingsState.trendYScale || 'normal',
    prices: realPrices,
    preClose: pre,
  })
  const zeroColor = tc.avg || '#8b949e'
  const hasSub = !!subInd.value
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
    { type: 'category', data: times, gridIndex: 0, boundaryGap: false, axisLabel: { color: tc.axis, fontSize: 11 }, axisLine: { lineStyle: { color: tc.split } } },
    { type: 'category', data: times, gridIndex: 1, boundaryGap: false, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
  ]
  const yAxes = [
    {
      type: 'value', gridIndex: 0, min: yMin, max: yMax,
      splitLine: { lineStyle: { color: tc.split } },
      axisLabel: { color: tc.axis, fontSize: 11, formatter: v => Number(v).toFixed(2) },
    },
    { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { color: tc.axis, fontSize: 10 } },
    {
      type: 'value', gridIndex: 0, position: 'right', min: pctMin, max: pctMax,
      splitLine: { show: false },
      axisLabel: {
        color: tc.axis, fontSize: 10,
        formatter: (v) => (v > 0 ? '+' : '') + Number(v).toFixed(1) + '%',
      },
    },
  ]
  if (hasSub) {
    xAxes.push({ type: 'category', data: times, gridIndex: 2, boundaryGap: false, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } } })
    yAxes.push({ type: 'value', gridIndex: 2, scale: true, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { color: tc.axis, fontSize: 10 } })
  }
  const series = [
    {
      name: '点位', type: 'line', data: prices, showSymbol: false,
      lineStyle: { color, width: 1.8 }, itemStyle: { color },
      markLine: {
        silent: true, symbol: 'none',
        data: [{ yAxis: pre, name: '昨收' }],
        lineStyle: { color: zeroColor, type: 'solid', width: 1.2 },
        label: { show: false },
      },
    },
    ...(avgOk ? [{ name: '均价', type: 'line', data: avgs, showSymbol: false, lineStyle: { color: '#ffcc00', width: 1.5, type: 'solid' }, itemStyle: { color: '#ffcc00' } }] : []),
    {
      name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, barWidth: '60%',
      data: vols.map((v, i) => ({
        value: v,
        itemStyle: { color: prices[i] == null ? 'transparent' : (prices[i] >= pre ? tc.up : tc.down) + '8c' },
      })),
    },
  ]
  if (hasSub) {
    series.push(...subSeries(ind, tc).map(s => ({ ...s, xAxisIndex: 2, yAxisIndex: 3 })))
  }

  chart.setOption({
    animation: false,
    dataZoom: [{
      type: 'inside', xAxisIndex: hasSub ? [0, 1, 2] : [0, 1], filterMode: 'filter',
      zoomOnMouseWheel: false, moveOnMouseWheel: false, moveOnMouseMove: false,
    }],
    grid: grids,
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'cross' },
      formatter: (ps) => {
        const i = ps[0].dataIndex
        if (prices[i] == null) return null
        const chg = ((prices[i] - pre) / pre * 100)
        const chgColor = chg >= 0 ? tc.up : tc.down
        const row = (label, valHtml) =>
          `<div style="display:flex;justify-content:space-between;gap:24px;line-height:1.7"><span style="color:${tc.axis};opacity:.8">${label}</span><span>${valHtml}</span></div>`
        let html = `<div style="min-width:140px;font-size:12px">`
        html += row('时间', `<b>${times[i]}</b>`)
        html += row('点位', `<b style="color:${chgColor}">${fmtPrice(prices[i])}</b>`)
        html += row('涨跌幅', `<span style="color:${chgColor};font-weight:700">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</span>`)
        if (avgOk && avgs[i] != null) html += row('均价', fmtPrice(avgs[i]))
        html += row('昨收', fmtPrice(pre))
        if (vols[i] != null) html += row('成交量', fmtNum(vols[i], 0))
        html += `</div>`
        return html
      },
    },
    legend: { show: false },
    xAxis: xAxes,
    yAxis: yAxes,
    series,
  }, true)
}

let currentYAxis = null
let lastKData = null

/**
 * 准备 K 线渲染数据（指标 + 均线），同一数据源缓存复用，避免 datazoom 高频重算
 * @param {object} k K 线数据
 * @returns {{ ind: object, ma5: Array, ma10: Array, ma20: Array, ma60: Array, volMa5: Array }}
 */
function prepareKData(k) {
  const pts = k.points
  if (lastKData && lastKData.pts === pts) return lastKData
  const ind = ensureIndicators(pts, k.indicators)
  lastKData = {
    pts,
    ind,
    ma5: ind.ma5 || calcMA(pts, 5),
    ma10: ind.ma10 || calcMA(pts, 10),
    ma20: ind.ma20 || calcMA(pts, 20),
    ma60: ind.ma60 || calcMA(pts, 60),
    volMa5: ind.vol_ma5 || calcMA(pts.map(x => ({ close: x.volume || 0 })), 5),
  }
  return lastKData
}

/**
 * 当前 dataZoom 可见区间（按百分比映射到数据下标）
 * @param {number} total
 * @returns {{ startIdx: number, endIdx: number }}
 */
function visibleIndicesK(total) {
  let s = Math.round((klineZoom.start / 100) * total)
  let e = Math.round((klineZoom.end / 100) * total)
  s = Math.max(0, Math.min(total - 1, s))
  e = Math.max(s + 1, Math.min(total, e))
  return { startIdx: s, endIdx: e }
}

/**
 * 按可见区间计算 Y 轴范围（价格轴 + 右侧百分比轴），实现「随视图动态缩放」
 * @param {Array} pts K 线点
 * @param {Array[]} overlays 均线等叠加序列
 * @returns {object} calcKlineYRange 结果
 */
function visibleRangeForK(pts, overlays) {
  const { startIdx, endIdx } = visibleIndicesK(pts.length)
  const sl = (arr) => (Array.isArray(arr) ? arr.slice(startIdx, endIdx) : [])
  return calcKlineYRange({
    mode: settingsState.klineYScale || 'auto',
    highs: pts.slice(startIdx, endIdx).map(x => x.high),
    lows: pts.slice(startIdx, endIdx).map(x => x.low),
    overlays: overlays.map(sl),
    base: pts[startIdx]?.close,
  })
}

/**
 * 依据最新 dataZoom 窗口动态更新左右 Y 轴范围
 */
function applyVisibleYRange() {
  if (!chart || !currentYAxis || period.value === 'trend') return
  const k = klineCache[period.value]
  if (!k || !k.points || !k.points.length) return
  const pts = k.points
  const { ma5, ma10, ma20, ma60 } = prepareKData(k)
  const range = visibleRangeForK(pts, [ma5, ma10, ma20, ma60])
  const yAxis = currentYAxis.map(a => ({ ...a }))
  yAxis[0].min = range.yMin
  yAxis[0].max = range.yMax
  yAxis[0].scale = false
  if (range.pctMin != null) {
    yAxis[1].min = range.pctMin
    yAxis[1].max = range.pctMax
  }
  chart.setOption({ yAxis }, false)
}

function renderKline(p) {
  if (!chart) return
  const k = klineCache[p]
  if (!k || !k.points || !k.points.length) return
  const tc = themeColors()
  const pts = k.points
  const { ind, ma5, ma10, ma20, ma60, volMa5 } = prepareKData(k)
  const dates = pts.map(x => x.date)
  const base = pts[0].close || pts[0].low || 1
  const vols = pts.map(x => x.volume || 0)

  // 初始视图：日周月默认显示 60 个蜡烛图（须先设置 zoom，可见区间才能对应）
  if (klineZoom.start === 0 && klineZoom.end === 100 && pts.length > 60) {
    klineZoom.start = Math.max(0, 100 - Math.round(60 / pts.length * 100))
    klineZoom.end = 100
  }

  const priceRange = visibleRangeForK(pts, [ma5, ma10, ma20, ma60])

  const hasSub = !!subInd.value
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
    { type: 'category', data: dates, gridIndex: 0, axisLabel: { color: tc.axis, fontSize: 11 }, axisLine: { lineStyle: { color: tc.split } } },
    { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
  ]
  const yAxes = [
    {
      type: 'value', gridIndex: 0, position: 'left',
      min: priceRange.yMin, max: priceRange.yMax,
      splitLine: { lineStyle: { color: tc.split } },
      axisLabel: { color: tc.axis, fontSize: 11 },
      axisLine: { lineStyle: { color: tc.split } },
    },
    {
      type: 'value', gridIndex: 0, position: 'right',
      min: priceRange.pctMin, max: priceRange.pctMax,
      splitLine: { show: false },
      axisLabel: { color: tc.axis, fontSize: 10, formatter: (v) => (v > 0 ? '+' : '') + Number(v).toFixed(1) + '%' },
      axisLine: { lineStyle: { color: tc.split } },
    },
    {
      type: 'value', gridIndex: 1,
      splitLine: { show: false },
      axisLabel: { color: tc.axis, fontSize: 10 },
    },
  ]
  if (hasSub) {
    xAxes.push({ type: 'category', data: dates, gridIndex: 2, axisLabel: { show: false }, axisLine: { lineStyle: { color: tc.split } } })
    yAxes.push({
      type: 'value', gridIndex: 2, scale: true,
      splitLine: { lineStyle: { color: tc.split } },
      axisLabel: { color: tc.axis, fontSize: 10 },
    })
  }
  currentYAxis = yAxes

  const series = [
    {
      name: 'K线', type: 'candlestick',
      xAxisIndex: 0, yAxisIndex: 0,
      data: pts.map(x => [x.open, x.close, x.low, x.high]),
      itemStyle: { color: tc.up, color0: tc.down, borderColor: tc.up, borderColor0: tc.down },
    },
    { name: 'MA5', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma5, showSymbol: false, lineStyle: { width: 1, color: '#f5a623' }, itemStyle: { color: '#f5a623' } },
    { name: 'MA10', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma10, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' }, itemStyle: { color: '#4c9aff' } },
    { name: 'MA20', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma20, showSymbol: false, lineStyle: { width: 1, color: '#f04444' }, itemStyle: { color: '#f04444' } },
    { name: 'MA60', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ma60, showSymbol: false, lineStyle: { width: 1, color: '#2fbf8f' }, itemStyle: { color: '#2fbf8f' } },
    {
      name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 2, barWidth: '60%',
      data: vols.map((v, i) => ({
        value: v,
        itemStyle: { color: pts[i].close >= pts[i].open ? tc.up + '8c' : tc.down + '8c' },
      })),
    },
    {
      name: 'VOL MA5', type: 'line', data: volMa5, xAxisIndex: 1, yAxisIndex: 2, showSymbol: false,
      lineStyle: { width: 1, color: '#f5a623', type: 'dashed' }, itemStyle: { color: '#f5a623' },
    },
  ]
  if (hasSub) {
    series.push(...subSeries(ind, tc).map(s => ({ ...s, xAxisIndex: 2, yAxisIndex: 3 })))
  }

  chart.setOption({
    animation: false,
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: hasSub ? [0, 1, 2] : [0, 1],
        filterMode: 'filter',
        zoomOnMouseWheel: true,
        start: klineZoom.start,
        end: klineZoom.end,
      },
    ],
    grid: grids,
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'cross' },
      formatter: (ps) => {
        const i = ps[0].dataIndex
        const x = pts[i]
        const prev = pts[i - 1]
        const chgNum = prev && prev.close ? ((x.close - prev.close) / prev.close) * 100 : null
        const chg = chgNum != null ? chgNum.toFixed(2) : '-'
        const chgColor = chgNum > 0 ? tc.up : chgNum < 0 ? tc.down : tc.axis
        const cum = base ? ((x.close - base) / base) * 100 : null

        const row = (label, valHtml) =>
          `<div style="display:flex;justify-content:space-between;gap:24px;line-height:1.7"><span style="color:${tc.axis};opacity:.8">${label}</span><span>${valHtml}</span></div>`

        let html = `<div style="min-width:140px;font-size:12px">`
        html += row('时间', `<b>${x.date}</b>`)
        html += row('开盘', fmtPrice(x.open))
        html += row('收盘', `<b>${fmtPrice(x.close)}</b>`)
        html += row('最高', fmtPrice(x.high))
        html += row('最低', fmtPrice(x.low))
        if (chgNum != null) {
          html += row('涨跌幅', `<span style="color:${chgColor};font-weight:700">${chgNum > 0 ? '+' : ''}${chg}%</span>`)
        }
        if (cum != null) {
          html += row('区间涨幅', `<span style="color:${chgColor};font-weight:700">${cum > 0 ? '+' : ''}${cum.toFixed(2)}%</span>`)
        }
        if (x.volume != null) {
          html += row('成交量', fmtNum(x.volume, 0))
        }
        html += `</div>`
        return html
      },
    },
    legend: { data: ['MA5', 'MA10', 'MA20', 'MA60'], top: 0, right: 0, textStyle: { color: tc.axis, fontSize: 10 }, itemWidth: 12, itemHeight: 6 },
    xAxis: xAxes,
    yAxis: yAxes,
    series,
  }, true)
}

function onResize() { chart && chart.resize() }
function onThemeChange() {
  if (period.value === 'trend') renderTrend()
  else renderKline(period.value)
}
function onChartScaleChange() {
  if (period.value === 'trend') renderTrend()
  else renderKline(period.value)
}

watch(() => props.secid, (n) => {
  if (n && n !== secid.value) {
    secid.value = n
    trend.value = null
    Object.keys(klineCache).forEach(k => delete klineCache[k])
    // 保持当前选中的图表类型（分时 / 日K / 周K / 月K）
    load()
  }
})

const poll = usePolling(load, 5000)

onMounted(async () => {
  await nextTick()
  chart = echarts.init(chartEl.value)
  chart.on('datazoom', (params) => {
    if (params.batch && params.batch[0]) {
      klineZoom.start = params.batch[0].start != null ? params.batch[0].start : klineZoom.start
      klineZoom.end = params.batch[0].end != null ? params.batch[0].end : klineZoom.end
    } else if (params.start != null) {
      klineZoom.start = params.start
      klineZoom.end = params.end != null ? params.end : klineZoom.end
    }
    applyVisibleYRange()
    if (klineZoom.start <= 8 && period.value !== 'trend') {
      maybeLoadMoreHistory()
    }
  })
  window.addEventListener('resize', onResize)
  window.addEventListener('theme-change', onThemeChange)
  window.addEventListener('chart-scale-change', onChartScaleChange)
  load()
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('theme-change', onThemeChange)
  window.removeEventListener('chart-scale-change', onChartScaleChange)
  chart && chart.dispose()
})
</script>

<style scoped>
.mini-tabs { margin-bottom: 0; }
.mini-tabs .tab { padding: 3px 12px; font-size: 12px; }
.btn-nav-idx {
  background: var(--bg-hover); border: 1px solid var(--border); border-radius: 4px;
  color: var(--text); cursor: pointer; padding: 2px 8px; font-size: 14px; line-height: 1;
}
.btn-nav-idx:hover { background: var(--accent-bg); color: var(--accent); }

.index-quote-header {
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 2px;
}
.index-quote-main {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.change-amt {
  margin-left: 6px;
  font-size: 15px;
  font-weight: 500;
  opacity: 0.9;
}
.index-quote-sub {
  color: var(--text-dim);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.index-quote-sub b {
  color: var(--text);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.index-quote-sub b.up { color: var(--up); }
.index-quote-sub b.down { color: var(--down); }
.sub-dot { color: var(--border); }
.index-breadth {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}
.breadth-pill {
  font-size: 12px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 6px;
  font-variant-numeric: tabular-nums;
}
.breadth-pill.up { background: var(--up-bg); color: var(--up); }
.breadth-pill.down { background: var(--down-bg); color: var(--down); }
.breadth-pill.flat { background: var(--bg-hover); color: var(--text-dim); }
.breadth-val .up { color: var(--up); }
.breadth-val .down { color: var(--down); }
.breadth-val .flat { color: var(--text-dim); }

.index-kv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  width: 100%;
}
.index-kv-grid .kv {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 10px 14px;
  background: var(--kv-bg);
  border-radius: 8px;
  min-width: 0;
  box-sizing: border-box;
}
.index-kv-grid .kv .k {
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 4px;
}
.index-kv-grid .kv .v {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
