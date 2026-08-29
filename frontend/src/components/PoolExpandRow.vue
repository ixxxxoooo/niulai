<template>
  <tr class="pool-expand-row" @click.stop>
    <td :colspan="colspan">
      <div class="expand-wrap">
        <!-- 分时图 -->
        <div class="expand-block expand-trend">
          <div class="expand-chart-title">分时走势</div>
          <div v-if="trendErr" class="expand-empty">{{ trendErr }}</div>
          <div v-else ref="trendEl" class="expand-chart"></div>
          <a class="expand-link" :href="stockUrl" target="_blank" rel="noopener">点击查看大图</a>
        </div>

        <!-- 日K线 -->
        <div class="expand-block expand-kline">
          <div class="expand-chart-title">日K线</div>
          <div v-if="klineErr" class="expand-empty">{{ klineErr }}</div>
          <div v-else ref="klineEl" class="expand-chart"></div>
          <a class="expand-link" :href="stockUrl" target="_blank" rel="noopener">点击查看大图</a>
        </div>

        <!-- 综合评分 -->
        <div class="expand-block expand-score">
          <template v-if="scoreLoading">
            <div class="expand-empty">加载中...</div>
          </template>
          <template v-else-if="score">
            <div class="score-header">
              <span class="score-label">综合评分</span>
              <span class="score-value" :class="scoreColorClass">{{ Math.round(score.total_score) }}</span>
            </div>
            <div class="score-row">
              <span class="score-item-label">今日表现</span>
              <span class="score-item-value" :class="changeClass">{{ fmtChange(score.change_rate) }}</span>
            </div>
            <div class="score-beat">
              打败了 <span class="score-pct">{{ score.beat_ratio }}%</span> 的股票
            </div>
            <div class="score-row">
              <span class="score-item-label">次日上涨概率</span>
              <span class="score-item-value accent">{{ score.rise_probability }}%</span>
            </div>
            <div v-if="score.words_explain" class="score-explain">{{ truncate(score.words_explain, 120) }}</div>
            <div class="score-disclaimer">
              <span>免责声明</span>
              <span class="score-help" data-tooltip="本功能中的内容均仅供参考，建议投资者根据自身投资风格进行筛选，并合理控制风险。">?</span>
            </div>
          </template>
          <template v-else>
            <div class="expand-empty">暂无评分</div>
          </template>
        </div>
      </div>
    </td>
  </tr>
</template>

<script setup>
/**
 * 股池表格展开行：分时图 + 日K线 + 综合评分
 * 点击表格行时展开/收起，参考东方财富涨停板详情页交互
 * @author ygw
 */
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api.js'
import { themeColors } from '../utils.js'
import { calcTrendYRange } from '../utils/chartScale.js'
import { settingsState } from '../composables/useSettings.js'
import { ensureIndicators } from '../chartIndicators.js'
import { calcMA } from './stock/chartCommon.js'

const props = defineProps({
  code: { type: String, required: true },
  name: { type: String, default: '' },
  colspan: { type: Number, default: 11 },
})

const trendEl = ref(null)
const klineEl = ref(null)
const trendErr = ref('')
const klineErr = ref('')
const score = ref(null)
const scoreLoading = ref(true)
let trendChart = null
let klineChart = null

const stockUrl = `/#/stock/${props.code}`

function fmtChange(v) {
  if (v == null) return '-'
  return (v >= 0 ? '+' : '') + Number(v).toFixed(2)
}

function truncate(s, max) {
  if (!s || s.length <= max) return s
  return s.slice(0, max) + '…'
}

const changeClass = computed(() => {
  if (!score.value) return ''
  const v = score.value.change_rate
  if (v == null) return ''
  return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
})

const scoreColorClass = computed(() => {
  if (!score.value) return ''
  const s = score.value.total_score
  if (s >= 80) return 'score-high'
  if (s >= 50) return 'score-mid'
  return 'score-low'
})

async function loadData() {
  const code = props.code
  const [trendRes, klineRes, commentRes] = await Promise.allSettled([
    api.trends(code),
    api.kline(code, 'day', 60),
    api.stockComment(code),
  ])

  await nextTick()

  if (trendRes.status === 'fulfilled' && trendRes.value) {
    renderTrend(trendRes.value)
  } else {
    trendErr.value = '分时暂不可用'
  }

  if (klineRes.status === 'fulfilled' && klineRes.value) {
    renderKline(klineRes.value)
  } else {
    klineErr.value = 'K线暂不可用'
  }

  if (commentRes.status === 'fulfilled' && commentRes.value && commentRes.value.total_score != null) {
    score.value = commentRes.value
  }
  scoreLoading.value = false
}

