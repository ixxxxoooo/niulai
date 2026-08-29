<template>
  <div>
    <div class="page-title">板块资金流向</div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <div class="tabs">
      <div class="tab" :class="{ active: type === 'industry' }" @click="type = 'industry'; load()">行业板块</div>
      <div class="tab" :class="{ active: type === 'concept' }" @click="type = 'concept'; load()">概念板块</div>
      <span style="color: var(--text-dim); font-size: 12px">
        当日主力资金净流入排行（红色=净流入，绿色=净流出；同类细分已折叠）
      </span>
      <a class="source-link" href="https://data.eastmoney.com/bkzj/hy.html" target="_blank" rel="noopener" style="margin-left:auto">行业资金 <UiIcon name="external" :size="11" /></a>
      <a class="source-link" href="https://data.eastmoney.com/bkzj/jlr.html" target="_blank" rel="noopener">净流入榜 <UiIcon name="external" :size="11" /></a>
      <a class="source-link" href="https://data.eastmoney.com/zjlx/detail.html" target="_blank" rel="noopener">个股资金 <UiIcon name="external" :size="11" /></a>
    </div>

    <div class="grid-2">
      <div class="card" ref="inCard">
        <div class="card-title">
          <span>净流入 TOP{{ chartTopN }}（流入最多最靠上）</span>
          <button class="btn-screenshot" @click="shotIn" title="截图"><UiIcon name="screenshot" :size="14" /></button>
        </div>
        <div ref="inEl" :style="{ width: '100%', height: chartHeight + 'px' }"></div>
      </div>
      <div class="card" ref="outCard">
        <div class="card-title">
          <span>净流出 TOP{{ chartTopN }}（共 {{ flowOutCount }} 个净流出）</span>
          <button class="btn-screenshot" @click="shotOut" title="截图"><UiIcon name="screenshot" :size="14" /></button>
        </div>
        <div ref="outEl" v-if="flowOutCount" :style="{ width: '100%', height: chartHeight + 'px' }"></div>
        <div v-else class="empty" style="padding: 60px 0">当前没有净流出板块</div>
      </div>
    </div>

    <div class="card mt16">
      <div class="card-title">板块资金明细（点击板块/领涨股）</div>
      <div class="table-wrap" style="max-height: 480px; overflow-y: auto;">
        <table class="data-table">
          <thead><tr><th>板块</th><th>涨跌幅</th><th>主力净流入</th><th>领涨股</th></tr></thead>
          <tbody>
            <tr v-for="s in flowRows" :key="s.code" @click="openSector(s.code)">
              <td class="stock-name">{{ s.name }}</td>
              <td :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</td>
              <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
              <td>
                <a v-if="s.leader_code" class="leader-chip" @click.stop="openStock(s.leader_code)">
                  {{ s.leader_name || '-' }}<span v-for="b in boardBadges({code:s.leader_code,name:s.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span> <span class="up">{{ s.leader_pct != null ? fmtPct(s.leader_pct) : '' }}</span>
                </a>
              </td>
            </tr>
            <tr v-if="!flowRows.length"><td colspan="4" class="empty">暂无数据</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api.js'
import { fmtAmount, fmtPct, pctClass, themeColors, boardBadges } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock as goStock } from '../composables/useStockMeta.js'
import { settingsState } from '../composables/useSettings.js'
import { captureElement } from '../composables/useScreenshot.js'

const type = ref('industry')
const flowRows = ref([])
const error = ref('')
const chartTopN = computed(() => settingsState.chartTopN || 20)
const chartHeight = computed(() => Math.max(400, chartTopN.value * 28))

const flowOutCount = computed(() => flowRows.value.filter(s => (s.main_inflow || 0) < 0).length)

const inEl = ref(null)
const outEl = ref(null)
const inCard = ref(null)
const outCard = ref(null)
let inChart = null
let outChart = null

/**
 * 截图净流入榜卡片
 * @author ygw
 */
async function shotIn() {
  await nextTick()
  inChart && inChart.resize()
  await captureElement(inCard.value, `板块净流入TOP${chartTopN.value}.png`)
}

/**
 * 截图净流出榜卡片
 */
