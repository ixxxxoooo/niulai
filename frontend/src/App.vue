<template>
  <div>
    <div class="topbar">
      <div class="brand">
        <svg class="brand-logo" viewBox="0 0 64 64" width="22" height="22">
          <rect width="64" height="64" rx="14" fill="var(--accent)"/>
          <path d="M12 44 L22 34 L30 40 L42 22 L52 28" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="52" cy="28" r="3.5" fill="#fff"/>
        </svg>
        盯盘
      </div>
      <nav class="nav">
        <a :class="{ active: route.name === 'overview' }" @click="go('/')">盘面总览</a>
        <a :class="{ active: route.name === 'sectors' }" @click="go('/sectors')">板块分析</a>
        <a :class="{ active: route.name === 'sectorMoves' }" @click="go('/sector-moves')">板块资金</a>
        <a :class="{ active: route.name === 'rank' }" @click="go('/rank')">热门与资金</a>
        <a :class="{ active: route.name === 'ladder' }" @click="go('/ladder')">连板梯队</a>
        <a :class="{ active: route.name === 'watchlist' }" @click="go('/watchlist')">自选股</a>
        <a :class="{ active: route.name === 'alerts' }" @click="go('/alerts')">监控</a>
      </nav>
      <div class="topbar-right">
        <div
          class="refresh-indicator"
          title="点击立即刷新"
          role="button"
          tabindex="0"
          @click="manualRefresh"
          @keydown.enter.prevent="manualRefresh"
        >
          <span class="ri-dot" :class="{ active: polling.refreshing }"></span>
          <span class="ri-text">{{ polling.countdown }}s</span>
        </div>
        <SearchSuggest placeholder="代码 / 名称 / 拼音，如 茅台、gzmt" @select="onSearchSelect" />
        <button class="theme-btn" title="设置" @click="go('/settings')">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1.08 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1.08z" />
          </svg>
        </button>
        <button class="theme-btn" :title="isLight ? '切换到深色模式' : '切换到浅色模式'" @click="toggleTheme">
          <!-- 深色模式显示太阳（点击切浅色）；浅色模式显示月亮（点击切深色） -->
          <svg v-if="!isLight" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
          </svg>
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        </button>
        <div class="clock">
          <div>{{ now }}</div>
          <div class="session">{{ session }}</div>
        </div>
      </div>
    </div>
    <div class="container">
      <component
        :is="viewComp"
        v-bind="
          route.name === 'stock' ? { code: route.code }
          : route.name === 'sector' ? { code: route.code }
          : route.name === 'index' ? { secid: route.secid }
          : route.name === 'rank' ? { tab: route.tab }
          : (route.name === 'sectors' ? { sector: route.sector } : {})
        "
      />
    </div>
    <div class="footer">
      盯盘 · 数据来源：东方财富 / 腾讯 / 同花顺公开行情（免费，仅个人学习使用，不构成投资建议）
    </div>
    <div class="bottom-index-bar">
      <IndexTicker />
    </div>
    <GlobalTip />
    <ToastHost />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef } from 'vue'
import { parseHash, navigate } from './router.js'
import { api } from './api.js'
import { globalPollingState, setTradingState, triggerPrimaryRefresh } from './composables/usePolling.js'
import { logAction } from './composables/useActionLog.js'
import { loadWatchlist } from './composables/useWatchlist.js'
import { loadSettings, saveSetting, migrateFromLocalStorage, settingsState } from './composables/useSettings.js'
import { openStock } from './composables/useStockMeta.js'
import SearchSuggest from './components/SearchSuggest.vue'
import IndexTicker from './components/IndexTicker.vue'
import GlobalTip from './components/GlobalTip.vue'
import ToastHost from './components/ToastHost.vue'
import Overview from './views/Overview.vue'
import Sectors from './views/Sectors.vue'
import SectorDetail from './views/SectorDetail.vue'
import SectorMoves from './views/SectorMoves.vue'
import IndexDetail from './views/IndexDetail.vue'
import Rank from './views/Rank.vue'
import Ladder from './views/Ladder.vue'
import Stock from './views/Stock.vue'
import Watchlist from './views/Watchlist.vue'
import Alerts from './views/Alerts.vue'
import Settings from './views/Settings.vue'
import { startAlertWatcher, stopAlertWatcher } from './composables/useAlertNotify.js'

const route = ref(parseHash())
const now = ref('')
const session = ref('')
const isLight = ref(false)
const polling = globalPollingState

const views = {
  overview: Overview, sectors: Sectors, sector: SectorDetail,
  sectorMoves: SectorMoves, index: IndexDetail,
  rank: Rank, ladder: Ladder, stock: Stock, watchlist: Watchlist,
  alerts: Alerts, settings: Settings,
}
const viewComp = shallowRef(views[route.value.name] || Overview)

// ---------- 主题 ----------
function applyTheme(light) {
  isLight.value = light
  document.body.classList.toggle('light', light)
  localStorage.setItem('theme', light ? 'light' : 'dark')
  settingsState.theme = light ? 'light' : 'dark'
  window.dispatchEvent(new CustomEvent('theme-change', { detail: { light } }))
}
function toggleTheme() {
  applyTheme(!isLight.value)
  saveSetting('theme', isLight.value ? 'light' : 'dark')
  logAction('theme_toggle', '', isLight.value ? 'light' : 'dark')
}

// ---------- 路由 ----------
function onHash() {
  route.value = parseHash()
  viewComp.value = views[route.value.name] || Overview
  logAction('page_view', route.value.name, location.hash || '#/')
}
function go(p) { navigate(p) }

/** 点击倒计时：手动触发当前页主轮询刷新 */
function manualRefresh() {
  if (polling.refreshing) return
  triggerPrimaryRefresh()
}

// 搜索选中 → 跳转个股页（支持中文模糊搜索）
function onSearchSelect(s) {
  if (s && s.code) {
    logAction('search_select', s.code, s.name || '')
    // 搜索直达：不带列表切换，清空旧入口上下文
    openStock(s)
  }
}

let clockTimer = null
let sessionTimer = null

// 时钟：每秒刷新（纯本地时间，无需接口）
function tickClock() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  now.value = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

// 交易时段：慢轮询接口（变化慢，无需每秒请求）
async function tickSession() {
  try {
    const t = await api.tradingTime()
    session.value = t.session + (t.is_trading_time ? ' · 交易中' : '')
    setTradingState(t.is_trading_time)
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  const saved = localStorage.getItem('theme')
  applyTheme(saved === 'light')
  window.addEventListener('hashchange', onHash)
  logAction('page_view', route.value.name, location.hash || '#/')
  try {
    await migrateFromLocalStorage()
    await loadSettings()
    applyTheme(settingsState.theme === 'light')
    await loadWatchlist()
  } catch (e) { /* 迁移/加载失败不阻塞页面 */ }
  tickClock()
  tickSession()
  clockTimer = setInterval(tickClock, 1000)
  sessionTimer = setInterval(tickSession, 15000)
  startAlertWatcher(8000)
})
onUnmounted(() => {
  window.removeEventListener('hashchange', onHash)
  clearInterval(clockTimer)
  clearInterval(sessionTimer)
  stopAlertWatcher()
})
</script>
