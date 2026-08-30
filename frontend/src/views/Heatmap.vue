<template>
  <div class="heatmap-page" :class="{ 'is-fullscreen': isFullscreen }" ref="fullscreenContainer">
    <div class="heatmap-header-row" v-if="!isFullscreen">
      <MarketNavTabs current-tab="heatmap" />
      <div class="page-actions">
        <!-- 搜索定位 -->
        <div class="heatmap-search-box">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="搜索高亮代码/拼音/名称…"
            @input="onSearchInput"
          />
          <button v-if="searchQuery" class="search-clear" @click="clearSearch">✕</button>
        </div>

        <button class="btn-tool" @click="load" :disabled="loading" title="立即刷新数据">
          <UiIcon name="refresh" :size="14" :class="{ rotating: loading }" /> 刷新
        </button>
        <button class="btn-tool" @click="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏盯盘'">
          <UiIcon :name="isFullscreen ? 'close' : 'menu'" :size="14" /> {{ isFullscreen ? '退出全屏' : '全屏' }}
        </button>
        <button class="btn-tool" @click="doScreenshot" title="截图云图">
          <UiIcon name="screenshot" :size="14" /> 截图
        </button>
      </div>
    </div>

    <!-- 全屏下简要标题栏 -->
    <div class="page-title-row" v-else>
      <div class="page-title">大盘热力云图</div>
      <div class="page-actions">
        <button class="btn-tool" @click="toggleFullscreen" title="退出全屏">
          <UiIcon name="close" :size="14" /> 退出全屏
        </button>
      </div>
    </div>

    <!-- 范围与面积控制胶囊栏 -->
    <div class="heatmap-toolbar">
      <!-- 范围切换 -->
      <div class="toolbar-section">
        <span class="toolbar-label">范围：</span>
        <div class="filter-pills">
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'all_top300' }"
            @click="switchScope('all_top300')"
          >
            🔥 全市场 TOP 300
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'all_top500' }"
            @click="switchScope('all_top500')"
          >
            🚀 全市场 TOP 500
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'hs300' }"
            @click="switchScope('hs300')"
          >
            👑 沪深 300
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'cyb_kcb' }"
            @click="switchScope('cyb_kcb')"
          >
            ⚡ 双创核心
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'zz500' }"
            @click="switchScope('zz500')"
          >
            📈 中证 500
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'watchlist' }"
            @click="switchScope('watchlist')"
          >
            ⭐ 我的自选股
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'industry_overview' }"
            @click="switchScope('industry_overview')"
          >
            🏭 行业全景
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentScope === 'concept_overview' }"
            @click="switchScope('concept_overview')"
          >
            💡 题材全景
          </button>
        </div>
      </div>

      <!-- 面积指标切换 -->
      <div class="toolbar-section">
        <span class="toolbar-label">面积：</span>
        <div class="filter-pills">
          <button
            class="filter-pill"
            :class="{ active: currentSizeBy === 'amount' }"
            @click="switchSizeBy('amount')"
            title="以今日成交额作为方块大小（反映资金活跃度）"
          >
            💰 成交额
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentSizeBy === 'float_mv' }"
            @click="switchSizeBy('float_mv')"
            title="以流通市值作为方块大小（反映行业真实体量权重）"
          >
            🏢 流通市值
          </button>
          <button
            class="filter-pill"
            :class="{ active: currentSizeBy === 'total_mv' }"
            @click="switchSizeBy('total_mv')"
            title="以总市值作为方块大小"
          >
            🏛️ 总市值
          </button>
        </div>
      </div>
    </div>

    <!-- 统计状态与色阶图例栏 -->
    <div class="heatmap-stat-bar mt12">
      <div class="stat-left">
        <span class="stat-item">
          监控总成交额：<strong>{{ fmtAmount(totalAmount) }}</strong>
        </span>
        <span class="stat-item">
          覆盖标的：<strong>{{ totalStockCount }} 只</strong>
        </span>
        <span class="stat-item">
          覆盖板块：<strong>{{ totalGroupCount }} 个</strong>
        </span>
        <span class="stat-item stat-up" v-if="upCount || downCount">
          上涨 <strong>{{ upCount }}</strong> · 下跌 <strong>{{ downCount }}</strong>
        </span>
        <span class="stat-search-hit" v-if="searchQuery">
          🔍 已高亮 <strong>{{ searchHitCount }}</strong> 只标的
        </span>
      </div>

      <div class="legend-bar">
        <span class="legend-label legend-down">≤ -7%</span>
        <span class="legend-label legend-down">-3%</span>
        <div class="legend-grad"></div>
        <span class="legend-label legend-up">+3%</span>
        <span class="legend-label legend-up">≥ +7%</span>
      </div>
    </div>

    <!-- 错误横幅 -->
    <div class="error-banner mt12" v-if="error">{{ error }}</div>

    <!-- 核心云图容器 -->
    <div class="card heatmap-card mt12" ref="chartCardRef">
      <div ref="chartEl" class="chart-container"></div>
      <div class="chart-loading-mask" v-if="loading && !hasRendered">
        <UiIcon name="refresh" :size="24" class="rotating" />
        <span>正在构建大盘金融热力云图…</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 大盘热力云图（Market Treemap - 业界金融标准版）
 * @author ygw
 */
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api.js'
import { fmtAmount, fmtPct } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { usePageTab } from '../composables/usePageTab.js'
import { captureElement } from '../composables/useScreenshot.js'
import MarketNavTabs from '../components/MarketNavTabs.vue'
import { openStock } from '../composables/useStockMeta.js'
import UiIcon from '../components/ui/UiIcon.vue'

