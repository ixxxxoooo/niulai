<template>
  <div class="calendar-page">
    <ToolNavTabs current-tab="calendar" />
    <div class="page-title-row">
      <div>
        <div class="page-title">交易与财经日历</div>
        <div class="page-subtitle">关键交割日 · 期权到期 · 宏观数据 · 央行利率 · 法定休市</div>
      </div>
      <div class="page-actions">
        <button class="btn-tool" @click="load" :disabled="loading" title="刷新数据">
          <UiIcon name="refresh" :size="14" :class="{ rotating: loading }" /> 刷新
        </button>
        <button class="btn-tool" @click="doScreenshot" title="截图日历">
          <UiIcon name="screenshot" :size="14" /> 截图
        </button>
      </div>
    </div>

    <div class="error-banner" v-if="error">{{ error }}</div>

    <div ref="calendarEl">
      <!-- ── 顶部 4 大核心倒计时卡片 ── -->
      <div class="hero-grid mt16" v-if="heroCards.length">
        <div
          v-for="c in heroCards"
          :key="c.key"
          class="hero-card"
          :class="['hero-' + c.badge_color, { 'hero-today': c.days_left === 0 }]"
        >
          <div class="hero-head">
            <span class="hero-badge" :class="'badge-' + c.badge_color">{{ c.badge }}</span>
            <span class="hero-days" :class="{ 'days-alert': c.days_left <= 3 && c.days_left >= 0 }">
              {{ c.status_text }}
            </span>
          </div>
          <div class="hero-title">{{ c.title }}</div>
          <div class="hero-date">{{ c.date }} · {{ formatDateWeekday(c.date) }}</div>
          <div class="hero-target">{{ c.target }}</div>
          <div class="hero-tip" :title="c.tip">💡 {{ c.tip }}</div>
        </div>
      </div>

      <!-- ── 筛选栏与视图切换 ── -->
      <div class="calendar-filter-bar mt16">
        <div class="filter-pills">
          <button
            v-for="f in FILTER_TYPES"
            :key="f.key"
            class="filter-pill"
            :class="{ active: filterType === f.key }"
            @click="filterType = f.key"
          >
            {{ f.label }}
            <span class="pill-count" v-if="countByType(f.key)">{{ countByType(f.key) }}</span>
          </button>
        </div>
        <div class="filter-scope">
          <span class="scope-hint">查看范围：未来 4 个月</span>
        </div>
      </div>

      <!-- ── 按月聚合时间轴 (非解禁模式) ── -->
      <div class="timeline-container mt16" v-if="filterType !== 'unlock'">
        <div v-for="group in groupedEvents" :key="group.monthKey" class="month-group">
          <div class="month-header">
            <span class="month-title">{{ group.monthLabel }}</span>
            <span class="month-count">{{ group.events.length }} 个关键节点</span>
          </div>

          <div class="events-list">
            <div
              v-for="ev in group.events"
              :key="ev.id"
              class="event-card"
              :class="['card-' + ev.badge_color, { 'ev-today': ev.days_left === 0, 'ev-past': ev.days_left < 0 }]"
            >
              <div class="ev-date-col">
                <div class="ev-day">{{ formatDayNumber(ev.date) }}</div>
                <div class="ev-weekday">{{ formatWeekdayShort(ev.date) }}</div>
                <div class="ev-days-tag" :class="ev.status_cls">{{ ev.status_text }}</div>
              </div>

              <div class="ev-body-col">
                <div class="ev-top">
                  <span class="ev-badge" :class="'badge-' + ev.badge_color">{{ ev.type_label }}</span>
                  <span class="ev-title">{{ ev.title }}</span>
                  <span class="ev-time-desc">{{ ev.time_desc }}</span>
                </div>

                <div class="ev-target" v-if="ev.target">
                  <span class="target-label">影响标的：</span>
                  <span class="target-val">{{ ev.target }}</span>
                </div>

                <div class="ev-summary">{{ ev.summary }}</div>

                <div class="ev-tips-box" v-if="ev.tips">
                  <span class="tips-icon">💡 交易策略：</span>
                  <span class="tips-text">{{ ev.tips }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="empty" v-if="!groupedEvents.length && !loading">
          当前筛选分类下无日历事件
        </div>
      </div>

      <!-- ── 限售股解禁看板 (解禁模式) ── -->
      <div class="unlock-container mt16" v-else>
        <div class="card">
          <div class="card-title">
            <span>🔓 未来 60 天两市限售股解禁明细 (共 {{ unlockData.total || 0 }} 笔 · <strong class="text-danger">{{ unlockData.heavy_count || 0 }} 笔大额解禁</strong>)</span>
            <span style="font-size: 12px; color: var(--text-dim)">大额解禁：占总股本 ≥ 5% 或 市值 ≥ 10亿</span>
          </div>

          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th style="text-align:left">解禁日期</th>
                  <th style="text-align:left">股票代码</th>
                  <th style="text-align:left">股票名称</th>
                  <th>解禁股份类型</th>
                  <th>解禁市值</th>
                  <th>占总股本比例</th>
                  <th>占流通盘比例</th>
                  <th style="text-align:center">排雷诊断</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(u, idx) in unlockData.items"
                  :key="idx"
                  :class="{ 'row-danger': u.ratio_total >= 5 || u.market_cap >= 1000000000 }"
                >
                  <td style="text-align:left"><strong>{{ u.date }}</strong></td>
                  <td style="text-align:left"><a @click="openStockDetail(u)">{{ u.code }}</a></td>
                  <td style="text-align:left"><strong class="stock-name" @click="openStockDetail(u)">{{ u.name }}</strong></td>
                  <td><span class="badge-neutral">{{ u.share_type }}</span></td>
                  <td>{{ fmtAmount(u.market_cap) }}</td>
                  <td>
                    <span :class="u.ratio_total >= 5 ? 'pct-badge up' : ''">
                      {{ u.ratio_total ? u.ratio_total.toFixed(2) + '%' : '-' }}
                    </span>
                  </td>
                  <td>{{ u.ratio_float ? u.ratio_float.toFixed(2) + '%' : '-' }}</td>
                  <td style="text-align:center">
                    <button class="btn-tool" style="padding: 2px 8px; font-size: 11px;" @click="openRiskModal(u)">
                      🛡️ 诊断
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>


      <!-- ── 衍生品与交割规则速查手册 ── -->
      <div class="card mt16">
        <div class="card-title" style="cursor: pointer; user-select: none;" @click="showCheatSheet = !showCheatSheet">
          <span>📖 A 股与全球市场关键衍生品交割规则速查手册</span>
          <span style="font-size: 12px; color: var(--text-dim); margin-left: auto">
            {{ showCheatSheet ? '收起 ▲' : '展开查看 ▼' }}
          </span>
        </div>
        <div v-show="showCheatSheet" class="cheatsheet-body">
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>品种分类</th>
                  <th>具体标的</th>
                  <th>标准交割时间</th>
                  <th>顺延规则</th>
                  <th>交易特征与应对策略</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><span class="badge-danger">中金所股指期货</span></td>
                  <td><strong>IF</strong> (沪深300) / <strong>IH</strong> (上证50)<br><strong>IC</strong> (中证500) / <strong>IM</strong> (中证1000)</td>
                  <td>每月第 3 个周五</td>
                  <td>遇法定节假日顺延至下一个交易日</td>
                  <td>最后交易日下午 13:00~15:00 算数平均价结算；主力移仓换月，尾盘波动剧烈，谨防跳水或脉冲。</td>
                </tr>
                <tr>
                  <td><span class="badge-warning">ETF 股票期权</span></td>
                  <td><strong>50ETF</strong> / <strong>300ETF</strong> / <strong>500ETF</strong> / <strong>创业板ETF</strong> 等期权</td>
                  <td>每月第 4 个周三</td>
                  <td>遇法定节假日顺延至下一个交易日</td>
                  <td>到期日虚值期权迅速归零；平值附近多空激烈博弈，现货 ETF 易被资金“磁吸”至关键整数行权价。</td>
                </tr>
                <tr>
                  <td><span class="badge-primary">央行宏观利率</span></td>
                  <td><strong>1年期 LPR</strong> / <strong>5年期以上 LPR</strong></td>
                  <td>每月 20 日 09:00</td>
                  <td>遇法定节假日顺延</td>
                  <td>全国银行间同业拆借中心公布，直接影响房地产按揭、大金融银行估值及流动性预期。</td>
                </tr>
                <tr>
                  <td><span class="badge-success">官方宏观数据</span></td>
                  <td>国家统计局 <strong>制造业 / 非制造业 PMI</strong></td>
                  <td>每月最后一天 09:30</td>
                  <td>法定节假日通常提前或微调</td>
                  <td>50% 荣枯线；高于预期提振顺周期（有色、化工、机械等）与大盘多头信心。</td>
                </tr>
                <tr>
                  <td><span class="badge-warning">美股四巫日</span></td>
                  <td>美股股指期货/期权 + 股票期货/期权</td>
                  <td>每年 3、6、9、12 月第 3 个周五</td>
                  <td>美股休市顺延</td>
                  <td>美股季度衍生品集中结算，成交额创峰值，外盘隔夜波动加剧，常传导至次日 A 股早盘。</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 排雷诊断弹窗 -->
    <RiskModal
      v-if="showRisk"
      :code="riskCode"
      :stock-name="riskName"
      @close="showRisk = false"
    />
  </div>
</template>

<script setup>
/**
 * 交易与财经日历页面
 * @author ygw
 */
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { fmtAmount } from '../utils.js'
import { captureElement } from '../composables/useScreenshot.js'
import { usePageTab } from '../composables/usePageTab.js'
import { openStock } from '../composables/useStockMeta.js'
import RiskModal from '../components/RiskModal.vue'
import ToolNavTabs from '../components/ToolNavTabs.vue'

const loading = ref(false)
const error = ref('')
const heroCards = ref([])
const events = ref([])
const unlockData = ref({ total: 0, heavy_count: 0, items: [] })
const calendarEl = ref(null)
const showCheatSheet = ref(true)

// 排雷弹窗状态
const showRisk = ref(false)
const riskCode = ref('')
const riskName = ref('')

function openRiskModal(row) {
  riskCode.value = row.code
  riskName.value = row.name
  showRisk.value = true
}

function openStockDetail(row) {
  openStock(row, { origin: '/calendar', originLabel: '返回日历' })
}

const filterType = usePageTab('calendar_filter', 'all')

const FILTER_TYPES = [
  { key: 'all', label: '全部事件' },
  { key: 'derivative', label: '🔴 衍生品交割' },
  { key: 'macro', label: '🔵 央行与宏观' },
  { key: 'unlock', label: '🔓 限售解禁' },
  { key: 'holiday', label: '🟡 节假日休市' },
  { key: 'global', label: '🌍 国际大事件' },
]

function countByType(typeKey) {
  if (typeKey === 'all') return events.value.length
  if (typeKey === 'unlock') return unlockData.value.items.length
  return events.value.filter(e => e.type === typeKey).length
}

const filteredEvents = computed(() => {
  if (filterType.value === 'all') return events.value
  return events.value.filter(e => e.type === filterType.value)
})


const groupedEvents = computed(() => {
  const map = new Map()
  for (const ev of filteredEvents.value) {
    const monthKey = String(ev.date).slice(0, 7) // YYYY-MM
    if (!map.has(monthKey)) {
      const [y, m] = monthKey.split('-')
      map.set(monthKey, {
        monthKey,
        monthLabel: `${y} 年 ${parseInt(m, 10)} 月`,
        events: [],
      })
    }
    map.get(monthKey).events.push(ev)
  }
  return Array.from(map.values())
})

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function formatDateWeekday(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return WEEKDAYS[d.getDay()] || ''
}

function formatDayNumber(dateStr) {
  if (!dateStr) return ''
  return String(dateStr).slice(8, 10)
}

function formatWeekdayShort(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return WEEKDAYS[d.getDay()] || ''
}

async function load() {
  loading.value = true
  try {
    const [evData, unData] = await Promise.all([
      api.calendarEvents(4).catch(() => ({ hero_cards: [], events: [] })),
      api.calendarUnlocks(60).catch(() => ({ total: 0, heavy_count: 0, items: [] })),
    ])
    heroCards.value = evData.hero_cards || []
    events.value = evData.events || []
    unlockData.value = unData || { total: 0, heavy_count: 0, items: [] }
    error.value = ''
  } catch (e) {
    error.value = '日历数据加载失败：' + e.message
  } finally {
    loading.value = false
  }
}

async function doScreenshot() {
  if (!calendarEl.value) return
  await captureElement(calendarEl.value, '交易与财经日历.png')
}

onMounted(() => {
  load()
})
</script>


<style scoped>
.calendar-page {
  padding-bottom: 30px;
}
.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}
.page-subtitle {
  font-size: 13px;
  color: var(--text-dim);
  margin-top: 4px;
}
.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-tool {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--card-bg);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
}
.btn-tool:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--accent);
  color: var(--accent);
}
.rotating {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 顶部倒计时卡片 */
.hero-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}
.hero-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
  overflow: hidden;
  transition: transform .15s, border-color .15s;
}
.hero-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
}
.hero-card.hero-today {
  border-color: var(--up);
  box-shadow: 0 0 12px rgba(240, 68, 68, 0.2);
}
.hero-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hero-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
}
.hero-days {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
}
.hero-days.days-alert {
  color: var(--up);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}
