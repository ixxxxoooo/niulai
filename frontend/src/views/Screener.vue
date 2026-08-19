<template>
  <div class="page screener-page">
    <!-- 顶部标题 -->
    <div class="header-section">
      <div class="title-wrap">
        <h2>盘后量化选股</h2>
        <span class="sub-title">8 大高胜率经典实战策略 · 多策略共振扫描 · 智能排雷去杂</span>
      </div>
      <div class="auto-badge" title="交易日 15:30 自动收盘归档">
        <UiIcon name="flash" :size="13" /> 交易日 15:30 自动全市场归档
      </div>
    </div>

    <!-- 步骤一：数据底座状态 -->
    <div class="card section-card">
      <div class="card-title">
        <span class="step-num">1</span>
        <span>日 K 线数据底座</span>
        <span class="card-sub-info">选股依赖本地收盘日 K 线数据，1.5 秒极速全量归档</span>
      </div>

      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-meta">覆盖股票池</div>
          <div class="stat-num">{{ syncSt.stock_count || 0 }} <span class="stat-unit">只</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-meta">最新收盘日期</div>
          <div class="stat-num accent">{{ syncSt.latest_date || '—' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-meta">本地 K 线总条数</div>
          <div class="stat-num">{{ fmtNum(syncSt.total_bars || 0) }} <span class="stat-unit">条</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-meta">批量接口性能</div>
          <div class="stat-num success">11 次请求 / 1.5s (0频控)</div>
        </div>
      </div>

      <div class="sync-bar-row">
        <UiButton variant="primary" :disabled="syncing" @click="startSyncToday">
          <UiIcon name="flash" :size="14" />
          {{ syncing && syncMode === 'today_bulk' ? '全市场极速同步中…' : '⚡ 极速同步今日日K (1.5秒)' }}
        </UiButton>
        <UiButton variant="subtle" :disabled="syncing" @click="startSyncHistory">
          <UiIcon name="sync" :size="14" />
          {{ syncing && syncMode === 'history' ? '历史K线同步中…' : '同步历史K线 (前120日)' }}
        </UiButton>
        <span class="sync-hint" v-if="syncSt.latest_date">
          数据已归档至 {{ syncSt.latest_date }}，随时可开启量化选股
        </span>
      </div>

      <div class="progress-wrap" v-if="syncing || syncMsg">
        <div class="progress-track"><i :style="{ width: syncPct + '%' }"></i></div>
        <div class="progress-info">
          <span>{{ syncMsg || '正在处理中…' }}</span>
          <span class="progress-pct">{{ syncPct }}%</span>
        </div>
      </div>
    </div>

    <!-- 步骤二：选股策略与参数配置 -->
    <div class="card section-card">
      <div class="card-title">
        <span class="step-num">2</span>
        <span>量化策略选择与智能排雷</span>
        <span class="card-sub-info">点击卡片即可勾选策略，多策略叠加将自动计算「共振强势标的」</span>
      </div>

      <!-- 8 大高胜率策略卡片网格 -->
      <div class="strategy-cards-grid">
        <div
          v-for="r in ruleList"
          :key="r.id"
          class="strategy-card-item"
          :class="{ active: selectedRules.includes(r.id) }"
          @click="toggleRule(r.id)"
        >
          <div class="st-header">
            <div class="st-check-box">
              <UiIcon v-if="selectedRules.includes(r.id)" name="check" :size="13" />
            </div>
            <div class="st-name">{{ r.name }}</div>
            <span class="st-badge" :class="getBadgeClass(r.badge)">{{ r.badge || r.tag }}</span>
          </div>
          <div class="st-desc">{{ r.desc }}</div>
        </div>
      </div>

      <!-- 股票池范围与排除项过滤 -->
      <div class="filter-panel">
        <div class="filter-row">
          <span class="filter-title">扫描范围：</span>
          <div class="filter-options">
            <label class="radio-pill" :class="{ active: scope === 'all' }" @click="scope = 'all'">
              <span class="radio-dot"></span> 全 A 股市场 (5400+只)
            </label>
            <label class="radio-pill" :class="{ active: scope === 'watchlist' }" @click="scope = 'watchlist'">
              <span class="radio-dot"></span> 仅我的自选股
            </label>
          </div>
        </div>

        <div class="filter-row">
          <span class="filter-title">排雷与排除：</span>
          <div class="filter-chips">
            <div
              class="chip-btn"
              :class="{ active: filters.exclude_st }"
              @click="filters.exclude_st = !filters.exclude_st"
            >
              <UiIcon name="check" :size="12" v-if="filters.exclude_st" />
              <span>排除 ST / *ST 股</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_broken }"
              @click="filters.exclude_broken = !filters.exclude_broken"
            >
              <UiIcon name="check" :size="12" v-if="filters.exclude_broken" />
              <span>排除破位大跌股 (&lt;-3%)</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_bjs }"
              @click="filters.exclude_bjs = !filters.exclude_bjs"
            >
              <UiIcon name="check" :size="12" v-if="filters.exclude_bjs" />
              <span>排除北交所 (8/4/920)</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_kcb }"
              @click="filters.exclude_kcb = !filters.exclude_kcb"
            >
              <UiIcon name="check" :size="12" v-if="filters.exclude_kcb" />
              <span>排除科创板 (688)</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_cyb }"
              @click="filters.exclude_cyb = !filters.exclude_cyb"
            >
              <UiIcon name="check" :size="12" v-if="filters.exclude_cyb" />
              <span>排除创业板 (300/301)</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: notifyFeishu }"
              @click="notifyFeishu = !notifyFeishu"
            >
              <UiIcon name="check" :size="12" v-if="notifyFeishu" />
              <span>完成推送到飞书群</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 居中大气的主执行按钮 -->
      <div class="execute-center-wrap">
        <button
          class="btn-execute-glow"
          :disabled="running || !selectedRules.length"
          @click="runScreen"
        >
          <UiIcon name="search" :size="18" />
          <span>{{ running ? '量化引擎极速扫描中…' : '开始量化选股 (一键多策略共振扫描)' }}</span>
        </button>
      </div>
    </div>

    <!-- 步骤三：选股结果看板 -->
    <div class="card section-card result-panel" v-if="result">
      <div class="result-header">
        <div class="result-title-group">
          <span class="step-num">3</span>
          <span class="result-main-title">选股结果看板</span>
          <span class="result-stat-badge">
            扫描 <b>{{ result.scanned }}</b> 只 · 精选命中 <b>{{ result.hit_count }}</b> 只优质标的
          </span>
        </div>
        <div class="result-extra-info">
          <span>耗时 <b>{{ result.elapsed_ms }}ms</b> (本地纯内存向量化计算)</span>
        </div>
      </div>

      <!-- Tab 切换：全部共振聚合榜单 + 单策略筛选 -->
      <div class="tabs-container">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'all_aggregated' }"
          @click="activeTab = 'all_aggregated'"
        >
          🔥 全部共振优选榜
          <span class="badge-num">{{ result.items ? result.items.length : result.hit_count }}</span>
        </button>
        <button
          v-for="r in resultRules"
          :key="r"
          class="tab-btn"
          :class="{ active: activeTab === r }"
          @click="activeTab = r"
        >
          {{ getRuleName(r) }}
          <span class="badge-num">{{ (result.hits[r] || []).length }}</span>
        </button>
      </div>

      <!-- 排序切换按钮组（聚合榜特有） -->
      <div class="sort-bar" v-if="activeTab === 'all_aggregated' && currentDisplayList.length">
        <span class="sort-label">排序方式：</span>
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'resonance' }"
          @click="sortBy = 'resonance'"
        >
          🌟 策略共振度优先
        </button>
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'change_pct' }"
          @click="sortBy = 'change_pct'"
        >
          📈 今日涨跌幅优先
        </button>
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'amount' }"
          @click="sortBy = 'amount'"
        >
          💰 成交额优先
        </button>
      </div>

      <!-- 结果明细表格 -->
      <div class="table-box" v-if="sortedDisplayList.length">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:90px">代码</th>
              <th style="width:110px">名称</th>
              <th style="width:90px" class="tar">最新收盘</th>
              <th style="width:90px" class="tar">涨跌幅</th>
              <th style="width:100px" class="tar">成交额</th>
              <th style="width:180px">命中策略共振</th>
              <th>技术形态与信号明细</th>
              <th style="width:80px" class="tac">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedDisplayList"
              :key="item.code"
              class="clickable-row"
              @click="openStockModal(item.code, item.name)"
            >
              <td class="code-col">{{ item.code }}</td>
              <td class="name-col">
                <a @click.stop="openStockModal(item.code, item.name)">{{ item.name }}</a>
              </td>
              <td class="tar num-val">{{ item.close != null ? fmtPrice(item.close) : '—' }}</td>
              <td class="tar num-val" :class="pctClass(item.change_pct)">
                {{ item.change_pct != null ? fmtPct(item.change_pct) : '—' }}
              </td>
              <td class="tar num-val dim">{{ item.amount ? fmtAmount(item.amount) : '—' }}</td>
              <td>
                <div class="resonance-tags">
                  <span
                    v-for="r_id in (item.hit_rules || (activeTab !== 'all_aggregated' ? [activeTab] : []))"
                    :key="r_id"
                    class="tag-resonance"
                    :class="getRuleTagClass(r_id)"
                  >
                    {{ getRuleName(r_id) }}
                  </span>
                </div>
              </td>
              <td class="signal-col">{{ item.detail }}</td>
              <td class="tac">
                <button class="btn-view" @click.stop="openStockModal(item.code, item.name)">速览</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-box">
        <UiIcon name="search" :size="28" style="opacity:0.3;margin-bottom:8px" />
        <div>所选策略组合在当前股票池中未命中符合条件的标的</div>
      </div>
    </div>

    <!-- 历史任务归档 -->
    <details class="card section-card history-panel" v-if="runs.length">
      <summary class="history-summary">
        <div class="history-title-wrap">
          <span>📜 历史选股扫描归档 (共 {{ runs.length }} 次)</span>
        </div>
        <div class="history-summary-right">
          <button class="btn-clear-history" @click.prevent.stop="clearHistory">
            <UiIcon name="trash" :size="12" /> 清空历史归档
          </button>
          <span class="chevron-indicator">
            <span class="chevron-text">展开历史</span>
            <span class="chevron-arrow">▾</span>
          </span>
        </div>
      </summary>
      <div class="history-table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>执行时间</th>
              <th>执行策略组合</th>
              <th>扫描范围</th>
              <th class="tar">命中标的数</th>
              <th class="tac">状态</th>
              <th class="tac">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in runs" :key="r.id">
              <td class="dim">{{ (r.started_at || '').slice(5) }}</td>
              <td>{{ formatRules(r.rules) }}</td>
              <td>{{ r.scope === 'watchlist' ? '自选股' : '全A股' }}</td>
              <td class="tar num-val" style="font-weight:700">{{ r.hit_count }}</td>
              <td class="tac"><span class="badge-status">{{ r.status }}</span></td>
              <td class="tac">
                <a @click.prevent="loadRun(r.id)" class="action-btn">查看该次结果</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <!-- 个股快捷居中大弹窗 -->
    <StockQuickModal
      :code="modalCode"
      :name="modalName"
      v-model:open="modalOpen"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api } from '../api.js'