async function shotOut() {
  await nextTick()
  outChart && outChart.resize()
  await captureElement(outCard.value, `板块净流出TOP${chartTopN.value}.png`)
}

function openSector(code) { navigate('/sector/' + code) }
function openStock(code) {
  if (!code) return
  goStock({ code }, { origin: '/sectors/flow', originLabel: '返回板块' })
}

/**
 * 同类细分折叠：同前缀（名称前 2 字，去掉 Ⅱ/Ⅲ/Ⅳ 层级后缀）只保留资金最大的代表，
 * 名称标注同类数量（如"通信(5)"）。仅展示层折叠，不合并计算，数据仍是原始板块。
 */
function foldSamePrefix(rows) {
  const map = new Map()
  for (const s of rows) {
    const key = s.name.replace(/[ⅡⅢⅣⅠ]+/g, '').slice(0, 2)
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(s)
  }
  const out = []
  for (const group of map.values()) {
    const rep = [...group].sort((a, b) => Math.abs(b.main_inflow || 0) - Math.abs(a.main_inflow || 0))[0]
    out.push({ ...rep, name: group.length > 1 ? `${rep.name}(${group.length})` : rep.name })
  }
  return out
}

async function load() {
  try {
    const rows = await api.sectorMoneyflow(type.value, 300)
    flowRows.value = rows
    error.value = ''
    await nextTick()
    renderFlowCharts(rows)
  } catch (e) {
    error.value = '板块数据加载失败：' + e.message
  }
}

function renderFlowCharts(raw) {
  if (!inChart && inEl.value) inChart = echarts.init(inEl.value)
  if (!outChart && outEl.value) outChart = echarts.init(outEl.value)
  if (!raw || !raw.length) return

  const tc = themeColors()
  const topN = settingsState.chartTopN || 20
  const folded = foldSamePrefix(raw)
  const sorted = [...folded].sort((a, b) => (b.main_inflow || 0) - (a.main_inflow || 0))
  const inflow = sorted.filter(s => (s.main_inflow || 0) >= 0).slice(0, topN).slice().reverse()
  const outflow = sorted.filter(s => (s.main_inflow || 0) < 0).slice(-topN)

  const mkOption = (items, color, isOutflow = false) => ({
    animation: false,
    grid: { left: 110, right: 80, top: 10, bottom: 20 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps) => {
        const s = items[ps[0].dataIndex]
        return `${s.name}<br/>主力净流入 <b>${fmtAmount(s.main_inflow)}</b><br/>涨跌幅 ${fmtPct(s.change_pct)}`
      },
    },
    xAxis: {
      type: 'value',
      axisLabel: { color: tc.axis, fontSize: 10, formatter: (v) => fmtAmount(isOutflow ? -v : v) },
      splitLine: { lineStyle: { color: tc.split } },
    },
    yAxis: { type: 'category', data: items.map(s => s.name), axisLabel: { color: tc.axis, fontSize: 11 }, axisLine: { lineStyle: { color: tc.split } } },
    series: [{
      type: 'bar', barWidth: '62%',
      data: items.map(s => ({
        value: isOutflow ? Math.abs(s.main_inflow) : s.main_inflow,
        itemStyle: { color, borderRadius: [0, 4, 4, 0] },
      })),
      label: { show: true, position: 'right', color: tc.axis, fontSize: 10, formatter: (p) => fmtAmount(isOutflow ? -p.value : p.value) },
    }],
  })

  if (inChart) inChart.setOption(mkOption(inflow, tc.up, false), true)
  if (outChart) outChart.setOption(mkOption(outflow, tc.down, true), true)
}

function onResize() { inChart && inChart.resize(); outChart && outChart.resize() }
function onThemeChange() { renderFlowCharts(flowRows.value) }

const poll = usePolling(load, 5000)

onMounted(async () => {
  await nextTick()
  if (inEl.value) inChart = echarts.init(inEl.value)
  window.addEventListener('resize', onResize)
  window.addEventListener('theme-change', onThemeChange)
})
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('theme-change', onThemeChange)
  inChart && inChart.dispose()
  outChart && outChart.dispose()
})
</script>
