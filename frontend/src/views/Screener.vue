<template>
  <div class="page screener-page">
    <div class="page-title"><h2>盘后量化选股</h2></div>

    <!-- 日K数据状态与极速同步 -->
    <div class="card">
      <div class="card-title" style="display:flex;align-items:center;gap:8px">
        日K线数据底座
        <span class="auto-badge" title="交易日 15:30 自动执行全市场打包归档">
          ⚡ 每日 15:30 自动全市场极速归档
        </span>
      </div>
      <div class="setting-row">
        <span class="setting-label">覆盖股票：<b>{{ syncSt.stock_count || 0 }}</b> 只</span>
        <span class="setting-label" style="margin-left:18px">最新数据日期：<b>{{ syncSt.latest_date || '—' }}</b></span>
        <span class="setting-label" style="margin-left:18px" v-if="syncSt.total_bars">
          总K线条数：<b>{{ syncSt.total_bars }}</b> 条
        </span>
      </div>
      <div class="setting-row" style="gap:10px;flex-wrap:wrap">
        <UiButton variant="primary" :disabled="syncing" @click="startSyncToday">
          {{ syncing && syncMode === 'today_bulk' ? '极速同步中…' : '⚡ 极速同步今日日K（1.5秒）' }}
        </UiButton>
        <UiButton variant="subtle" :disabled="syncing" @click="startSyncHistory">
          {{ syncing && syncMode === 'history' ? '历史同步中…' : '同步历史K线（前120日）' }}
        </UiButton>
      </div>
      <div class="setting-row" v-if="syncing || syncMsg">
        <div class="progress-wrap">
          <div class="progress"><i :style="{ width: syncPct + '%' }"></i></div>
          <div class="progress-msg">{{ syncMsg || '准备中…' }} · {{ syncPct }}%</div>
        </div>
      </div>
    </div>

    <!-- 选股规则配置 -->
    <div class="card">
      <div class="card-title">选股策略模型</div>
      <div class="rule-checks">
        <label v-for="r in ruleList" :key="r.id" class="rule-item">
          <UiCheckbox v-model="selectedRules" :value="r.id" />
          <b class="rule-name">{{ r.name }}</b>
          <span class="rule-desc">{{ r.desc }}</span>
        </label>
      </div>
      <div class="setting-row" style="margin-top:14px">
        <span class="setting-label">扫描股票池：</span>
        <label style="margin-right:16px;cursor:pointer">
          <UiRadio v-model="scope" value="all" /> 全 A 股（{{ syncSt.stock_count || 5400 }}只）
        </label>
        <label style="cursor:pointer">
          <UiRadio v-model="scope" value="watchlist" /> 仅我的自选股
        </label>
      </div>
      <div class="setting-row">
        <label style="cursor:pointer">
          <UiCheckbox v-model="notifyFeishu" /> 扫描完成后推送到飞书群
        </label>
      </div>
      <div class="setting-row" style="margin-top:10px">
        <UiButton variant="primary" :disabled="running || !selectedRules.length || !syncSt.stock_count" @click="runScreen">
          {{ running ? '量化模型极速扫描中…' : '🚀 开始量化选股' }}
        </UiButton>
      </div>
    </div>

    <!-- 选股结果展示 -->
    <div class="card" v-if="result">
      <div class="card-title">
        选股结果 · 扫描 {{ result.scanned }} 只 · 命中 {{ result.hit_count }} 只
        <span style="font-weight:400;font-size:12px;color:var(--text-dim);margin-left:8px">
          耗时 {{ result.elapsed_ms }}ms
        </span>
      </div>
      <div class="result-tabs">
        <button
          v-for="r in resultRules" :key="r"
          :class="['tab-btn', { active: activeTab === r }]"
          @click="activeTab = r"
        >
          {{ getRuleName(r) }}（{{ (result.hits[r] || []).length }}）
        </button>
      </div>
      <div class="result-table" v-if="activeHits.length">
        <table>
          <thead>
            <tr>
              <th>代码</th><th>名称</th><th>最新收盘</th><th>涨跌幅</th><th>命中信号与技术形态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in activeHits" :key="h.code" @click="openStockPage(h.code)" class="clickable">
              <td style="font-weight:600">{{ h.code }}</td>
              <td><a @click.stop="openStockPage(h.code)" style="color:var(--accent)">{{ h.name }}</a></td>
              <td>{{ h.close != null ? h.close.toFixed(2) : '—' }}</td>
              <td :class="h.change_pct > 0 ? 'up' : h.change_pct < 0 ? 'down' : 'flat'">
                {{ h.change_pct != null ? (h.change_pct > 0 ? '+' : '') + h.change_pct.toFixed(2) + '%' : '—' }}
              </td>
              <td class="detail-col">{{ h.detail }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-hint">当前策略在所选股票池中未命中符合条件的标的</div>
    </div>

    <!-- 历史任务记录 -->
    <details class="card" v-if="runs.length">
      <summary class="card-title" style="cursor:pointer">历史选股记录（{{ runs.length }}）</summary>
      <table class="history-table">
        <thead>
          <tr><th>执行时间</th><th>运行策略</th><th>股票池</th><th>命中数</th><th>状态</th><th>操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in runs" :key="r.id">
            <td>{{ (r.started_at || '').slice(5) }}</td>
            <td>{{ formatRules(r.rules) }}</td>
            <td>{{ r.scope === 'watchlist' ? '自选股' : '全A股' }}</td>
            <td style="font-weight:600">{{ r.hit_count }}</td>
            <td><span class="status-badge">{{ r.status }}</span></td>
            <td><a @click.prevent="loadRun(r.id)" style="cursor:pointer;color:var(--accent)">查看详情</a></td>
          </tr>
        </tbody>
      </table>
    </details>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { showToast } from '../composables/useToast.js'
import UiButton from '../components/ui/UiButton.vue'
import UiCheckbox from '../components/ui/UiCheckbox.vue'
import UiRadio from '../components/ui/UiRadio.vue'

const syncSt = ref({})
const syncing = ref(false)
const syncPct = ref(0)
const syncMsg = ref('')
const syncMode = ref('today_bulk')
let syncTimer = null

const ruleList = ref([])
const selectedRules = ref(['breakout', 'golden_cross', 'volume_surge', 'ma_bullish'])
const scope = ref('all')
const notifyFeishu = ref(false)
const running = ref(false)
const result = ref(null)
const activeTab = ref('')
const runs = ref([])

const ruleMap = computed(() => {
  const m = {}
  for (const r of ruleList.value) m[r.id] = r.name
  return m
})

function getRuleName(id) {
  return ruleMap.value[id] || id
}

const resultRules = computed(() => result.value ? Object.keys(result.value.hits) : [])
const activeHits = computed(() => result.value && activeTab.value ? (result.value.hits[activeTab.value] || []) : [])

function openStockPage(code) { navigate(`/stock/${code}`) }

function formatRules(json) {
  try {
    return JSON.parse(json).map(r => getRuleName(r)).join(' / ')
  } catch { return json }
}

async function loadStatus() {
  try { syncSt.value = await api.screenerSyncStatus() } catch {}
}

async function startSyncToday() {
  syncMode.value = 'today_bulk'
  syncing.value = true
  syncPct.value = 5
  syncMsg.value = '正在全市场批量打包拉取今日日K（约1.5秒）…'
  try {
    await api.screenerSyncBars(1, 'all', 'today_bulk')
  } catch (e) {
    showToast('启动同步失败：' + (e.message || e), 'error')
  }
  startPolling()
}

async function startSyncHistory() {
  syncMode.value = 'history'
  syncing.value = true
  syncPct.value = 2
  syncMsg.value = `正在同步 ${scope.value === 'watchlist' ? '自选股' : '全市场'} 历史K线…`
  try {
    await api.screenerSyncBars(120, scope.value, 'history')
  } catch (e) {
    showToast('启动同步失败：' + (e.message || e), 'error')
  }
  startPolling()
}

function startPolling() {
  clearInterval(syncTimer)
  syncTimer = setInterval(pollSync, 1000)
}

async function pollSync() {
  try {
    const st = await api.screenerSyncStatus()
    syncSt.value = st
    syncPct.value = st.percent || 0
    syncMsg.value = st.message || ''
    if (!st.running && syncPct.value >= 100) {
      clearInterval(syncTimer)
      syncTimer = null
      syncing.value = false
      showToast('日K线同步完成！')
      setTimeout(() => { if (!syncing.value) { syncMsg.value = ''; syncPct.value = 0 } }, 4000)
    }
  } catch {
    clearInterval(syncTimer)
    syncTimer = null
    syncing.value = false
  }
}

async function runScreen() {
  running.value = true
  result.value = null
  try {
    const res = await api.screenerRun(selectedRules.value, scope.value, notifyFeishu.value)
    result.value = res
    if (resultRules.value.length) activeTab.value = resultRules.value[0]
    loadRuns()
    showToast(`选股完成，命中 ${res.hit_count || 0} 只股票`)
  } catch (e) {
    showToast('选股失败：' + (e.message || e), 'error')
  } finally {
    running.value = false
  }
}

async function loadRuns() {
  try { runs.value = (await api.screenerRuns(20)).runs || [] } catch {}
}

async function loadRun(id) {
  try {
    const data = await api.screenerRunDetail(id)
    result.value = { ...data.run, hits: data.hits, scanned: '—', hit_count: data.run?.hit_count || 0, elapsed_ms: '—' }
    const keys = Object.keys(data.hits)
    if (keys.length) activeTab.value = keys[0]
  } catch {}
}

onMounted(async () => {
  loadStatus()
  try { ruleList.value = (await api.screenerRules()).rules || [] } catch {}
  loadRuns()
})
</script>

<style scoped>
.screener-page { max-width: 960px; margin: 0 auto; }
.auto-badge {
  font-size: 11px; font-weight: normal; color: var(--accent);
  background: var(--accent-bg); padding: 2px 8px; border-radius: var(--radius-sm);
  margin-left: auto;
}
.rule-checks { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 10px; margin-top: 4px; }
.rule-item {
  display: flex; align-items: flex-start; gap: 8px; font-size: 13px; cursor: pointer;
  background: var(--kv-bg); padding: 8px 12px; border-radius: var(--radius-md); border: 1px solid var(--border);
  transition: all .15s;
}
.rule-item:hover { border-color: var(--accent); background: var(--bg-hover); }
.rule-name { color: var(--text); white-space: nowrap; font-size: 13px; }
.rule-desc { font-size: 12px; color: var(--text-dim); line-height: 1.4; }
.result-tabs { display: flex; gap: 6px; margin-bottom: 12px; flex-wrap: wrap; }
.tab-btn {
  padding: 5px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--bg-card); color: var(--text-dim); cursor: pointer; font-size: 13px; transition: all 0.15s;
}
.tab-btn:hover { color: var(--text); background: var(--bg-hover); }
.tab-btn.active { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600; }
.result-table { overflow-x: auto; }
.result-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.result-table th { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border); color: var(--text-dim); font-weight: 500; }
.result-table td { padding: 7px 10px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
.clickable { cursor: pointer; }
.clickable:hover { background: var(--bg-hover); }
.detail-col { font-size: 12px; color: var(--accent); font-weight: 500; }
.empty-hint { padding: 24px; text-align: center; color: var(--text-dim); font-size: 13px; }
.history-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
.history-table th, .history-table td { padding: 6px 10px; border-bottom: 1px solid var(--border); text-align: left; font-variant-numeric: tabular-nums; }
.status-badge { font-size: 11px; padding: 1px 6px; background: var(--bg-hover); border-radius: 4px; color: var(--text-dim); }
.up { color: var(--up); font-weight: 600; }
.down { color: var(--down); font-weight: 600; }
.flat { color: var(--text-dim); }
.progress-wrap { flex: 1; }
.progress { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.progress i { display: block; height: 100%; background: var(--accent); border-radius: 3px; transition: width .3s; }
.progress-msg { font-size: 12px; color: var(--text-dim); margin-top: 3px; }
</style>