import { showToast } from '../composables/useToast.js'
import { showConfirm } from '../composables/useConfirm.js'
import { fmtPrice, fmtPct, fmtNum, fmtAmount, pctClass } from '../utils.js'
import UiButton from '../components/ui/UiButton.vue'
import UiIcon from '../components/ui/UiIcon.vue'
import StockQuickModal from '../components/StockQuickModal.vue'

const STORAGE_KEY = 'niulai_screener_state_v1'

const syncSt = ref({})
const syncing = ref(false)
const syncPct = ref(0)
const syncMsg = ref('')
const syncMode = ref('today_bulk')
let syncTimer = null

const ruleList = ref([])
const selectedRules = ref(['breakout', 'ma_bullish', 'main_inflow_surge', 'volume_surge', 'box_breakout'])
const scope = ref('all')
const notifyFeishu = ref(false)
const running = ref(false)
const result = ref(null)
const activeTab = ref('all_aggregated')
const sortBy = ref('resonance')
const runs = ref([])

// 弹窗状态
const modalOpen = ref(false)
const modalCode = ref('')
const modalName = ref('')

function openStockModal(code, name = '') {
  modalCode.value = code
  modalName.value = name
  modalOpen.value = true
}

// 排除项过滤器：默认排除 ST、破位、北交所、科创板、创业板
const filters = reactive({
  exclude_st: true,
  exclude_broken: true,
  exclude_bjs: true,
  exclude_kcb: true,
  exclude_cyb: true,
})

