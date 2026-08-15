<template>
  <div class="index-ticker" v-if="items.length">
    <a
      v-for="q in items"
      :key="q.secid || q.code"
      class="it-item"
      :class="pctClass(q.change_pct)"
      @click="goIndex(q)"
      :title="(q.name || '') + ' · 点击查看详情'"
    >
      <span class="it-name">{{ shortName(q) }}</span>
      <span class="it-price">{{ fmtPrice(q.price) }}</span>
      <span class="it-pct">{{ fmtPct(q.change_pct) }}</span>
    </a>
  </div>
</template>

<script setup>
/**
 * 导航栏常驻指数：上证 / 创业板 / 科创50，定时刷新。
 * @author ygw
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { fmtPrice, fmtPct, pctClass } from '../utils.js'
import { navigate } from '../router.js'
import { settingsState } from '../composables/useSettings.js'
import { globalPollingState } from '../composables/usePolling.js'

const SECIDS = '1.000001,0.399006,1.000688'
const items = ref([])
let pollTimer = null
let rescheduleTimer = null

const SHORT = {
  '000001': '上证',
  '399006': '创业',
  '000688': '科创',
}

function shortName(q) {
  return SHORT[q.code] || (q.name || '').slice(0, 2)
}

function goIndex(q) {
  const map = { '000001': '1.000001', '399006': '0.399006', '000688': '1.000688' }
  const secid = q.secid || map[q.code]
  if (secid) navigate('/index/' + secid)
}

async function load() {
  try {
    items.value = await api.indicesQuotes(SECIDS)
  } catch (e) { /* 行情条失败不阻塞 */ }
}

function schedule() {
  clearInterval(pollTimer)
  const trading = globalPollingState.isTrading
  const sec = trading
    ? (settingsState.refreshInterval || 5)
    : Math.max(15, Math.round((settingsState.offMarketInterval || 30000) / 1000))
  pollTimer = setInterval(load, sec * 1000)
}

onMounted(() => {
  load()
  schedule()
  rescheduleTimer = setInterval(schedule, 60000)
})
onUnmounted(() => {
  clearInterval(pollTimer)
  clearInterval(rescheduleTimer)
})
</script>
