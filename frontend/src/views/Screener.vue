<template>
  <div class="page screener-page">
    <div class="header-section">
      <div class="title-wrap">
        <h2>盘后量化选股</h2>
        <span class="sub-title">多策略共振扫描 · 智能排雷去杂 · 本地极速量化引擎</span>
      </div>
      <div class="auto-badge" title="交易日 15:30 自动收盘归档">
        <UiIcon name="flash" :size="13" /> 交易日 15:30 自动全市场归档
      </div>
    </div>

    <!-- 步骤一：数据底座状态 -->
    <div class="card section-card">
      <div class="card-title">
        <span class="step-num">1</span>
        <span>日 K 线数据状态</span>
        <span class="card-sub-info">选股依赖本地收盘日 K 线数据</span>
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
          <div class="stat-meta">全市场批量打包</div>
          <div class="stat-num success">11 次请求 / 1.5s</div>
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
          数据已归档至 {{ syncSt.latest_date }}，可直接开始选股
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
        <span>策略模型选择</span>
        <span class="card-sub-info">支持多策略组合，系统将自动计算多策略共振强势标的</span>
      </div>

      <div class="strategy-cards-grid">
        <div
          v-for="r in ruleList"
          :key="r.id"
          class="strategy-card-item"
          :class="{ active: selectedRules.includes(r.id) }"
          @click="toggleRule(r.id)"
        >
          <div class="st-header">
            <div class="st-check-icon">
              <UiIcon v-if="selectedRules.includes(r.id)" name="check" :size="12" />
            </div>
            <div class="st-name">{{ r.name }}</div>
            <span class="st-badge">{{ getStrategyTag(r.id) }}</span>
          </div>
          <div class="st-desc">{{ r.desc }}</div>
        </div>
      </div>

      <div class="options-bar">
        <div class="opt-group">
          <span class="opt-label">扫描股票池：</span>
          <UiRadio v-model="scope" value="all" label="全 A 股 (排除ST/破位)" />
          <UiRadio v-model="scope" value="watchlist" label="仅我的自选股" />
        </div>

        <div class="opt-group">
          <UiCheckbox v-model="notifyFeishu" label="扫描完成后推送到飞书群" />
        </div>
      </div>

      <div class="action-execute-row">
        <UiButton
          variant="primary"
          size="lg"
          :disabled="running || !selectedRules.length || !syncSt.stock_count"
          @click="runScreen"
        >
          <UiIcon name="search" :size="15" />
          {{ running ? '量化引擎极速扫描中…' : '🚀 开始量化选股 (一键多策略共振扫描)' }}
        </UiButton>
        <span class="warn-tip" v-if="!syncSt.stock_count">请先同步日 K 数据底座后再执行选股</span>
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
              <th style="width:70px" class="tac">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedDisplayList"
              :key="item.code"
              class="clickable-row"
              @click="openStockPage(item.code)"
            >
              <td class="code-col">{{ item.code }}</td>
              <td class="name-col">
                <a @click.stop="openStockPage(item.code)">{{ item.name }}</a>
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
                <button class="btn-view" @click.stop="openStockPage(item.code)">详情</button>
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
        <span>📜 历史选股扫描归档 (共 {{ runs.length }} 次)</span>
        <span class="summary-hint">点击展开查看历史记录</span>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { showToast } from '../composables/useToast.js'
import { fmtPrice, fmtPct, fmtNum, fmtAmount, pctClass } from '../utils.js'
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
const activeTab = ref('all_aggregated')
const sortBy = ref('resonance')
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

function getRuleTagClass(id) {
  const map = {
    breakout: 'tag-breakout',
    golden_cross: 'tag-gold',
    volume_surge: 'tag-vol',
    ma_bullish: 'tag-ma',
    pullback_support: 'tag-pullback',
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

const resultRules = computed(() => result.value && result.value.hits ? Object.keys(result.value.hits) : [])

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
    const res = await api.screenerRun(selectedRules.value, scope.value, notifyFeishu.value)
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

async function loadRun(id) {
  try {
    const data = await api.screenerRunDetail(id)
    result.value = {
      ...data.run,
      items: data.items || [],
      hits: data.hits || {},
      scanned: '—',
      hit_count: data.run?.hit_count || 0,
      elapsed_ms: '—'
    }
    activeTab.value = 'all_aggregated'
  } catch {}
}

onMounted(async () => {
  loadStatus()
  try { ruleList.value = (await api.screenerRules()).rules || [] } catch {}
  loadRuns()
})
</script>

<style scoped>
.screener-page { max-width: 1040px; margin: 0 auto; padding-bottom: 40px; }

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
  color: var(--text); margin-bottom: 12px;
}
.step-num {
  width: 20px; height: 20px; border-radius: 50%; background: var(--accent);
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
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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
  box-shadow: 0 0 10px rgba(76, 154, 255, 0.15);
}
.st-header { display: flex; align-items: center; gap: 8px; }
.st-check-icon {
  width: 18px; height: 18px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--bg-card); display: inline-flex; align-items: center; justify-content: center;
  color: transparent; transition: all .15s; flex-shrink: 0;
}
.strategy-card-item.active .st-check-icon {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.st-name { font-size: 14px; font-weight: 600; color: var(--text); }
.st-badge {
  margin-left: auto; font-size: 11px; color: var(--text-dim);
  background: var(--bg-hover); padding: 2px 6px; border-radius: 4px;
}
.st-desc { font-size: 12px; color: var(--text-dim); line-height: 1.45; }

.options-bar {
  border-top: 1px solid var(--border); padding-top: 14px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 14px; margin-bottom: 16px;
}
.opt-group { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.opt-label { font-size: 13px; color: var(--text-dim); font-weight: 500; }

.action-execute-row { display: flex; align-items: center; gap: 14px; }
.warn-tip { font-size: 12px; color: var(--up); }

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
.tag-vol { background: rgba(168, 85, 247, 0.12); color: #a855f7; border-color: rgba(168, 85, 247, 0.25); }
.tag-ma { background: rgba(59, 130, 246, 0.12); color: var(--accent); border-color: rgba(59, 130, 246, 0.25); }
.tag-pullback { background: rgba(34, 197, 94, 0.12); color: #22c55e; border-color: rgba(34, 197, 94, 0.25); }

.signal-col { font-size: 12px; color: var(--text); line-height: 1.4; }
.btn-view {
  padding: 2px 8px; font-size: 11px; border: 1px solid var(--border);
  border-radius: 4px; background: transparent; color: var(--text-dim); cursor: pointer;
}
.btn-view:hover { color: var(--accent); border-color: var(--accent); }

.empty-box {
  padding: 40px 0; text-align: center; color: var(--text-dim); font-size: 13px;
  display: flex; flex-direction: column; align-items: center;
}

/* 历史面板 */
.history-summary {
  cursor: pointer; user-select: none; font-size: 14px; font-weight: 600;
  color: var(--text); display: flex; align-items: center; justify-content: space-between;
}
.summary-hint { font-size: 12px; color: var(--text-dim); font-weight: normal; }
.history-table-wrap { margin-top: 12px; overflow-x: auto; }
.badge-status { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: var(--bg-hover); color: var(--text-dim); }
.action-btn { color: var(--accent); font-size: 12px; cursor: pointer; }
.action-btn:hover { text-decoration: underline; }
</style>