// 状态持久化存储
function saveState() {
  try {
    const state = {
      selectedRules: selectedRules.value,
      scope: scope.value,
      filters: { ...filters },
      notifyFeishu: notifyFeishu.value,
      sortBy: sortBy.value,
      activeTab: activeTab.value,
      result: result.value,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch (e) {}
}

function loadSavedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const state = JSON.parse(raw)
    if (Array.isArray(state.selectedRules) && state.selectedRules.length) selectedRules.value = state.selectedRules
    if (state.scope) scope.value = state.scope
    if (state.filters) Object.assign(filters, state.filters)
    if (state.notifyFeishu !== undefined) notifyFeishu.value = !!state.notifyFeishu
    if (state.sortBy) sortBy.value = state.sortBy
    if (state.activeTab) activeTab.value = state.activeTab
    if (state.result) result.value = state.result
  } catch (e) {}
}

// 监听所有状态变化并即时保存
watch([selectedRules, scope, filters, notifyFeishu, sortBy, activeTab, result], () => {
  saveState()
}, { deep: true })

const ruleMap = computed(() => {
  const m = {}
  for (const r of ruleList.value) m[r.id] = r.name
  return m
})

function getRuleName(id) {
  return ruleMap.value[id] || id
}

function getBadgeClass(badge) {
  if (!badge) return ''
  if (badge.includes('强烈推荐')) return 'badge-fire'
  if (badge.includes('胜率极高')) return 'badge-diamond'
  if (badge.includes('爆发力强')) return 'badge-rocket'
  if (badge.includes('极佳盈亏比')) return 'badge-target'
  return ''
}

