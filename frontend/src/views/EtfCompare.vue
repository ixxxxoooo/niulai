<template>
  <div class="page etf-compare-page">
    <ToolNavTabs current-tab="etf-compare" />

    <!-- ① 选择区 -->
    <div class="card picker-card">
      <div class="card-title">① 选择 ETF（最多 {{ MAX_PICK }} 只）</div>
      <div class="picker-row">
        <UiInput
          v-model="kw"
          class="search-input"
          placeholder="输入板块 / 名称 / 代码，如：半导体、人工智能、医疗…"
          @keydown.enter="doSearch"
        />
        <button class="btn-search" :disabled="!kw.trim()" @click="doSearch">搜索</button>
      </div>
      <div class="sector-chips">
        <span
          v-for="b in SECTORS"
          :key="b"
          class="chip"
          :class="{ active: activeChip === b }"
          @click="searchBy(b)"
        >{{ b }}</span>
      </div>

      <div v-if="searching" class="result-hint">搜索中…</div>
      <div v-else-if="results.length" class="result-list">
        <div
          v-for="r in results"
          :key="r.code"
          class="result-item"
          :class="{ checked: selected.includes(r.code), dim: !canPick(r.code) }"
          @click="toggle(r)"
        >
          <span class="ri-check">{{ selected.includes(r.code) ? '✓' : '' }}</span>
          <span class="ri-name">{{ r.name }}</span>
          <span class="ri-code">{{ r.code }}</span>
          <span class="ri-tag">ETF</span>
        </div>
      </div>
      <div v-else-if="kw.trim() && !searching" class="result-hint">未找到匹配的 ETF</div>
      <div v-else class="result-hint dim-hint">
        支持按板块关键词（半导体 / 医疗 / 军工…）、名称、代码或拼音搜索；点击上方板块标签快速筛选
      </div>
    </div>

    <!-- ② 对比区 -->
    <div v-if="selected.length" class="card compare-card">
      <div class="card-title">
        ② 对比（{{ selected.length }} 只）
        <span class="compare-sub">点击标签移除 · 点击行跳详情</span>
      </div>
      <div class="picked-chips">
        <span v-for="c in selected" :key="c" class="chip picked" @click="remove(c)">{{ pickedName(c) }} ✕</span>
        <span class="chip clear" @click="clearAll">清空</span>
      </div>
      <div class="chart-toolbar">
        <span class="tool-label">走势回看</span>
        <span v-for="d in LOOKBACKS" :key="d" class="chip" :class="{ active: days === d }" @click="setDays(d)">{{ d }}日</span>
        <span class="updated">更新 {{ updated }}</span>
      </div>

      <div class="cmp-table-wrap">
        <table class="cmp-table">
          <thead>
            <tr>
              <th class="th-label">ETF</th>
              <th v-for="m in METRICS" :key="m.key">{{ m.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="q in quotes"
              :key="q.code"
              class="cmp-row"
              @click="openDetail(q)"
            >
              <td class="td-name">
                {{ q.name }}<span class="th-code">{{ q.code }}</span>
              </td>
              <td
                v-for="m in METRICS"
                :key="m.key"
                class="tabular"
                :class="m.cls(q)"
              >{{ m.fmt(q) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="cmp-chart-head">
        <span>近 {{ days }} 日走势（归一化涨幅 %）</span>
      </div>
      <div ref="chartEl" class="cmp-chart"></div>
    </div>
  </div>
</template>

<script setup>
/**
 * ETF 选择对比：关键字/板块搜索 → 多选 → 横向指标对比 + 归一化走势叠加图
 * @author ygw
 */
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import ToolNavTabs from '../components/ToolNavTabs.vue'
import UiInput from '../components/ui/UiInput.vue'
import { api } from '../api.js'
import { fmtPrice, fmtPct, fmtAmount, fmtNum, pctClass, themeColors } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock } from '../composables/useStockMeta.js'

const MAX_PICK = 10
const SECTORS = [
  '半导体', '人工智能', '云计算', '芯片', '通信', '消费电子', '光伏', '新能源',
  '电池', '机器人', '军工', '证券', '银行', '白酒', '医疗', '创新药', '煤炭',
  '黄金', '恒生科技', '港股通', '纳斯达克', '沪深300', '创业板', '科创50',
]
const LOOKBACKS = [10, 30, 60, 120]

const kw = ref('')
const activeChip = ref('')
const searching = ref(false)
const results = ref([])
const selected = ref([])
const quotes = ref([])
const trends = ref({})
const dates = ref([])
const days = ref(30)
const updated = ref('')
const chartEl = ref(null)
let chart = null

const METRICS = [
  { key: 'price', label: '现价', fmt: q => fmtPrice(q.price), cls: () => 'flat' },
  { key: 'change_pct', label: '涨跌幅', fmt: q => fmtPct(q.change_pct), cls: q => pctClass(q.change_pct) },
  { key: 'amount', label: '成交额', fmt: q => fmtAmount(q.amount), cls: () => 'flat' },
  { key: 'fund_scale', label: '规模', fmt: q => fmtAmount(q.fund_scale), cls: () => 'flat' },
  { key: 'turnover', label: '换手率', fmt: q => fmtPct(q.turnover), cls: () => 'flat' },
  { key: 'volume_ratio', label: '量比', fmt: q => fmtNum(q.volume_ratio), cls: () => 'flat' },
  { key: 'amplitude', label: '振幅', fmt: q => fmtPct(q.amplitude), cls: () => 'flat' },
]

function isEtf(x) {
  const code = String(x.code || '')
  return x.type === 'ETF'
    || /ETF/i.test(String(x.name || ''))
    || /^5\d{4}$/.test(code)
    || /^1[0-9]{4}$/.test(code)
}

function canPick(code) {
  return selected.value.includes(code) || selected.value.length < MAX_PICK
}

let searchTimer = null
function doSearch() {
  const q = kw.value.trim()
  if (!q) return
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    searching.value = true
    try {
      const r = await api.search(q, 30)
      results.value = (r || []).filter(isEtf).slice(0, 30)
    } catch (e) {
      results.value = []
    } finally {
      searching.value = false
    }
  }, 200)
}

function searchBy(sector) {
  activeChip.value = sector
  kw.value = sector
  doSearch()
}

function toggle(r) {
  const i = selected.value.indexOf(r.code)
  if (i >= 0) selected.value.splice(i, 1)
  else if (selected.value.length < MAX_PICK) selected.value.push(r.code)
  load()
}

function remove(code) {
  selected.value = selected.value.filter(c => c !== code)
  load()
}

function clearAll() {
  selected.value = []
  quotes.value = []
  trends.value = {}
  dates.value = []
}

function setDays(d) {
  days.value = d
  load()
}

function pickedName(code) {
  const q = quotes.value.find(x => x.code === code)
  return q ? q.name : code
}

function nowStr() {
  const d = new Date()
  const p = n => String(n).padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

async function load() {
  if (!selected.value.length) return
  try {
    const r = await api.etfCompare(selected.value.join(','), days.value)
    quotes.value = r.quotes || []
    trends.value = r.trends || {}
    dates.value = r.dates || []
    updated.value = nowStr()
    renderChart()
  } catch (e) {
    /* 静默：下次轮询重试 */
  }
}

function openDetail(q) {
  if (q && q.code) openStock({ code: q.code, name: q.name })
}

const PALETTE = ['#4c9aff', '#f04444', '#2fbf8f', '#e3b341', '#9a7bff', '#4fd6be', '#ff9d5c', '#5aa2ff', '#f27ab5', '#7bd44c']

function renderChart() {
  if (!chart || !chartEl.value) return
  const entries = Object.entries(trends.value)
  if (!entries.length || !dates.value.length) return
  const tc = themeColors()
  const colors = entries.map((_, i) => PALETTE[i % PALETTE.length])
  const series = entries.map(([code, t], i) => ({
    name: t.name || code,
    type: 'line',
    smooth: true,
    symbol: 'none',
    data: (t.points || []).map(p => p.value),
    lineStyle: { width: 2, color: colors[i] },
    itemStyle: { color: colors[i] },
    emphasis: { focus: 'series' },
  }))
  chart.setOption({
    animation: false,
    grid: { left: 52, right: 20, top: 20, bottom: 28 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(24,26,32,0.92)',
      borderColor: 'rgba(255,255,255,0.12)',
      textStyle: { color: '#e6e8ec', fontSize: 12 },
      valueFormatter: v => (v == null ? '-' : v.toFixed(2) + '%'),
    },
    legend: {
      top: 0, type: 'scroll', itemWidth: 16, itemHeight: 8,
      textStyle: { color: tc.axis, fontSize: 11 },
    },
    xAxis: {
      type: 'category', data: dates.value,
      boundaryGap: false,
      axisLine: { lineStyle: { color: tc.split } },
      axisLabel: { color: tc.axis, fontSize: 10 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: tc.axis, fontSize: 10, formatter: v => v + '%' },
      splitLine: { lineStyle: { color: tc.split } },
    },
    series,
  }, true)
}

function resizeChart() {
  if (chart && chartEl.value) chart.resize()
}

function onThemeChange() {
  renderChart()
}

onMounted(() => {
  if (chartEl.value) {
    chart = echarts.init(chartEl.value)
    renderChart()
  }
  window.addEventListener('resize', resizeChart)
  window.addEventListener('theme-change', onThemeChange)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  window.removeEventListener('theme-change', onThemeChange)
  if (chart) { chart.dispose(); chart = null }
})

// 已选非空时周期刷新实时行情（非交易时段自动降频）
usePolling(async () => {
  if (!selected.value.length) return
  await load()
}, 10000, { primary: false, immediate: false })
</script>

<style scoped>
.etf-compare-page { display: flex; flex-direction: column; gap: 14px; }

.card-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.compare-sub { font-size: 11px; color: var(--text-dim); font-weight: 400; margin-left: 6px; }

.picker-row { display: flex; gap: 8px; margin-bottom: 10px; }
.search-input { flex: 1; }
.btn-search {
  height: 32px; padding: 0 18px; border-radius: 6px; border: none;
  background: var(--accent); color: #fff; font-size: 13px; cursor: pointer;
  transition: opacity 0.15s;
}
.btn-search:disabled { opacity: 0.4; cursor: not-allowed; }

.sector-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.chip {
  display: inline-flex; align-items: center; height: 24px; padding: 0 10px;
  border-radius: 12px; font-size: 12px; cursor: pointer; user-select: none;
  background: var(--kv-bg); border: 1px solid var(--border); color: var(--text);
  transition: all 0.15s;
}
.chip:hover { border-color: var(--accent); color: var(--accent); }
.chip.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.chip.picked { background: var(--accent-bg); border-color: var(--accent); color: var(--accent); }
.chip.clear { color: var(--text-dim); }

.result-hint { padding: 14px 4px; font-size: 12px; color: var(--text-dim); }
.dim-hint { line-height: 1.8; }

.result-list {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 6px;
  max-height: 320px; overflow-y: auto;
}
.result-item {
  display: flex; align-items: center; gap: 8px; padding: 7px 10px;
  border-radius: 6px; background: var(--kv-bg); border: 1px solid var(--border);
  cursor: pointer; transition: all 0.15s; font-size: 13px;
}
.result-item:hover { border-color: var(--accent); }
.result-item.checked { border-color: var(--accent); background: var(--accent-bg); }
.result-item.dim { opacity: 0.45; cursor: not-allowed; }
.ri-check {
  width: 16px; height: 16px; border-radius: 4px; flex-shrink: 0;
  border: 1px solid var(--border); background: var(--bg-card);
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-size: 11px;
}
.result-item.checked .ri-check { background: var(--accent); border-color: var(--accent); }
.ri-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ri-code { color: var(--text-dim); font-size: 12px; font-variant-numeric: tabular-nums; }
.ri-tag {
  font-size: 10px; color: var(--accent); border: 1px solid var(--accent);
  border-radius: 4px; padding: 1px 4px;
}

.picked-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }

.chart-toolbar {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 12px;
}
.tool-label { color: var(--text-dim); }
.updated { margin-left: auto; color: var(--text-dim); font-size: 11px; font-variant-numeric: tabular-nums; }

.cmp-table-wrap { overflow-x: auto; margin-bottom: 18px; }
.cmp-table {
  width: 100%; border-collapse: collapse; font-size: 13px; min-width: 560px;
}
.cmp-table th {
  padding: 9px 12px; text-align: left; font-weight: 600; color: var(--text);
  background: var(--kv-bg); border-bottom: 1px solid var(--border); white-space: nowrap;
}
.th-label { color: var(--text-dim) !important; width: 170px; }
.th-code { display: block; font-size: 11px; color: var(--text-dim); font-weight: 400; }
.cmp-table td {
  padding: 9px 12px; border-bottom: 1px solid var(--border); white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.cmp-row { cursor: pointer; transition: background 0.15s; }
.cmp-row:hover { background: var(--kv-bg); }
.td-name { color: var(--text); font-weight: 600; }
.tabular.up { color: var(--up); }
.tabular.down { color: var(--down); }
.tabular.flat { color: var(--text); }

.cmp-chart-head { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }
.cmp-chart { width: 100%; height: 380px; }
</style>