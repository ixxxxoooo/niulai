<template>
  <div class="ui-datepicker" ref="rootEl">
    <button type="button" class="dp-trigger" :class="{ open }" @click="toggle">
      <span class="dp-trigger-label">{{ display }}</span>
      <svg class="dp-trigger-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>
    </button>

    <div v-if="open" class="dp-panel">
      <div class="dp-head">
        <button type="button" class="dp-nav" @click="shiftMonth(-1)" aria-label="上一月">‹</button>
        <span class="dp-title">{{ viewYear }} 年 {{ viewMonth + 1 }} 月</span>
        <button type="button" class="dp-nav" @click="shiftMonth(1)" aria-label="下一月">›</button>
      </div>
      <div class="dp-grid dp-week">
        <span v-for="w in weekLabels" :key="w" class="dp-cell dp-week-label">{{ w }}</span>
      </div>
      <div class="dp-grid dp-days">
        <button
          v-for="d in dayCells"
          :key="d.key"
          type="button"
          class="dp-cell dp-day"
          :class="{
            outside: d.outside,
            weekend: d.weekend,
            today: d.today,
            selected: d.selected,
            trading: d.trading,
          }"
          :disabled="d.outside"
          @click="pick(d)"
        >{{ d.day }}</button>
      </div>
      <div class="dp-foot">
        <button type="button" class="dp-today" @click="pickToday">今天</button>
        <button v-if="modelValue" type="button" class="dp-clear" @click="clear">清空</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' }, // YYYY-MM-DD
  max: { type: String, default: '' },        // 可选最大日期 YYYY-MM-DD
  tradingDates: { type: Array, default: () => [] }, // 可选的交易日集合，用于灰显非交易日
})
const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const rootEl = ref(null)
const viewDate = ref(new Date())
const now = new Date()

const viewYear = computed(() => viewDate.value.getFullYear())
const viewMonth = computed(() => viewDate.value.getMonth())
const weekLabels = ['一', '二', '三', '四', '五', '六', '日']

const display = computed(() => {
  if (!props.modelValue) return '选择日期'
  const [y, m, d] = props.modelValue.split('-').map(Number)
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
})

function isTrading(dateStr) {
  if (!props.tradingDates || !props.tradingDates.length) return true
  return props.tradingDates.includes(dateStr)
}

const dayCells = computed(() => {
  const y = viewYear.value
  const m = viewMonth.value
  const first = new Date(y, m, 1)
  const startDow = first.getDay() === 0 ? 6 : first.getDay() - 1 // 周一起始
  const cells = []
  const start = new Date(y, m, 1 - startDow)
  for (let i = 0; i < 42; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i)
    const dateStr = fmt(d)
    const outside = d.getMonth() !== m
    const weekday = d.getDay()
    const weekend = weekday === 0 || weekday === 6
    const today = dateStr === fmt(now)
    const selected = dateStr === props.modelValue
    cells.push({
      key: dateStr,
      day: d.getDate(),
      dateStr,
      outside,
      weekend,
      today,
      selected,
      trading: isTrading(dateStr),
    })
  }
  return cells
})

function fmt(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function shiftMonth(step) {
  viewDate.value = new Date(viewYear.value, viewMonth.value + step, 1)
}

function pick(d) {
  if (props.max && d.dateStr > props.max) return
  emit('update:modelValue', d.dateStr)
  emit('change', d.dateStr)
  open.value = false
}

function pickToday() {
  const today = fmt(now)
  if (props.max && today > props.max) return
  emit('update:modelValue', today)
  emit('change', today)
  open.value = false
}

function clear() {
  emit('update:modelValue', '')
  emit('change', '')
  open.value = false
}

function toggle() {
  open.value = !open.value
  if (open.value && props.modelValue) {
    const [y, m] = props.modelValue.split('-').map(Number)
    viewDate.value = new Date(y, m - 1, 1)
  }
}

function onDocClick(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.ui-datepicker { position: relative; display: inline-flex; }

.dp-trigger {
  display: inline-flex; align-items: center; gap: 6px; height: 32px;
  padding: 0 12px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text);
  font-size: 13px; cursor: pointer; font-family: inherit; transition: all 0.15s;
}
.dp-trigger:hover, .dp-trigger.open { border-color: var(--accent); color: var(--accent); }
.dp-trigger-label { white-space: nowrap; }
.dp-trigger-icon { flex-shrink: 0; color: var(--text-dim); }
.dp-trigger:hover .dp-trigger-icon, .dp-trigger.open .dp-trigger-icon { color: var(--accent); }

.dp-panel {
  position: absolute; top: calc(100% + 6px); right: 0; z-index: 300;
  width: 268px; padding: 10px;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28);
}

.dp-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.dp-title { font-size: 13px; font-weight: 700; color: var(--text); }
.dp-nav {
  width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 6px; background: transparent; color: var(--text-dim);
  font-size: 16px; cursor: pointer; transition: all 0.15s;
}
.dp-nav:hover { color: var(--accent); background: var(--bg-hover); }

.dp-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.dp-cell {
  display: inline-flex; align-items: center; justify-content: center;
  width: 100%; height: 30px; border-radius: 6px;
  font-size: 12px; border: none; background: transparent; cursor: pointer;
  color: var(--text); transition: all 0.1s; font-family: inherit;
}
.dp-week-label { height: 22px; font-size: 11px; color: var(--text-dim); }
.dp-day:hover:not(.outside) { background: var(--bg-hover); color: var(--accent); }
.dp-day.weekend { color: var(--text-dim); }
.dp-day.outside { color: var(--border); }
.dp-day.today { box-shadow: inset 0 0 0 1px var(--accent); }
.dp-day.selected { background: var(--accent); color: #fff; font-weight: 700; }
.dp-day.trading:not(.selected) { font-weight: 600; }

.dp-foot { display: flex; justify-content: flex-end; gap: 6px; margin-top: 8px; }
.dp-today, .dp-clear {
  height: 26px; padding: 0 10px; border-radius: 6px; font-size: 12px;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text-dim);
  cursor: pointer; transition: all 0.15s; font-family: inherit;
}
.dp-today:hover, .dp-clear:hover { border-color: var(--accent); color: var(--accent); }
</style>