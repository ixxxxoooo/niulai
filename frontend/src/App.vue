<template>
  <div class="app-shell" :class="[navMode === 'side' ? 'nav-side' : 'nav-top', { 'sidebar-collapsed': sideCollapsed }]">
    <div v-if="sectorMenu" class="nav-overlay" @click="sectorMenu = false"></div>

    <!-- ========== 顶部导航栏（仅 top 模式） ========== -->
    <div v-if="navMode === 'top'" class="topbar">
      <div class="brand" @click="go('/')">
        <img class="brand-logo" src="/niulai.png" alt="牛来" />
      </div>
      <nav class="nav">
        <a :class="{ active: route.name === 'overview' }" @click="go('/')">盘面总览</a>
        <a :class="{ active: route.name === 'global' }" @click="go('/global')">全球</a>
        <span class="nav-drop" @click.stop="sectorMenu = !sectorMenu">
          <a class="nav-drop-btn" :class="{ active: route.name === 'sectors' }">板块 <span class="caret">▾</span></a>
          <div v-if="sectorMenu" class="submenu" @click.stop>
            <a :class="{ active: route.name === 'sectors' && !route.flow && !route.strength }" @click="go('/sectors'); sectorMenu = false">板块分析</a>
            <a :class="{ active: route.name === 'sectors' && route.flow }" @click="go('/sectors/flow'); sectorMenu = false">板块资金</a>
            <a :class="{ active: route.name === 'sectors' && route.strength }" @click="go('/sectors/strength'); sectorMenu = false">板块强度</a>
          </div>
        </span>
        <a :class="{ active: route.name === 'rank' }" @click="go('/rank')">榜单</a>
        <a :class="{ active: route.name === 'ladder' }" @click="go('/ladder')">连板梯队</a>
        <a :class="{ active: route.name === 'watchlist' }" @click="go('/watchlist')">自选股</a>
        <a :class="{ active: route.name === 'alerts' }" @click="go('/alerts')">监控</a>
        <a :class="{ active: route.name === 'seats' }" @click="go('/seats')">游资</a>
        <a :class="{ active: route.name === 'screener' }" @click="go('/screener')">选股</a>
      </nav>
      <div class="topbar-right">
        <SearchSuggest placeholder="代码 / 名称 / 拼音" @select="onSearchSelect" />
        <div class="clock">
          <div>{{ now }}</div>
          <div class="clock-sub">
            <span class="session">{{ session }}</span>
            <span
              class="clock-count"
              role="button"
              tabindex="0"
              title="点击立即刷新"
              @click="manualRefresh"
              @keydown.enter.prevent="manualRefresh"
            >
              <span class="ri-dot" :class="{ active: polling.refreshing }"></span>
              <span>{{ polling.countdown }}s</span>
            </span>
          </div>
          <div class="topbar-actions">
            <button class="icon-btn" title="整页截图" @click="screenshotPage">
              <UiIcon name="screenshot" :size="16" />
            </button>
            <button class="icon-btn" title="设置" @click="go('/settings')">
              <UiIcon name="settings" :size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== 左侧导航栏（仅 side 模式） ========== -->
    <aside v-if="navMode === 'side'" class="sidebar" :class="{ collapsed: sideCollapsed }">
      <div class="side-head">
        <div class="brand" :class="{ 'brand-collapsed': sideCollapsed }" :title="sideCollapsed ? '展开导航' : '牛来'" @click="onSideBrandClick">
          <img class="brand-logo" :src="sideCollapsed ? '/favicon.png' : '/niulai.png'" :alt="sideCollapsed ? '牛来' : '牛来'" />
        </div>
        <button v-if="!sideCollapsed" class="icon-btn side-toggle" title="收起导航" @click="sideCollapsed = true">
          <UiIcon name="menu" :size="15" />
        </button>
      </div>

      <!-- 搜索：展开状态直接显示输入框，收起状态显示放大镜图标 -->
      <div class="side-search">
        <button v-if="sideCollapsed" class="side-search-btn" title="搜索股票" @click="onOpenSearch">
          <UiIcon name="search" :size="15" />
        </button>
        <SearchSuggest
          v-else
          placeholder="代码 / 名称 / 拼音"
          @select="onSearchSelect"
        />
      </div>

      <nav class="side-nav" v-if="!sideCollapsed">
        <a :class="{ active: route.name === 'overview' }" @click="go('/')">盘面总览</a>
        <a :class="{ active: route.name === 'global' }" @click="go('/global')">全球</a>
        <span class="side-group">板块</span>
        <a class="side-sub" :class="{ active: route.name === 'sectors' && !route.flow && !route.strength }" @click="go('/sectors')">板块分析</a>
        <a class="side-sub" :class="{ active: route.name === 'sectors' && route.flow }" @click="go('/sectors/flow')">板块资金</a>
        <a class="side-sub" :class="{ active: route.name === 'sectors' && route.strength }" @click="go('/sectors/strength')">板块强度</a>
        <a :class="{ active: route.name === 'rank' }" @click="go('/rank')">榜单</a>
        <a :class="{ active: route.name === 'ladder' }" @click="go('/ladder')">连板梯队</a>
        <a :class="{ active: route.name === 'watchlist' }" @click="go('/watchlist')">自选股</a>
        <a :class="{ active: route.name === 'alerts' }" @click="go('/alerts')">监控</a>
        <a :class="{ active: route.name === 'seats' }" @click="go('/seats')">游资</a>
        <a :class="{ active: route.name === 'screener' }" @click="go('/screener')">选股</a>
      </nav>
      <nav class="side-nav side-collapsed-nav" v-else>
        <a :class="{ active: route.name === 'overview' }" @click="go('/')" title="盘面总览">盘</a>
        <a :class="{ active: route.name === 'global' }" @click="go('/global')" title="全球">全</a>
        <a :class="{ active: route.name === 'sectors' }" @click="go('/sectors')" title="板块分析">板</a>
        <a :class="{ active: route.name === 'rank' }" @click="go('/rank')" title="榜单">热</a>
        <a :class="{ active: route.name === 'ladder' }" @click="go('/ladder')" title="连板梯队">连</a>
        <a :class="{ active: route.name === 'watchlist' }" @click="go('/watchlist')" title="自选股">自</a>
        <a :class="{ active: route.name === 'alerts' }" @click="go('/alerts')" title="监控">监</a>
        <a :class="{ active: route.name === 'seats' }" @click="go('/seats')" title="游资">游</a>
        <a :class="{ active: route.name === 'screener' }" @click="go('/screener')" title="选股">选</a>
      </nav>

      <!-- 侧边栏底部：设置 + 时间 -->
      <div class="side-foot">
        <button class="side-foot-btn" title="设置" @click="go('/settings')">
          <UiIcon name="settings" :size="15" />
          <span v-if="!sideCollapsed">设置</span>
        </button>
        <div class="side-clock" v-if="!sideCollapsed">
          <div class="clock">
            <div>{{ now }}</div>
            <div class="clock-sub">
              <span class="session">{{ session }}</span>
              <span
                class="clock-count"
                role="button"
                tabindex="0"
                title="点击立即刷新"
                @click="manualRefresh"
                @keydown.enter.prevent="manualRefresh"
              >
                <span class="ri-dot" :class="{ active: polling.refreshing }"></span>
                <span>{{ polling.countdown }}s</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <div class="container">
      <component
        :is="viewComp"
        v-bind="
          route.name === 'stock' ? { code: route.code }
          : route.name === 'sector' ? { code: route.code }
          : route.name === 'index' ? { secid: route.secid }
          : route.name === 'rank' ? { tab: route.tab }
          : (route.name === 'sectors' ? { sector: route.sector, flow: route.flow, strength: route.strength } : {})
        "
      />
    </div>
    <div class="footer">
      <img class="footer-logo" src="/niulai.png" alt="牛来" />
    </div>
    <div class="bottom-index-bar">
      <IndexTicker />
    </div>
    <GlobalTip />
    <ToastHost />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, shallowRef, computed, watch } from 'vue'
