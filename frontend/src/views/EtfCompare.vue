<template>
  <div class="page etf-compare-page">
    <ToolNavTabs current-tab="etf-compare" />

    <!-- ① 选择区 -->
    <div class="card picker-card">
      <div class="card-title">① 选择 ETF（已选 {{ selected.length }} / 最多 {{ MAX_PICK }} 只）</div>
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

      <div class="result-head" v-if="results.length">
        <span class="result-count">共 {{ results.length }} 条 · 点击勾选</span>
        <button class="select-all-btn" :disabled="!selectableCount" @click="selectAll">全选当前结果</button>
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
    <div v-if="selected.length" ref="compareCardRef" class="card compare-card">
      <div class="card-title">
        <span class="ct-left">
          ② 对比（{{ selected.length }} 只）
          <span class="compare-sub">点击行跳详情</span>
        </span>
        <button class="shot-btn" title="截图对比区域" @click="screenshotCompare">
          <UiIcon name="screenshot" :size="14" />
        </button>
      </div>
      <div class="chart-toolbar">
        <span class="tool-label">走势回看</span>
        <span v-for="d in LOOKBACKS" :key="d" class="chip" :class="{ active: days === d }" @click="setDays(d)">{{ d }}日</span>
        <span class="tool-label">视图</span>
        <span class="chip" :class="{ active: view === 'row' }" @click="view = 'row'">列表</span>
        <span class="chip" :class="{ active: view === 'col' }" @click="view = 'col'">横向</span>
        <span class="toolbar-sep"></span>
        <button class="batch-btn ghost" :disabled="!selected.length" @click="clearAll">清空已选</button>
        <span class="updated">更新 {{ updated }}</span>
      </div>

      <div class="cmp-table-wrap">
        <table v-if="view === 'row'" class="cmp-table">
          <thead>
            <tr>
              <th class="th-label th-sortable" @click="sort.toggleSort('name')">
                ETF<span class="sort-arrow">{{ sort.sortKey === 'name' ? (sort.sortDir === 1 ? ' ▲' : ' ▼') : '' }}</span>
              </th>
              <th
                v-for="m in METRICS"
                :key="m.key"
                class="th-sortable"
                @click="sort.toggleSort(m.key)"
              >
                {{ m.label }}<span class="sort-arrow">{{ sort.sortKey === m.key ? (sort.sortDir === 1 ? ' ▲' : ' ▼') : '' }}</span>
              </th>
              <th class="th-op">操作</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="q in sort.sorted" :key="q.code">
            <tr
              class="cmp-row"
              :class="{ 'row-expanded': expandedCode === q.code }"
              @click="toggleExpand(q.code)"
              @dblclick.stop="openDetail(q)"
            >
              <td class="td-name">
                <span class="td-name-text">{{ q.name }}</span>
                <span class="th-code">{{ q.code }}</span>
              </td>
              <td
                v-for="m in METRICS"
                :key="m.key"
                class="tabular"
                :class="m.cls(q)"
              >{{ m.fmt(q) }}</td>
              <td class="td-op">
                <button
                  class="op-btn"
                  :class="{ watched: isWatched(q.code) }"
                  :title="isWatched(q.code) ? '移出自选' : '加入自选'"
                  @click.stop="toggleWatchFn(q)"
                >{{ isWatched(q.code) ? '已自选' : '自选' }}</button>
                <button class="op-btn" title="设置自选分组" @click.stop="openGroup(q)">分组</button>
              </td>
            </tr>
            <PoolExpandRow
              v-if="expandedCode === q.code"
              :code="q.code"
              :name="q.name"
              :colspan="9"
              :show-score="false"
            />
          </template>
          </tbody>
        </table>

        <table v-else class="cmp-table cmp-table-col">
          <thead>
            <tr>
              <th class="th-label">指标</th>
              <th v-for="q in quotes" :key="q.code">
                {{ q.name }}<span class="th-code">{{ q.code }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in METRICS" :key="m.key">
              <td class="td-label">{{ m.label }}</td>
              <td
                v-for="q in quotes"
                :key="q.code"
                class="tabular"
                :class="m.cls(q)"
              >{{ m.fmt(q) }}</td>
            </tr>
            <tr>
              <td class="td-label">操作</td>
              <td v-for="q in quotes" :key="q.code" class="td-op">
                <button
                  class="op-btn"
                  :class="{ watched: isWatched(q.code) }"
                  :title="isWatched(q.code) ? '移出自选' : '加入自选'"
                  @click="toggleWatchFn(q)"
                >{{ isWatched(q.code) ? '已自选' : '自选' }}</button>
                <button class="op-btn" title="设置自选分组" @click="openGroup(q)">分组</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="cmp-chart-head">
        <span>近 {{ days }} 日走势（归一化涨幅 %）</span>
      </div>
      <div ref="chartEl" class="cmp-chart"></div>

      <div class="holdings-bar">
        <button class="batch-btn" :disabled="!selected.length" @click="toggleHoldings">
          {{ showHoldings ? '收起持仓对比' : '对比前十大持仓' }}
        </button>
      </div>

      <div v-if="showHoldings" class="holdings-block">
        <div v-if="holdingsLoading" class="result-hint">加载持仓中…</div>
        <div v-else-if="!holdingsEtfs.length" class="result-hint">暂无可对比的持仓数据</div>
        <div v-else class="cmp-table-wrap">
          <table class="cmp-table holdings-table">
            <thead>
              <tr>
                <th class="th-label">持仓序号</th>
                <th v-for="c in holdingsEtfs" :key="c">
                  {{ nameOfCode(c) }}<span class="th-code">{{ c }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="i in HOLDINGS_TOP" :key="i">
                <td class="td-label">{{ i }}</td>
                <td v-for="c in holdingsEtfs" :key="c">
                  <template v-if="holdings[c][i - 1]">
                    <span class="h-name">{{ holdings[c][i - 1].name }}</span>
                    <span class="h-code">{{ holdings[c][i - 1].code }}</span>
                    <span class="h-ratio" :class="hRatioClass(holdings[c][i - 1])">{{ holdings[c][i - 1].ratio }}%</span>
                  </template>
                  <span v-else class="h-empty">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <StockGroupModal
      :open="groupOpen"
      :code="groupTarget?.code || ''"
      :name="groupTarget?.name || ''"
      @close="groupOpen = false"
      @saved="groupOpen = false; onGroupSaved()"
    />
  </div>
</template>

<script setup>
/**
 * ETF 选择对比：关键字/板块搜索 → 多选 → 横向指标对比 + 归一化走势叠加图
 * @author ygw
 */
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import ToolNavTabs from '../components/ToolNavTabs.vue'
import UiInput from '../components/ui/UiInput.vue'
import UiIcon from '../components/ui/UiIcon.vue'
import StockGroupModal from '../components/StockGroupModal.vue'
import PoolExpandRow from '../components/PoolExpandRow.vue'
import { api } from '../api.js'
import { fmtPrice, fmtPct, fmtAmount, fmtNum, pctClass, themeColors } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { useTableSort } from '../composables/useTableSort.js'
import { isWatched, toggleWatch } from '../composables/useWatchlist.js'
import { showToast } from '../composables/useToast.js'
import { openStock } from '../composables/useStockMeta.js'
import { captureElement } from '../composables/useScreenshot.js'

const MAX_PICK = 50
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

const SELECTED_KEY = 'niulai_etf_compare_selected'
const VIEW_KEY = 'niulai_etf_compare_view'
const DAYS_KEY = 'niulai_etf_compare_days'
const SHOW_HOLDINGS_KEY = 'niulai_etf_compare_show_holdings'

function loadStored(key, fallback) {
  try {
    const v = localStorage.getItem(key)
    return v == null ? fallback : JSON.parse(v)
  } catch (e) {
    return fallback
  }
}

function saveStored(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (e) { /* ignore */ }
}

const storedDays = loadStored(DAYS_KEY, 30)
const storedSelected = loadStored(SELECTED_KEY, [])
const selected = ref(Array.isArray(storedSelected) ? storedSelected : [])
const view = ref(loadStored(VIEW_KEY, 'row') === 'col' ? 'col' : 'row')
const days = ref(LOOKBACKS.includes(storedDays) ? storedDays : 30)

watch([selected, view, days], () => {
  saveStored(SELECTED_KEY, selected.value)
  saveStored(VIEW_KEY, view.value)
  saveStored(DAYS_KEY, days.value)
})
watch(showHoldings, v => saveStored(SHOW_HOLDINGS_KEY, v))
watch(selected, () => {
  if (showHoldings.value) loadHoldings()
})

const quotes = ref([])
const sort = useTableSort(quotes, 'etf_compare')
const trends = ref({})
const dates = ref([])
const updated = ref('')
const chartEl = ref(null)
const compareCardRef = ref(null)
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

const selectableCount = computed(() => results.value.filter(r => !selected.value.includes(r.code)).length)

function selectAll() {
  const room = MAX_PICK - selected.value.length
  if (room <= 0) return
  let n = 0
  for (const r of results.value) {
    if (n >= room) break
    if (!selected.value.includes(r.code)) {
      selected.value.push(r.code)
      n++
    }
  }
  load()
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
      holdings.value = {}
      showHoldings.value = false
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

function clearAll() {
  selected.value = []
  quotes.value = []
  trends.value = {}
  dates.value = []
  holdings.value = {}
  showHoldings.value = false
}

function setDays(d) {
  days.value = d
  load()
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
    await nextTick()
    renderChart()
  } catch (e) {
    /* 静默：下次轮询重试 */
  }
}

function openDetail(q) {
  if (q && q.code) openStock({ code: q.code, name: q.name })
}

async function screenshotCompare() {
  if (!compareCardRef.value) return
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  await captureElement(compareCardRef.value, `etf_compare_${ts}.png`, { withFrame: false })
}

const expandedCode = ref('')

function toggleExpand(code) {
  expandedCode.value = expandedCode.value === code ? '' : code
}

const groupOpen = ref(false)
const groupTarget = ref(null)

function openGroup(r) {
  groupTarget.value = { code: r.code, name: r.name || r.code }
  groupOpen.value = true
}

function onGroupSaved() {
  showToast('分组已保存', 'success')
}

async function toggleWatchFn(r) {
  try {
    const was = isWatched(r.code)
    await toggleWatch(r.code)
    showToast(`${was ? '已移出' : '已加入'}自选：${r.name || r.code}`, 'success')
  } catch (e) {
    showToast('操作失败：' + e.message, 'error')
  }
}

const HOLDINGS_TOP = 10
const holdings = ref({})
const holdingsLoading = ref(false)
const showHoldings = ref(loadStored(SHOW_HOLDINGS_KEY, false))

const holdingsEtfs = computed(() => Object.keys(holdings.value))

function nameOfCode(code) {
  const q = quotes.value.find(x => x.code === code)
  return q ? q.name : code
}

function hRatioClass(item) {
  const r = item && item.ratio
  if (r == null) return 'flat'
  return r >= 10 ? 'up' : r >= 5 ? 'accent' : 'flat'
}

async function loadHoldings() {
  if (!selected.value.length) return
  holdingsLoading.value = true
  const list = selected.value.slice(0, 12)
  const res = await Promise.allSettled(list.map(async (c) => {
    const r = await api.holdings(c)
    return { code: c, items: (r && r.items) || [] }
  }))
  const map = {}
  for (const r of res) {
    if (r.status === 'fulfilled') map[r.value.code] = r.value.items
  }
  holdings.value = map
  holdingsLoading.value = false
}

function toggleHoldings() {
  showHoldings.value = !showHoldings.value
  if (showHoldings.value) loadHoldings()
}

const PALETTE = ['#4c9aff', '#f04444', '#2fbf8f', '#e3b341', '#9a7bff', '#4fd6be', '#ff9d5c', '#5aa2ff', '#f27ab5', '#7bd44c']

function renderChart() {
  if (!chartEl.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const entries = Object.entries(trends.value)
  if (!entries.length || !dates.value.length) {
    chart.setOption({
      animation: false,
      grid: { left: 52, right: 20, top: 20, bottom: 28 },
      tooltip: { show: false },
      xAxis: { type: 'category', data: [], axisLine: { lineStyle: { color: 'rgba(128,128,128,0.2)' } }, axisLabel: { show: false }, axisTick: { show: false } },
      yAxis: { type: 'value', splitLine: { show: false }, axisLabel: { show: false } },
      series: [],
      graphic: [{
        type: 'text',
        left: 'center',
        top: 'middle',
        style: { text: '暂无走势数据', fill: '#8b9099', fontSize: 12 },
      }],
    }, true)
    return
  }
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
    graphic: [],
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
  if (selected.value.length) load()
  if (showHoldings.value) loadHoldings()
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

.card-title { display: flex; align-items: center; justify-content: space-between; font-size: 14px; font-weight: 600; margin-bottom: 12px; }
.ct-left { display: flex; align-items: center; }
.compare-sub { font-size: 11px; color: var(--text-dim); font-weight: 400; margin-left: 6px; }
.shot-btn {
  width: 26px; height: 26px; border: 1px solid var(--border); border-radius: 6px;
  background: transparent; color: var(--text-dim); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.shot-btn:hover { border-color: var(--accent); color: var(--accent); }

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

.result-hint { padding: 14px 4px; font-size: 12px; color: var(--text-dim); }
.dim-hint { line-height: 1.8; }

.result-head {
  display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 12px;
}
.result-count { color: var(--text-dim); }
.select-all-btn {
  height: 24px; padding: 0 12px; border-radius: 12px; font-size: 12px; cursor: pointer;
  background: var(--accent-bg); border: 1px solid var(--accent); color: var(--accent);
  transition: all 0.15s;
}
.select-all-btn:hover { background: var(--accent); color: #fff; }
.select-all-btn:disabled { opacity: 0.4; cursor: not-allowed; }

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

.chart-toolbar {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px; font-size: 12px;
}
.tool-label { color: var(--text-dim); }
.toolbar-sep { flex: 1; }
.batch-btn {
  height: 24px; padding: 0 12px; border-radius: 12px; font-size: 12px; cursor: pointer;
  background: var(--accent-bg); border: 1px solid var(--accent); color: var(--accent);
  transition: all 0.15s;
}
.batch-btn:hover { background: var(--accent); color: #fff; }
.batch-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.batch-btn.ghost { background: transparent; }
.updated { margin-left: auto; color: var(--text-dim); font-size: 11px; font-variant-numeric: tabular-nums; }

.cmp-table-wrap { overflow-x: auto; margin-bottom: 18px; }
.cmp-table {
  width: 100%; border-collapse: collapse; font-size: 13px; min-width: 560px;
}
.cmp-table th {
  padding: 9px 12px; text-align: left; font-weight: 600; color: var(--text);
  background: var(--kv-bg); border-bottom: 1px solid var(--border); white-space: nowrap;
}
.th-sortable { cursor: pointer; user-select: none; }
.th-sortable:hover { color: var(--accent); }
.sort-arrow { color: var(--accent); font-size: 10px; }
.th-label { color: var(--text-dim) !important; width: 170px; }
.th-code { display: block; font-size: 11px; color: var(--text-dim); font-weight: 400; }
.cmp-table td {
  padding: 9px 12px; border-bottom: 1px solid var(--border); white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.cmp-row { cursor: pointer; transition: background 0.15s; }
.cmp-row:hover { background: var(--kv-bg); }
.row-expanded { background: var(--accent-bg) !important; }
.td-name { color: var(--text); font-weight: 600; }
.td-name-text { display: inline-block; max-width: 130px; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; white-space: nowrap; }
.th-op, .td-op { text-align: center; width: 130px; }
.td-op { white-space: nowrap; }
.td-label { color: var(--text-dim); font-size: 12px; }
.cmp-table-col { min-width: 480px; }
.cmp-table-col .th-label { width: 70px; }
.op-btn {
  height: 22px; padding: 0 10px; border-radius: 11px; font-size: 12px; cursor: pointer;
  background: transparent; border: 1px solid var(--border); color: var(--text);
  transition: all 0.15s; margin-right: 6px;
}
.op-btn:hover { border-color: var(--accent); color: var(--accent); }
.op-btn.watched { background: var(--accent-bg); border-color: var(--accent); color: var(--accent); }
.tabular.up { color: var(--up); }
.tabular.down { color: var(--down); }
.tabular.flat { color: var(--text); }

.cmp-chart-head { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; }
.cmp-chart { width: 100%; height: 380px; }

.holdings-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
.holdings-block { margin-top: 12px; }
.holdings-table td { text-align: left; }
.h-name { display: inline-block; max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: bottom; }
.h-code { display: block; font-size: 11px; color: var(--text-dim); }
.h-ratio { font-size: 11px; margin-left: 6px; font-variant-numeric: tabular-nums; }
.h-ratio.up { color: var(--up); }
.h-ratio.accent { color: var(--accent); }
.h-ratio.flat { color: var(--text-dim); }
.h-empty { color: var(--text-dim); }
</style>