<template>
  <div>
    <div class="page-title">板块分析</div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <div class="tabs">
      <div class="tab" :class="{ active: stype === 'industry' }" @click="switchType('industry')">行业板块（申万）</div>
      <div class="tab" :class="{ active: stype === 'concept' }" @click="switchType('concept')">概念板块</div>
      <span style="color: var(--text-dim); font-size: 12px; margin-left: auto">
        {{ stype === 'industry' ? '申万 2021 版 · 一级/二级/三级下钻 · 点击进入成分股' : '点击列名排序 · 点击板块进入成分股' }}
      </span>
      <a class="source-link" :href="stype === 'industry' ? 'https://www.swsresearch.com/' : 'https://data.eastmoney.com/bkzj/gn.html'" target="_blank" rel="noopener">数据来源↗</a>
    </div>

    <!-- 申万行业：下钻三级 -->
    <div class="card" v-if="stype === 'industry'">
      <div class="card-title">
        <span class="breadcrumb">
          <span class="crumb" @click="swGoHome">申万行业</span>
          <template v-for="(b, i) in swBread" :key="i">
            <span class="crumb-sep">/</span>
            <span class="crumb" @click="swUp(b.level)">{{ b.name }}</span>
          </template>
          <span v-if="swStocksView" class="crumb-sep">/</span>
          <span v-if="swStocksView" class="crumb cur">成分股（{{ swStocksList.length }}）</span>
        </span>
        <span class="sw-status" v-if="swSyncing">申万行业同步中（首次约 1 分钟）…</span>
        <button class="btn btn-sm" v-if="swSyncable" @click="swDoSync">{{ swSyncing ? '同步中…' : '重新同步' }}</button>
      </div>

      <!-- 成分股视图 -->
      <template v-if="swStocksView">
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr><th>代码</th><th>名称</th><th>东财行业</th><th>概念</th></tr></thead>
            <tbody>
              <tr v-for="s in swStocksList" :key="s.code" @click="openStock(s.code)">
                <td>{{ s.code }}</td>
                <td class="stock-name">{{ s.name }}</td>
                <td>{{ s.industry || '—' }}</td>
                <td class="sw-concepts">{{ s.concepts || '—' }}</td>
              </tr>
              <tr v-if="!swStocksList.length"><td colspan="4" class="empty">暂无成分股</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 行业列表视图 -->
      <template v-else>
        <div class="sw-grid">
          <div v-for="s in swList" :key="s.code" class="sw-item" @click="swDrill(s)">
            <div class="sw-name">{{ s.name }}</div>
            <div class="sw-sub">
              <span>{{ s.stock_count }} 只</span>
              <span class="sw-code">{{ s.code.replace('.SI', '') }}</span>
            </div>
          </div>
          <div v-if="!swList.length" class="empty" style="padding:24px">
            暂无行业数据<template v-if="!swSyncing"><br /><button class="btn btn-sm" @click="swDoSync">立即同步申万行业</button></template>
          </div>
        </div>
      </template>
    </div>

    <!-- 东财概念板块 -->
    <div class="card" v-else>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>板块</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'change_pct' }" @click="ts.toggleSort('change_pct')">涨跌幅</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'amount' }" @click="ts.toggleSort('amount')">成交额</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'main_inflow' }" @click="ts.toggleSort('main_inflow')">主力净流入</th>
              <th>涨/跌家数</th><th>领涨股</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in ts.sorted" :key="s.code" @click="openSector(s.code)">
              <td class="stock-name">{{ s.name }} <span style="color: var(--text-dim); font-weight: 400; font-size: 12px">{{ s.code }}</span></td>
              <td><span class="pct-badge" :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</span></td>
              <td>{{ fmtAmount(s.amount) }}</td>
              <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
              <td><span class="up">{{ s.up_count ?? '-' }}</span> / <span class="down">{{ s.down_count ?? '-' }}</span></td>
              <td>
                <a v-if="s.leader_code" class="leader-chip" @click.stop="openStock(s.leader_code)">
                  <span v-for="b in boardBadges({code:s.leader_code,name:s.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span>{{ s.leader_name || '-' }} <span class="up">{{ s.leader_pct != null ? fmtPct(s.leader_pct) : '' }}</span>
                </a>
              </td>
            </tr>
            <tr v-if="!ts.sorted.length"><td colspan="6" class="empty">暂无数据</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPct, pctClass, boardBadges } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { useTableSort } from '../composables/useTableSort.js'
