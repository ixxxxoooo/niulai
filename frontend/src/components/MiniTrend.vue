<template>
  <span
    class="mini-host"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
  >
    <slot />
    <Teleport to="body">
      <div
        v-if="visible"
        class="mini-pop"
        :style="pos"
        @mouseenter="onEnter"
        @mouseleave="onLeave"
        @click.stop
      >
        <div class="mini-hd">
          <span>{{ title }}</span>
          <span class="mini-code">{{ code }}</span>
          <span v-if="changePct != null" class="mini-pct" :class="changePct >= 0 ? 'up' : 'down'">{{ changePct >= 0 ? '+' : '' }}{{ changePct.toFixed(2) }}%</span>
        </div>
        <div v-if="industry" class="mini-ind">{{ industry }}</div>
        <div v-if="err" class="mini-empty">{{ err }}</div>
        <div v-else ref="el" class="mini-chart"></div>
      </div>
    </Teleport>
  </span>
</template>

<script setup>
// 名称悬停分时小窗
// @author ygw
import { ref, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api.js'
import { themeColors } from '../utils.js'
import { calcTrendYRange } from '../utils/chartScale.js'
import { settingsState } from '../composables/useSettings.js'

const props = defineProps({
  code: { type: String, default: '' },
  name: { type: String, default: '' },
})

const visible = ref(false)
const err = ref('')
const el = ref(null)
const pos = ref({ left: '0px', top: '0px' })
const title = ref('')
const changePct = ref(null)
const industry = ref('')
let timer = null
let chart = null
const cache = new Map()

function place(e) {
  const x = Math.min((e?.clientX || 0) + 14, window.innerWidth - 280)
  const y = Math.min((e?.clientY || 0) + 14, window.innerHeight - 200)
  pos.value = { left: x + 'px', top: y + 'px' }
}

function onEnter(e) {
  if (!props.code) return
  place(e)
  clearTimeout(timer)
  timer = setTimeout(show, 280)
}

function onLeave() {
  clearTimeout(timer)
  timer = setTimeout(hide, 180)
}

async function show() {
  visible.value = true
  err.value = ''
  title.value = props.name || props.code
  changePct.value = null
  industry.value = ''
  await Promise.resolve()
  try {
    let data = cache.get(props.code)
    if (!data || Date.now() - data.ts > 30000) {
      const t = await api.trends(props.code)
      data = { ts: Date.now(), t }
      cache.set(props.code, data)
    }
    const t = data.t
    if (t && t.points && t.points.length && t.pre_close) {
      const last = t.points[t.points.length - 1].price
      changePct.value = ((last - t.pre_close) / t.pre_close * 100)
    }
    if (t && t.industry) industry.value = t.industry
    render(t)
  } catch (e) {
    err.value = '分时暂不可用'
  }
}

function hide() {
  visible.value = false
  if (chart) { chart.dispose(); chart = null }
}

function render(t) {
  if (!el.value || !t || !t.points || !t.points.length) {
    err.value = '暂无分时'
    return
  }
  if (!chart) chart = echarts.init(el.value)
  const tc = themeColors()
  const times = t.points.map(p => p.time)
  const prices = t.points.map(p => p.price)
  const pre = t.pre_close || prices[0]
  const last = prices[prices.length - 1]
  const color = last >= pre ? tc.up : tc.down
  const { yMin, yMax } = calcTrendYRange({
    mode: settingsState.trendYScale || 'normal',
    prices,
    preClose: pre,
  })
  chart.setOption({
    animation: false,
    grid: { left: 8, right: 8, top: 8, bottom: 18 },
    xAxis: { type: 'category', data: times, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: tc.split } } },
    yAxis: {
      type: 'value', min: yMin, max: yMax,
      splitLine: { lineStyle: { color: tc.split } },
      axisLabel: { show: false },
    },
    series: [{
      type: 'line', data: prices, showSymbol: false,
      lineStyle: { width: 1.4, color },
      areaStyle: { color: color + '22' },
      markLine: {
        silent: true, symbol: 'none',
        data: [{ yAxis: pre }],
        lineStyle: { color: tc.split, width: 1, type: 'solid' },
        label: { show: false },
      },
    }],
  }, true)
}

onUnmounted(() => { clearTimeout(timer); hide() })
</script>

<style scoped>
.mini-host { display: inline; }
</style>
