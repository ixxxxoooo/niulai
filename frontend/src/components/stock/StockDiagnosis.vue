<template>
  <div class="card mt16 stock-diagnosis-card" v-if="loading || (data && Object.keys(data).length)">
    <div class="diagnosis-header">
      <div class="diagnosis-title-group">
        <span class="card-title">智能诊股与综合研判</span>
        <div class="diag-meta" v-if="data && data.diagnose_time">
          <span class="diag-time">{{ data.diagnose_time.slice(0, 10) }}</span>
          <span class="diag-badge score" v-if="evalData.total_score != null">
            {{ Number(evalData.total_score).toFixed(1) }}分
          </span>
          <span class="diag-badge control" :class="controlClass" v-if="mfData.control_type">
            {{ mfData.control_type }}
          </span>
        </div>
      </div>

      <div class="diagnosis-tabs">
        <button
          class="diag-tab"
          :class="{ active: activeTab === 'eval' }"
          @click="activeTab = 'eval'"
        >
          综合评价
        </button>
        <button
          class="diag-tab"
          :class="{ active: activeTab === 'main_force' }"
          @click="activeTab = 'main_force'"
        >
          主力控盘
        </button>
        <button
          class="diag-tab"
          :class="{ active: activeTab === 'shareholders' }"
          @click="activeTab = 'shareholders'"
        >
          股东筹码
        </button>
        <button
          class="diag-tab"
          :class="{ active: activeTab === 'trend' }"
          @click="activeTab = 'trend'"
        >
          趋势研判
        </button>
        <button
          class="diag-tab"
          :class="{ active: activeTab === 'flow' }"
          @click="activeTab = 'flow'"
        >
          资金动向
        </button>
        <a class="source-link" :href="eastmoneyCommentUrl" target="_blank" rel="noopener">
          千股千评 <UiIcon name="external" :size="11" />
        </a>
      </div>
    </div>

    <!-- 加载态 -->
    <div v-if="loading && !data" class="diag-loading">
      <UiIcon name="refresh" :size="14" class="rotating" /> 研判数据加载中…
    </div>

    <div v-else-if="data" class="diag-body">
      <!-- 1. 综合评价 -->
      <div v-if="activeTab === 'eval'" class="tab-pane">
        <div class="eval-grid">
          <!-- 评分大卡 -->
          <div class="eval-score-card">
            <div class="score-num-wrap">
              <div class="score-main">{{ evalData.total_score != null ? Number(evalData.total_score).toFixed(1) : '-' }}</div>
              <div class="score-sub">
                <span class="score-label">综合得分</span>
                <span class="score-diff" :class="pctClass(evalData.score_change)" v-if="evalData.score_change != null">
                  较前日 {{ evalData.score_change >= 0 ? '+' : '' }}{{ Number(evalData.score_change).toFixed(1) }}
                </span>
              </div>
            </div>
            <div class="beat-bar-wrap" v-if="evalData.beat_ratio != null">
              <div class="beat-text">打败了全市场 <strong>{{ Number(evalData.beat_ratio).toFixed(1) }}%</strong> 的股票</div>
              <div class="progress-track">
                <div class="progress-bar" :style="{ width: Math.min(100, Math.max(0, evalData.beat_ratio)) + '%' }"></div>
              </div>
            </div>
          </div>

          <!-- 智能点评语 -->
          <div class="eval-comment-card">
            <div class="comment-quote-icon">“</div>
            <p class="comment-text">{{ evalData.words_explain || '暂无详细研判结论。' }}</p>
            <div class="rank-badges-row">
              <div class="rank-chip" v-if="evalData.market_rank != null">
                <span class="chip-k">全市场排名</span>
                <span class="chip-v">第 <strong>{{ evalData.market_rank }}</strong> / {{ evalData.market_total || 5000 }} 名</span>
              </div>
              <div class="rank-chip" v-if="evalData.industry_rank != null">
                <span class="chip-k">{{ evalData.industry_name || '行业' }}排名</span>
                <span class="chip-v">第 <strong>{{ evalData.industry_rank }}</strong> / {{ evalData.industry_total || '-' }} 名</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 大数据涨跌预测卡片 -->
        <div class="predict-row mt16">
          <div class="predict-card">
            <div class="predict-header">
              <span class="p-title">次日涨跌预测</span>
              <span class="p-sample" v-if="evalData.predict_next_day?.sample_count">样本量：{{ fmtNum(evalData.predict_next_day.sample_count, 0) }}</span>
            </div>
            <div class="predict-main">
              <div class="p-prob-group">
                <span class="p-k">上涨概率</span>
                <span class="p-v" :class="pctClass(evalData.predict_next_day?.rise_prob != null ? evalData.predict_next_day.rise_prob - 50 : 0)">
                  {{ evalData.predict_next_day?.rise_prob != null ? Number(evalData.predict_next_day.rise_prob).toFixed(1) + '%' : '-' }}
                </span>
              </div>
              <div class="p-avg-group">
                <span class="p-k">平均涨跌</span>
                <span class="p-v" :class="pctClass(evalData.predict_next_day?.avg_increase)">
                  {{ evalData.predict_next_day?.avg_increase != null ? fmtPct(evalData.predict_next_day.avg_increase) : '-' }}
                </span>
              </div>
            </div>
            <div class="progress-track" v-if="evalData.predict_next_day?.rise_prob != null">
              <div
                class="progress-bar"
                :class="evalData.predict_next_day.rise_prob >= 50 ? 'up' : 'down'"
                :style="{ width: Math.min(100, Math.max(0, evalData.predict_next_day.rise_prob)) + '%' }"
              ></div>
            </div>
          </div>

          <div class="predict-card">
            <div class="predict-header">
              <span class="p-title">5日涨跌预测</span>
              <span class="p-sample" v-if="evalData.predict_5_day?.sample_count">样本量：{{ fmtNum(evalData.predict_5_day.sample_count, 0) }}</span>
            </div>
            <div class="predict-main">
              <div class="p-prob-group">
                <span class="p-k">上涨概率</span>
                <span class="p-v" :class="pctClass(evalData.predict_5_day?.rise_prob != null ? evalData.predict_5_day.rise_prob - 50 : 0)">
                  {{ evalData.predict_5_day?.rise_prob != null ? Number(evalData.predict_5_day.rise_prob).toFixed(1) + '%' : '-' }}
                </span>
              </div>
              <div class="p-avg-group">
                <span class="p-k">平均涨跌</span>
                <span class="p-v" :class="pctClass(evalData.predict_5_day?.avg_increase)">
                  {{ evalData.predict_5_day?.avg_increase != null ? fmtPct(evalData.predict_5_day.avg_increase) : '-' }}
                </span>
              </div>
            </div>
            <div class="progress-track" v-if="evalData.predict_5_day?.rise_prob != null">
              <div
                class="progress-bar"
                :class="evalData.predict_5_day.rise_prob >= 50 ? 'up' : 'down'"
                :style="{ width: Math.min(100, Math.max(0, evalData.predict_5_day.rise_prob)) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. 主力控盘 -->
      <div v-else-if="activeTab === 'main_force'" class="tab-pane">
        <div class="mf-grid">
          <!-- 控盘状态卡片 -->
          <div class="mf-status-card">
            <div class="mf-status-top">
              <div class="mf-control-badge" :class="controlClass">
                {{ mfData.control_type || '暂无评定' }}
              </div>
              <div class="mf-org-info">
                <span class="mf-k">机构参与度</span>
                <span class="mf-org-val">{{ mfData.org_participate != null ? mfData.org_participate + '%' : '-' }}</span>
              </div>
            </div>
            <div class="progress-track mt8" v-if="mfData.org_participate != null">
              <div class="progress-bar up" :style="{ width: Math.min(100, Math.max(0, mfData.org_participate)) + '%' }"></div>
            </div>

            <!-- 主力净买率指标 -->
            <div class="mf-ratios-grid mt16">
              <div class="mf-ratio-item">
                <span class="r-k">主力净买率</span>
                <span class="r-v" :class="pctClass(mfData.main_ratio)">{{ mfData.main_ratio != null ? fmtPct(mfData.main_ratio) : '-' }}</span>
              </div>
              <div class="mf-ratio-item">
                <span class="r-k">3日主力净买率</span>
                <span class="r-v" :class="pctClass(mfData.main_ratio_3d)">{{ mfData.main_ratio_3d != null ? fmtPct(mfData.main_ratio_3d) : '-' }}</span>
              </div>
              <div class="mf-ratio-item">
                <span class="r-k">50日主力净买率</span>
                <span class="r-v" :class="pctClass(mfData.main_ratio_50d)">{{ mfData.main_ratio_50d != null ? fmtPct(mfData.main_ratio_50d) : '-' }}</span>
              </div>
            </div>
          </div>

          <!-- 主力持仓成本线 -->
          <div class="mf-cost-card">
            <div class="cost-title">主力持仓成本线对照</div>
            <div class="cost-items">
              <div class="cost-item current">
                <span class="c-k">当前现价</span>
                <span class="c-v">{{ fmtPrice(price) }}</span>
              </div>
              <div class="cost-item">
                <span class="c-k">当期主力成本</span>
                <span class="c-v">{{ fmtPrice(mfData.prime_cost) }}</span>
                <span class="c-tag" :class="priceDiffClass(mfData.prime_cost)">
                  {{ priceDiffText(mfData.prime_cost) }}
                </span>
              </div>
              <div class="cost-item">
                <span class="c-k">20日主力成本</span>
                <span class="c-v">{{ fmtPrice(mfData.prime_cost_20d) }}</span>
                <span class="c-tag" :class="priceDiffClass(mfData.prime_cost_20d)">
                  {{ priceDiffText(mfData.prime_cost_20d) }}
                </span>
              </div>
              <div class="cost-item">
                <span class="c-k">60日主力成本</span>
                <span class="c-v">{{ fmtPrice(mfData.prime_cost_60d) }}</span>
                <span class="c-tag" :class="priceDiffClass(mfData.prime_cost_60d)">
                  {{ priceDiffText(mfData.prime_cost_60d) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 超大单/大单分布明细 -->
        <div class="mf-flows-row mt16">
          <div class="mf-flow-box">
            <span class="fb-k">超大单流入 / 流出</span>
            <span class="fb-v">
              <span class="up">{{ fmtAmount(mfData.superdeal_inflow) }}</span> /
              <span class="down">{{ fmtAmount(mfData.superdeal_outflow) }}</span>
            </span>
          </div>
          <div class="mf-flow-box">
            <span class="fb-k">大单流入 / 流出</span>
            <span class="fb-v">
              <span class="up">{{ fmtAmount(mfData.bigdeal_inflow) }}</span> /
              <span class="down">{{ fmtAmount(mfData.bigdeal_outflow) }}</span>
            </span>
          </div>
          <div class="mf-flow-box">
            <span class="fb-k">主力合计净流入</span>
            <span class="fb-v" :class="pctClass(mfData.prime_inflow)">
              {{ fmtAmount(mfData.prime_inflow) }}
            </span>
          </div>
        </div>
      </div>

      <!-- 3. 股东筹码（股东户数与筹码集中度） -->
      <div v-else-if="activeTab === 'shareholders'" class="tab-pane">
        <!-- 核心指标卡片 -->
        <div class="sh-summary-grid" v-if="shLatest.holder_num != null">
          <div class="sh-card">
            <div class="sh-k">最新股东总户数</div>
            <div class="sh-v highlight">{{ fmtNum(shLatest.holder_num, 0) }} <span class="sh-unit">户</span></div>
            <div class="sh-sub">截至 {{ shLatest.end_date || '-' }}</div>
          </div>
          <div class="sh-card">
            <div class="sh-k">较上期增减户数</div>
            <div class="sh-v" :class="pctClass(shLatest.holder_change)">
              {{ shLatest.holder_change != null ? (shLatest.holder_change > 0 ? '+' : '') + fmtNum(shLatest.holder_change, 0) + ' 户' : '-' }}
            </div>
            <div class="sh-sub" :class="pctClass(shLatest.change_ratio)">
              变动比例 {{ shLatest.change_ratio != null ? (shLatest.change_ratio > 0 ? '+' : '') + Number(shLatest.change_ratio).toFixed(2) + '%' : '-' }}
            </div>
          </div>
          <div class="sh-card">
            <div class="sh-k">筹码集中度评级</div>
            <div class="sh-v">
              <span class="focus-pill" :class="focusPillClass(shLatest.hold_focus)">
                {{ shLatest.hold_focus || '暂无评定' }}
              </span>
            </div>
            <div class="sh-sub">
              <span v-if="shLatest.change_ratio != null">
                {{ shLatest.change_ratio < 0 ? '筹码趋于集中（主力吸筹）' : (shLatest.change_ratio > 0 ? '筹码趋于分散（散户接盘）' : '筹码保持稳定') }}
              </span>
              <span v-else>东财大数据评级</span>
            </div>
          </div>
          <div class="sh-card">
            <div class="sh-k">户均持股市值</div>
            <div class="sh-v accent">{{ shLatest.avg_hold_amt != null ? fmtAmount(shLatest.avg_hold_amt) : '-' }}</div>
            <div class="sh-sub">户均持股 {{ shLatest.avg_shares != null ? fmtNum(shLatest.avg_shares, 0) + ' 股' : '-' }}</div>
          </div>
        </div>

        <!-- 股东户数与筹码变动历史表 -->
        <div class="sh-history-wrap mt16" v-if="shHistory.length">
          <div class="sh-table-title">
            <span>近 8 期股东户数与筹码变动历史</span>
            <span class="sh-table-tip">数据来源：上市公司定期报告与互动平台披露</span>
          </div>
          <div class="table-wrap">
            <table class="data-table sh-table">
              <thead>
                <tr>
                  <th>截止日期</th>
                  <th>股东总户数</th>
                  <th>较上期增减</th>
                  <th>变动比例</th>
                  <th>筹码集中度</th>
                  <th>户均持股 (股)</th>
                  <th>户均市值</th>
                  <th>统计期收盘价</th>
                  <th>公告日期</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(h, idx) in shHistory" :key="h.end_date || idx">
                  <td class="td-date">{{ h.end_date || '-' }}</td>
                  <td class="td-num"><strong>{{ fmtNum(h.holder_num, 0) }}</strong> 户</td>
                  <td :class="pctClass(h.holder_change)">
                    {{ h.holder_change != null ? (h.holder_change > 0 ? '+' : '') + fmtNum(h.holder_change, 0) : '-' }}
                  </td>
                  <td :class="pctClass(h.change_ratio)">
                    {{ h.change_ratio != null ? (h.change_ratio > 0 ? '+' : '') + Number(h.change_ratio).toFixed(2) + '%' : '-' }}
                  </td>
                  <td>
                    <span class="focus-tag" :class="focusPillClass(h.hold_focus)">{{ h.hold_focus || '—' }}</span>
                  </td>
                  <td>{{ h.avg_shares != null ? fmtNum(h.avg_shares, 0) : '-' }}</td>
                  <td class="accent">{{ h.avg_hold_amt != null ? fmtAmount(h.avg_hold_amt) : '-' }}</td>
                  <td>{{ h.price != null ? fmtPrice(h.price) : '-' }}</td>
                  <td class="td-dim">{{ h.notice_date || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else class="expand-empty" style="padding: 24px">
          暂无历史股东户数数据
        </div>
      </div>

      <!-- 4. 趋势研判 -->
      <div v-else-if="activeTab === 'trend'" class="tab-pane">
        <!-- 趋势官方点评 -->
        <div class="trend-comment-box">
          <div class="tc-title">
            <UiIcon name="lamp" :size="14" />
            <span>趋势与量能研判</span>
          </div>
          <p class="tc-content">{{ trendData.comment || '暂无趋势点评。' }}</p>
        </div>

        <!-- 关键位与均线量能 -->
        <div class="trend-levels-row mt16">
          <div class="level-card support">
            <span class="lv-k">短期支撑位</span>
            <span class="lv-v">{{ fmtPrice(trendData.support_level) }}</span>
            <span class="lv-sub" v-if="trendData.support_level && price">
              距现价 {{ Number(((trendData.support_level - price) / price) * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="level-card pressure">
            <span class="lv-k">短期压力位</span>
            <span class="lv-v">{{ fmtPrice(trendData.pressure_level) }}</span>
            <span class="lv-sub" v-if="trendData.pressure_level && price">
              距现价 {{ Number(((trendData.pressure_level - price) / price) * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="level-card info">
            <span class="lv-k">量能与均线状态</span>
            <span class="lv-v highlight">{{ trendData.volume_judge || '-' }}</span>
            <span class="lv-sub">{{ trendData.price_relation || '均线' }}</span>
          </div>
        </div>

        <!-- 6大技术指标信号矩阵 -->
        <div class="signals-matrix mt16">
          <div class="matrix-title">6 大经典指标信号矩阵</div>
          <div class="signals-grid">
            <div
              v-for="s in (trendData.signals || [])"
              :key="s.key"
              class="signal-card"
              :class="signalCardClass(s.color)"
            >
              <div class="sc-header">
                <span class="sc-name">{{ s.title }}</span>
                <span class="sc-badge" :class="signalBadgeClass(s.color)">{{ signalLabel(s.color) }}</span>
              </div>
              <p class="sc-text">{{ s.text }}</p>
            </div>
          </div>
        </div>

        <!-- 60交易日统计 -->
        <div class="stats-60d-row mt16" v-if="trendData.stats_60d">
          <div class="stat-box">
            <span class="sb-k">近60日涨跌幅</span>
            <span class="sb-v" :class="pctClass(trendData.stats_60d.stock_change)">
              {{ fmtPct(trendData.stats_60d.stock_change) }}
            </span>
          </div>
          <div class="stat-box">
            <span class="sb-k">区间振幅</span>
            <span class="sb-v">{{ trendData.stats_60d.swing != null ? Number(trendData.stats_60d.swing).toFixed(1) + '%' : '-' }}</span>
          </div>
          <div class="stat-box">
            <span class="sb-k">跑赢沪深300</span>
            <span class="sb-v" :class="pctClass(trendData.stats_60d.stock_change != null && trendData.stats_60d.index_change != null ? trendData.stats_60d.stock_change - trendData.stats_60d.index_change : null)">
              {{ trendData.stats_60d.stock_change != null && trendData.stats_60d.index_change != null ? fmtPct(trendData.stats_60d.stock_change - trendData.stats_60d.index_change) : '-' }}
            </span>
          </div>
          <div class="stat-box">
            <span class="sb-k">日均换手率</span>
            <span class="sb-v">{{ trendData.stats_60d.avg_turnover != null ? Number(trendData.stats_60d.avg_turnover).toFixed(2) + '%' : '-' }}</span>
          </div>
        </div>
      </div>

      <!-- 5. 资金动向 -->
      <div v-else-if="activeTab === 'flow'" class="tab-pane">
        <div class="flow-tab-content">
          <div class="flow-header-intro">
            <span>主力大单与超大单资金流向追踪（单位：万元）</span>
          </div>
          <div class="flow-summary-grid">
            <div class="flow-card">
              <span class="fc-k">超大单净流入</span>
              <span class="fc-v" :class="pctClass((mfData.superdeal_inflow || 0) - (mfData.superdeal_outflow || 0))">
                {{ fmtAmount((mfData.superdeal_inflow || 0) - (mfData.superdeal_outflow || 0)) }}
              </span>
            </div>
            <div class="flow-card">
              <span class="fc-k">大单净流入</span>
              <span class="fc-v" :class="pctClass((mfData.bigdeal_inflow || 0) - (mfData.bigdeal_outflow || 0))">
                {{ fmtAmount((mfData.bigdeal_inflow || 0) - (mfData.bigdeal_outflow || 0)) }}
              </span>
            </div>
            <div class="flow-card">
              <span class="fc-k">主力合计净流入</span>
              <span class="fc-v" :class="pctClass(mfData.prime_inflow)">
                {{ fmtAmount(mfData.prime_inflow) }}
              </span>
            </div>
            <div class="flow-card">
              <span class="fc-k">主力买入占比</span>
              <span class="fc-v highlight">{{ mfData.main_ratio != null ? mfData.main_ratio + '%' : '-' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// @author ygw
import { ref, computed, watch } from 'vue'
import { api } from '../../api.js'
import { fmtAmount, fmtPrice, fmtPct, fmtNum, pctClass } from '../../utils.js'
import UiIcon from '../ui/UiIcon.vue'

const props = defineProps({
  code: { type: String, required: true },
  displayName: { type: String, default: '' },
  price: { type: Number, default: null },
})

const activeTab = ref('eval')
const loading = ref(false)
const data = ref(null)

const eastmoneyCommentUrl = computed(() => {
  const c = props.code.replace(/^(sh|sz|bj)/i, '')
  return `https://data.eastmoney.com/stockcomment/stock/${c}.html`
})

const evalData = computed(() => data.value?.evaluation || {})
const mfData = computed(() => data.value?.main_force || {})
const trendData = computed(() => data.value?.trend || {})
const shData = computed(() => data.value?.shareholders || {})
const shLatest = computed(() => shData.value.latest || {})
const shHistory = computed(() => shData.value.history || [])

const controlClass = computed(() => {
  const t = mfData.value.control_type || ''
  if (t.includes('高度') || t.includes('完全')) return 'control-high'
  if (t.includes('中度')) return 'control-mid'
  if (t.includes('轻度')) return 'control-low'
  if (t.includes('出逃') || t.includes('减持')) return 'control-out'
  return ''
})

function focusPillClass(focus) {
  if (!focus) return ''
  if (focus.includes('非常集中') || focus.includes('高度集中')) return 'focus-high'
  if (focus.includes('较集中') || focus.includes('集中')) return 'focus-mid-high'
  if (focus.includes('较分散') || focus.includes('分散')) return 'focus-mid-low'
  if (focus.includes('非常分散')) return 'focus-low'
  return ''
}

function priceDiffText(cost) {
  if (cost == null || props.price == null) return ''
  const diff = props.price - cost
  const pct = (diff / cost) * 100
  if (Math.abs(pct) < 0.5) return '成本线附近'
  return diff > 0 ? `获利 ${pct.toFixed(1)}%` : `受套 ${Math.abs(pct).toFixed(1)}%`
}

function priceDiffClass(cost) {
  if (cost == null || props.price == null) return ''
  const diff = props.price - cost
  return diff > 0 ? 'up' : 'down'
}

function signalCardClass(color) {
  if (color === '红') return 'signal-up'
  if (color === '绿') return 'signal-down'
  return 'signal-neutral'
}

function signalBadgeClass(color) {
  if (color === '红') return 'badge-up'
  if (color === '绿') return 'badge-down'
  return 'badge-neutral'
}

function signalLabel(color) {
  if (color === '红') return '多头信号'
  if (color === '绿') return '空头信号'
  return '中性提示'
}

async function loadDiagnosis() {
  if (!props.code) return
  loading.value = true
  try {
    const res = await api.stockDiagnosis(props.code)
    data.value = res && Object.keys(res).length ? res : null
  } catch (e) {
    data.value = null
  } finally {
    loading.value = false
  }
}

watch(() => props.code, () => {
  loadDiagnosis()
}, { immediate: true })
</script>

<style scoped>
.stock-diagnosis-card {
  padding: 16px 20px;
}
.diagnosis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
  margin-bottom: 16px;
}
.diagnosis-title-group {
  display: flex;
  align-items: center;
  gap: 12px;
}
.diag-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}
.diag-time {
  color: var(--text-dim);
}
.diag-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: var(--radius-pill);
}
.diag-badge.score {
  background: var(--accent-bg);
  color: var(--accent);
  border: 1px solid var(--accent);
}
.diag-badge.control {
  background: var(--kv-bg);
  color: var(--text);
  border: 1px solid var(--border);
}
.control-high { background: var(--up-bg) !important; color: var(--up) !important; border-color: var(--up) !important; }
.control-mid { background: var(--yellow-bg) !important; color: var(--yellow) !important; border-color: var(--yellow) !important; }
.control-low { background: var(--accent-bg) !important; color: var(--accent) !important; border-color: var(--accent) !important; }
.control-out { background: var(--down-bg) !important; color: var(--down) !important; border-color: var(--down) !important; }

.diagnosis-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
}
.diag-tab {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  color: var(--text-dim);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s ease;
}
.diag-tab:hover {
  color: var(--accent);
  border-color: var(--accent);
}
.diag-tab.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
  font-weight: 700;
}
.diag-loading {
  padding: 30px 0;
  text-align: center;
  color: var(--text-dim);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* 综合评价 Tab */
.eval-grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}
@media (max-width: 768px) {
  .eval-grid { grid-template-columns: 1fr; }
}
.eval-score-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.score-num-wrap {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}
.score-main {
  font-size: 38px;
  font-weight: 800;
  color: var(--accent);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.score-sub {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.score-label {
  font-size: 12px;
  color: var(--text-dim);
}
.score-diff {
  font-size: 12px;
  font-weight: 600;
}
.beat-text {
  font-size: 12px;
  color: var(--text);
  margin-bottom: 6px;
}
.progress-track {
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: var(--accent);
  border-radius: 3px;
  transition: width .4s ease;
}
.progress-bar.up { background: var(--up); }
.progress-bar.down { background: var(--down); }

.eval-comment-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
}
.comment-quote-icon {
  font-size: 32px;
  line-height: 1;
  color: var(--accent);
  opacity: 0.4;
  position: absolute;
  top: 10px;
  left: 14px;
}
.comment-text {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  margin: 0;
  padding-left: 20px;
  font-weight: 500;
}
.rank-badges-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  padding-left: 20px;
}
.rank-chip {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  font-size: 12px;
  display: inline-flex;
  gap: 6px;
}
.chip-k { color: var(--text-dim); }
.chip-v strong { color: var(--accent); }

/* 预测卡片 */
.predict-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 600px) {
  .predict-row { grid-template-columns: 1fr; }
}
.predict-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.predict-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.p-title { font-weight: 700; font-size: 13px; color: var(--text); }
.p-sample { font-size: 11px; color: var(--text-dim); }
.predict-main {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.p-prob-group, .p-avg-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.p-k { font-size: 11px; color: var(--text-dim); }
.p-v { font-size: 16px; font-weight: 700; font-variant-numeric: tabular-nums; }

/* 主力控盘 Tab */
.mf-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 768px) {
  .mf-grid { grid-template-columns: 1fr; }
}
.mf-status-card, .mf-cost-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
}
.mf-status-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.mf-control-badge {
  font-size: 14px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
.mf-org-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}
.mf-k { font-size: 11px; color: var(--text-dim); }
.mf-org-val { font-size: 18px; font-weight: 800; color: var(--up); font-variant-numeric: tabular-nums; }
.mf-ratios-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  text-align: center;
}
.mf-ratio-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.r-k { font-size: 11px; color: var(--text-dim); }
.r-v { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }

.cost-title { font-weight: 700; font-size: 13px; margin-bottom: 12px; }
.cost-items { display: flex; flex-direction: column; gap: 8px; }
.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 4px 0;
  border-bottom: 1px dashed var(--border);
}
.cost-item.current { font-weight: 700; color: var(--accent); }
.cost-item:last-child { border-bottom: none; }
.c-k { color: var(--text-dim); }
.c-v { font-weight: 700; font-variant-numeric: tabular-nums; }
.c-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
}
.c-tag.up { background: var(--up-bg); color: var(--up); }
.c-tag.down { background: var(--down-bg); color: var(--down); }

.mf-flows-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
@media (max-width: 600px) {
  .mf-flows-row { grid-template-columns: 1fr; }
}
.mf-flow-box {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.fb-k { font-size: 11px; color: var(--text-dim); }
.fb-v { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }

/* 趋势研判 Tab */
.trend-comment-box {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.tc-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 13px;
  color: var(--accent);
  margin-bottom: 6px;
}
.tc-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--text);
  margin: 0;
}
.trend-levels-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}
@media (max-width: 600px) {
  .trend-levels-row { grid-template-columns: 1fr; }
}
.level-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.level-card.support { border-left: 3px solid var(--up); }
.level-card.pressure { border-left: 3px solid var(--down); }
.level-card.info { border-left: 3px solid var(--accent); }
.lv-k { font-size: 11px; color: var(--text-dim); }
.lv-v { font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
.lv-v.highlight { font-size: 15px; color: var(--accent); }
.lv-sub { font-size: 11px; color: var(--text-dim); }

.signals-matrix {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.matrix-title {
  font-weight: 700;
  font-size: 13px;
  margin-bottom: 12px;
}
.signals-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
@media (max-width: 768px) {
  .signals-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .signals-grid { grid-template-columns: 1fr; }
}
.signal-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sc-name { font-weight: 700; font-size: 12px; }
.sc-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
}
.badge-up { background: var(--up-bg); color: var(--up); }
.badge-down { background: var(--down-bg); color: var(--down); }
.badge-neutral { background: var(--kv-bg); color: var(--text-dim); }
.sc-text {
  font-size: 11px;
  color: var(--text-dim);
  margin: 0;
  line-height: 1.4;
}

.stats-60d-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 600px) {
  .stats-60d-row { grid-template-columns: repeat(2, 1fr); }
}
.stat-box {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: center;
}
.sb-k { font-size: 11px; color: var(--text-dim); }
.sb-v { font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }

/* 资金动向 Tab */
.flow-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 12px;
}
@media (max-width: 600px) {
  .flow-summary-grid { grid-template-columns: repeat(2, 1fr); }
}
.flow-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: center;
}
.fc-k { font-size: 11px; color: var(--text-dim); }
.fc-v { font-size: 16px; font-weight: 700; font-variant-numeric: tabular-nums; }
.fc-v.highlight { color: var(--accent); }
.flow-header-intro {
  font-size: 12px;
  color: var(--text-dim);
}

/* 股东筹码 Tab */
.sh-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
@media (max-width: 768px) {
  .sh-summary-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .sh-summary-grid { grid-template-columns: 1fr; }
}
.sh-card {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sh-k { font-size: 11px; color: var(--text-dim); }
.sh-v { font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; }
.sh-v.highlight { color: var(--accent); }
.sh-v.accent { color: var(--accent); }
.sh-unit { font-size: 12px; font-weight: 500; color: var(--text-dim); margin-left: 2px; }
.sh-sub { font-size: 11px; color: var(--text-dim); margin-top: 2px; }

.focus-pill {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
}
.focus-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
}
.focus-high { background: rgba(47, 191, 143, 0.15); color: var(--down); }
.focus-mid-high { background: var(--accent-bg); color: var(--accent); }
.focus-mid-low { background: rgba(227, 179, 65, 0.15); color: var(--yellow); }
.focus-low { background: var(--up-bg); color: var(--up); }

.sh-history-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}
.sh-table-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 700;
}
.sh-table-tip {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-dim);
}
.sh-table th {
  font-size: 11px;
  color: var(--text-dim);
  font-weight: 600;
  white-space: nowrap;
}
.sh-table td {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.sh-table .td-date { font-weight: 600; color: var(--text); }
.sh-table .td-num { font-weight: 700; }
.sh-table .td-dim { color: var(--text-dim); }
</style>
