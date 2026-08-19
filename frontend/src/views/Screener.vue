<template>
  <div class="page screener-page">
    <!-- 顶部标题栏与数据底座紧凑条 -->
    <div class="header-section">
      <div class="title-wrap">
        <h2>盘后量化选股</h2>
        <span class="sub-title">12 大经典高胜率实战策略 · 多策略共振严选 · 智能排雷去杂</span>
      </div>
      <div class="top-status-bar">
        <div class="status-kvs">
          <span class="sk-item" title="当前本地数据库已收录的 A 股股票总数">股票池 <b>{{ syncSt.stock_count || 0 }}</b> 只</span>
          <span class="sk-sep">/</span>
          <span class="sk-item" title="本地日 K 线已归档至最新真实收盘交易日">收盘日期 <b class="accent">{{ syncSt.latest_date || '—' }}</b></span>
          <span class="sk-sep">/</span>
          <span class="sk-item" title="本地 SQLite 数据库中存储的日 K 线总条数">本地K线 <b>{{ fmtNum(syncSt.total_bars || 0) }}</b> 条</span>
        </div>
        <div class="status-actions">
          <button
            class="btn-sync-compact primary"
            :disabled="syncing"
            @click="startSyncToday"
            title="【极速同步今日日K】&#10;调用东财全市场 clist 批量打包接口，约 1.5 秒极速拉取并归档全市场 5400+ 只股票今日收盘日 K（含 18 维全量量价、盘口、主力资金流与估值指标）"
          >
            <UiIcon name="flash" :size="12" />
            <span>{{ syncing && syncMode === 'today_bulk' ? '同步中…' : '⚡ 极速同步今日' }}</span>
          </button>
          <button
            class="btn-sync-compact ghost"
            :disabled="syncing"
            @click="startSyncHistory"
            title="【补齐历史K线（前120日）】&#10;并发多线程智能增量补齐均线与历史形态所需的日 K 线；系统会自动识别，已具备完整数据的标的将自动 0 秒极速跳过"
          >
            <UiIcon name="sync" :size="12" />
            <span>{{ syncing && syncMode === 'history' ? '补齐中…' : '🔄 补齐历史K线' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 同步进度条 -->
    <div class="progress-wrap-compact" v-if="syncing || syncMsg">
      <div class="progress-track"><i :style="{ width: syncPct + '%' }"></i></div>
      <div class="progress-info">
        <span>{{ syncMsg || '正在处理中…' }}</span>
        <span class="progress-pct">{{ syncPct }}%</span>
      </div>
    </div>

    <!-- 步骤一：量化策略选择与智能配置 -->
    <div class="card section-card">
      <div class="card-header-compact">
        <div class="card-title-compact">
          <span class="step-num">1</span>
          <span class="st-title-text">量化策略选择（已选 <b>{{ selectedRules.length }}</b> 项）</span>
        </div>
        <div class="quick-pick-actions">
          <button
            class="quick-link-btn"
            @click="selectPresetGolden"
            title="【推荐黄金组合】&#10;一键勾选『突破前高 + 均线多头 + 主力抢筹 + 放量拉升 + 箱体突破』5 大核心主升浪战法"
          >
            🌟 推荐黄金组合
          </button>
          <button
            class="quick-link-btn"
            @click="selectAllRules"
            title="一键勾选全部 12 大量化选股策略"
          >
            全选
          </button>
          <button
            class="quick-link-btn"
            @click="clearAllRules"
            title="清空当前所有策略勾选"
          >
            清空
          </button>
        </div>
      </div>

      <!-- 12 大策略紧凑网格 -->
      <div class="strategy-cards-grid">
        <div
          v-for="r in ruleList"
          :key="r.id"
          class="strategy-card-item"
          :class="{ active: selectedRules.includes(r.id) }"
          @click="toggleRule(r.id)"
          :title="`${r.name}（${r.badge || r.tag}）&#10;&#10;【策略原理与买点逻辑】：&#10;${r.desc}&#10;&#10;点击即可${selectedRules.includes(r.id) ? '取消勾选' : '加入选股组合'}`"
        >
          <div class="st-header">
            <div class="st-check-box">
              <UiIcon v-if="selectedRules.includes(r.id)" name="check" :size="12" />
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
            <label
              class="radio-pill"
              :class="{ active: scope === 'all' }"
              @click="scope = 'all'"
              title="【扫描全 A 股市场】&#10;在沪深主板、科创板、创业板、北交所全部 5400+ 只股票中执行量化策略筛选"
            >
              <span class="radio-dot"></span> 全 A 股市场 (5400+只)
            </label>
            <label
              class="radio-pill"
              :class="{ active: scope === 'watchlist' }"
              @click="scope = 'watchlist'"
              title="【仅我的自选股】&#10;仅在您个人收藏添加的自选股列表中执行量化策略筛选，秒级聚焦核心自选"
            >
              <span class="radio-dot"></span> 仅我的自选股
            </label>
          </div>
        </div>

        <div class="filter-row">
          <span class="filter-title">策略组合：</span>
          <div class="filter-options">
            <label
              class="radio-pill"
              :class="{ active: filters.match_mode === 'and' }"
              @click="filters.match_mode = 'and'"
              title="【🎯 严格交集严选 · 默认】&#10;必须同时满足所有勾选策略的超级核心龙头才入选主榜，百里挑一，胜率极高"
            >
              <span class="radio-dot"></span> 🎯 严格交集 (必须同时满足所有策略 · 默认)
            </label>
            <label
              class="radio-pill"
              :class="{ active: filters.match_mode === 'resonance' }"
              @click="filters.match_mode = 'resonance'"
              title="【🌟 共振优选总榜】&#10;按命中策略数量降序排序，共振度越高（满足策略越多）排位越靠前，兼顾胜率与机会广度"
            >
              <span class="radio-dot"></span> 🌟 共振优选 (命中越多越优先)
            </label>
            <label
              class="radio-pill"
              :class="{ active: filters.match_mode === 'or' }"
              @click="filters.match_mode = 'or'"
              title="【📋 广度并集总榜】&#10;只要满足任意一个勾选策略即入选展示，最大化捕捉全市场潜在异动标的"
            >
              <span class="radio-dot"></span> 📋 广度并集 (满足任意策略即可)
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
              title="【排除 ST / *ST 股】&#10;自动剔除带有风险警示的 ST 及 *ST 股票，杜绝退市与黑天鹅风险"
            >
              <UiIcon name="check" :size="11" v-if="filters.exclude_st" />
              <span>排除 ST 股</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_broken }"
              @click="filters.exclude_broken = !filters.exclude_broken"
              title="【排除破位弱势股】&#10;自动剔除当日跌幅超过 3% 的破位大跌股票，规避下跌趋势中的假阳线反弹陷阱"
            >
              <UiIcon name="check" :size="11" v-if="filters.exclude_broken" />
              <span>排除破位股 (&lt;-3%)</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_bjs }"
              @click="filters.exclude_bjs = !filters.exclude_bjs"
              title="【排除北交所】&#10;自动剔除 8/4/920 开头的北交所股票，仅保留流动性更强的沪深主板与双创板标的"
            >
              <UiIcon name="check" :size="11" v-if="filters.exclude_bjs" />
              <span>排除北交所</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_kcb }"
              @click="filters.exclude_kcb = !filters.exclude_kcb"
              title="【排除科创板】&#10;自动剔除 688 开头的科创板股票（适合无科创板交易权限或专注主板的交易者）"
            >
              <UiIcon name="check" :size="11" v-if="filters.exclude_kcb" />
              <span>排除科创板</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: filters.exclude_cyb }"
              @click="filters.exclude_cyb = !filters.exclude_cyb"
              title="【排除创业板】&#10;自动剔除 300/301 开头的创业板股票（适合专注 10cm 涨跌幅主板龙头的交易者）"
            >
              <UiIcon name="check" :size="11" v-if="filters.exclude_cyb" />
              <span>排除创业板</span>
            </div>

            <div
              class="chip-btn"
              :class="{ active: notifyFeishu }"
              @click="notifyFeishu = !notifyFeishu"
              title="【推送到飞书群】&#10;选股扫描完成后，自动将符合条件的强势标的及核心信号明细实时推送至飞书群机器人"
            >
              <UiIcon name="check" :size="11" v-if="notifyFeishu" />
              <span>推送到飞书</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 紧凑执行主操作条 -->
      <div class="execute-center-wrap">
        <button
          class="btn-execute-glow"
          :disabled="running || !selectedRules.length"
          @click="runScreen"
          title="【启动量化选股】&#10;基于本地 18 维高精度日 K 数据底座，利用纯内存向量化计算引擎，毫秒级完成全市场扫描与共振计算"
        >
          <UiIcon name="search" :size="15" />
          <span>{{ running ? '量化引擎极速扫描中…' : (filters.match_mode === 'and' ? '开始量化选股 (执行严格交集严选)' : '开始量化选股 (一键多策略共振扫描)') }}</span>
        </button>
      </div>
    </div>

    <!-- 步骤二：选股结果看板 -->
    <div class="card section-card result-panel" v-if="result">
      <div class="result-header">
        <div class="result-title-group">
          <span class="step-num">2</span>
          <span class="result-main-title">选股结果看板</span>
          <span class="result-stat-badge" title="本次策略筛选的扫描覆盖量与命中达标量">
            扫描 <b>{{ result.scanned }}</b> 只 · 精选命中 <b>{{ result.hit_count }}</b> 只标的
          </span>
        </div>
        <div class="result-extra-info" title="本地 SQLite 向量化纯内存计算耗时">
          <span>耗时 <b>{{ result.elapsed_ms }}ms</b> (本地纯内存向量化计算)</span>
        </div>
      </div>

      <!-- Tab 切换：全部共振聚合榜单 + 单策略筛选 -->
      <div class="tabs-container">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'all_aggregated' }"
          @click="activeTab = 'all_aggregated'"
          :title="filters.match_mode === 'and' ? '查看同时满足所有勾选策略的交集精选标的' : (filters.match_mode === 'resonance' ? '查看多策略共振优选总榜' : '查看所有满足任一策略的并集总榜')"
        >
          {{ filters.match_mode === 'and' ? '🎯 严格交集精选榜' : (filters.match_mode === 'resonance' ? '🌟 共振优选总榜' : '📋 广度并集总榜') }}
          <span class="badge-num">{{ result.items ? result.items.length : result.hit_count }}</span>
        </button>
        <button
          v-for="r in resultRules"
          :key="r"
          class="tab-btn"
          :class="{ active: activeTab === r }"
          @click="activeTab = r"
          :title="`查看符合【${getRuleName(r)}】单策略的全部标的列表`"
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
          title="【共振度优先排序】&#10;按命中的策略数量从多到少排序，多策略共同验证的最强标的排在最前"
        >
          🌟 策略共振度优先
        </button>
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'change_pct' }"
          @click="sortBy = 'change_pct'"
          title="【涨跌幅优先排序】&#10;按今日收盘涨跌幅从高到低排序，强势涨停与领涨龙头排在最前"
        >
          📈 今日涨跌幅优先
        </button>
        <button
          class="sort-btn"
          :class="{ active: sortBy === 'amount' }"
          @click="sortBy = 'amount'"
          title="【成交额优先排序】&#10;按今日总成交金额从大到小排序，市场焦点与高流动性核心标的排在最前"
        >
          💰 成交额优先
        </button>
      </div>

      <!-- 结果明细表格 -->
      <div class="table-box" v-if="sortedDisplayList.length">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width:85px">代码</th>
              <th style="width:105px">名称</th>
              <th style="width:85px" class="tar" title="最新一个交易日的收盘价格">最新收盘</th>
              <th style="width:80px" class="tar" title="最新一个交易日的收盘涨跌幅">涨跌幅</th>
              <th style="width:95px" class="tar" title="最新一个交易日的成交总金额">成交额</th>
              <th style="width:190px" title="该股票同时命中的所有多维量化策略">命中策略共振</th>
              <th class="signal-th tal" style="text-align:left" title="多维策略计算得出的核心形态、买点支撑、均线数据与资金流入明细">技术形态与信号明细</th>
              <th style="width:75px" class="tac action-th">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedDisplayList"
              :key="item.code"
              class="clickable-row"
              @click="openStockModal(item.code, item.name)"
              title="点击查看该股票沉浸式速览"
            >
              <td class="code-col">{{ item.code }}</td>
              <td class="name-col">
                <a @click.stop="openStockModal(item.code, item.name)" title="点击查看个股详情">{{ item.name }}</a>
              </td>
              <td class="tar num-val">{{ item.close != null ? fmtPrice(item.close) : '—' }}</td>
              <td class="tar num-val" :class="pctClass(item.change_pct)">
                {{ item.change_pct != null ? fmtPct(item.change_pct) : '—' }}
              </td>
              <td class="tar num-val dim">{{ item.amount ? fmtAmount(item.amount) : '—' }}</td>
              <td>
                <div class="resonance-tags">
                  <span
                    v-for="r_id in (item.hit_rules && item.hit_rules.length ? item.hit_rules : [activeTab])"
                    :key="r_id"
                    class="tag-resonance"
                    :class="getRuleTagClass(r_id)"
                    :title="`命中策略：${getRuleName(r_id)}`"
                  >
                    {{ getRuleName(r_id) }}
                  </span>
                </div>
              </td>
              <td
                class="signal-col tal"
                style="text-align:left"
                :title="(item.signals && item.signals.length) ? item.signals.map(s => `【${s.name}】：${s.detail}`).join('\n') : item.detail"
              >
                {{ (item.signals && item.signals.length > 1) ? item.signals.map(s => `[${s.name}] ${s.detail}`).join(' · ') : item.detail }}
              </td>
              <td class="tac action-td">
                <button
                  class="btn-view"
                  @click.stop="openStockModal(item.code, item.name)"
                  title="【个股速览】&#10;无需离开当前页面，即刻在居中浮窗中查看该股票的分时走势、日K形态、五档买卖盘与主力资金流详情"
                >
                  速览
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-box">
        <UiIcon name="search" :size="24" style="opacity:0.3;margin-bottom:6px" />
        <div>所选策略组合在当前股票池中未命中符合条件的标的</div>
      </div>
    </div>

    <!-- 历史任务归档 -->
    <details class="card section-card history-panel" v-if="runs.length">
      <summary class="history-summary" title="点击展开/收起历史选股任务归档记录">
        <div class="history-title-wrap">
          <span>📜 历史选股扫描归档 (共 {{ runs.length }} 次)</span>
        </div>
        <div class="history-summary-right">
          <button
            class="btn-clear-history"
            @click.prevent.stop="clearHistory"
            title="清空所有历史选股任务归档记录"
          >
            <UiIcon name="trash" :size="11" /> 清空历史
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
              <th>命中数</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in runs" :key="r.id">
              <td>{{ r.started_at }}</td>
              <td>{{ formatRules(r.rules) }}</td>
              <td>{{ r.scope === 'watchlist' ? '自选股' : '全A股' }}</td>
              <td><b class="accent">{{ r.hit_count }}</b> 只</td>
              <td>
                <span class="action-btn" @click="loadRunDetail(r.id)" title="一键加载并回放本次历史扫描任务的完整选股结果与策略组合">回放结果</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>

    <!-- 个股沉浸式速览大弹窗 (直接嵌入完整 Stock.vue) -->
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
import UiIcon from '../components/ui/UiIcon.vue'
import StockQuickModal from '../components/StockQuickModal.vue'