import { openStock as goStock } from '../composables/useStockMeta.js'

const stype = ref('industry')
const sort = ref('change_pct')
const sectors = ref([])
const error = ref('')
const ts = useTableSort(sectors)

// ── 申万行业：一级 → 二级 → 三级 → 成分股 ──
const swList = ref([])
const swBread = ref([])          // [{level, name, code}] 已进入的上级（不含当前级）
const swLevel = ref(1)
const swParent = ref('')         // 当前列表的父级 code
const swStocksView = ref(false)
const swStocksList = ref([])
const swSyncing = ref(false)
let swPollTimer = null

function switchType(t) {
  stype.value = t
  if (t === 'industry') loadSw()
  else load()
}

function swGoHome() {
  swLevel.value = 1
  swParent.value = ''
  swBread.value = []
  swStocksView.value = false
  loadSw()
}

function swUp(level) {
  // 返回面包屑中 level 对应层级（移除其后所有）
  const idx = swBread.value.findIndex(b => b.level === level)
  const keep = idx >= 0 ? swBread.value.slice(0, idx) : []
  swBread.value = keep
  const prev = keep[keep.length - 1]
  swLevel.value = prev ? prev.level + 1 : 1
  swParent.value = prev ? prev.code : ''
  swStocksView.value = false
  loadSw()
}

async function swDrill(s) {
  if (swStocksView.value) return
  if (swLevel.value < 3) {
    swBread.value.push({ level: swLevel.value, name: s.name, code: s.code })
    swLevel.value += 1
    swParent.value = s.code
    loadSw()
  } else {
    swStocksView.value = true
    swStocksList.value = []
    try {
      const d = await api.swStocks(s.code)
      swStocksList.value = d.items || []
    } catch (e) {
      swStocksList.value = []
    }
  }
}

async function loadSw() {
  try {
    const d = await api.swIndustries(swLevel.value, swParent.value)
    swList.value = d.items || []
    error.value = ''
  } catch (e) {
    error.value = '申万行业数据加载失败：' + e.message
  }
}

async function swDoSync() {
  swSyncing.value = true
  try {
    await api.swSync()
    startSwPoll()
  } catch (e) { swSyncing.value = false }
}

async function startSwPoll() {
  clearInterval(swPollTimer)
  swPollTimer = setInterval(async () => {
    try {
      const st = await api.swSyncStatus()
      swSyncing.value = st.running
      if (!st.running) {
        clearInterval(swPollTimer)
        swPollTimer = null
        loadSw()
      }
    } catch (e) { /* ignore */ }
  }, 2000)
}

const swSyncable = true

function openSector(code) { navigate('/sector/' + code) }
function openStock(code) {
  if (!code) return
  goStock({ code }, { origin: '/sectors', originLabel: '返回板块' })
}

async function load() {
  try {
    sectors.value = await api.sectors(stype.value, sort.value, 100)
    error.value = ''
  } catch (e) {
    error.value = '板块数据加载失败：' + e.message
  }
}

usePolling(load, 5000)
onUnmounted(() => clearInterval(swPollTimer))
</script>

<style scoped>
.breadcrumb { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; font-size: 13px; font-weight: 400; }
.crumb { cursor: pointer; color: var(--text-dim); }
.crumb:hover { color: var(--accent); text-decoration: underline; }
.crumb.cur { color: var(--text); font-weight: 600; }
.crumb-sep { color: var(--border); }
.sw-status { font-size: 12px; color: var(--accent); }
.sw-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.sw-item {
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px;
  cursor: pointer; background: var(--bg-card); transition: border-color .15s, background .15s;
}
.sw-item:hover { border-color: var(--accent); background: var(--bg-hover); }
.sw-name { font-weight: 600; font-size: 13px; color: var(--accent); }
.sw-sub { display: flex; justify-content: space-between; margin-top: 4px; font-size: 11px; color: var(--text-dim); }
.sw-code { color: var(--border); }
.sw-concepts { max-width: 260px; color: var(--text-dim); font-size: 12px; }
</style>