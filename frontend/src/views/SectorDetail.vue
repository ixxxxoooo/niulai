<template>
  <div>
    <div class="stock-head">
      <BackButton label="返回板块" fallback="/sectors" />
      <span class="name">{{ sector ? sector.name : code }}</span>
      <span class="code">{{ code }}</span>
      <a class="source-link" :href="'https://data.eastmoney.com/bkzj/' + code + '.html'" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
      <span class="quote-time" v-if="sector">
        <span :class="pctClass(sector.change_pct)">{{ fmtPct(sector.change_pct) }}</span>
        · 成交 {{ fmtAmount(sector.amount) }}
      </span>
    </div>

    <div class="error-banner" v-if="error">{{ error }}</div>

    <!-- 板块概览 -->
    <div class="sentiment" v-if="sector">
      <div class="item">
        <div class="label">涨跌幅</div>
        <div class="value" :class="pctClass(sector.change_pct)">{{ fmtPct(sector.change_pct) }}</div>
      </div>
      <div class="item">
        <div class="label">成交额</div>
        <div class="value">{{ fmtAmount(sector.amount) }}</div>
      </div>
      <div class="item">
        <div class="label">主力净流入</div>
        <div class="value" :class="pctClass(sector.main_inflow)">{{ fmtAmount(sector.main_inflow) }}</div>
      </div>
      <div class="item">
        <div class="label">上涨 / 下跌</div>
        <div class="value"><span class="up">{{ sector.up_count ?? '-' }}</span> / <span class="down">{{ sector.down_count ?? '-' }}</span></div>
      </div>
      <div class="item">
        <div class="label">领涨股</div>
        <div class="value">
          <a class="leader-chip" @click="openFromSector({ code: sector.leader_code, name: sector.leader_name })">
            <span v-for="b in boardBadges({code:sector.leader_code,name:sector.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span>{{ sector.leader_name || '-' }} <span class="up">{{ sector.leader_pct != null ? fmtPct(sector.leader_pct) : '' }}</span>
          </a>
        </div>
      </div>
    </div>

    <!-- 板块强度 + 分时（开盘啦，容错：匹配不到或失败自动隐藏） -->
    <div class="card mt16" v-if="kplOk">
      <div class="card-title">
        <span>板块强度 · 开盘啦<span style="font-weight:400;color:var(--text-dim);font-size:12px" data-tip="开盘啦板块强度指标，数值越高代表该板块资金与连板情绪越强">强度 {{ kplStrength != null ? kplStrength : '—' }}</span></span>
      </div>
      <div ref="kplChartEl" style="width:100%;height:180px" v-if="kplTrend"></div>
      <div class="empty" v-else>板块分时暂不可用</div>
    </div>

    <!-- 成分股列表 -->
    <div class="card mt16">
      <div class="card-title">
        <span>板块成分股（{{ stocks.length }} 只 · 点击列名排序）</span>
      </div>
      <StockTable :rows="stocks" :columns="stockColumns" @row-click="openFromSector" />
    </div>
  </div>
</template>

<script setup>
// @author ygw
import { ref, watch, nextTick, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { api, briefColumns } from '../api.js'
import { fmtAmount, fmtPct, pctClass, boardBadges, themeColors } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock } from '../composables/useStockMeta.js'
import StockTable from '../components/StockTable.vue'
import BackButton from '../components/BackButton.vue'

const props = defineProps({ code: { type: String, default: '' } })
const code = ref(props.code || '')

const sector = ref(null)
const stocks = ref([])
const error = ref('')

const stockColumns = briefColumns.filter(c =>
  ['name', 'code', 'price', 'change_pct', 'zhangsu', 'amount', 'turnover', 'volume_ratio', 'main_inflow'].includes(c.key),
)

/**
 * 从板块成分进入个股：在成分内左右切换，返回本板块页。
 * @param {object} row
 */
function openFromSector(row) {
  if (!row?.code) return
  openStock(row, {
    list: stocks.value,
    origin: '/sector/' + code.value,
    originLabel: '返回板块',
  })
}

async function load() {
  if (!code.value) return
  try {
    const d = await api.sectorDetail(code.value, 100)
    sector.value = d.sector
    stocks.value = d.stocks
    error.value = ''
    loadKpl()
  } catch (e) {
    error.value = '板块数据加载失败：' + e.message
  }
}

// ── 开盘啦：板块强度 + 分时（容错，匹配不到申万代码即隐藏） ──
const kplOk = ref(false)
const kplStrength = ref(null)
const kplTrend = ref(null)
const kplChartEl = ref(null)
let kplChart = null

async function loadKpl() {
  kplOk.value = false
  kplStrength.value = null
  kplTrend.value = null
  const name = sector.value?.name
  if (!name) return
  try {
    const codes = await api.kaipanlaSectorCodes()
    const items = codes.items || {}
    let sc = items[name]
    if (!sc) {
      const hit = Object.keys(items).find(k => k.includes(name) || name.includes(k))
      sc = hit && items[hit]
    }
    if (!sc) return
    const [str, tr] = await Promise.all([
      api.kaipanlaSectorStrength(sc).catch(() => null),
      api.kaipanlaSectorIntraday(sc).catch(() => null),
    ])
    if (str && str.strength != null) kplStrength.value = str.strength
    if (tr && tr.points && tr.points.length) kplTrend.value = tr
    if (kplStrength.value != null || kplTrend.value) {
      kplOk.value = true
      await nextTick()
      renderKplTrend()
    }
  } catch (e) { /* 容错：隐藏区块 */ }
}

function renderKplTrend() {
  const t = kplTrend.value
  if (!t || !kplChartEl.value) return
  if (!kplChart) kplChart = echarts.init(kplChartEl.value)
  const tc = themeColors()
  const times = t.points.map(p => p.time)
  const prices = t.points.map(p => p.price)
  const pre = t.preclose || prices[0]
  const last = prices[prices.length - 1]
  const color = last >= pre ? tc.up : tc.down
  kplChart.setOption({
    animation: false,
    grid: { left: 8, right: 8, top: 10, bottom: 8 },
    xAxis: { type: 'category', data: times, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { show: false } },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'cross' },
      formatter: (ps) => {
        const i = ps[0].dataIndex
        const chg = ((prices[i] - pre) / pre * 100)
        const c = chg >= 0 ? tc.up : tc.down
        return `${times[i]}<br/>点位 <b style="color:${c}">${prices[i].toFixed(2)}</b><br/>涨跌 <span style="color:${c}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</span>`
      },
    },
    series: [{
      type: 'line', data: prices, showSymbol: false,
      lineStyle: { width: 1.6, color },
      areaStyle: { color: color + '22' },
      markLine: { silent: true, symbol: 'none', data: [{ yAxis: pre }], lineStyle: { color: tc.split, width: 1 }, label: { show: false } },
    }],
  }, true)
}

function onResize() { kplChart && kplChart.resize() }

watch(() => props.code, (n) => {
  if (n && n !== code.value) { code.value = n; load() }
})

usePolling(load, 5000)

window.addEventListener('resize', onResize)
onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  kplChart && kplChart.dispose()
  kplChart = null
})
</script>

<style scoped>
</style>