const STORAGE_KEY = 'niulai_screener_state_v1'

const syncSt = ref({})
const syncing = ref(false)
const syncMsg = ref('')
const syncPct = ref(0)
const syncMode = ref('')
let pollTimer = null

const ruleList = ref([])

// 默认勾选 5 大黄金主升浪共振战法
const DEFAULT_RULES = [
  'breakout',
  'ma_bullish',
  'main_inflow_surge',
  'volume_surge',
  'box_breakout',
]

const selectedRules = ref([...DEFAULT_RULES])
const scope = ref('all')
const notifyFeishu = ref(false)
const sortBy = ref('resonance')
const activeTab = ref('all_aggregated')

const running = ref(false)
const result = ref(null)
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

// 策略组合与排除项过滤器：默认严格交集，默认排除 ST、破位、北交所、科创板、创业板
const filters = reactive({
  match_mode: 'and', // 'and' (严格交集 · 默认) | 'resonance' (共振排序) | 'or' (并集)
  exclude_st: true,
  exclude_broken: true,
  exclude_bjs: true,
  exclude_kcb: true,
  exclude_cyb: true,
})

function selectPresetGolden() {
  selectedRules.value = [...DEFAULT_RULES]
}

function selectAllRules() {
  selectedRules.value = ruleList.value.map(r => r.id)
}