import { parseHash, navigate } from './router.js'
import { api } from './api.js'
import { globalPollingState, setTradingState, triggerPrimaryRefresh } from './composables/usePolling.js'
import { logAction } from './composables/useActionLog.js'
import { loadWatchlist } from './composables/useWatchlist.js'
import { loadSettings, migrateFromLocalStorage, settingsState, applyThemeMode, resolveThemeLight } from './composables/useSettings.js'
import { openStock } from './composables/useStockMeta.js'
import { captureElement } from './composables/useScreenshot.js'
import SearchSuggest from './components/SearchSuggest.vue'
import IndexTicker from './components/IndexTicker.vue'
import GlobalTip from './components/GlobalTip.vue'
import ToastHost from './components/ToastHost.vue'
import Overview from './views/Overview.vue'
import Global from './views/Global.vue'
import SectorHome from './views/SectorHome.vue'
import SectorDetail from './views/SectorDetail.vue'
import IndexDetail from './views/IndexDetail.vue'
import Rank from './views/Rank.vue'
import Ladder from './views/Ladder.vue'
import Stock from './views/Stock.vue'
import Watchlist from './views/Watchlist.vue'
import Alerts from './views/Alerts.vue'
import Seats from './views/Seats.vue'
import Settings from './views/Settings.vue'
import Screener from './views/Screener.vue'
import { startAlertWatcher, stopAlertWatcher } from './composables/useAlertNotify.js'

