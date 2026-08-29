<template>
  <div class="card" ref="rootEl">
    <div class="card-title" style="display:flex;align-items:center;gap:10px">
      <span>资金流向</span>
      <a v-if="flowUrl" class="source-link" style="margin-left:auto" :href="flowUrl" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
      <button class="btn-screenshot" @click="onShot" title="截图"><UiIcon name="screenshot" :size="14" /></button>
    </div>
    <template v-if="flow.length">
      <div class="hist-head">
        <span class="hist-title">资金流向</span>
        <div class="hist-tabs">
          <button class="hist-tab" :class="{ on: viewDays === 1 }" @click="viewDays = 1">近1日</button>
          <button class="hist-tab" :class="{ on: viewDays === 5 }" @click="viewDays = 5">近5日</button>
          <button class="hist-tab" :class="{ on: viewDays === 10 }" @click="viewDays = 10">近10日</button>
          <button class="hist-tab" :class="{ on: viewDays === 20 }" @click="viewDays = 20">近20日</button>
        </div>
      </div>

      <template v-if="viewDays === 1">
        <div class="flow-overview">
          <div class="fo-main fo-single">
            <div class="fo-single-l">
              <div class="fo-k">当日主力净流入</div>
              <div class="fo-v" :class="pctClass(mainFlow.total)">{{ fmtFlowVal(mainFlow.total) }}</div>
            </div>
            <div class="fo-single-r">
              <div class="fo-s">
                <span class="fo-badge" :class="pctClass(mainFlow.total)">{{ mainFlow.total >= 0 ? '净流入' : '净流出' }}</span>
                <span>占比 {{ mainFlow.pctText }}</span>
              </div>
              <div class="fo-inout" v-if="mainFlow.in || mainFlow.out">
                <span>流入 {{ fmtFlowVal(mainFlow.in) }}</span>
                <span>流出 {{ fmtFlowVal(mainFlow.out) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div ref="chartEl" class="flow-chart"></div>
        <table class="data-table flow-table">
          <thead><tr><th style="text-align:left">类别</th><th>净流入</th><th>净占比</th></tr></thead>
          <tbody>
            <tr v-for="item in flowTableRows" :key="item.label">
              <td style="font-weight:500">{{ item.label }}</td>
              <td :class="item.val >= 0 ? 'up' : 'down'">{{ fmtFlowVal(item.val) }}</td>
              <td :class="item.pct >= 0 ? 'up' : 'down'">{{ item.pct >= 0 ? '+' : '' }}{{ item.pct.toFixed(2) }}%</td>
            </tr>
          </tbody>
        </table>
      </template>

      <template v-else-if="histRows.length">
        <div ref="histChartEl" class="hist-chart"></div>
        <table class="data-table flow-table">
          <thead><tr><th style="text-align:left">日期</th><th>涨跌幅</th><th>主力净流入</th><th>主力净占比</th></tr></thead>
          <tbody>
            <tr v-for="d in histRows" :key="d.date">
              <td style="text-align:left;font-variant-numeric:tabular-nums">{{ d.date.slice(5) }}</td>
              <td :class="pctClass(d.change_pct)">{{ fmtPct(d.change_pct) }}</td>
              <td :class="d.main_inflow >= 0 ? 'up' : 'down'">{{ fmtFlowVal(d.main_inflow) }}</td>
              <td :class="d.main_pct >= 0 ? 'up' : 'down'">{{ fmtPct(d.main_pct) }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </template>
    <div v-else style="padding:20px;text-align:center;color:var(--text-dim);font-size:13px">
      暂无资金流数据
      <span v-if="dataSource" class="src-tag" style="margin-left:6px">{{ dataSource }}</span>
    </div>
  </div>
</template>

<script setup>
/**
 * 个股资金流向：总览卡 + 柱状图 + 分类表
 * @author ygw
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { pctClass, themeColors, fmtPct } from '../../utils.js'

const props = defineProps({
  flow: { type: Array, default: () => [] },
  displayName: { type: String, default: '' },
  dataSource: { type: String, default: '' },
  sourceTip: { type: String, default: '' },
  code: { type: String, default: '' },
})

const emit = defineEmits(['screenshot'])
const rootEl = ref(null)
const chartEl = ref(null)
const histChartEl = ref(null)
let chart = null
let histChart = null

const flowUrl = computed(() => (props.code ? `https://data.eastmoney.com/zjlx/${props.code}.html` : ''))

const flowTableRows = computed(() => {
  if (!props.flow.length) return []
  const d = props.flow[props.flow.length - 1]
  const total = Math.abs(d.extra_large || 0) + Math.abs(d.large || 0) + Math.abs(d.medium || 0) + Math.abs(d.small || 0)
  const pct = (v) => total > 0 ? (v / total * 100) : 0
  return [
    { label: '超大单', val: d.extra_large || 0, pct: d.extra_large_pct || pct(d.extra_large || 0) },
    { label: '大单', val: d.large || 0, pct: d.large_pct || pct(d.large || 0) },
    { label: '中单', val: d.medium || 0, pct: d.medium_pct || pct(d.medium || 0) },
    { label: '小单', val: d.small || 0, pct: d.small_pct || pct(d.small || 0) },
  ]
})

const mainFlow = computed(() => {
  if (!props.flow.length) return { total: null, in: null, out: null, pctText: '-' }
  const d = props.flow[props.flow.length - 1]
  const total = (d.extra_large || 0) + (d.large || 0)
  const totalAbs = Math.abs(d.extra_large || 0) + Math.abs(d.large || 0) + Math.abs(d.medium || 0) + Math.abs(d.small || 0)
  const pct = d.main_pct != null ? d.main_pct : (totalAbs > 0 ? total / totalAbs * 100 : 0)
  return { total, in: d.main_in || 0, out: d.main_out || 0, pctText: (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%' }
})

function fmtFlowVal(v) {
  if (v == null || isNaN(v)) return '-'
  const abs = Math.abs(v)
  const sign = v >= 0 ? '+' : '-'
  if (abs >= 1e8) return `${sign}${(abs / 1e8).toFixed(2)}亿`
  if (abs >= 1e4) return `${sign}${(abs / 1e4).toFixed(2)}万`
  return `${sign}${abs.toFixed(0)}`
}

const viewDays = ref(1)
const histRows = computed(() => {
  if (!props.flow.length) return []
  // 倒序：最新日期在前，方便查看最近资金流向
  return props.flow.slice(-viewDays.value).slice().reverse()
})

function renderHistChart() {
  if (!histChartEl.value) {
    if (histChart) { histChart.dispose(); histChart = null }
    return
  }
  const rows = histRows.value
  if (!rows.length) return
  if (!histChart) histChart = echarts.init(histChartEl.value)
  const tc = themeColors()
  const dates = rows.map(r => r.date.slice(5))
  const vals = rows.map(r => r.main_inflow || 0)
  histChart.setOption({
    animation: false,
    grid: { left: 10, right: 48, top: 14, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps) => {
        const d = rows[ps[0].dataIndex]
        if (!d) return ''
        return `${d.date}<br/>主力净流入 <b style="color:${d.main_inflow >= 0 ? tc.up : tc.down}">${fmtFlowVal(d.main_inflow)}</b><br/>净占比 ${fmtPct(d.main_pct)}<br/>涨跌幅 ${fmtPct(d.change_pct)}`
      },
    },
    xAxis: {
      type: 'category', data: dates, axisLine: { show: false },
      axisTick: { show: false }, axisLabel: { color: tc.axis, fontSize: 10 },
    },
    yAxis: {
      type: 'value', splitLine: { lineStyle: { color: 'rgba(128,128,128,0.12)' } },
      axisLabel: { color: tc.axis, fontSize: 10, formatter: (v) => fmtFlowVal(v) },
    },
    series: [{
      type: 'bar', barMaxWidth: 16,
      data: vals.map(v => ({ value: v, itemStyle: { color: v >= 0 ? tc.up : tc.down, borderRadius: 2 } })),
    }],
  }, true)
  histChart.resize()
}

function renderChart() {
  if (!chartEl.value) {
    if (chart) { chart.dispose(); chart = null }
    return
  }
  const d = props.flow[props.flow.length - 1]
  if (!d) return
  if (!chart) chart = echarts.init(chartEl.value)
  const tc = themeColors()
  const cats = ['超大单', '大单', '中单', '小单']
  const vals = [d.extra_large || 0, d.large || 0, d.medium || 0, d.small || 0]
  const totalAbs = vals.reduce((a, x) => a + Math.abs(x), 0)
  chart.setOption({
    animation: false,
    grid: { left: 14, right: 52, top: 6, bottom: 6, containLabel: true },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps) => {
        const p = ps[0]
        const i = cats.indexOf(p.name)
        const v = vals[i]
        const pct = totalAbs > 0 ? (v / totalAbs * 100) : 0
        return `${p.name}<br/>净流入 <b style="color:${v >= 0 ? tc.up : tc.down}">${fmtFlowVal(v)}</b><br/>净占比 ${(pct >= 0 ? '+' : '') + pct.toFixed(2)}%`
      },
    },
    xAxis: {
      type: 'value', splitLine: { show: false }, axisLine: { show: false },
      axisTick: { show: false }, axisLabel: { show: false },
    },
    yAxis: {
      type: 'category', data: cats, axisLine: { show: false },
      axisTick: { show: false }, axisLabel: { color: tc.axis, fontSize: 11 },
    },
    series: [{
      type: 'bar', barWidth: '52%',
      data: vals.map(v => ({ value: v, itemStyle: { color: v >= 0 ? tc.up : tc.down, borderRadius: 2 } })),
      label: { show: true, position: 'right', color: tc.axis, fontSize: 10, formatter: (p) => fmtFlowVal(p.value) },
    }],
  }, true)
  chart.resize()
}

function onShot() { emit('screenshot', rootEl.value) }
function onResize() { chart && chart.resize(); histChart && histChart.resize() }
function onTheme() { renderChart(); renderHistChart() }

watch(() => props.flow, async () => {
  await nextTick()
  renderChart()
  renderHistChart()
}, { deep: true })

watch(viewDays, async () => {
  await nextTick()
  renderChart()
  renderHistChart()
})

onMounted(() => {
  window.addEventListener('resize', onResize)
  window.addEventListener('theme-change', onTheme)
  nextTick(() => { renderChart(); renderHistChart() })
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('theme-change', onTheme)
  chart && chart.dispose()
  histChart && histChart.dispose()
})

defineExpose({ rootEl, renderChart })
</script>

<style scoped>
.flow-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
.flow-table th { font-weight: 500; color: var(--text-dim); text-align: right; padding: 6px 12px; border-bottom: 1px solid var(--border); }
.flow-table td { padding: 8px 12px; text-align: right; border-bottom: 1px solid var(--border-light, rgba(128,128,128,0.1)); }
.flow-table td.up { color: var(--up); font-weight: 600; }
.flow-table td.down { color: var(--down); font-weight: 600; }
.flow-table tr:last-child td { border-bottom: none; }
.flow-overview { display: flex; align-items: stretch; }
.fo-main { background: var(--accent-bg); }
.fo-single {
  flex: 1; display: flex; align-items: center; justify-content: space-between;
  gap: 16px; padding: 12px 18px; border-radius: 8px;
}
.fo-single-l { display: flex; flex-direction: column; }
.fo-single-r { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; }
.fo-single .fo-v { font-size: 22px; margin-top: 4px; }
.fo-k { font-size: 12px; color: var(--text-dim); }
.fo-v { font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; margin-top: 2px; }
.fo-s { font-size: 11px; margin-top: 2px; display: inline-flex; align-items: center; gap: 5px; }
.fo-inout { font-size: 11px; margin-top: 2px; display: block; color: var(--text-dim); }
.fo-inout span + span { margin-left: 8px; }
.fo-badge {
  display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 11px; font-weight: 600;
}
.fo-badge.up { background: var(--up-bg); color: var(--up); }
.fo-badge.down { background: var(--down-bg); color: var(--down); }
.flow-chart { height: 132px; margin-top: 4px; }
.hist-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.hist-title { font-size: 13px; font-weight: 600; color: var(--text-dim); }
.hist-tabs { margin-left: auto; display: inline-flex; gap: 4px; }
.hist-tab {
  border: 1px solid var(--border); background: var(--kv-bg); color: var(--text-dim);
  font-size: 11px; padding: 2px 10px; border-radius: var(--radius-sm); cursor: pointer;
  transition: all .15s;
}
.hist-tab.on { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600; }
.hist-chart { height: 168px; margin-bottom: 6px; }
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; font-size: 16px;
  padding: 2px 6px; border-radius: 4px; opacity: .7; transition: opacity .2s;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }
.src-tag {
  display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 3px;
  background: var(--kv-bg); color: var(--text-dim); border: 1px solid var(--border);
}
</style>