const currentScope = usePageTab('heatmap_scope', 'all_top300')
const currentSizeBy = usePageTab('heatmap_size_by', 'amount')

const loading = ref(false)
const hasRendered = ref(false)
const error = ref('')
const totalAmount = ref(0)
const totalStockCount = ref(0)
const totalGroupCount = ref(0)
const upCount = ref(0)
const downCount = ref(0)

const searchQuery = ref('')
const searchHitCount = ref(0)
const rawItems = ref([])

const isFullscreen = ref(false)
const fullscreenContainer = ref(null)
const chartEl = ref(null)
const chartCardRef = ref(null)
let chartInstance = null

function switchScope(scope) {
  currentScope.value = scope
  load()
}

function switchSizeBy(sizeBy) {
  currentSizeBy.value = sizeBy
  load()
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    fullscreenContainer.value?.requestFullscreen?.()
    isFullscreen.value = true
  } else {
    document.exitFullscreen?.()
    isFullscreen.value = false
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
  nextTick(() => {
    chartInstance?.resize()
  })
}

function onSearchInput() {
  renderChart(rawItems.value)
}

function clearSearch() {
  searchQuery.value = ''
  renderChart(rawItems.value)
}

// ------------------------------------------------------------- 颜色平滑渐变算法
function hexToRgb(hex) {
  const clean = hex.replace(/^#/, '')
  return [
    parseInt(clean.substring(0, 2), 16),
    parseInt(clean.substring(2, 4), 16),
    parseInt(clean.substring(4, 6), 16),
  ]
}

function lerpRgb(c1, c2, t) {
  const clamped = Math.max(0, Math.min(1, t))
  return [
    Math.round(c1[0] + (c2[0] - c1[0]) * clamped),
    Math.round(c1[1] + (c2[1] - c1[1]) * clamped),
    Math.round(c1[2] + (c2[2] - c1[2]) * clamped),
  ]
}

const C_NEUTRAL = hexToRgb('222733')   // 0.0% 高级暗炭黑灰 (TradingView 质感)
const C_UP_MID  = hexToRgb('a82d2d')   // +3.0% 沉稳正红
const C_UP_MAX  = hexToRgb('e53935')   // +7.0% 鲜亮红
const C_DOWN_MID = hexToRgb('1b5e3f')  // -3.0% 沉稳墨绿
const C_DOWN_MAX = hexToRgb('00a676')  // -7.0% 翡翠绿

/**
 * 根据涨跌幅连续插值生成 A 股标准金融红绿平滑色彩
 * @param {number} pct - 涨跌幅百分比
 * @param {boolean} isDimmed - 是否因未被搜索命中而虚化
 */
function getPctColor(pct, isDimmed = false) {
  if (pct == null || isNaN(pct)) return isDimmed ? 'rgba(75,85,99,0.15)' : '#222733'

  let rgb = C_NEUTRAL
  if (pct > 0) {
    if (pct <= 3.0) {
      rgb = lerpRgb(C_NEUTRAL, C_UP_MID, pct / 3.0)
    } else {
      rgb = lerpRgb(C_UP_MID, C_UP_MAX, (pct - 3.0) / 4.0)
    }
  } else if (pct < 0) {
    const val = Math.abs(pct)
    if (val <= 3.0) {
      rgb = lerpRgb(C_NEUTRAL, C_DOWN_MID, val / 3.0)
    } else {
      rgb = lerpRgb(C_DOWN_MID, C_DOWN_MAX, (val - 3.0) / 4.0)
    }
  }

  if (isDimmed) {
    return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.18)`
  }
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`
}

/**
 * 转换后端树状数据为 ECharts Treemap 系列数据
 */
function transformTreemapData(groups) {
  const query = searchQuery.value.trim().toLowerCase()
  let hits = 0

  const res = groups.map(g => {
    const gPct = g.change_pct || 0
    const gAmt = g.amount || 0
    const stocks = g.children || []

    const transformedChildren = stocks.map(s => {
      const sPct = s.change_pct || 0
      const sName = s.name || ''
      const sCode = s.code || ''
      const isMatched = !query || sName.toLowerCase().includes(query) || sCode.includes(query)
      if (query && isMatched) hits++

      const color = getPctColor(sPct, query && !isMatched)
      const sign = sPct > 0 ? '+' : ''

      return {
        name: sName,
        code: sCode,
        value: s.value || 1,
        price: s.price,
        change_pct: sPct,
        amount: s.amount,
        turnover: s.turnover,
        float_mv: s.float_mv,
        total_mv: s.total_mv,
        main_inflow: s.main_inflow,
        industry: s.industry || g.name,
        isStock: true,
        isMatched,
        itemStyle: {
          color: color,
          borderColor: 'rgba(15, 23, 42, 0.75)',
          borderWidth: 1,
          gapWidth: 1,
        },
        label: {
          show: true,
          position: 'inside',
          formatter: (params) => {
            const d = params.data
            if (!d) return ''
            return `{name|${d.name}}\n{pct|${sign}${fmtPct(d.change_pct)}}`
          },
          rich: {
            name: {
              fontSize: 12,
              fontWeight: 700,
              color: '#ffffff',
              lineHeight: 16,
              textShadowColor: 'rgba(0,0,0,0.85)',
              textShadowBlur: 2,
            },
            pct: {
              fontSize: 11,
              fontWeight: 600,
              color: '#ffffff',
              lineHeight: 14,
              textShadowColor: 'rgba(0,0,0,0.85)',
              textShadowBlur: 2,
            }
          }
        }
      }
    })

    const sign = gPct > 0 ? '+' : ''
    const gPctText = `${sign}${fmtPct(gPct)}`

    return {
      name: g.name,
      code: g.code,
      value: g.value || 1,
      change_pct: gPct,
      amount: gAmt,
      stock_count: g.stock_count || stocks.length,
      up_count: g.up_count || 0,
      down_count: g.down_count || 0,
      children: transformedChildren,
      itemStyle: {
        borderColor: '#1e293b',
        borderWidth: 2,
        gapWidth: 2,
      },
      upperLabel: {
        show: true,
        height: 24,
        color: '#f8fafc',
        backgroundColor: 'rgba(15, 23, 42, 0.92)',
        borderColor: '#334155',
        borderWidth: 1,
        borderRadius: [3, 3, 0, 0],
        padding: [0, 8],
        fontSize: 12,
        fontWeight: 700,
        formatter: `${g.name}  ${gPctText} · ${fmtAmount(gAmt)}`,
      }
    }
  })

  searchHitCount.value = hits
  return res
}

function renderChart(groups) {
  if (!chartEl.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartEl.value)
    chartInstance.on('click', params => {
      const data = params.data
      if (!data) return
      if (data.isStock && data.code) {
        openStock(data, { origin: '/heatmap', originLabel: '返回云图' })
      } else if (data.code && !data.isStock) {
        navigate(`/sector/${data.code}`)
      }
    })
  }

  const seriesData = transformTreemapData(groups)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.96)',
      borderColor: '#334155',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: (info) => {
        const d = info.data
        if (!d) return ''
        const pctCls = d.change_pct > 0 ? '#ef4444' : d.change_pct < 0 ? '#10b981' : '#9ca3af'
        const sign = d.change_pct > 0 ? '+' : ''

        if (d.isStock) {
          return `
            <div style="font-weight:700;font-size:14px;margin-bottom:6px;color:#ffffff;">${d.name} <span style="font-size:12px;color:#94a3b8;">(${d.code})</span> · <span style="font-size:12px;color:#cbd5e1;">${d.industry || ''}</span></div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;line-height:1.6;">
              <div>现价: <strong>${d.price != null ? d.price.toFixed(2) : '-'}</strong></div>
              <div>涨跌幅: <span style="color:${pctCls};font-weight:700;">${sign}${fmtPct(d.change_pct)}</span></div>
              <div>成交额: <strong>${fmtAmount(d.amount)}</strong></div>
              ${d.turnover != null ? `<div>换手率: <strong>${fmtPct(d.turnover)}</strong></div>` : ''}
              ${d.float_mv ? `<div>流通市值: <strong>${fmtAmount(d.float_mv)}</strong></div>` : ''}
              ${d.main_inflow != null ? `<div>主力净流入: <span style="color:${d.main_inflow > 0 ? '#ef4444' : '#10b981'};font-weight:600;">${fmtAmount(d.main_inflow)}</span></div>` : ''}
            </div>
            <div style="font-size:11px;color:#64748b;margin-top:6px;border-top:1px dashed #334155;padding-top:4px;">💡 点击直接打开个股分时/K线详情</div>
          `
        }

        return `
          <div style="font-weight:700;font-size:14px;margin-bottom:6px;color:#ffffff;">${d.name} <span style="font-size:12px;color:#94a3b8;">(${d.stock_count || 0} 只标的)</span></div>
          <div style="line-height:1.6;">
            <div>板块综合涨跌: <span style="color:${pctCls};font-weight:700;">${sign}${fmtPct(d.change_pct)}</span></div>
            <div>板块总成交额: <strong>${fmtAmount(d.amount)}</strong></div>
            <div style="font-size:11px;color:#94a3b8;margin-top:4px;">上涨: <span style="color:#ef4444;font-weight:600;">${d.up_count || 0}</span> 家 · 下跌: <span style="color:#10b981;font-weight:600;">${d.down_count || 0}</span> 家</div>
          </div>
        `
      }
    },
    series: [
      {
        type: 'treemap',
        width: '100%',
        height: '100%',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        levels: [
          {
            itemStyle: {
              borderWidth: 2,
              borderColor: '#0f172a',
              gapWidth: 2,
            }
          },
          {
            itemStyle: {
              borderWidth: 2,
              borderColor: '#1e293b',
              gapWidth: 2,
            },
            upperLabel: {
              show: true,
            }
          },
          {
            itemStyle: {
              borderWidth: 1,
              borderColor: 'rgba(15, 23, 42, 0.75)',
              gapWidth: 1,
            }
          }
        ],
        data: seriesData,
      }
    ]
  }

  chartInstance.setOption(option, true)
  hasRendered.value = true
}

