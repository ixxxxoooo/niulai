<template>
  <div class="card">
    <div class="card-title">
      <span>{{ chartTitle }}</span>
      <div class="tabs mini-tabs">
        <div class="tab" :class="{ active: chartPeriod === 'trend' }" @click="switchChart('trend')">分时</div>
        <div class="tab" :class="{ active: chartPeriod === 'day' }" @click="switchChart('day')">日K</div>
        <div class="tab" :class="{ active: chartPeriod === 'week' }" @click="switchChart('week')">周K</div>
        <div class="tab" :class="{ active: chartPeriod === 'month' }" @click="switchChart('month')">月K</div>
      </div>
      <div class="tabs mini-tabs">
        <div class="tab" :class="{ active: subInd === 'macd' }" data-tip="MACD 由快线 DIF（12日均线-26日均线）、慢线 DEA（DIF 的9日均线）和红绿柱组成。金叉（DIF 上穿 DEA）看多，死叉看空；红柱放大=多头动能增强，绿柱放大=空头动能增强。震荡行情中金叉/死叉频繁，容易假信号。" @click="setSub('macd')">MACD</div>
        <div class="tab" :class="{ active: subInd === 'kdj' }" data-tip="KDJ 由 K、D、J 三条线组成，取值 0~100（J 可越界）。K 上穿 D 为金叉（买入信号），下穿为死叉（卖出信号）；K/D 低于 20 为超卖区，高于 80 为超买区。J 线最灵敏，J>100 短期过热、J<0 短期超跌。KDJ 在强趋势里会钝化，配合 MACD 一起看更可靠。" @click="setSub('kdj')">KDJ</div>
        <div class="tab" :class="{ active: subInd === 'rsi' }" data-tip="RSI 反映近期涨跌力量的强弱，取值 0~100（默认 14 日）。RSI>70 偏超买（涨多可能回调），<30 偏超卖（跌多可能反弹）；50 上方多头占优、50 下方空头占优。RSI 与价格背离是重要的转折信号。" @click="setSub('rsi')">RSI</div>
      </div>
      <div class="tabs mini-tabs">
        <div class="tab" :class="{ active: showBuySell }" @click="toggleBuySell">买卖点</div>
      </div>
      <div class="tabs mini-tabs" v-if="chartPeriod !== 'trend'">
        <div class="tab" @click="zoomKline(1)" title="显示更多历史K线 (视野变宽)">拉长K线</div>
        <div class="tab" @click="zoomKline(-1)" title="聚焦近期K线 (蜡烛变粗)">缩短K线</div>
      </div>
      <button class="btn-screenshot" @click="screenshotChart" title="截图到剪贴板"><UiIcon name="screenshot" :size="14" /></button>
    </div>
    <div class="sr-picker" v-if="srOptions.length && chartPeriod !== 'trend'">
      <span class="sr-picker-label">压力/支撑</span>
      <span v-for="opt in srOptions" :key="opt.id" class="sr-opt" :class="{ on: selectedSR.has(opt.id), resist: opt.side==='r', support: opt.side==='s' }">
        <UiCheckbox :checked="selectedSR.has(opt.id)" @change="toggleSRItem(opt.id)" />
        <span>{{ opt.label }} {{ opt.price }}</span>
      </span>
    </div>
    <!-- 分时 / K 线分组件，共享同一 DOM 容器由父级切换渲染 -->
    <TrendChart
      v-show="chartPeriod === 'trend'"
      ref="trendRef"
      :trend="trend"
      :detail="detail"
      :code="code"
      :sub-ind="subInd"
      :show-buy-sell="showBuySell"
      :sr-options="srOptions"
      :selected-set="selectedSR"
    />
    <KlineChart
      v-show="chartPeriod !== 'trend'"
      ref="klineRef"
      :period="chartPeriod"
      :kline="klineCache[chartPeriod]"
      :detail="detail"
      :sub-ind="subInd"
      :sr-options="srOptions"
      :selected-set="selectedSR"
    />
  </div>
</template>

<script setup>
/**
 * 个股图表面板：分时 / 日周月 K 切换 + 副图指标 + 压力支撑
 * @author ygw
 */
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { getCachedKline } from '../../composables/useKlineCache.js'
import { showToast } from '../../composables/useToast.js'
import { applyWatermark } from '../../composables/useScreenshot.js'
import TrendChart from './TrendChart.vue'
import KlineChart from './KlineChart.vue'

const props = defineProps({
  code: { type: String, required: true },
  detail: { type: Object, default: () => ({}) },
  trend: { type: Object, default: null },
  displayName: { type: String, default: '' },
  initialKlineDay: { type: Object, default: null },
  srLevels: { type: Object, default: () => ({ support: [], resistance: [] }) },
})

const emit = defineEmits(['error', 'kline-day'])

const chartPeriod = ref('trend')
const subInd = ref('macd')
const showBuySell = ref(true)
const klineCache = reactive({})
const selectedSR = ref(new Set())
const trendRef = ref(null)
const klineRef = ref(null)