const route = ref(parseHash())
const sectorMenu = ref(false)
const now = ref('')
const session = ref('')
const isLight = ref(false)
const polling = globalPollingState
const navMode = computed(() => settingsState.navMode === 'side' ? 'side' : 'top')
const sideCollapsed = ref(localStorage.getItem('niulai_side_collapsed') === '1')

const views = {
  overview: Overview, global: Global, sectors: SectorHome, sector: SectorDetail,
  index: IndexDetail,
  rank: Rank, ladder: Ladder, stock: Stock, watchlist: Watchlist,
  alerts: Alerts, settings: Settings, screener: Screener,
  seats: Seats,
}
const viewComp = shallowRef(views[route.value.name] || Overview)

// ---------- 主题 ----------
function applyTheme(mode) {
  isLight.value = applyThemeMode(mode)
}

// 跟随系统：系统主题变化时自动切换
let mql = null
function onSystemTheme() {
  if (settingsState.theme === 'system') {
    isLight.value = resolveThemeLight('system')
    document.body.classList.toggle('light', isLight.value)
    window.dispatchEvent(new CustomEvent('theme-change', { detail: { light: isLight.value, mode: 'system' } }))
  }
}

// ---------- 路由 ----------
function onHash() {
  route.value = parseHash()
  viewComp.value = views[route.value.name] || Overview
  logAction('page_view', route.value.name, location.hash || '#/')
}
function go(p) { navigate(p) }

/** 收起状态下点击放大镜：展开导航栏即可看到搜索框 */
function onOpenSearch() {
  sideCollapsed.value = false
}

/** 点击侧边栏 logo：收起时先展开，展开时回首页 */
function onSideBrandClick() {
  if (sideCollapsed.value) sideCollapsed.value = false
  else go('/')
}

/** 点击倒计时：手动触发当前页主轮询刷新 */
function manualRefresh() {
  if (polling.refreshing) return
  triggerPrimaryRefresh()
}

/** 整页截图：截取内容区（container），复制到剪贴板或下载 PNG */
async function screenshotPage() {
  const el = document.querySelector('.container')
  const routeName = route.value?.name || 'overview'
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  await captureElement(el, `niulai_${routeName}_${ts}.png`, { withFrame: false })
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
let collapseWatch = null

// 收起状态持久化到 localStorage；布局变化会改变容器宽度，通知图表重新适配
collapseWatch = watch(sideCollapsed, v => {
  try { localStorage.setItem('niulai_side_collapsed', v ? '1' : '0') } catch (e) { /* ignore */ }
  window.dispatchEvent(new Event('resize'))
})
watch(navMode, () => window.dispatchEvent(new Event('resize')))

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
  applyTheme(['light', 'dark', 'system'].includes(saved) ? saved : 'light')
  window.addEventListener('hashchange', onHash)
  logAction('page_view', route.value.name, location.hash || '#/')
  try {
    await migrateFromLocalStorage()
    await loadSettings()
    applyTheme(settingsState.theme || 'light')
    await loadWatchlist()
  } catch (e) { /* 迁移/加载失败不阻塞页面 */ }
  try {
    mql = window.matchMedia('(prefers-color-scheme: light)')
    mql.addEventListener('change', onSystemTheme)
  } catch (e) { /* 老浏览器不支持 */ }
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
  if (collapseWatch) collapseWatch()
  if (mql && mql.removeEventListener) mql.removeEventListener('change', onSystemTheme)
})
</script>
