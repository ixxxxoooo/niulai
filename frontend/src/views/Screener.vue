<template>
  <div class="page screener-page">
    <div class="page-title">
      <h2>盘后量化选股</h2>
      <span class="auto-badge" title="交易日 15:30 自动执行全市场打包归档">
        <UiIcon name="flash" :size="12" /> 交易日 15:30 自动全市场极速归档
      </span>
    </div>

    <!-- 数据底座与同步控制卡片 -->
    <div class="card data-status-card">
      <div class="card-title">
        <span>日 K 线数据底座</span>
        <span class="sub-hint">量化选股依赖本地日 K 数据，每日收盘自动极速归档</span>
      </div>

      <!-- 统计指标格 -->
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-label">覆盖股票数</div>
          <div class="stat-val">{{ syncSt.stock_count || 0 }} <span class="stat-unit">只</span></div>
        </div>
        <div class="stat-box">
          <div class="stat-label">最新数据日期</div>
          <div class="stat-val highlight">{{ syncSt.latest_date || '—' }}</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">本地日K总条数</div>
          <div class="stat-val">{{ fmtNum(syncSt.total_bars || 0) }} <span class="stat-unit">条</span></div>
        </div>
        <div class="stat-box">
          <div class="stat-label">定时同步状态</div>
          <div class="stat-val status-on">已启用 (15:30)</div>
        </div>
      </div>

      <!-- 快捷同步操作 -->
      <div class="sync-actions-row">
        <UiButton variant="primary" :disabled="syncing" @click="startSyncToday">
          <UiIcon name="flash" :size="13" />
          {{ syncing && syncMode === 'today_bulk' ? '全市场极速同步中…' : '极速同步今日日K（1.5秒）' }}
        </UiButton>
        <UiButton variant="subtle" :disabled="syncing" @click="startSyncHistory">
          <UiIcon name="sync" :size="13" />
          {{ syncing && syncMode === 'history' ? '历史K线同步中…' : '同步历史K线（前120日）' }}
        </UiButton>
      </div>

      <!-- 进度条 -->
      <div class="progress-bar-wrap" v-if="syncing || syncMsg">
        <div class="progress-track"><i :style="{ width: syncPct + '%' }"></i></div>
        <div class="progress-info">
          <span>{{ syncMsg || '正在处理中…' }}</span>
          <span class="progress-num">{{ syncPct }}%</span>
        </div>
      </div>
    </div>

    <!-- 选股策略配置 -->
    <div class="card strategy-card">
      <div class="card-title">
        <span>量化策略选择</span>
        <span class="sub-hint">支持单选或多策略组合叠加筛选</span>
      </div>

      <!-- 策略网格卡片 -->
      <div class="strategy-grid">
        <div
          v-for="r in ruleList"
          :key="r.id"
          class="strategy-item"
          :class="{ selected: selectedRules.includes(r.id) }"
          @click="toggleRule(r.id)"
        >
          <div class="strategy-head">
            <span class="strategy-check">
              <UiIcon v-if="selectedRules.includes(r.id)" name="check" :size="12" />
            </span>
            <span class="strategy-name">{{ r.name }}</span>
            <span class="strategy-tag">{{ getStrategyTag(r.id) }}</span>
          </div>
          <div class="strategy-desc">{{ r.desc }}</div>
        </div>
      </div>

      <!-- 选股范围与控制参数 -->
      <div class="filter-controls">
        <div class="control-row">
          <span class="control-label">扫描股票池：</span>
          <div class="radio-group">
            <UiRadio v-model="scope" value="all" label="全 A 股 (5400+只)" />
            <UiRadio v-model="scope" value="watchlist" label="仅我的自选股" />
          </div>
        </div>

        <div class="control-row">
          <span class="control-label">消息推送：</span>
          <UiCheckbox v-model="notifyFeishu" label="扫描完成后自动推送命中结果到飞书群" />
        </div>
      </div>

      <div class="submit-row">
        <UiButton
          variant="primary"
          size="lg"
          :disabled="running || !selectedRules.length || !syncSt.stock_count"
          @click="runScreen"
        >
          <UiIcon name="search" :size="14" />
          {{ running ? '量化模型极速扫描中…' : '开始量化选股' }}
        </UiButton>
        <span class="btn-hint" v-if="!syncSt.stock_count">请先同步日 K 数据后再执行选股</span>
      </div>
    </div>

    <!-- 选股结果卡片 -->
    <div class="card result-card" v-if="result">
      <div class="card-title result-title">
        <div class="result-title-left">
          <span>选股结果</span>
          <span class="result-summary">
            扫描 <b>{{ result.scanned }}</b> 只 · 共命中 <b class="hit-count">{{ result.hit_count }}</b> 只
          </span>
        </div>
        <span class="result-time">耗时 {{ result.elapsed_ms }}ms</span>
      </div>

      <!-- 策略 Tab 切换 -->
      <div class="result-tabs">
        <button
          v-for="r in resultRules"
          :key="r"
          :class="['tab-pill', { active: activeTab === r }]"
          @click="activeTab = r"
        >
          {{ getRuleName(r) }}
          <span class="tab-badge">{{ (result.hits[r] || []).length }}</span>
        </button>
      </div>

      <!-- 命中结果表格 -->
      <div class="result-table-wrap" v-if="activeHits.length">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:100px">代码</th>
              <th style="width:120px">名称</th>
              <th style="width:90px" class="tar">最新收盘</th>
              <th style="width:90px" class="tar">涨跌幅</th>
              <th>命中信号与技术形态</th>
              <th style="width:80px" class="tac">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="h in activeHits" :key="h.code" @click="openStockPage(h.code)" class="clickable-row">
              <td class="stock-code">{{ h.code }}</td>
              <td class="stock-name">
                <a @click.stop="openStockPage(h.code)">{{ h.name }}</a>
              </td>
              <td class="tar num">{{ h.close != null ? fmtPrice(h.close) : '—' }}</td>
              <td class="tar num" :class="pctClass(h.change_pct)">
                {{ h.change_pct != null ? fmtPct(h.change_pct) : '—' }}
              </td>
              <td class="signal-detail">{{ h.detail }}</td>
              <td class="tac">
                <button class="btn-detail" @click.stop="openStockPage(h.code)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-hint">当前策略在所选股票池中未命中符合条件的标的</div>
    </div>

    <!-- 历史任务记录 -->
    <details class="card history-card" v-if="runs.length">
      <summary class="card-title" style="cursor:pointer;user-select:none">
        <span>历史选股记录（{{ runs.length }} 条）</span>
        <span class="sub-hint">点击展开查看历史扫描归档</span>
      </summary>
      <div class="table-wrap mt12">
        <table class="data-table">
          <thead>
            <tr>
              <th>执行时间</th>
              <th>运行策略</th>
              <th>股票池</th>
              <th class="tar">命中数量</th>
              <th class="tac">状态</th>
              <th class="tac">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in runs" :key="r.id">
              <td>{{ (r.started_at || '').slice(5) }}</td>
              <td>{{ formatRules(r.rules) }}</td>
              <td>{{ r.scope === 'watchlist' ? '自选股' : '全A股' }}</td>
              <td class="tar num" style="font-weight:600">{{ r.hit_count }}</td>
              <td class="tac"><span class="badge-status">{{ r.status }}</span></td>
              <td class="tac">
                <a @click.prevent="loadRun(r.id)" class="action-link">查看详情</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { showToast } from '../composables/useToast.js'
