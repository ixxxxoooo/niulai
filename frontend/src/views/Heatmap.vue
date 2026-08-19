<template>
  <div class="heatmap-page">
    <div class="page-title-row">
      <div>
        <div class="page-title">大盘热力云图</div>
        <div class="page-subtitle">面积代表成交资金体量 · 色彩反映板块与龙头涨跌强度</div>
      </div>
      <div class="page-actions">
        <!-- 维度切换 -->
        <div class="filter-pills">
          <button
            class="filter-pill"
            :class="{ active: sectorType === 'industry' }"
            @click="switchType('industry')"
          >
            🏭 行业板块
          </button>
          <button
            class="filter-pill"
            :class="{ active: sectorType === 'concept' }"
            @click="switchType('concept')"
          >
            💡 概念题材
          </button>
        </div>

        <button class="btn-tool" @click="load" :disabled="loading" title="刷新数据">
          <UiIcon name="refresh" :size="14" :class="{ rotating: loading }" /> 刷新
        </button>
        <button class="btn-tool" @click="doScreenshot" title="截图云图">
          <UiIcon name="screenshot" :size="14" /> 截图
        </button>
      </div>
    </div>

    <!-- 图例与统计状态栏 -->
    <div class="heatmap-stat-bar mt12">
      <div class="stat-left">
        <span class="stat-item">
          总监控成交额：<strong>{{ fmtAmount(totalAmount) }}</strong>
        </span>
        <span class="stat-item">
          板块总数：<strong>{{ sectorCount }}</strong>
        </span>
        <span class="stat-hint">
          💡 点击板块可直接进入板块详情；悬停查看领涨龙头与资金流向。
        </span>
      </div>

      <div class="legend-bar">
        <span class="legend-label">跌幅 ≥ -5%</span>
        <div class="legend-grad"></div>
        <span class="legend-label">涨幅 ≥ +5%</span>
      </div>
    </div>

    <!-- 错误横幅 -->
    <div class="error-banner mt12" v-if="error">{{ error }}</div>

    <!-- 核心云图容器 -->
    <div class="card heatmap-card mt12" ref="chartCardRef">
      <div ref="chartEl" class="chart-container"></div>
      <div class="chart-loading-mask" v-if="loading && !hasRendered">
        <UiIcon name="refresh" :size="24" class="rotating" />
        <span>正在加载大盘热力云图…</span>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 大盘热力云图（Market Treemap）
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
import { openStock } from '../composables/useStockMeta.js'

const sectorType = usePageTab('heatmap_type', 'industry')
const loading = ref(false)
const hasRendered = ref(false)
const error = ref('')
const totalAmount = ref(0)
const sectorCount = ref(0)

const chartEl = ref(null)
const chartCardRef = ref(null)
let chartInstance = null

function switchType(t) {
  sectorType.value = t
  load()
}

/**
 * 根据涨跌幅生成 A 股标准红绿渐变色
 * @param {number} pct - 涨跌幅百分比
 */
function getPctColor(pct) {
  if (pct == null || isNaN(pct)) return '#4b5563'
  if (pct >= 5.0) return '#b91c1c'  // 极强深红
  if (pct >= 3.0) return '#dc2626'  // 强势红
  if (pct >= 1.5) return '#ef4444'  // 亮红
  if (pct > 0.0) return '#f87171'   // 微涨浅红
  if (pct === 0.0) return '#6b7280' // 平盘暗灰
  if (pct > -1.5) return '#34d399'  // 微跌浅绿
  if (pct > -3.0) return '#10b981'  // 弱势绿
  if (pct > -5.0) return '#059669'  // 强跌绿
  return '#047857'                  // 极弱深绿
}

/**
 * 转换后端树状数据为 ECharts Treemap 系列数据
 */
function transformTreemapData(items) {
  return items.map(item => {
    const pct = item.change_pct || 0
    const color = getPctColor(pct)
    const node = {
      name: item.name,
      code: item.code,
      value: item.value || 1,
      change_pct: pct,
      amount: item.amount,
      main_inflow: item.main_inflow,
      leader_name: item.leader_name,
      leader_code: item.leader_code,
      leader_pct: item.leader_pct,
      up_count: item.up_count,
      down_count: item.down_count,
      itemStyle: {
        color: color,
        borderColor: '#1f2937',
        borderWidth: 1,
        gapWidth: 1,
      },
    }

    if (item.children && item.children.length) {
      node.children = item.children.map(c => {
        const cPct = c.change_pct || 0
        return {
          name: c.name,
          code: c.code,
          value: c.value || 1,
          change_pct: cPct,
          amount: c.amount,
          main_inflow: c.main_inflow,
          price: c.price,
          isStock: true,
          itemStyle: {
            color: getPctColor(cPct),
            borderColor: '#111827',
            borderWidth: 1,
          },
        }
      })
    }
    return node
  })
}