function renderTrend(t) {
  if (!trendEl.value || !t?.points?.length) {
    trendErr.value = '暂无分时'
    return
  }
  if (!trendChart) trendChart = echarts.init(trendEl.value)
  const tc = themeColors()
  const times = t.points.map(p => p.time)
  const prices = t.points.map(p => p.price)
  const vols = t.points.map(p => p.volume || 0)
  const pre = t.pre_close || prices[0]
  const last = prices[prices.length - 1]
  const color = last >= pre ? tc.up : tc.down
  const { yMin, yMax } = calcTrendYRange({
    mode: settingsState.trendYScale || 'normal',
    prices,
    preClose: pre,
  })
  trendChart.setOption({
    animation: false,
    grid: [
      { left: 42, right: 8, top: 20, bottom: 56 },
      { left: 42, right: 8, top: '75%', bottom: 14 },
    ],
    xAxis: [
      { type: 'category', data: times, gridIndex: 0, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
      { type: 'category', data: times, gridIndex: 1, axisLabel: { fontSize: 10, color: tc.dim }, axisTick: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
    ],
    yAxis: [
      { type: 'value', min: yMin, max: yMax, gridIndex: 0, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { fontSize: 10, color: tc.dim } },
      { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    series: [
      {
        type: 'line', data: prices, xAxisIndex: 0, yAxisIndex: 0,
        showSymbol: false, lineStyle: { width: 1.2, color },
        areaStyle: { color: color + '22' },
        markLine: {
          silent: true, symbol: 'none',
          data: [{ yAxis: pre }],
          lineStyle: { color: tc.split, width: 1, type: 'solid' },
          label: { show: false },
        },
      },
      {
        type: 'bar', data: vols.map((v, i) => ({
          value: v,
          itemStyle: { color: prices[i] >= (prices[i - 1] || pre) ? tc.up + '88' : tc.down + '88' },
        })),
        xAxisIndex: 1, yAxisIndex: 1,
        barMaxWidth: 2,
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: tc.tooltipBg || 'rgba(20,21,25,0.9)',
      borderColor: tc.split,
      textStyle: { color: tc.text, fontSize: 11 },
      formatter(params) {
        const p = params[0]
        if (!p) return ''
        const idx = p.dataIndex
        const price = prices[idx]
        const chg = ((price - pre) / pre * 100).toFixed(2)
        return `<b>${times[idx]}</b><br/>价格: ${price.toFixed(2)}<br/>涨跌: ${chg}%`
      },
    },
  }, true)
}

function renderKline(k) {
  if (!klineEl.value || !k?.points?.length) {
    klineErr.value = '暂无K线'
    return
  }
  if (!klineChart) klineChart = echarts.init(klineEl.value)
  const tc = themeColors()
  const pts = k.points
  const ind = ensureIndicators(pts, k.indicators)
  const dates = pts.map(p => p.date)
  const kdata = pts.map(p => [p.open, p.close, p.low, p.high])
  const vols = pts.map(p => p.volume)
  const ma5 = ind.ma5 || calcMA(pts, 5)
  const ma10 = ind.ma10 || calcMA(pts, 10)

  klineChart.setOption({
    animation: false,
    grid: [
      { left: 42, right: 8, top: 20, bottom: 56 },
      { left: 42, right: 8, top: '75%', bottom: 14 },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { fontSize: 10, color: tc.dim }, axisTick: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true, splitLine: { lineStyle: { color: tc.split } }, axisLabel: { fontSize: 10, color: tc.dim } },
      { type: 'value', gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
    ],
    series: [
      {
        type: 'candlestick', data: kdata, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: tc.up, color0: tc.down, borderColor: tc.up, borderColor0: tc.down },
      },
      { type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { width: 1, color: '#e8a634' } },
      { type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { width: 1, color: '#4c9aff' } },
      {
        type: 'bar', data: vols.map((v, i) => ({
          value: v,
          itemStyle: { color: (pts[i]?.close >= pts[i]?.open) ? tc.up + '88' : tc.down + '88' },
        })),
        xAxisIndex: 1, yAxisIndex: 1,
        barMaxWidth: 4,
      },
    ],
    tooltip: {
      trigger: 'axis',
      backgroundColor: tc.tooltipBg || 'rgba(20,21,25,0.9)',
      borderColor: tc.split,
      textStyle: { color: tc.text, fontSize: 11 },
    },
  }, true)
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  if (trendChart) { trendChart.dispose(); trendChart = null }
  if (klineChart) { klineChart.dispose(); klineChart = null }
})
</script>

<style scoped>
.pool-expand-row > td {
  padding: 0 !important;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.expand-wrap {
  display: flex;
  gap: 1px;
  background: var(--border);
  border-top: 1px solid var(--border);
}
.expand-block {
  background: var(--bg-card);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.expand-trend,
.expand-kline {
  flex: 1 1 0;
  min-width: 280px;
}
.expand-score {
  flex: 0 0 240px;
  min-width: 200px;
}
.expand-chart-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
}
.expand-chart {
  width: 100%;
  height: 200px;
}
.expand-link {
  font-size: 11px;
  color: var(--accent);
  text-align: center;
  text-decoration: none;
}
.expand-link:hover {
  text-decoration: underline;
}
.expand-empty {
  color: var(--text-dim);
  font-size: 12px;
  text-align: center;
  padding: 40px 0;
}

/* 评分样式 */
.score-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.score-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.score-value {
  font-size: 36px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.score-high { color: var(--up); }
.score-mid { color: var(--accent); }
.score-low { color: var(--down); }

.score-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  padding: 2px 0;
}
.score-item-label {
  color: var(--text-dim);
}
.score-item-value {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.score-item-value.up { color: var(--up); }
.score-item-value.down { color: var(--down); }
.score-item-value.flat { color: var(--text-dim); }
.score-item-value.accent { color: var(--accent); }

.score-beat {
  font-size: 12px;
  color: var(--text-dim);
  padding: 2px 0;
}
.score-pct {
  font-weight: 700;
  color: var(--accent);
}

.score-explain {
  font-size: 11px;
  color: var(--text-dim);
  line-height: 1.5;
  padding: 4px 0;
  border-top: 1px solid var(--border);
  margin-top: 4px;
}

.score-disclaimer {
  font-size: 11px;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: auto;
  padding-top: 4px;
}
.score-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid var(--text-dim);
  font-size: 10px;
  cursor: help;
}
</style>