import { fmtPrice, fmtPct, fmtNum, pctClass } from '../utils.js'
import UiButton from '../components/ui/UiButton.vue'
import UiCheckbox from '../components/ui/UiCheckbox.vue'
import UiRadio from '../components/ui/UiRadio.vue'
import UiIcon from '../components/ui/UiIcon.vue'

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

function getStrategyTag(id) {
  const map = {
    breakout: '趋势突破',
    golden_cross: '均线指标',
    volume_surge: '量价异动',
    ma_bullish: '多头排列',
    pullback_support: '回踩买点',
  }
  return map[id] || '量化策略'
}

function toggleRule(id) {
  if (selectedRules.value.includes(id)) {
    selectedRules.value = selectedRules.value.filter(v => v !== id)
  } else {
    selectedRules.value.push(id)
  }
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
  syncMsg.value = '正在全市场批量打包拉取今日收盘日K（约1.5秒）…'
  try {
    await api.screenerSyncBars(1, 'all', 'today_bulk')
    startPolling()
  } catch (e) {
    syncing.value = false
    showToast('启动同步失败：' + (e.message || e), 'error')
  }
}

async function startSyncHistory() {
  syncMode.value = 'history'
  syncing.value = true
  syncPct.value = 2
  syncMsg.value = `正在同步 ${scope.value === 'watchlist' ? '自选股' : '全市场'} 历史K线…`
  try {
    await api.screenerSyncBars(120, scope.value, 'history')
    startPolling()
  } catch (e) {
    syncing.value = false
    showToast('启动同步失败：' + (e.message || e), 'error')
  }
}

function startPolling() {
  clearInterval(syncTimer)
  syncTimer = setInterval(pollSync, 800)
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
      showToast('全市场日K线同步完成！')
      setTimeout(() => { if (!syncing.value) { syncMsg.value = ''; syncPct.value = 0 } }, 3500)
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
    showToast(`选股完成，扫描 ${res.scanned} 只，命中 ${res.hit_count || 0} 只股票`)
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
.screener-page { max-width: 980px; margin: 0 auto; }
.page-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title h2 { margin: 0; font-size: 20px; font-weight: 700; }
.auto-badge {
  font-size: 12px; color: var(--accent); background: var(--accent-bg);
  padding: 4px 10px; border-radius: var(--radius-pill); display: inline-flex;
  align-items: center; gap: 5px; border: 1px solid rgba(76, 154, 255, 0.2);
}

.sub-hint { font-size: 12px; color: var(--text-dim); font-weight: normal; margin-left: 8px; }

/* 统计网格 */
.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin: 14px 0 16px;
}
.stat-box {
  background: var(--kv-bg); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 12px 14px; display: flex; flex-direction: column; gap: 4px;
}
.stat-label { font-size: 12px; color: var(--text-dim); }
.stat-val { font-size: 18px; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
.stat-val.highlight { color: var(--accent); }
.stat-val.status-on { font-size: 14px; color: var(--down); }
.stat-unit { font-size: 12px; font-weight: normal; color: var(--text-dim); margin-left: 2px; }

.sync-actions-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }

/* 进度条 */
.progress-bar-wrap {
  margin-top: 14px; padding: 10px 12px; background: var(--kv-bg);
  border-radius: var(--radius-md); border: 1px solid var(--border);
}
.progress-track { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.progress-track i { display: block; height: 100%; background: var(--accent); border-radius: 3px; transition: width .3s ease; }
.progress-info { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-top: 6px; }
.progress-num { font-weight: 600; color: var(--accent); }

/* 策略选择卡片网格 */
.strategy-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px; margin: 14px 0;
}
.strategy-item {
  background: var(--kv-bg); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 12px 14px; cursor: pointer; transition: all .18s ease;
  display: flex; flex-direction: column; gap: 6px;
}
.strategy-item:hover { border-color: var(--accent); background: var(--bg-hover); }
.strategy-item.selected {
  border-color: var(--accent); background: rgba(76, 154, 255, 0.08);
  box-shadow: 0 0 12px rgba(76, 154, 255, 0.12);
}
.strategy-head { display: flex; align-items: center; gap: 8px; }
.strategy-check {
  width: 18px; height: 18px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); display: inline-flex; align-items: center; justify-content: center;
  background: var(--bg-card); color: transparent; transition: all .15s;
}
.strategy-item.selected .strategy-check {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.strategy-name { font-size: 14px; font-weight: 600; color: var(--text); }
.strategy-tag {
  margin-left: auto; font-size: 11px; color: var(--text-dim);
  background: var(--bg-hover); padding: 1px 6px; border-radius: 4px;
}
.strategy-desc { font-size: 12px; color: var(--text-dim); line-height: 1.5; }

/* 过滤控件与按钮 */
.filter-controls {
  border-top: 1px solid var(--border); padding-top: 14px;
  display: flex; flex-direction: column; gap: 10px;
}
.control-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.control-label { font-size: 13px; color: var(--text-dim); font-weight: 500; }
.radio-group { display: flex; gap: 16px; align-items: center; }

.submit-row { display: flex; align-items: center; gap: 14px; margin-top: 16px; }
.btn-hint { font-size: 12px; color: var(--up); }

/* 选股结果 */
.result-title { display: flex; justify-content: space-between; align-items: center; }
.result-title-left { display: flex; align-items: center; gap: 10px; }
.result-summary { font-size: 13px; color: var(--text-dim); font-weight: normal; }
.hit-count { color: var(--accent); font-weight: 700; }
.result-time { font-size: 12px; color: var(--text-dim); }

.result-tabs { display: flex; gap: 8px; margin: 14px 0 12px; flex-wrap: wrap; }
.tab-pill {
  padding: 6px 14px; border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-dim); font-size: 13px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px; transition: all .15s;
}
.tab-pill:hover { color: var(--text); border-color: var(--accent); }
.tab-pill.active {
  background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600;
}
.tab-badge {
  font-size: 11px; background: rgba(0, 0, 0, 0.2); padding: 1px 6px; border-radius: 10px;
}
.tab-pill.active .tab-badge { background: rgba(255, 255, 255, 0.25); color: #fff; }

.result-table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-md); }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th {
  background: var(--bg-hover); color: var(--text-dim); font-weight: 500;
  padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left;
}
.data-table td {
  padding: 8px 10px; border-bottom: 1px solid var(--border);
}
.clickable-row { cursor: pointer; transition: background .12s; }
.clickable-row:hover { background: var(--bg-hover); }
.clickable-row:last-child td { border-bottom: none; }

.stock-code { font-weight: 600; color: var(--text); }
.stock-name a { color: var(--accent); font-weight: 500; cursor: pointer; }
.stock-name a:hover { text-decoration: underline; }
.signal-detail { color: var(--text); font-size: 12px; }
.btn-detail {
  padding: 2px 8px; font-size: 11px; border: 1px solid var(--border);
  border-radius: 4px; background: transparent; color: var(--text-dim); cursor: pointer;
}
.btn-detail:hover { color: var(--accent); border-color: var(--accent); }

.badge-status {
  font-size: 11px; padding: 2px 6px; border-radius: 4px;
  background: var(--kv-bg); color: var(--text-dim);
}
.action-link { color: var(--accent); font-size: 12px; cursor: pointer; }
.action-link:hover { text-decoration: underline; }
.empty-hint { padding: 32px 0; text-align: center; color: var(--text-dim); font-size: 13px; }
</style>
