<template>
  <div class="page screener-page">
    <div class="page-title"><h2>盘后选股</h2></div>

    <!-- 日K数据状态 -->
    <div class="card">
      <div class="card-title">日K线数据</div>
      <div class="setting-row">
        <span class="setting-label">覆盖股票数：{{ syncSt.stock_count || 0 }}</span>
        <span class="setting-label" style="margin-left:18px">最新日期：{{ syncSt.latest_date || '—' }}</span>
      </div>
      <div class="setting-row">
        <UiButton variant="subtle" :disabled="syncing" @click="startSync">
          {{ syncing ? '同步中…' : '同步日K' }}
        </UiButton>
        <span style="margin-left:12px;font-size:12px;color:var(--text-dim)">
          首次约需 50~80 分钟，增量很快
        </span>
      </div>
      <div class="setting-row" v-if="syncing || syncMsg">
        <div class="progress-wrap">
          <div class="progress"><i :style="{ width: syncPct + '%' }"></i></div>
          <div class="progress-msg">{{ syncMsg || '准备中…' }} · {{ syncPct }}%</div>
        </div>
      </div>
    </div>

    <!-- 选股规则 -->
    <div class="card">
      <div class="card-title">选股规则</div>
      <div class="rule-checks">
        <label v-for="r in ruleList" :key="r.id" class="rule-item">
          <UiCheckbox v-model="selectedRules" :value="r.id" />
          <b>{{ r.name }}</b>
          <span class="rule-desc">{{ r.desc }}</span>
        </label>
      </div>
      <div class="setting-row" style="margin-top:12px">
        <span class="setting-label">范围</span>
        <label style="margin-right:16px">
          <UiRadio v-model="scope" value="all" /> 全 A 股
        </label>
        <label>
          <UiRadio v-model="scope" value="watchlist" /> 仅自选
        </label>
      </div>
      <div class="setting-row">
        <label>
          <UiCheckbox v-model="notifyFeishu" /> 完成后推飞书
        </label>
      </div>
      <div class="setting-row" style="margin-top:8px">
        <UiButton variant="primary" :disabled="running || !selectedRules.length || !syncSt.stock_count" @click="runScreen">
          {{ running ? '扫描中…' : '开始选股' }}
        </UiButton>
      </div>
    </div>

    <!-- 结果展示 -->
    <div class="card" v-if="result">
      <div class="card-title">
        选股结果 · 扫描 {{ result.scanned }} 只 · 命中 {{ result.hit_count }} 只
        <span style="font-weight:400;font-size:12px;color:var(--text-dim);margin-left:8px">
          {{ result.elapsed_ms }}ms
        </span>
      </div>
      <div class="result-tabs">
        <button
          v-for="r in resultRules" :key="r"
          :class="['tab-btn', { active: activeTab === r }]"
          @click="activeTab = r"
        >
          {{ ruleNameMap[r] || r }}（{{ (result.hits[r] || []).length }}）
        </button>
      </div>
      <div class="result-table" v-if="activeHits.length">
        <table>
          <thead>
            <tr>
              <th>代码</th><th>名称</th><th>收盘</th><th>涨跌幅</th><th>信号</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in activeHits" :key="h.code" @click="openStockPage(h.code)" class="clickable">
              <td>{{ h.code }}</td>
              <td>{{ h.name }}</td>
              <td>{{ h.close }}</td>
              <td :class="h.change_pct > 0 ? 'up' : h.change_pct < 0 ? 'down' : ''">
                {{ h.change_pct != null ? (h.change_pct > 0 ? '+' : '') + h.change_pct + '%' : '' }}
              </td>
              <td class="detail-col">{{ h.detail }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-hint">该规则无命中</div>
    </div>

    <!-- 历史任务 -->
    <details class="card" v-if="runs.length">
      <summary class="card-title" style="cursor:pointer">历史任务（{{ runs.length }}）</summary>
      <table class="history-table">
        <thead>
          <tr><th>时间</th><th>规则</th><th>范围</th><th>命中</th><th>状态</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="r in runs" :key="r.id">
            <td>{{ (r.started_at || '').slice(5) }}</td>
            <td>{{ formatRules(r.rules) }}</td>
            <td>{{ r.scope === 'watchlist' ? '自选' : '全A' }}</td>
            <td>{{ r.hit_count }}</td>
            <td>{{ r.status }}</td>
            <td><a @click.prevent="loadRun(r.id)" style="cursor:pointer;color:var(--accent)">查看</a></td>
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

const syncSt = ref({})
const syncing = ref(false)
const syncPct = ref(0)
const syncMsg = ref('')
let syncTimer = null

const ruleList = ref([])
const selectedRules = ref(['breakout', 'golden_cross', 'volume_surge'])
const scope = ref('all')
const notifyFeishu = ref(false)
const running = ref(false)
const result = ref(null)
const activeTab = ref('')
const runs = ref([])

const ruleNameMap = { breakout: '突破', golden_cross: '金叉', volume_surge: '放量' }

const resultRules = computed(() => result.value ? Object.keys(result.value.hits) : [])
const activeHits = computed(() => result.value && activeTab.value ? (result.value.hits[activeTab.value] || []) : [])

function openStockPage(code) { navigate(`/stock/${code}`) }

function formatRules(json) {
  try {
    return JSON.parse(json).map(r => ruleNameMap[r] || r).join('/')
  } catch { return json }
}

async function loadStatus() {
  try { syncSt.value = await api.screenerSyncStatus() } catch {}
}

async function startSync() {
  syncing.value = true
  syncPct.value = 0
  syncMsg.value = '启动中…'
  try { await api.screenerSyncBars(120, scope.value) } catch {}
  syncTimer = setInterval(pollSync, 2000)
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
  } catch (e) {
    alert('选股失败：' + (e.message || e))
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
.screener-page { max-width: 900px; margin: 0 auto; }
.rule-checks { display: flex; flex-direction: column; gap: 8px; }
.rule-item { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
.rule-item input { margin: 0; }
.rule-desc { font-size: 12px; color: var(--text-dim); }
.result-tabs { display: flex; gap: 4px; margin-bottom: 10px; }
.tab-btn { padding: 4px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text-dim); cursor: pointer; font-size: 13px; transition: all 0.15s; }
.tab-btn:hover { color: var(--text); background: var(--bg-hover); }
.tab-btn.active { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600; }
.result-table { overflow-x: auto; }
.result-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.result-table th { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); color: var(--text-dim); font-weight: 500; }
.result-table td { padding: 5px 8px; border-bottom: 1px solid var(--border); font-variant-numeric: tabular-nums; }
.clickable { cursor: pointer; }
.clickable:hover { background: var(--bg-hover); }
.detail-col { font-size: 12px; color: var(--text-dim); max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty-hint { padding: 20px; text-align: center; color: var(--text-dim); font-size: 13px; }
.history-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
.history-table th, .history-table td { padding: 4px 8px; border-bottom: 1px solid var(--border); text-align: left; font-variant-numeric: tabular-nums; }
.up { color: var(--up); }
.down { color: var(--down); }
.progress-wrap { flex: 1; }
.progress { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.progress i { display: block; height: 100%; background: var(--accent); border-radius: 3px; transition: width .3s; }
.progress-msg { font-size: 12px; color: var(--text-dim); margin-top: 3px; }
.btn-primary { background: var(--accent); color: #fff; border: none; border-radius: var(--radius-sm); }

</style>