function getRuleTagClass(id) {
  const map = {
    breakout: 'tag-breakout',
    ma_bullish: 'tag-ma',
    main_inflow_surge: 'tag-inflow',
    volume_surge: 'tag-vol',
    box_breakout: 'tag-box',
    pullback_support: 'tag-pullback',
    golden_cross: 'tag-gold',
    macd_zero_cross: 'tag-macd',
    active_turnover: 'tag-turnover',
    small_cap_leader: 'tag-smallcap',
    bullish_engulfing: 'tag-engulfing',
    oversold_rebound: 'tag-bounce',
  }
  return map[id] || ''
}

function toggleRule(id) {
  if (selectedRules.value.includes(id)) {
    selectedRules.value = selectedRules.value.filter(v => v !== id)
  } else {
    selectedRules.value.push(id)
  }
}

const resultRules = computed(() => {
  if (!result.value || !result.value.hits || Array.isArray(result.value.hits)) return []
  return Object.keys(result.value.hits)
})

const currentDisplayList = computed(() => {
  if (!result.value) return []
  if (activeTab.value === 'all_aggregated') {
    return result.value.items || []
  }
  return (result.value.hits && result.value.hits[activeTab.value]) || []
})

const sortedDisplayList = computed(() => {
  const list = [...currentDisplayList.value]
  if (activeTab.value !== 'all_aggregated') return list

  if (sortBy.value === 'resonance') {
    return list.sort((a, b) => ((b.match_count || 1) - (a.match_count || 1)) || ((b.change_pct || 0) - (a.change_pct || 0)))
  } else if (sortBy.value === 'change_pct') {
    return list.sort((a, b) => (b.change_pct || 0) - (a.change_pct || 0))
  } else if (sortBy.value === 'amount') {
    return list.sort((a, b) => (b.amount || 0) - (a.amount || 0))
  }
  return list
})

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
      showToast('全市场日K线极速同步完成！')
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
    const res = await api.screenerRun(selectedRules.value, scope.value, notifyFeishu.value, null, filters)
    result.value = res
    activeTab.value = 'all_aggregated'
    loadRuns()
    showToast(`选股完成！扫描 ${res.scanned} 只，命中 ${res.hit_count || 0} 只优质标的`)
  } catch (e) {
    showToast('选股失败：' + (e.message || e), 'error')
  } finally {
    running.value = false
  }
}

async function loadRuns() {
  try { runs.value = (await api.screenerRuns(20)).runs || [] } catch {}
}