const chartTitle = computed(() => ({
  trend: '分时走势', day: '日K线', week: '周K线', month: '月K线',
}[chartPeriod.value]))

const srOptions = computed(() => {
  const out = []
  for (const lv of (props.srLevels.resistance || [])) {
    out.push({ id: `r-${lv.label}-${lv.price}`, side: 'r', label: lv.label, price: lv.price })
  }
  for (const lv of (props.srLevels.support || [])) {
    out.push({ id: `s-${lv.label}-${lv.price}`, side: 's', label: lv.label, price: lv.price })
  }
  return out
})

watch(() => props.srLevels, (sr) => {
  if (!sr) return
  const ids = new Set()
  for (const lv of (sr.resistance || [])) ids.add(`r-${lv.label}-${lv.price}`)
  for (const lv of (sr.support || [])) ids.add(`s-${lv.label}-${lv.price}`)
  selectedSR.value = ids
}, { deep: true })

watch(() => props.initialKlineDay, (kd) => {
  if (kd && kd.points && kd.points.length) {
    klineCache.day = kd
    emit('kline-day', kd)
  }
}, { immediate: true })

watch(() => props.trend, () => {
  if (chartPeriod.value === 'trend') nextTick(() => trendRef.value?.render())
})

watch(() => props.code, () => {
  Object.keys(klineCache).forEach(k => delete klineCache[k])
  chartPeriod.value = 'trend'
})

function toggleSRItem(id) {
  const next = new Set(selectedSR.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedSR.value = next
  redraw()
}

async function switchChart(p) {
  chartPeriod.value = p
  if (p === 'trend') { await nextTick(); trendRef.value?.render(); return }
  const draw = async () => {
    await nextTick()
    klineRef.value?.resize?.()
    klineRef.value?.render()
  }
  if (klineCache[p]) { await draw(); return }
  try {
    const k = await getCachedKline(props.code, p, 120)
    if (k && k.points && k.points.length) {
      klineCache[p] = k
      if (p === 'day') emit('kline-day', k)
      await draw()
    } else {
      emit('error', `${chartTitle.value}数据暂不可用`)
    }
  } catch (e) {
    emit('error', 'K线数据加载失败：' + e.message)
  }
}

function setSub(t) {
  subInd.value = subInd.value === t ? '' : t
  redraw()
}

function toggleBuySell() {
  showBuySell.value = !showBuySell.value
  redraw()
}

function zoomKline(dir) {
  klineRef.value?.zoom(dir)
}

function redraw() {
  if (chartPeriod.value === 'trend') trendRef.value?.render()
  else klineRef.value?.render()
}

async function screenshotChart() {
  const inst = chartPeriod.value === 'trend' ? trendRef.value : klineRef.value
  const chart = inst?.getChart?.()
  if (!chart) return
  const bg = getComputedStyle(document.body).getPropertyValue('--bg-card').trim() || '#1a1b26'
  const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: bg })
  const ok = await captureToClipboard(url, `${props.displayName}_${chartTitle.value}.png`)
  showToast(ok ? '截图成功，已复制到剪贴板' : '截图失败', ok ? 'success' : 'error')
}

/**
 * 截图复制/下载前在图上绘制「牛来」logo 水印。
 * 加载 dataURL → canvas → 打水印 → 输出新 dataURL。
 * @param {string} dataUrl
 * @param {string} filename
 * @returns {Promise<boolean>}
 */
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
    try {
      const a = document.createElement('a')
      a.href = dataUrl
      a.download = filename
      a.click()
      return true
    } catch (e2) {
      return false
    }
  }
}

function onThemeChange() { redraw() }
function onChartScaleChange() { redraw() }

onMounted(() => {
  window.addEventListener('theme-change', onThemeChange)
  window.addEventListener('chart-scale-change', onChartScaleChange)
  nextTick(() => trendRef.value?.render())
})
onUnmounted(() => {
  window.removeEventListener('theme-change', onThemeChange)
  window.removeEventListener('chart-scale-change', onChartScaleChange)
})

defineExpose({
  chartPeriod,
  klineCache,
  switchChart,
  redraw,
  setDayKline(kd) {
    if (kd && kd.points?.length) {
      klineCache.day = kd
      emit('kline-day', kd)
      if (chartPeriod.value === 'day') klineRef.value?.render()
    }
  },
})
</script>

<style scoped>
.mini-tabs { margin-bottom: 0; }
.mini-tabs .tab { padding: 3px 12px; font-size: 12px; }
.card-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; font-size: 16px;
  padding: 2px 6px; border-radius: 4px; opacity: .7; transition: opacity .2s;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }
.sr-picker {
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding: 6px 0 4px; font-size: 12px;
}
.sr-picker-label { color: var(--text-dim); margin-right: 4px; }
.sr-opt {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border);
  cursor: pointer; color: var(--text-dim); user-select: none;
}
.sr-opt input { margin: 0; }
.sr-opt.on.resist { border-color: var(--down); color: var(--down); background: var(--down-bg); }
.sr-opt.on.support { border-color: var(--up); color: var(--up); background: var(--up-bg); }
</style>
