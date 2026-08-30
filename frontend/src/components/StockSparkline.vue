<template>
  <div class="stock-spark-wrap" :title="tooltipText">
    <svg v-if="hasData" :viewBox="`0 0 ${vw} ${vh}`" preserveAspectRatio="none" class="stock-spark-svg">
      <defs>
        <linearGradient :id="`spark-grad-${code}`" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" :stop-color="isUp ? 'var(--up)' : 'var(--down)'" stop-opacity="0.28" />
          <stop offset="100%" :stop-color="isUp ? 'var(--up)' : 'var(--down)'" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <!-- 昨收基准平盘虚线 -->
      <line :x1="0" :x2="vw" :y1="baseY" :y2="baseY" class="spark-base" />
      <!-- 半透明渐变背景面积 -->
      <polygon :points="areaPoints" :fill="`url(#spark-grad-${code})`" />
      <!-- 分时走势折线 -->
      <polyline :points="polyPoints" fill="none" class="spark-line" :class="isUp ? 'up' : 'down'" />
    </svg>
    <div v-else-if="loading" class="spark-loading">
      <span class="spark-skeleton"></span>
    </div>
    <div v-else class="spark-empty">—</div>
  </div>
</template>

<script setup>
/**
 * 表格行内迷你分时折线图（纯 SVG，毫秒级轻量渲染）
 * @author ygw
 */
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api.js'

const props = defineProps({
  code: { type: String, required: true },
})

const vw = 100
const vh = 28
const PAD = 2

// 模块级缓存，30 秒内复用避免重复请求
const _sparkCache = window._stockSparkCache || (window._stockSparkCache = new Map())

const trendData = ref(null)
const loading = ref(false)

async function loadTrend() {
  if (!props.code) return
  const hit = _sparkCache.get(props.code)
  if (hit && Date.now() - hit.ts < 30000) {
    trendData.value = hit.data
    return
  }
  loading.value = true
  try {
    const res = await api.trends(props.code)
    if (res && res.points && res.points.length) {
      trendData.value = res
      _sparkCache.set(props.code, { ts: Date.now(), data: res })
    }
  } catch (e) {
    // 忽略单项加载异常
  } finally {
    loading.value = false
  }
}

onMounted(loadTrend)
watch(() => props.code, loadTrend)

const hasData = computed(() => {
  return trendData.value && trendData.value.points && trendData.value.points.length > 1
})

const preClose = computed(() => trendData.value?.pre_close || 0)

// 全天固定时间轴 09:30~11:30 (121) + 13:00~15:00 (121) = 242 分钟
const fullTimes = (() => {
  const out = []
  const push = (startH, startM, endH, endM) => {
    for (let m = startH * 60 + startM; m <= endH * 60 + endM; m++) {
      out.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`)
    }
  }
  push(9, 30, 11, 30)
  push(13, 0, 15, 0)
  return out
})()
const timeIndex = new Map(fullTimes.map((t, i) => [t, i]))

const spacedPoints = computed(() => {
  const pts = trendData.value?.points || []
  const out = []
  for (const p of pts) {
    const idx = timeIndex.get(p.time)
    if (idx != null) out.push({ price: p.price, idx })
  }
  if (!out.length && pts.length) {
    // 兼容非标准时间戳格式等距映射
    pts.forEach((p, i) => out.push({ price: p.price, idx: Math.floor((i / pts.length) * 241) }))
  }
  return out
})

const prices = computed(() => spacedPoints.value.map(p => p.price))

const scale = computed(() => {
  const pre = preClose.value || prices.value[0] || 1
  const maxAbsPct = Math.max(...prices.value.map(p => Math.abs((p - pre) / pre)), 0.005)
  const range = Math.max(maxAbsPct, 0.005) * 1.15
  return { range, pre }
})

const isUp = computed(() => {
  if (!prices.value.length) return true
  const last = prices.value[prices.value.length - 1]
  return last >= (preClose.value || prices.value[0])
})

const baseY = computed(() => PAD + (vh - PAD * 2) / 2)

const computedPts = computed(() => {
  const pts = spacedPoints.value
  if (!pts.length) return []
  const n = 242
  const stepX = (vw - PAD * 2) / (n - 1)
  const pre = scale.value.pre
  const range = scale.value.range
  const halfH = (vh - PAD * 2) / 2

  return pts.map(pt => {
    const x = PAD + Math.min(pt.idx, 241) * stepX
    const dy = ((pt.price - pre) / (range * pre)) * halfH
    const y = Math.max(PAD, Math.min(vh - PAD, baseY.value - dy))
    return { x, y }
  })
})

const polyPoints = computed(() => {
  return computedPts.value.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
})

const areaPoints = computed(() => {
  const pts = computedPts.value
  if (!pts.length) return ''
  const first = pts[0]
  const last = pts[pts.length - 1]
  const bottomY = vh - PAD
  return `${first.x.toFixed(1)},${bottomY} ${polyPoints.value} ${last.x.toFixed(1)},${bottomY}`
})

const tooltipText = computed(() => {
  if (!trendData.value) return '分时走势'
  const pre = preClose.value
  const last = prices.value[prices.value.length - 1]
  if (pre && last) {
    const pct = ((last - pre) / pre * 100).toFixed(2)
    return `分时现价: ${last} (${pct >= 0 ? '+' : ''}${pct}%)`
  }
  return '分时走势'
})
</script>

<style scoped>
.stock-spark-wrap {
  width: 96px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  background: var(--kv-bg);
  border-radius: 4px;
  padding: 1px 3px;
  border: 1px solid var(--border);
  box-sizing: border-box;
}

.stock-spark-svg {
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}

.spark-line {
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.spark-line.up {
  stroke: var(--up);
}
.spark-line.down {
  stroke: var(--down);
}

.spark-base {
  stroke: var(--border);
  stroke-width: 0.8;
  stroke-dasharray: 2 2;
  opacity: 0.7;
}

.spark-loading {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.spark-skeleton {
  width: 60%;
  height: 2px;
  background: var(--border);
  border-radius: 1px;
  opacity: 0.5;
}

.spark-empty {
  color: var(--text-dim);
  font-size: 11px;
}
</style>