async function clearHistory() {
  const confirmed = await showConfirm({
    title: '清空历史选股归档',
    message: '确认清空所有历史选股任务归档记录吗？',
    detail: '清空后历史扫描记录将全部移除，但不会影响本地日 K 数据库和当前选股策略。',
    confirmText: '确认清空',
    cancelText: '取消',
    variant: 'danger',
  })
  if (!confirmed) return
  try {
    await api.screenerClearRuns()
    runs.value = []
    showToast('已清空历史选股记录')
  } catch (e) {
    showToast('清空失败：' + (e.message || e), 'error')
  }
}

async function loadRun(id) {
  try {
    const data = await api.screenerRunDetail(id)
    result.value = {
      ...data.run,
      items: data.items || [],
      hits: data.hits || {},
      scanned: '—',
      hit_count: data.run?.hit_count || (data.items ? data.items.length : 0),
      elapsed_ms: '—'
    }
    activeTab.value = 'all_aggregated'
    showToast(`已调出第 ${id} 次历史扫描结果`)
  } catch (e) {
    showToast('加载历史记录失败：' + (e.message || e), 'error')
  }
}

onMounted(async () => {
  loadSavedState()
  loadStatus()
  try { ruleList.value = (await api.screenerRules()).rules || [] } catch {}
  loadRuns()
  if (!result.value) {
    runScreen()
  }
})
</script>

<style scoped>
.screener-page { max-width: 1060px; margin: 0 auto; padding-bottom: 40px; }

.header-section {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 18px; flex-wrap: wrap; gap: 10px;
}
.title-wrap h2 { margin: 0 0 4px; font-size: 22px; font-weight: 700; color: var(--text); }
.sub-title { font-size: 13px; color: var(--text-dim); }

.auto-badge {
  font-size: 12px; color: var(--accent); background: var(--accent-bg);
  padding: 5px 12px; border-radius: var(--radius-pill); display: inline-flex;
  align-items: center; gap: 6px; border: 1px solid rgba(76, 154, 255, 0.25);
  font-weight: 500;
}

.section-card { margin-bottom: 16px; }
.card-title {
  display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600;
  color: var(--text); margin-bottom: 14px;
}
.step-num {
  width: 22px; height: 22px; border-radius: 50%; background: var(--accent);
  color: #fff; font-size: 12px; display: inline-flex; align-items: center;
  justify-content: center; font-weight: 700;
}
.card-sub-info { font-size: 12px; color: var(--text-dim); font-weight: normal; margin-left: 6px; }

/* 统计卡片网格 */
.stats-row {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 14px;
}
.stat-card {
  background: var(--kv-bg); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 10px 14px;
}
.stat-meta { font-size: 12px; color: var(--text-dim); margin-bottom: 4px; }
.stat-num { font-size: 18px; font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }
.stat-num.accent { color: var(--accent); }
.stat-num.success { color: var(--down); font-size: 14px; }
.stat-unit { font-size: 12px; font-weight: normal; color: var(--text-dim); margin-left: 3px; }

.sync-bar-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.sync-hint { font-size: 12px; color: var(--text-dim); margin-left: 4px; }

.progress-wrap {
  margin-top: 12px; padding: 10px 12px; background: var(--kv-bg);
  border-radius: var(--radius-md); border: 1px solid var(--border);
}
.progress-track { height: 6px; background: var(--border); border-radius: 3px; overflow: hidden; }
.progress-track i { display: block; height: 100%; background: var(--accent); border-radius: 3px; transition: width .3s ease; }
.progress-info { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-top: 6px; }
.progress-pct { font-weight: 700; color: var(--accent); }