async function load() {
  loading.value = true
  try {
    const data = await api.marketHeatmap(currentScope.value, currentSizeBy.value, 300)
    rawItems.value = data.items || []
    totalAmount.value = data.total_amount || 0
    totalStockCount.value = data.stock_count || 0
    totalGroupCount.value = data.count || 0

    let up = 0
    let down = 0
    for (const g of rawItems.value) {
      up += (g.up_count || 0)
      down += (g.down_count || 0)
    }
    upCount.value = up
    downCount.value = down

    error.value = ''
    await nextTick()
    renderChart(rawItems.value)
  } catch (e) {
    error.value = '大盘金融云图加载失败：' + e.message
  } finally {
    loading.value = false
  }
}

function handleResize() {
  if (chartInstance) chartInstance.resize()
}

async function doScreenshot() {
  if (!chartCardRef.value) return
  await captureElement(chartCardRef.value, `大盘热力云图_${currentScope.value}_${currentSizeBy.value}.png`)
}

usePolling(load, 15000)

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.heatmap-page {
  padding-bottom: 24px;
}

.heatmap-page.is-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--bg);
  padding: 16px 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.heatmap-page.is-fullscreen .heatmap-card {
  flex: 1;
  height: 100%;
  min-height: auto;
}

.heatmap-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