function clearAllRules() {
  selectedRules.value = []
}

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
  syncMsg.value = '正在全市场批量打包拉取收盘日K（约1.5秒）…'
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
  syncMsg.value = `正在增量补齐 ${scope.value === 'watchlist' ? '自选股' : '全市场'} 历史K线…`
  try {
    await api.screenerSyncBars(120, scope.value, 'history')
    startPolling()
  } catch (e) {
    syncing.value = false
    showToast('启动同步失败：' + (e.message || e), 'error')
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const st = await api.screenerSyncStatus()
      syncSt.value = st
      if (!st.running) {
        clearInterval(pollTimer)
        pollTimer = null
        syncing.value = false
        syncMsg.value = ''
        syncPct.value = 0
        if (st.error) {
          showToast('同步异常：' + st.error, 'error')
        } else {
          showToast('日 K 数据底座同步完成', 'success')
        }
      } else {
        syncMsg.value = st.message
        syncPct.value = st.percent || 0
      }
    } catch {}
  }, 1000)
}

async function runScreen() {
  if (!selectedRules.value.length) {
    showToast('请至少选择一个量化策略', 'warn')
    return
  }
  running.value = true
  try {
    const res = await api.screenerRun(
      selectedRules.value,
      scope.value,
      notifyFeishu.value,
      null,
      filters,
    )
    result.value = res
    activeTab.value = 'all_aggregated'
    showToast(`选股完成：扫描 ${res.scanned} 只，精选命中 ${res.hit_count} 只标的`, 'success')
    loadRuns()
  } catch (e) {
    showToast('选股执行失败：' + (e.message || e), 'error')
  } finally {
    running.value = false
  }
}

