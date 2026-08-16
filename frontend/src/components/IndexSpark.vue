<template>
  <div class="spark-wrap" v-if="hasData">
    <svg :viewBox="`0 0 ${vw} ${vh}`" preserveAspectRatio="none" class="spark-svg">
      <line :x1="0" :x2="vw" :y1="baseY" :y2="baseY" class="spark-base" />
      <polyline :points="polyPoints" fill="none" class="spark-line" :class="up ? 'up' : 'down'" />
    </svg>
  </div>
  <div class="spark-empty" v-else>—</div>
</template>

<script setup>
// 指数分时迷你缩略图（纯 SVG，无 echarts 实例开销，常驻卡片最省性能）
// @author ygw
import { computed } from 'vue'

const props = defineProps({
  trend: { type: Object, default: null },
})

const vw = 200
const vh = 44
const PAD = 3

const hasData = computed(() =>
  props.trend && props.trend.points && props.trend.points.length > 1)

const preClose = computed(() => props.trend?.pre_close || 0)
const prices = computed(() => (props.trend?.points || []).map(p => p.price))

// 以昨收为基准中心，按涨跌幅比例缩放（两边留等距），避免个别大波动压扁整体
const scale = computed(() => {
  const pre = preClose.value || 1
  const maxAbsPct = Math.max(...prices.value.map(p => Math.abs((p - pre) / pre)), 0.001)
  const range = Math.max(maxAbsPct, 0.002) * 1.15
  const innerH = vh - PAD * 2
  return { pxPerPct: (innerH / 2) / range, range }
})

const up = computed(() => {
  const last = prices.value[prices.value.length - 1]
  return last >= preClose.value
})

const baseY = computed(() => PAD + (vh - PAD * 2) / 2)

const polyPoints = computed(() => {
  const pts = prices.value
  const n = pts.length
  const stepX = (vw - PAD * 2) / (n - 1)
  const pre = preClose.value || pts[0]
  return pts.map((p, i) => {
    const x = PAD + i * stepX
    const y = baseY.value - ((p - pre) / (scale.value.range * pre)) * ((vh - PAD * 2) / 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})
</script>

<style scoped>
.spark-wrap { width: 100%; height: 44px; margin-top: 6px; }
.spark-svg { width: 100%; height: 100%; display: block; overflow: visible; }
.spark-line { stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
.spark-line.up { stroke: var(--up); }
.spark-line.down { stroke: var(--down); }
.spark-base { stroke: var(--border); stroke-width: 1; stroke-dasharray: 3 3; }
.spark-empty { height: 44px; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 12px; }
</style>