/* 策略选择卡片 */
.strategy-cards-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.strategy-card-item {
  background: var(--kv-bg); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 12px 14px; cursor: pointer; transition: all .16s ease;
  display: flex; flex-direction: column; gap: 6px; user-select: none;
}
.strategy-card-item:hover { border-color: var(--accent); background: var(--bg-hover); }
.strategy-card-item.active {
  border-color: var(--accent); background: rgba(76, 154, 255, 0.08);
  box-shadow: 0 0 12px rgba(76, 154, 255, 0.15);
}
.st-header { display: flex; align-items: center; gap: 8px; }
.st-check-box {
  width: 18px; height: 18px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--bg-card); display: inline-flex; align-items: center; justify-content: center;
  color: transparent; transition: all .15s; flex-shrink: 0;
}
.strategy-card-item.active .st-check-box {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.st-name { font-size: 14px; font-weight: 600; color: var(--text); }
.st-badge {
  margin-left: auto; font-size: 11px; color: var(--text-dim);
  background: var(--bg-hover); padding: 2px 6px; border-radius: 4px;
}
.badge-fire { color: var(--up); background: var(--up-bg); font-weight: 600; }
.badge-diamond { color: var(--accent); background: var(--accent-bg); font-weight: 600; }
.badge-rocket { color: #a855f7; background: rgba(168, 85, 247, 0.12); font-weight: 600; }
.badge-target { color: #22c55e; background: rgba(34, 197, 94, 0.12); font-weight: 600; }
.st-desc { font-size: 12px; color: var(--text-dim); line-height: 1.45; }

/* 过滤排雷面板 */
.filter-panel {
  border-top: 1px solid var(--border); padding-top: 14px;
  display: flex; flex-direction: column; gap: 12px; margin-bottom: 20px;
}
.filter-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.filter-title { font-size: 13px; font-weight: 600; color: var(--text-dim); min-width: 80px; }
.filter-options { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.radio-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px;
  border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); font-size: 13px;
  cursor: pointer; user-select: none; transition: all .15s;
}
.radio-pill:hover { border-color: var(--accent); color: var(--text); }
.radio-pill.active {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}
.radio-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--border);
}
.radio-pill.active .radio-dot { background: var(--accent); }

.filter-chips { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.chip-btn {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); font-size: 12px;
  cursor: pointer; user-select: none; transition: all .15s;
}
.chip-btn:hover { border-color: var(--accent); color: var(--text); }
.chip-btn.active {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}

/* 居中执行主按钮 */
.execute-center-wrap {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 10px 0 8px;
}
.btn-execute-glow {
  display: inline-flex; align-items: center; justify-content: center; gap: 10px;
  padding: 14px 42px; border-radius: 30px; border: none;
  background: linear-gradient(135deg, #4c9aff 0%, #2563eb 100%);
  color: #ffffff; font-size: 16px; font-weight: 700; cursor: pointer;
  box-shadow: 0 4px 18px rgba(37, 99, 235, 0.35); transition: all .2s ease;
}
.btn-execute-glow:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 24px rgba(37, 99, 235, 0.45);
  background: linear-gradient(135deg, #60a5fa 0%, #1d4ed8 100%);
}
.btn-execute-glow:active:not(:disabled) { transform: translateY(0); }
.btn-execute-glow:disabled {
  opacity: 0.5; cursor: not-allowed; box-shadow: none;
}
.warn-tip { font-size: 12px; color: var(--up); margin-top: 8px; }

/* 结果面板 */
.result-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px; flex-wrap: wrap; gap: 10px;
}
.result-title-group { display: flex; align-items: center; gap: 8px; }
.result-main-title { font-size: 16px; font-weight: 700; color: var(--text); }
.result-stat-badge {
  font-size: 13px; color: var(--text-dim); background: var(--bg-hover);
  padding: 3px 10px; border-radius: var(--radius-sm); margin-left: 6px;
}
.result-stat-badge b { color: var(--accent); }
.result-extra-info { font-size: 12px; color: var(--text-dim); }

.tabs-container { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.tab-btn {
  padding: 6px 14px; border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-dim); font-size: 13px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px; transition: all .15s;
}
.tab-btn:hover { color: var(--text); border-color: var(--accent); }
.tab-btn.active {
  background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600;
}
.badge-num {
  font-size: 11px; background: rgba(0, 0, 0, 0.15); padding: 1px 6px; border-radius: 10px;
}
.tab-btn.active .badge-num { background: rgba(255, 255, 255, 0.25); color: #fff; }

.sort-bar {
  display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
  font-size: 12px; color: var(--text-dim);
}
.sort-btn {
  padding: 3px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); cursor: pointer; font-size: 12px;
  transition: all .15s;
}
.sort-btn:hover { color: var(--text); border-color: var(--accent); }
.sort-btn.active {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}

.table-box { overflow-x: auto; border: 1px solid var(--border); border-radius: var(--radius-md); }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th {
  background: var(--bg-hover); color: var(--text-dim); font-weight: 500;
  padding: 9px 10px; border-bottom: 1px solid var(--border); text-align: left;
}
.data-table td { padding: 9px 10px; border-bottom: 1px solid var(--border); }
.clickable-row { cursor: pointer; transition: background .12s; }
.clickable-row:hover { background: var(--bg-hover); }
.clickable-row:last-child td { border-bottom: none; }