async function loadRuns() {
  try {
    const res = await api.screenerRuns(20)
    runs.value = res.runs || []
  } catch (e) {
    console.error('loadRuns error:', e)
  }
}

async function loadRunDetail(id) {
  try {
    const detail = await api.screenerRunDetail(id)
    if (detail.error) {
      showToast('加载失败：' + detail.error, 'error')
      return
    }
    result.value = {
      run_id: detail.run.id,
      scanned: detail.items ? detail.items.length : 0,
      hit_count: detail.items ? detail.items.length : 0,
      elapsed_ms: 0,
      items: detail.items || [],
      hits: detail.hits || {},
    }
    activeTab.value = 'all_aggregated'
    showToast(`已加载历史任务 #${id} 结果看板`, 'info')
  } catch (e) {
    showToast('加载任务详情失败：' + (e.message || e), 'error')
  }
}

async function clearHistory() {
  const ok = await showConfirm({
    title: '清空选股归档确认',
    content: '确定要清空所有历史选股任务归档记录吗？该操作不可撤回。',
    confirmText: '确认清空',
    cancelText: '取消',
    danger: true,
  })
  if (!ok) return

  try {
    await api.screenerClearRuns()
    runs.value = []
    showToast('历史选股归档记录已成功清空', 'success')
  } catch (e) {
    showToast('清空历史记录失败：' + (e.message || e), 'error')
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
.screener-page { width: 100%; margin: 0 auto; padding-bottom: 30px; }

.header-section {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px; flex-wrap: wrap; gap: 8px;
}
.title-wrap h2 { margin: 0 0 2px; font-size: 18px; font-weight: 700; color: var(--text); }
.sub-title { font-size: 11px; color: var(--text-dim); }

/* 顶部紧凑数据状态条 */
.top-status-bar {
  display: flex; align-items: center; gap: 12px; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 5px 10px; flex-wrap: wrap;
}
.status-kvs { display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-dim); }
.status-kvs b { color: var(--text); font-variant-numeric: tabular-nums; }
.status-kvs b.accent { color: var(--accent); }
.sk-sep { color: var(--border); }

.status-actions { display: flex; align-items: center; gap: 6px; }
.btn-sync-compact {
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px;
  border-radius: var(--radius-sm); font-size: 11px; font-weight: 600; cursor: pointer;
  border: 1px solid var(--border); transition: all .15s;
}
.btn-sync-compact.primary {
  background: var(--accent-bg); color: var(--accent); border-color: rgba(76, 154, 255, 0.4);
}
.btn-sync-compact.primary:hover:not(:disabled) {
  background: var(--accent); color: #fff;
}
.btn-sync-compact.ghost {
  background: var(--kv-bg); color: var(--text-dim);
}
.btn-sync-compact.ghost:hover:not(:disabled) {
  border-color: var(--accent); color: var(--text);
}
.btn-sync-compact:disabled { opacity: 0.5; cursor: not-allowed; }

.progress-wrap-compact {
  margin-bottom: 8px; padding: 6px 10px; background: var(--bg-card);
  border-radius: var(--radius-md); border: 1px solid var(--border);
}
.progress-track { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; }
.progress-track i { display: block; height: 100%; background: var(--accent); border-radius: 2px; transition: width .3s ease; }
.progress-info { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-dim); margin-top: 3px; }
.progress-pct { font-weight: 700; color: var(--accent); }