/* 顶部搜索框 */
.heatmap-search-box {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 8px;
  font-size: 12px;
  pointer-events: none;
  opacity: 0.6;
}
.search-input {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 5px 24px 5px 26px;
  font-size: 12px;
  color: var(--text);
  width: 180px;
  transition: all .15s;
}
.search-input:focus {
  outline: none;
  border-color: var(--accent);
  width: 220px;
  background: var(--bg);
}
.search-clear {
  position: absolute;
  right: 6px;
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 11px;
  cursor: pointer;
}

/* 胶囊控制栏 */
.heatmap-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}
.toolbar-section {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.toolbar-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
  white-space: nowrap;
}

.heatmap-stat-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 16px;
}

.stat-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.stat-item {
  font-size: 13px;
  color: var(--text-dim);
}
.stat-item strong {
  color: var(--text);
  font-weight: 700;
}
.stat-up strong {
  color: var(--up);
}
.stat-search-hit {
  font-size: 12px;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

/* 图例 */
.legend-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}
.legend-label {
  font-size: 11px;
  color: var(--text-dim);
  font-weight: 600;
}
.legend-label.legend-up {
  color: var(--up);
}
.legend-label.legend-down {
  color: var(--down);
}

.legend-grad {
  width: 140px;
  height: 10px;
  border-radius: var(--radius-pill);
  background: linear-gradient(90deg, #00a676 0%, #1b5e3f 28%, #222733 50%, #a82d2d 72%, #e53935 100%);
  border: 1px solid var(--border);
}

/* 云图卡片 */
.heatmap-card {
  position: relative;
  height: calc(100vh - 250px);
  min-height: 560px;
  padding: 6px;
  background: #0b0f19;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);
}

.chart-container {
  width: 100%;
  height: 100%;
}

.chart-loading-mask {
  position: absolute;
  inset: 0;
  background: rgba(11, 15, 25, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text);
  font-size: 13px;
  z-index: 10;
}

.rotating {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
