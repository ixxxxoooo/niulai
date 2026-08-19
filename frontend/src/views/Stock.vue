<template>
  <div>
    <StockHeader
      :back-label="backLabel"
      :back-to="backTo"
      :nav="nav"
      :badge-row="badgeRow"
      :display-name="displayName"
      :industry="detail.industry || localMeta.industry"
      :code="detail.code || code"
      :is-watched="isWatched"
      :eastmoney-url="eastmoneyUrl"
      :baidu-url="baiduUrl"
      :iwencai-url="iwencaiUrl"
      :quote-time="detail.time"
      :data-source="quoteSourceLabel"
      :source-tip="quoteSourceTip"
      @sibling="goSibling"
      @toggle-watch="toggleWatch"
      @add-alert="showAlert = true"
      @open-ai="openAiAnalysis"
    />

    <div class="error-banner" v-if="error">{{ error }}</div>

    <StockSnapshot
      :detail="detail"
      :signal-tags="signalTags"
      :vol5-text="vol5Text"
      :vol5-class="vol5Class"
      :concept-list="conceptList"
    />

    <div class="grid-3 mt16">
      <StockCharts
        ref="chartsRef"
        :code="code"
        :detail="detail"
        :trend="trend"
        :display-name="displayName"
        :initial-kline-day="klineDay"
        :sr-levels="srLevels"
        @error="(msg) => error = msg"
        @kline-day="onKlineDay"
      />
      <OrderBook :orderbook="detail.orderbook" :outer="detail.outer" :inner="detail.inner" />
    </div>

    <div class="grid-2 mt16">
      <div class="card">
        <div class="card-title">成交明细（最近 {{ ticks.length }} 笔 · 10 秒刷新）<a class="source-link" :href="eastmoneyUrl" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a></div>
        <div class="table-wrap" style="max-height: 380px; overflow-y: auto;">
          <table class="data-table">
            <thead><tr><th>时间</th><th>价格</th><th>数量(手)</th><th>金额</th><th>方向</th></tr></thead>
            <tbody>
              <tr v-for="(t, i) in ticks" :key="i">
                <td>{{ t.time }}</td>
                <td :class="pctClass(t.direction === 2 ? -1 : 1)">{{ fmtPrice(t.price) }}</td>
                <td>{{ fmtNum(t.volume, 0) }}</td>
                <td>{{ fmtAmount(t.amount) }}</td>
                <td>
                  <span :class="t.direction === 1 ? 'up' : t.direction === 2 ? 'down' : 'flat'">
                    {{ t.direction === 1 ? '买盘' : t.direction === 2 ? '卖盘' : '中性' }}
                  </span>
                </td>
              </tr>
              <tr v-if="!ticks.length"><td colspan="5" class="empty">暂无数据</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <MoneyFlow
        :flow="flow"
        :display-name="displayName"
        :data-source="flowSourceLabel"
        :source-tip="flowSourceTip"
        :code="code"
        @screenshot="screenshotFlow"
      />
    </div>

    <!-- ETF 持仓成分股（成交明细下方） -->
    <div class="card mt16" v-if="isEtf">
      <div class="card-title">
        <span>ETF 持仓成分（前 {{ holdings.length || 10 }} 大持仓）</span>
        <span class="card-title-sub" style="font-weight:400;color:var(--text-dim);font-size:12px">占比 = 占净值比例 · 行情为实时</span>
      </div>
      <div v-if="holdingsLoading" class="empty">正在加载持仓…</div>
      <div class="table-wrap" v-else-if="holdings.length">
        <table class="data-table">
          <thead><tr>
            <th>#</th><th>代码</th><th>名称</th><th>占净值比</th><th>最新价</th><th>涨跌幅</th><th>持股数(万股)</th><th>持仓市值(万元)</th>
          </tr></thead>
          <tbody>
            <tr v-for="h in holdings" :key="h.code">
              <td class="dim">{{ h.rank }}</td>
              <td class="dim">{{ h.code }}</td>
              <td><a class="leader-chip" @click="openStockFromHoldings(h)">{{ h.name }}</a></td>
              <td><span class="ratio-pill">{{ h.ratio != null ? h.ratio.toFixed(2) + '%' : '-' }}</span></td>
              <td>{{ h.price != null ? fmtPrice(h.price) : '-' }}</td>
              <td :class="h.change_pct != null ? pctClass(h.change_pct) : ''">{{ h.change_pct != null ? fmtPct(h.change_pct) : '-' }}</td>
              <td>{{ h.shares != null ? fmtNum(h.shares, 0) : '-' }}</td>
              <td>{{ h.market_value != null ? fmtNum(h.market_value, 0) : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty">暂无持仓数据</div>
    </div>

    <AiAnalysisPanel ref="aiPanelRef" :code="code" :name="displayName" />

    <div class="card mt16" v-if="lhb && lhb.date" ref="lhbEl">
      <div class="card-title">
        龙虎榜 · {{ lhb.date }}
        <span v-if="lhb.appear_count > 1" class="lhb-freq">近期上榜 {{ lhb.appear_count }} 次</span>
        <span style="font-weight:400;color:var(--text-dim);flex:1;min-width:0">{{ lhb.reason }}</span>
        <a class="source-link" :href="'https://data.eastmoney.com/stock/lhb/' + (detail.code || code) + '.html'" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
        <button class="btn-screenshot" @click="screenshotEl(lhbEl)" title="截图"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div class="kv-grid lhb-kv-grid mb12">
        <div class="kv"><span class="k">净买额</span><span class="v" :class="pctClass(lhb.net)">{{ fmtAmount(lhb.net, 2) }}</span></div>
        <div class="kv"><span class="k">买入</span><span class="v up">{{ fmtAmount(lhb.buy, 2) }}</span></div>
        <div class="kv"><span class="k">卖出</span><span class="v down">{{ fmtAmount(lhb.sell, 2) }}</span></div>
      </div>
      <div class="grid-2">
        <div>
          <div class="ob-title">买入席位{{ lhb.buy_seats && lhb.buy_seats.length > 5 ? '（多榜单合并，去重 ' + lhb.buy_seats.length + ' 家）' : '' }}</div>
          <table class="data-table">
            <thead><tr><th>席位</th><th>类型</th><th>买入</th><th>卖出</th><th>净额</th></tr></thead>
            <tbody>
              <tr v-for="(s, i) in (lhb.buy_seats || [])" :key="'b'+i" style="cursor:default">
                <td class="analyse-td seat-name-cell">
                  {{ s.name }}
                </td>
                <td><span v-if="!s.nickname" :class="['seat-badge', 'seat-' + (s.type || 'broker')]">{{ s.label || '营业部' }}</span><span v-if="s.nickname" class="youzi-badge" :data-tip="youziTip(s)" @click.stop="goSeat(s.nickname)">{{ s.nickname }}</span></td>
                <td class="up">{{ fmtAmount(s.buy, 2) }}</td>
                <td class="down">{{ fmtAmount(s.sell, 2) }}</td>
                <td :class="pctClass(s.net)">{{ fmtAmount(s.net, 2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div>
          <div class="ob-title">卖出席位{{ lhb.sell_seats && lhb.sell_seats.length > 5 ? '（多榜单合并，去重 ' + lhb.sell_seats.length + ' 家）' : '' }}</div>
          <table class="data-table">
            <thead><tr><th>席位</th><th>类型</th><th>买入</th><th>卖出</th><th>净额</th></tr></thead>
            <tbody>
              <tr v-for="(s, i) in (lhb.sell_seats || [])" :key="'s'+i" style="cursor:default">
                <td class="analyse-td seat-name-cell">
                  {{ s.name }}
                </td>
                <td><span v-if="!s.nickname" :class="['seat-badge', 'seat-' + (s.type || 'broker')]">{{ s.label || '营业部' }}</span><span v-if="s.nickname" class="youzi-badge" :data-tip="youziTip(s)" @click.stop="goSeat(s.nickname)">{{ s.nickname }}</span></td>
                <td class="up">{{ fmtAmount(s.buy, 2) }}</td>
                <td class="down">{{ fmtAmount(s.sell, 2) }}</td>
                <td :class="pctClass(s.net)">{{ fmtAmount(s.net, 2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <details v-if="lhb.history && lhb.history.length > 1" class="lhb-history">
        <summary style="font-size:12px;color:var(--text-dim);cursor:pointer;margin-top:10px">历史上榜（{{ lhb.history.length }}）</summary>
        <div class="lhb-history-list">
          <div v-for="h in lhb.history" :key="h.date" class="lhb-history-item">
            <span>{{ h.date }}</span>
            <span :class="pctClass(h.net)">{{ fmtAmount(h.net) }}</span>
            <span style="color:var(--text-dim)">{{ h.reason }}</span>
          </div>
        </div>
      </details>
    </div>

    <NewsAnnouncements :news="news" :announcements="announcements" />
  </div>

  <AlertQuickModal
    :open="showAlert"
    target-type="stock"
    :code="detail.code || code"
    :name="displayName"
    :price="detail.price"
    :change-pct="detail.change_pct"
    @close="showAlert = false"
  />
</template>

<script setup>
/**
 * 个股详情页：编排子组件，负责数据拉取与信号计算
 * @author ygw
 */
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPrice, fmtNum, fmtPct, pctClass } from '../utils.js'
import { parseHash, navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { isWatched as codeWatched, toggleWatch as tw } from '../composables/useWatchlist.js'
import { ensureIndicators } from '../chartIndicators.js'
import { lookupMeta, peekMeta, rememberStock, openStock } from '../composables/useStockMeta.js'
import { stockNavState, stockNavIndex, switchSiblingStock } from '../composables/useStockNav.js'
import AlertQuickModal from '../components/AlertQuickModal.vue'
import AiAnalysisPanel from '../components/AiAnalysisPanel.vue'
import { captureElement } from '../composables/useScreenshot.js'
import StockHeader from '../components/stock/StockHeader.vue'
import StockSnapshot from '../components/stock/StockSnapshot.vue'
import OrderBook from '../components/stock/OrderBook.vue'
import StockCharts from '../components/stock/StockCharts.vue'
import MoneyFlow from '../components/stock/MoneyFlow.vue'
import NewsAnnouncements from '../components/stock/NewsAnnouncements.vue'

const props = defineProps({ code: { type: String, default: '' } })
const code = ref(props.code || (parseHash().code || ''))

const detail = reactive({})
const trend = ref(null)
const ticks = ref([])
const flow = ref([])
const klineDay = ref(null)
const dayPoints = ref([])
const lhb = ref(null)
const error = ref('')
const isWatched = ref(false)
const showAlert = ref(false)
const srLevels = ref({ support: [], resistance: [] })
const news = ref([])
const announcements = ref([])
const chartsRef = ref(null)
const aiPanelRef = ref(null)
const lhbEl = ref(null)
const localMeta = ref(peekMeta(code.value) || {})
const limitTag = ref(null)
const holdings = ref([])
const holdingsLoading = ref(false)
const isEtf = computed(() => String(detail.classify || localMeta.value.classify || '').toUpperCase() === 'FUND' || /ETF/i.test(String(detail.name || '')))

const PREMIUM_TEXT = { positive: '正面', neutral_positive: '偏正面', neutral: '中性', negative: '负面' }

function youziTip(s) {
  const p = PREMIUM_TEXT[s.premium] ? `属性：${PREMIUM_TEXT[s.premium]}` : ''
  const st = s.style ? `风格：${s.style}` : '风格：待补充'
  return [p, st].filter(Boolean).join('\n')
}

function goSeat(nickname) {
  navigate('/seats?nick=' + encodeURIComponent(nickname))
}
const quoteSource = ref('')
const flowSource = ref('')
const quoteFetchedAt = ref('')
const flowFetchedAt = ref('')

function openAiAnalysis() {
  aiPanelRef.value && aiPanelRef.value.open()
}

const nav = computed(() => stockNavIndex(code.value))
const backTo = computed(() => stockNavState.origin || '')
const backLabel = computed(() => stockNavState.originLabel || '返回')
const conceptList = computed(() => String(detail.concepts || localMeta.value.concepts || '').split(',').map(s => s.trim()).filter(Boolean))
const displayName = computed(() => detail.name || localMeta.value.name || '')
const badgeRow = computed(() => ({
  code: detail.code || code.value,
  name: displayName.value,
  board: detail.board || localMeta.value.board,
  is_st: detail.is_st != null ? detail.is_st : localMeta.value.is_st,
}))
const eastmoneyUrl = computed(() => {
  const c = detail.code || code.value || ''
  const mkt = /^(5|6|9)/.test(c) ? 'sh' : 'sz'
  return `https://quote.eastmoney.com/${mkt}${c}.html`
})
const baiduUrl = computed(() => {
  const c = detail.code || code.value || ''
  return `https://finance.baidu.com/stock/ab-${c}?mainTab=${encodeURIComponent('概览')}`
})
const iwencaiUrl = computed(() => {
  const n = displayName.value || ''
  return n ? `https://www.iwencai.com/screener/result?w=${encodeURIComponent(n)}&querytype=stock` : '#'
})
const quoteSourceLabel = computed(() => quoteSource.value || '')
const quoteSourceTip = computed(() => {
  if (!quoteSource.value) return ''
  return `数据源：${quoteSource.value}${quoteFetchedAt.value ? ' · 上次成功 ' + quoteFetchedAt.value : ''}`
})
const flowSourceLabel = computed(() => {
  if (flow.value.length) return flowSource.value || '东财'
  return flowSource.value || '暂不可用'
})
const flowSourceTip = computed(() => {
  const src = flowSource.value || (flow.value.length ? '东财' : '无数据')
  return `数据源：${src}${flowFetchedAt.value ? ' · 上次成功 ' + flowFetchedAt.value : ''}`
})

const vol5 = computed(() => {
  const pts = dayPoints.value
  if (!pts || pts.length < 6) return null
  const vols = pts.map(p => p.volume)
  const today = vols[vols.length - 1]
  const avg5 = vols.slice(-6, -1).reduce((s, v) => s + v, 0) / 5
  if (avg5 <= 0) return null
  return { ratio: today / avg5, today, avg5 }
})
const vol5Text = computed(() => {
  if (!vol5.value) return '—'
  const r = vol5.value.ratio
  const label = r >= 1.5 ? '放量' : r <= 0.7 ? '缩量' : '平量'
  return `${label} ${r.toFixed(2)} 倍`
})
const vol5Class = computed(() => {
  if (!vol5.value) return 'flat'
  return vol5.value.ratio >= 1.5 ? 'up' : vol5.value.ratio <= 0.7 ? 'down' : 'flat'
})

/**
 * 根据日K收盘价计算连涨/连跌天数及区间累计涨跌幅（平盘中断）。
 * @param {Array} pts K线点
 * @returns {{ up: number, down: number, pct: number|null }}
 */
function calcPriceStreak(pts) {
  if (!pts || pts.length < 2) return { up: 0, down: 0, pct: null }
  let up = 0
  let down = 0
  for (let i = pts.length - 1; i >= 1; i--) {
    const cur = Number(pts[i].close)
    const prev = Number(pts[i - 1].close)
    if (!Number.isFinite(cur) || !Number.isFinite(prev)) break
    if (cur > prev) {
      if (down > 0) break
      up += 1
    } else if (cur < prev) {
      if (up > 0) break
      down += 1
    } else {
      break
    }
  }
  const n = up || down
  let pct = null
  if (n > 0) {
    const end = Number(pts[pts.length - 1].close)
    const base = Number(pts[pts.length - 1 - n].close)
    if (Number.isFinite(end) && Number.isFinite(base) && base !== 0) {
      pct = (end - base) / base * 100
    }
  }
  return { up, down, pct }
}

const signalTags = computed(() => {
  const tags = []
  if (limitTag.value && limitTag.value.lbc) {
    const n = Number(limitTag.value.lbc) || 1
    const kind = limitTag.value.kind
    if (kind === 'zt') {
      const zb = limitTag.value.zb_count || 0
      const base = n <= 1 ? '首板' : `${n}连板`
      tags.push({
        label: zb ? `${base}·炸${zb}` : base,
        cls: 'sig-up sig-hot',
        to: '/ladder',
        desc: `当前处于涨停池，连板数 ${n}${zb ? `，今日曾炸板 ${zb} 次` : ''}。点击查看连板梯队`,
      })
    } else {
      tags.push({
        label: n <= 1 ? '炸板' : `炸板${n}连板`,
        cls: 'sig-down sig-hot',
        to: '/ladder',
        desc: `今日炸板${limitTag.value.zb_count || 1}次，曾封板后打开。点击查看连板梯队`,
      })
    }
  }
  const pts = dayPoints.value
  const price = detail.price
  if (pts && pts.length >= 2) {
    const streak = calcPriceStreak(pts)
    const pctTxt = streak.pct != null
      ? ` ${streak.pct >= 0 ? '+' : ''}${streak.pct.toFixed(2)}%`
      : ''
    if (streak.up >= 2) {
      tags.push({
        label: `连涨${streak.up}天${pctTxt}`, cls: 'sig-up',
        desc: `按日K收盘价连续上涨 ${streak.up} 个交易日（平盘或下跌即中断；至少2天才显示连涨），区间累计涨跌幅${pctTxt || '—'}。连涨越长短期积累越大，注意回调风险`,
      })
    } else if (streak.down >= 2) {
      tags.push({
        label: `连跌${streak.down}天${pctTxt}`, cls: 'sig-down',
        desc: `按日K收盘价连续下跌 ${streak.down} 个交易日（平盘或上涨即中断；至少2天才显示连跌），区间累计涨跌幅${pctTxt || '—'}。关注是否缩量止跌或放量加速`,
      })
    }
  }
  if (pts && pts.length >= 11) {
    const closes = pts.map(p => p.close)
    const ma = (n, i) => closes.slice(i - n + 1, i + 1).reduce((s, v) => s + v, 0) / n
    const i = closes.length - 1
    const ma5 = ma(5, i), ma10 = ma(10, i)
    const ma5p = ma(5, i - 1), ma10p = ma(10, i - 1)
    if (ma5 > ma10 && ma5p <= ma10p) tags.push({ label: '金叉', cls: 'sig-up', desc: 'MA5上穿MA10，短线多头信号，后续看量能配合持续性' })
    else if (ma5 < ma10 && ma5p >= ma10p) tags.push({ label: '死叉', cls: 'sig-down', desc: 'MA5下穿MA10，短线转弱信号，若量能同步萎缩宜观望' })
    else if (ma5 > ma10) tags.push({ label: '多头', cls: 'sig-up', desc: 'MA5持续在MA10上方，多头排列延续中，趋势偏强' })
    else tags.push({ label: '空头', cls: 'sig-down', desc: 'MA5持续在MA10下方，空头排列延续中，趋势偏弱' })
    if (pts.length >= 20) {
      const ma20 = ma(20, i)
      if (price != null && price > ma20 && closes[i - 1] <= ma20) tags.push({ label: '突破MA20', cls: 'sig-up', desc: '站上20日均线（中期趋势线），可能开启中线行情' })
      else if (price != null && price < ma20 && closes[i - 1] >= ma20) tags.push({ label: '跌破MA20', cls: 'sig-down', desc: '跌破20日均线，中期趋势走弱，注意止损或减仓' })
    }
    const ind = ensureIndicators(pts, klineDay.value?.indicators)
    const dif = (ind.macd && ind.macd.dif) || []
    const dea = (ind.macd && ind.macd.dea) || []
    if (dif.length >= 2 && dea.length >= 2) {
      const a = dif[dif.length - 1], b = dea[dea.length - 1]
      const ap = dif[dif.length - 2], bp = dea[dea.length - 2]
      if (a != null && b != null && ap != null && bp != null) {
        if (a > b && ap <= bp) {
          const pos = a > 0 ? '零轴上方' : '零轴下方'
          tags.push({ label: 'MACD金叉', cls: 'sig-up', desc: `DIF上穿DEA（${pos}），${a > 0 ? '强势确认' : '可能反弹'}，关注量能配合` })
        } else if (a < b && ap >= bp) {
          const pos = a > 0 ? '零轴上方' : '零轴下方'
          tags.push({ label: 'MACD死叉', cls: 'sig-down', desc: `DIF下穿DEA（${pos}），${a > 0 ? '高位回调信号' : '弱势延续'}，注意风控` })
        }
      }
    }
    if (ind.kdj && ind.kdj.j && ind.kdj.j.length) {
      const j = ind.kdj.j[ind.kdj.j.length - 1]
      if (j != null && j > 100) tags.push({ label: 'KDJ超买', cls: 'sig-down', desc: `J值${j.toFixed(0)}超买区(>100)，短期有回调风险。高位钝化可能延续但需警惕` })
      else if (j != null && j < 0) tags.push({ label: 'KDJ超卖', cls: 'sig-up', desc: `J值${j.toFixed(0)}超卖区(<0)，短期有反弹需求。低位钝化说明还在探底` })
    }
    if (ind.rsi && ind.rsi.length) {
      const rsi = ind.rsi[ind.rsi.length - 1]
      if (rsi != null && rsi > 80) tags.push({ label: `RSI超买 ${rsi.toFixed(0)}`, cls: 'sig-down', desc: `RSI=${rsi.toFixed(1)}进入超买区(>80)，短线过热有回调压力` })
      else if (rsi != null && rsi < 20) tags.push({ label: `RSI超卖 ${rsi.toFixed(0)}`, cls: 'sig-up', desc: `RSI=${rsi.toFixed(1)}进入超卖区(<20)，超卖修复反弹概率较高` })
    }
  }
  if (detail.volume_ratio != null) {
    const vr = Number(detail.volume_ratio)
    if (vr >= 3) tags.push({ label: `巨量 ${vr.toFixed(1)}x`, cls: 'sig-up', desc: `量比${vr.toFixed(2)}，成交异常放大。上涨中可能加速拉升，高位需警惕主力出货` })
    else if (vr >= 1.5) tags.push({ label: `放量 ${vr.toFixed(1)}x`, cls: 'sig-up', desc: `量比${vr.toFixed(2)}，资金活跃度明显提升。配合上涨健康；高位放量需谨慎` })
    else if (vr <= 0.5) tags.push({ label: `极缩量 ${vr.toFixed(1)}x`, cls: 'sig-down', desc: `量比${vr.toFixed(2)}，成交极度萎缩。可能等待方向选择，一旦放量突破关键位可跟` })
    else if (vr <= 0.8) tags.push({ label: `缩量 ${vr.toFixed(1)}x`, cls: 'sig-down', desc: `量比${vr.toFixed(2)}，交投清淡观望为主。下跌缩量跌势趋缓，上涨缩量动能不足` })
  }
  const flowToday = flow.value.length ? flow.value[flow.value.length - 1].main_inflow : null
  const mainInflow = (flowToday != null && Math.abs(flowToday) > 100) ? flowToday
    : (detail.main_inflow != null && Math.abs(detail.main_inflow) > 100 ? detail.main_inflow : flowToday)
  if (mainInflow != null && mainInflow !== 0) {
    const amt = mainInflow
    const absAmt = Math.abs(amt)
    const fmtV = (v) => v >= 1e8 ? (v / 1e8).toFixed(2) + '亿' : (v / 1e4).toFixed(0) + '万'
    if (amt > 0) tags.push({ label: `主力流入 +${fmtV(absAmt)}`, cls: 'sig-up', desc: `超大单+大单净买入${fmtV(absAmt)}，与下方主力资金流一致。持续流入支撑股价；注意是否伴随拉升` })
    else tags.push({ label: `主力流出 -${fmtV(absAmt)}`, cls: 'sig-down', desc: `超大单+大单净卖出${fmtV(absAmt)}，与下方主力资金流一致。持续流出压制股价；注意是否加速下跌` })
  }
  if (detail.limit_up != null && price != null) {
    const hasLb = limitTag.value && limitTag.value.kind === 'zt'
    if (price >= detail.limit_up) {
      if (!hasLb) tags.push({ label: '涨停', cls: 'sig-up sig-hot', desc: '已达涨停价，多方极强。关注封单量与开板次数，封死则次日高开概率大' })
    }
    else if (price >= detail.limit_up * 0.97) {
      const pct = ((detail.limit_up - price) / price * 100).toFixed(1)
      tags.push({ label: `逼近涨停 ${pct}%`, cls: 'sig-up', desc: `距涨停仅${pct}%，有冲板意图。若量能跟上可能封板；关注封板资金量` })
    }
  }
  if (detail.limit_down != null && price != null) {
    if (price <= detail.limit_down) tags.push({ label: '跌停', cls: 'sig-down sig-hot', desc: '已达跌停价，空方极强。封死次日大概率继续低开，远离为宜' })
    else if (price <= detail.limit_down * 1.03) {
      const pct = ((price - detail.limit_down) / price * 100).toFixed(1)
      tags.push({ label: `逼近跌停 ${pct}%`, cls: 'sig-down', desc: `距跌停仅${pct}%，卖压沉重。若跌停板打开可能有资金抄底，未打开远离` })
    }
  }
  return tags
})

function goSibling(delta) { switchSiblingStock(code.value, delta) }
function onKlineDay(kd) {
  klineDay.value = kd
  dayPoints.value = kd?.points || []
}

async function toggleWatch() {
  const c = detail.code || code.value
  if (!c) return
  await tw(c)
  isWatched.value = codeWatched(c)
}

async function hydrateLocal() {
  const cached = peekMeta(code.value)
  if (cached) localMeta.value = cached
  const m = await lookupMeta(code.value)
  if (m) {
    localMeta.value = { ...localMeta.value, ...m }
    if (!detail.industry && m.industry) detail.industry = m.industry
    if (!detail.concepts && m.concepts) detail.concepts = m.concepts
    if (!detail.name && m.name) detail.name = m.name
    if (!detail.classify && m.classify) detail.classify = m.classify
  }
}

function nowLabel() {
  const d = new Date()
  return d.toTimeString().slice(0, 8)
}

async function loadFast() {
  try {
    const [d, t, lt] = await Promise.all([
      api.stock(code.value),
      api.trends(code.value),
      api.stockLimitTag(code.value).catch(() => null),
    ])
    Object.keys(detail).forEach(k => delete detail[k])
    Object.assign(detail, d)
    rememberStock(d)
    if (d.name) localMeta.value = { ...localMeta.value, ...d }
    trend.value = t
    limitTag.value = lt
    quoteSource.value = d.data_source || d.source || '东财/腾讯'
    quoteFetchedAt.value = d.fetched_at || nowLabel()
    error.value = ''
    loadHoldings()
  } catch (e) {
    error.value = '实时数据加载失败：' + e.message
  }
}

/** 从 ETF 持仓点击成分股，进入其详情页（带返回当前 ETF） */
function openStockFromHoldings(h) {
  if (h && h.code) openStock({ code: h.code, name: h.name }, { origin: `/stock/${code.value}`, originLabel: '返回 ETF' })
}

// ETF 持仓缓存：成分每日变更，5 分钟内复用，避免 3 秒轮询重复请求导致卡片闪烁
const HOLDINGS_TTL = 5 * 60 * 1000
let holdingsCache = { code: null, at: 0, data: null }
let holdingsInFlight = false

/** 加载 ETF 持仓成分股并批量补实时行情（带缓存，命中时复用不闪烁） */
async function loadHoldings() {
  if (!isEtf.value) { holdings.value = []; holdingsLoading.value = false; return }
  if (holdingsInFlight) return
  const now = Date.now()
  if (holdingsCache.code === code.value && holdingsCache.data && now - holdingsCache.at < HOLDINGS_TTL) {
    holdings.value = holdingsCache.data
    return
  }
  // 仅在无数据时显示加载态，已有数据时静默刷新，避免闪烁
  if (!holdings.value.length) holdingsLoading.value = true
  holdingsInFlight = true
  try {
    const data = await api.holdings(code.value)
    const items = data.items || []
    if (!items.length) { holdings.value = []; holdingsCache = { code: null, at: 0, data: null }; return }
    const codes = items.map(i => i.code)
    const quotes = await api.batch(codes).catch(() => [])
    const qMap = {}
    for (const q of quotes) if (q && q.code) qMap[q.code] = q
    holdings.value = items.map(i => {
      const q = qMap[i.code] || {}
      return {
        ...i,
        price: i.price ?? q.price ?? null,
        change_pct: i.change_pct ?? q.change_pct ?? null,
      }
    })
    holdingsCache = { code: code.value, at: now, data: holdings.value }
  } catch (e) { holdings.value = [] }
  finally { holdingsLoading.value = false; holdingsInFlight = false }
}

async function loadSlow() {
  try {
    const [tk, f, kd, lb, sr, nw, ann] = await Promise.all([
      api.ticks(code.value, 80),
      api.moneyflowHistory(code.value, 1),
      api.kline(code.value, 'day', 120).catch(() => null),
      api.stockLhb(code.value).catch(() => null),
      api.baiduSr(code.value, 'day').catch(() => null),
      api.stockNews(code.value, 8).catch(() => []),
      api.stockAnnouncements(code.value, 6).catch(() => []),
    ])
    ticks.value = (tk || []).slice().reverse()
    flow.value = f || []
    if (Array.isArray(f) && f.length) {
      flowSource.value = f[f.length - 1]?.data_source || '东财'
      flowFetchedAt.value = f[f.length - 1]?.fetched_at || nowLabel()
    } else {
      flowSource.value = '暂不可用'
    }
    if (lb && lb.latest) {
      lhb.value = { ...lb.latest, appear_count: lb.appear_count, appear_dates: lb.appear_dates, history: lb.history }
    } else if (lb && lb.date) {
      lhb.value = lb
    } else {
      lhb.value = null
    }
    announcements.value = ann || []
    if (kd && kd.points && kd.points.length) {
      klineDay.value = kd
      dayPoints.value = kd.points
      chartsRef.value?.setDayKline?.(kd)
    }
    if (sr && (sr.support?.length || sr.resistance?.length)) {
      srLevels.value = sr
    }
    news.value = nw || []
  } catch (e) { /* 明细/资金流失败不影响主页面 */ }
}


async function screenshotFlow(el) {
  if (!el) return
  await captureElement(el, `${displayName.value}_资金流.png`)
}
async function screenshotEl(el) {
  if (!el) return
  await captureElement(el, `${displayName.value}_截图.png`)
}

watch(() => props.code, (n) => {
  if (n && n !== code.value) {
    code.value = n
    isWatched.value = codeWatched(n)
    localMeta.value = peekMeta(n) || {}
  }
  klineDay.value = null
  dayPoints.value = []
  flow.value = []
  holdings.value = []
  holdingsCache = { code: null, at: 0, data: null }
  limitTag.value = null
  hydrateLocal()
  loadFast()
  loadSlow()
})

const pollFast = usePolling(loadFast, 3000)
const pollSlow = usePolling(loadSlow, 10000, { primary: false })
function onAppManualRefresh() { loadSlow() }

// isEtf 变为 true 时立即加载持仓，避免刷新时先闪"暂无持仓数据"再闪"正在加载"
watch(isEtf, (v) => { if (v) loadHoldings() })

onMounted(async () => {
  isWatched.value = codeWatched(code.value)
  hydrateLocal()
  window.addEventListener('app-manual-refresh', onAppManualRefresh)
})
onUnmounted(() => {
  window.removeEventListener('app-manual-refresh', onAppManualRefresh)
})
</script>

<style scoped>
.analyse-td { text-align: left; white-space: normal; font-size: 12px; }
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; font-size: 16px;
  padding: 2px 6px; border-radius: 4px; opacity: .7; transition: opacity .2s;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }

/* 龙虎榜席位增强 */
.lhb-freq { display: inline-block; font-size: 12px; background: var(--accent); color: #fff; padding: 1px 8px; border-radius: 10px; margin: 0 8px; font-weight: 500; }
.lhb-kv-grid { grid-template-columns: repeat(3, 1fr); }
.seat-badge { display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 4px; white-space: nowrap; }
.seat-legend { background: #f59e0b; color: #fff; }
.seat-new_gen { background: #3b82f6; color: #fff; }
.seat-regional { background: #8b5cf6; color: #fff; }
.seat-institution { background: #10b981; color: #fff; }
.seat-northbound { background: #06b6d4; color: #fff; }
.seat-broker { background: var(--border); color: var(--text-dim); }
.seat-nick { display: block; font-size: 11px; color: var(--accent); font-weight: 500; margin-top: 1px; }
.seat-name-cell { min-width: 100px; }
.lhb-history-list { display: flex; flex-direction: column; gap: 3px; margin-top: 6px; }
.lhb-history-item { display: flex; gap: 12px; font-size: 12px; align-items: center; }

/* ETF 持仓成分 */
.ratio-pill {
  display: inline-block; padding: 1px 8px; border-radius: 10px;
  font-size: 12px; font-weight: 600; color: var(--accent);
  background: var(--accent-bg); border: 1px solid var(--accent);
}
</style>