/* 卡片模块与标题 */
.section-card { margin-bottom: 10px; padding: 10px 14px; }
.card-header-compact {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; flex-wrap: wrap; gap: 6px;
}
.card-title-compact { display: flex; align-items: center; gap: 6px; }
.step-num {
  width: 17px; height: 17px; border-radius: 50%; background: var(--accent);
  color: #fff; font-size: 10px; display: inline-flex; align-items: center;
  justify-content: center; font-weight: 700; flex-shrink: 0;
}
.st-title-text { font-size: 13px; font-weight: 600; color: var(--text); }
.st-title-text b { color: var(--accent); }

.quick-pick-actions { display: flex; align-items: center; gap: 6px; }
.quick-link-btn {
  background: transparent; border: none; font-size: 11px; color: var(--accent);
  cursor: pointer; padding: 1px 5px; border-radius: 3px; transition: all .12s;
}
.quick-link-btn:hover { background: var(--accent-bg); text-decoration: underline; }

/* 12 大策略紧凑网格 */
.strategy-cards-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 6px; margin-bottom: 10px;
}
.strategy-card-item {
  background: var(--kv-bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 6px 8px; cursor: pointer; transition: all .14s ease;
  display: flex; flex-direction: column; gap: 2px; user-select: none;
}
.strategy-card-item:hover { border-color: var(--accent); background: var(--bg-hover); }
.strategy-card-item.active {
  border-color: var(--accent); background: rgba(76, 154, 255, 0.08);
  box-shadow: 0 0 6px rgba(76, 154, 255, 0.12);
}
.st-header { display: flex; align-items: center; gap: 5px; }
.st-check-box {
  width: 14px; height: 14px; border-radius: 3px; border: 1px solid var(--border);
  background: var(--bg-card); display: inline-flex; align-items: center; justify-content: center;
  color: transparent; transition: all .12s; flex-shrink: 0;
}
.strategy-card-item.active .st-check-box {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.st-name { font-size: 12px; font-weight: 600; color: var(--text); white-space: nowrap; }
.st-badge {
  margin-left: auto; font-size: 10px; color: var(--text-dim);
  background: var(--bg-hover); padding: 1px 4px; border-radius: 3px; white-space: nowrap;
}
.badge-fire { color: var(--up); background: var(--up-bg); font-weight: 600; }
.badge-diamond { color: var(--accent); background: var(--accent-bg); font-weight: 600; }
.badge-rocket { color: #a855f7; background: rgba(168, 85, 247, 0.12); font-weight: 600; }
.badge-target { color: #22c55e; background: rgba(34, 197, 94, 0.12); font-weight: 600; }
.st-desc {
  font-size: 10.5px; color: var(--text-dim); line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 过滤排雷面板 */
.filter-panel {
  border-top: 1px solid var(--border); padding-top: 8px;
  display: flex; flex-direction: column; gap: 6px; margin-bottom: 10px;
}
.filter-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.filter-title { font-size: 11px; font-weight: 600; color: var(--text-dim); min-width: 60px; }
.filter-options { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.radio-pill {
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px;
  border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); font-size: 11px;
  cursor: pointer; user-select: none; transition: all .15s;
}
.radio-pill:hover { border-color: var(--accent); color: var(--text); }
.radio-pill.active {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}
.radio-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--border); }
.radio-pill.active .radio-dot { background: var(--accent); }

.filter-chips { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; }
.chip-btn {
  display: inline-flex; align-items: center; gap: 3px; padding: 3px 7px;
  border-radius: var(--radius-sm); border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); font-size: 11px;
  cursor: pointer; user-select: none; transition: all .15s;
}
.chip-btn:hover { border-color: var(--accent); color: var(--text); }
.chip-btn.active {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}

/* 居中执行主按钮 */
.execute-center-wrap {
  display: flex; justify-content: center; padding: 2px 0 0;
}
.btn-execute-glow {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  padding: 7px 30px; border-radius: 18px; border: none;
  background: linear-gradient(135deg, #4c9aff 0%, #2563eb 100%);
  color: #ffffff; font-size: 13px; font-weight: 700; cursor: pointer;
  box-shadow: 0 2px 10px rgba(37, 99, 235, 0.35); transition: all .16s ease;
}
.btn-execute-glow:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 3px 14px rgba(37, 99, 235, 0.45);
  background: linear-gradient(135deg, #60a5fa 0%, #1d4ed8 100%);
}
.btn-execute-glow:active:not(:disabled) { transform: translateY(0); }
.btn-execute-glow:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

/* 结果面板 */
.result-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; flex-wrap: wrap; gap: 6px;
}
.result-title-group { display: flex; align-items: center; gap: 6px; }
.result-main-title { font-size: 14px; font-weight: 700; color: var(--text); }
.result-stat-badge {
  font-size: 11px; color: var(--text-dim); background: var(--bg-hover);
  padding: 2px 6px; border-radius: var(--radius-sm); margin-left: 3px;
}
.result-stat-badge b { color: var(--accent); }
.result-extra-info { font-size: 11px; color: var(--text-dim); }

.tabs-container { display: flex; gap: 5px; margin-bottom: 8px; flex-wrap: wrap; }
.tab-btn {
  padding: 3px 10px; border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-dim); font-size: 11px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 4px; transition: all .15s;
}
.tab-btn:hover { color: var(--text); border-color: var(--accent); }
.tab-btn.active {
  background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600;
}
.badge-num {
  font-size: 10px; background: rgba(0, 0, 0, 0.2); padding: 1px 4px; border-radius: 6px;
}
.tab-btn.active .badge-num { background: rgba(255, 255, 255, 0.25); color: #fff; }

.sort-bar {
  display: flex; align-items: center; gap: 5px; margin-bottom: 8px;
  font-size: 11px; color: var(--text-dim);
}
.sort-btn {
  padding: 2px 7px; border-radius: 3px; border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); cursor: pointer; font-size: 11px;
  transition: all .15s;
}
.sort-btn:hover { color: var(--text); border-color: var(--accent); }
.sort-btn.active {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}

.table-box {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-card);
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  table-layout: auto;
}
.data-table th {
  background: var(--bg-hover);
  color: var(--text-dim);
  font-weight: 500;
  padding: 7px 10px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  white-space: nowrap;
}
.data-table td {
  padding: 7px 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.clickable-row { cursor: pointer; transition: background .12s; }
.clickable-row:hover { background: var(--bg-hover); }
.clickable-row:last-child td { border-bottom: none; }

.code-col { font-weight: 600; color: var(--text); font-variant-numeric: tabular-nums; white-space: nowrap; }
.name-col a { color: var(--accent); font-weight: 600; cursor: pointer; white-space: nowrap; }
.name-col a:hover { text-decoration: underline; }
.num-val { font-variant-numeric: tabular-nums; font-weight: 600; white-space: nowrap; }
.num-val.dim { font-weight: normal; color: var(--text-dim); }

.resonance-tags { display: flex; gap: 3px; flex-wrap: wrap; }
.tag-resonance {
  font-size: 10px; padding: 1px 4px; border-radius: 3px;
  background: var(--bg-hover); color: var(--text); border: 1px solid var(--border);
  white-space: nowrap;
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

.signal-th {
  min-width: 240px;
  text-align: left !important;
}
.signal-col {
  font-size: 11px;
  color: var(--text);
  line-height: 1.45;
  white-space: normal;
  word-break: break-word;
  text-align: left !important;
}

.action-th, .action-td {
  width: 70px;
  min-width: 70px;
  max-width: 70px;
  text-align: center;
  white-space: nowrap;
}

.btn-view {
  padding: 3px 9px;
  font-size: 11px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--kv-bg);
  color: var(--accent);
  cursor: pointer;
  transition: all .15s;
  font-weight: 600;
  white-space: nowrap;
}
.btn-view:hover {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.empty-box {
  padding: 24px 0; text-align: center; color: var(--text-dim); font-size: 12px;
  display: flex; flex-direction: column; align-items: center;
}

/* 历史面板 */
.history-summary {
  cursor: pointer; user-select: none; font-size: 12px; font-weight: 600;
  color: var(--text); display: flex; align-items: center; justify-content: space-between;
  padding: 2px 0;
}
.history-summary-right { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.chevron-indicator {
  display: inline-flex; align-items: center; gap: 4px; font-size: 11px;
  color: var(--text-dim); font-weight: normal;
}
.chevron-arrow { transition: transform .2s ease; display: inline-block; font-size: 10px; }
details[open] .chevron-arrow { transform: rotate(180deg); }
details[open] .chevron-text { color: var(--accent); }

.btn-clear-history {
  padding: 2px 7px; font-size: 11px; border-radius: 3px; border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); cursor: pointer; display: inline-flex;
  align-items: center; gap: 3px; transition: all .15s;
}
.btn-clear-history:hover { color: var(--up); border-color: var(--up); background: var(--up-bg); }

.history-table-wrap { margin-top: 6px; overflow-x: auto; }
.action-btn { color: var(--accent); font-size: 11px; cursor: pointer; }
.action-btn:hover { text-decoration: underline; }
</style>