function renderChart(items) {
  if (!chartEl.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartEl.value)
    chartInstance.on('click', params => {
      const data = params.data
      if (!data) return
      if (data.isStock && data.code) {
        openStock(data, { origin: '/heatmap', originLabel: '返回云图' })
      } else if (data.code) {
        navigate(`/sector/${data.code}`)
      }
    })
  }

  const seriesData = transformTreemapData(items)

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      backgroundColor: 'rgba(17, 24, 39, 0.95)',
      borderColor: '#374151',
      borderWidth: 1,
      textStyle: { color: '#f3f4f6', fontSize: 12 },
      formatter: (info) => {
        const d = info.data
        if (!d) return ''
        const pctCls = d.change_pct > 0 ? '#ef4444' : d.change_pct < 0 ? '#10b981' : '#9ca3af'
        const sign = d.change_pct > 0 ? '+' : ''
        
        if (d.isStock) {
          return `
            <div style="font-weight:700;font-size:13px;margin-bottom:4px;">${d.name} (${d.code})</div>
            <div>现价: <strong>${d.price != null ? d.price.toFixed(2) : '-'}</strong></div>
            <div>涨跌幅: <span style="color:${pctCls};font-weight:700;">${sign}${fmtPct(d.change_pct)}</span></div>
            <div>成交额: <strong>${fmtAmount(d.amount)}</strong></div>
            ${d.main_inflow != null ? `<div>主力净流入: <span style="color:${d.main_inflow > 0 ? '#ef4444' : '#10b981'}">${fmtAmount(d.main_inflow)}</span></div>` : ''}
          `
        }

        return `
          <div style="font-weight:700;font-size:13px;margin-bottom:4px;">${d.name}</div>
          <div>板块涨跌: <span style="color:${pctCls};font-weight:700;">${sign}${fmtPct(d.change_pct)}</span></div>
          <div>板块成交: <strong>${fmtAmount(d.amount)}</strong></div>
          ${d.main_inflow != null ? `<div>主力净流入: <span style="color:${d.main_inflow > 0 ? '#ef4444' : '#10b981'}">${fmtAmount(d.main_inflow)}</span></div>` : ''}
          ${d.leader_name ? `<div style="margin-top:4px;border-top:1px dashed #4b5563;padding-top:4px;">领涨龙头: <strong>${d.leader_name}</strong> (<span style="color:#ef4444">${fmtPct(d.leader_pct)}</span>)</div>` : ''}
          <div style="font-size:11px;color:#9ca3af;margin-top:3px;">上涨: ${d.up_count || 0} 家 · 下跌: ${d.down_count || 0} 家</div>
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
        nodeClick: 'link',
        breadcrumb: { show: false },
        label: {
          show: true,
          position: 'inside',
          formatter: (params) => {
            const d = params.data
            if (!d) return ''
            const sign = d.change_pct > 0 ? '+' : ''
            return `{name|${d.name}}\n{pct|${sign}${fmtPct(d.change_pct)}}`
          },
          rich: {
            name: {
              fontSize: 13,
              fontWeight: 700,
              color: '#ffffff',
              lineHeight: 18,
              textShadowColor: 'rgba(0,0,0,0.6)',
              textShadowBlur: 2,
            },
            pct: {
              fontSize: 11,
              fontWeight: 600,
              color: '#ffffff',
              lineHeight: 16,
              textShadowColor: 'rgba(0,0,0,0.6)',
              textShadowBlur: 2,
            }
          }
        },
        upperLabel: {
          show: false,
        },
        itemStyle: {
          borderColor: '#111827',
          borderWidth: 1,
          gapWidth: 1,
        },
        levels: [
          {
            itemStyle: {
              borderWidth: 2,
              borderColor: '#111827',
              gapWidth: 2,
            }
          },
          {
            itemStyle: {
              borderWidth: 1,
              borderColor: '#1f2937',
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
    const data = await api.marketHeatmap(sectorType.value, 'amount', 80)
    totalAmount.value = data.total_amount || 0
    sectorCount.value = data.count || 0
    error.value = ''
    await nextTick()
    renderChart(data.items || [])
  } catch (e) {
    error.value = '大盘云图加载失败：' + e.message
  } finally {
    loading.value = false
  }
}

function handleResize() {
  if (chartInstance) chartInstance.resize()
}

async function doScreenshot() {
  if (!chartCardRef.value) return
  await captureElement(chartCardRef.value, `大盘热力云图_${sectorType.value}.png`)
}

usePolling(load, 10000)

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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

.heatmap-stat-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 16px;
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

.stat-hint {
  font-size: 12px;
  color: var(--text-dim);
}

/* 图例 */
.legend-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-label {
  font-size: 11px;
  color: var(--text-dim);
  font-weight: 600;
}

.legend-grad {
  width: 120px;
  height: 10px;
  border-radius: var(--radius-pill);
  background: linear-gradient(90deg, #047857, #10b981, #6b7280, #ef4444, #b91c1c);
  border: 1px solid var(--border);
}

/* 云图卡片 */
.heatmap-card {
  position: relative;
  height: calc(100vh - 210px);
  min-height: 520px;
  padding: 8px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.chart-loading-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
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