.code-col { font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums; }
.name-col a { color: var(--accent); font-weight: 600; cursor: pointer; }
.name-col a:hover { text-decoration: underline; }
.num-val { font-variant-numeric: tabular-nums; font-weight: 600; }
.num-val.dim { font-weight: normal; color: var(--text-dim); }

.resonance-tags { display: flex; gap: 4px; flex-wrap: wrap; }
.tag-resonance {
  font-size: 11px; padding: 2px 6px; border-radius: 4px;
  background: var(--bg-hover); color: var(--text); border: 1px solid var(--border);
}
.tag-breakout { background: rgba(240, 68, 68, 0.1); color: var(--up); border-color: rgba(240, 68, 68, 0.25); }
.tag-gold { background: rgba(234, 179, 8, 0.12); color: #eab308; border-color: rgba(234, 179, 8, 0.25); }
.tag-inflow { background: rgba(234, 179, 8, 0.12); color: #eab308; border-color: rgba(234, 179, 8, 0.3); font-weight: 600; }
.tag-vol { background: rgba(168, 85, 247, 0.12); color: #a855f7; border-color: rgba(168, 85, 247, 0.25); }
.tag-ma { background: rgba(59, 130, 246, 0.12); color: var(--accent); border-color: rgba(59, 130, 246, 0.25); }
.tag-pullback { background: rgba(34, 197, 94, 0.12); color: #22c55e; border-color: rgba(34, 197, 94, 0.25); }
.tag-box { background: rgba(236, 72, 153, 0.12); color: #ec4899; border-color: rgba(236, 72, 153, 0.25); }
.tag-macd { background: rgba(14, 165, 233, 0.12); color: #0ea5e9; border-color: rgba(14, 165, 233, 0.25); }
.tag-turnover { background: rgba(20, 184, 166, 0.12); color: #14b8a6; border-color: rgba(20, 184, 166, 0.3); }
.tag-smallcap { background: rgba(168, 85, 247, 0.12); color: #a855f7; border-color: rgba(168, 85, 247, 0.3); }
.tag-engulfing { background: rgba(244, 63, 94, 0.12); color: #f43f5e; border-color: rgba(244, 63, 94, 0.3); }
.tag-bounce { background: rgba(249, 115, 22, 0.12); color: #f97316; border-color: rgba(249, 115, 22, 0.25); }

.signal-col { font-size: 12px; color: var(--text); line-height: 1.4; }
.btn-view {
  padding: 3px 10px; font-size: 12px; border: 1px solid var(--border);
  border-radius: var(--radius-sm); background: var(--bg-hover); color: var(--accent);
  cursor: pointer; transition: all .15s; font-weight: 500;
}
.btn-view:hover { background: var(--accent); color: #fff; border-color: var(--accent); }

.empty-box {
  padding: 40px 0; text-align: center; color: var(--text-dim); font-size: 13px;
  display: flex; flex-direction: column; align-items: center;
}

/* 历史面板 */
.history-summary {
  cursor: pointer; user-select: none; font-size: 14px; font-weight: 600;
  color: var(--text); display: flex; align-items: center; justify-content: space-between;
  padding: 2px 0;
}
.history-summary-right { display: flex; align-items: center; gap: 14px; margin-left: auto; }
.chevron-indicator {
  display: inline-flex; align-items: center; gap: 4px; font-size: 12px;
  color: var(--text-dim); font-weight: normal;
}
.chevron-arrow { transition: transform .2s ease; display: inline-block; font-size: 11px; }
details[open] .chevron-arrow { transform: rotate(180deg); }
details[open] .chevron-text { color: var(--accent); }

.btn-clear-history {
  padding: 3px 10px; font-size: 12px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); cursor: pointer; display: inline-flex;
  align-items: center; gap: 4px; transition: all .15s;
}
.btn-clear-history:hover { color: var(--up); border-color: var(--up); background: var(--up-bg); }

.history-table-wrap { margin-top: 12px; overflow-x: auto; }
.badge-status { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: var(--bg-hover); color: var(--text-dim); }
.action-btn { color: var(--accent); font-size: 12px; cursor: pointer; }
.action-btn:hover { text-decoration: underline; }
</style>