.hero-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-top: 2px;
}
.hero-date {
  font-size: 13px;
  color: var(--accent);
  font-weight: 600;
}
.hero-target {
  font-size: 12px;
  color: var(--text-dim);
}
.hero-tip {
  font-size: 11px;
  color: var(--text-dim);
  background: var(--kv-bg);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  margin-top: 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 过滤栏 */
.calendar-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.scope-hint {
  font-size: 12px;
  color: var(--text-dim);
}

/* 时间轴 */
.timeline-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.month-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.month-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 6px;
}
.month-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}
.month-count {
  font-size: 12px;
  color: var(--text-dim);
  background: var(--kv-bg);
  padding: 2px 8px;
  border-radius: 12px;
}
.events-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.event-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  transition: all .15s;
}
.event-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow-sm);
}
.event-card.ev-today {
  border-color: var(--up);
  background: linear-gradient(to right, var(--up-bg), var(--bg-card));
}
.event-card.ev-past {
  opacity: 0.65;
}

/* 日期列 */
.ev-date-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding-right: 12px;
  border-right: 1px solid var(--border);
}
.ev-day {
  font-size: 22px;
  font-weight: 800;
  color: var(--text);
  line-height: 1;
}
.ev-weekday {
  font-size: 12px;
  color: var(--text-dim);
  margin-top: 3px;
}
.ev-days-tag {
  font-size: 10px;
  margin-top: 6px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
  font-weight: 600;
}
.ev-days-tag.today { background: var(--up); color: #fff; }
.ev-days-tag.future { background: var(--kv-bg); color: var(--accent); }
.ev-days-tag.past { background: var(--kv-bg); color: var(--text-dim); }

/* 主体列 */
.ev-body-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.ev-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ev-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}
.ev-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
.ev-time-desc {
  font-size: 12px;
  color: var(--text-dim);
  margin-left: auto;
}
.ev-target {
  font-size: 12px;
}
.target-label { color: var(--text-dim); }
.target-val { color: var(--accent); font-weight: 600; }
.ev-summary {
  font-size: 12px;
  color: var(--text-dim);
  line-height: 1.5;
}
.ev-tips-box {
  margin-top: 4px;
  padding: 6px 10px;
  background: var(--kv-bg);
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.5;
  border-left: 3px solid var(--yellow);
}
.tips-icon { font-weight: 600; color: var(--yellow); }
.tips-text { color: var(--text); }

/* 速查手册 */
.cheatsheet-body {
  margin-top: 12px;
}
</style>

