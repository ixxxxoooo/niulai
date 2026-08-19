// 自动刷新组合式函数：统一管理轮询、倒计时、手动刷新
// @author ygw
// 机制说明：前端定时器到点后调用 fetcher（内部请求后端 API，后端每次查询数据源并带 2 秒缓存）
// 非交易时段自动降频到 30 秒，减少无效请求
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { settingsState } from './useSettings.js'

function getSlowInterval() {
  return settingsState.offMarketInterval || 30000
}

// 全局轮询状态，供导航栏读取当前活动页面的刷新倒计时
export const globalPollingState = reactive({
  countdown: 0,
  refreshing: false,
  isTrading: true,
})

/** @type {null | (() => Promise<void>|void)} */
let primaryRefreshFn = null

/**
 * 导航栏点击触发当前页主轮询立即刷新。
 * @author ygw
 */
export function triggerPrimaryRefresh() {
  window.dispatchEvent(new CustomEvent('app-manual-refresh'))
  if (typeof primaryRefreshFn === 'function') return primaryRefreshFn()
  return Promise.resolve()
}

// 交易状态由 App.vue 的 tickClock 更新
export function setTradingState(trading) {
  globalPollingState.isTrading = trading
}

export function usePolling(fetcher, intervalMs = 5000, { immediate = true, primary = true } = {}) {
  const countdown = ref(Math.round(intervalMs / 1000))
  const lastUpdated = ref('')
  const refreshing = ref(false)
  let tickTimer = null

  function getInterval() {
    if (!globalPollingState.isTrading) return getSlowInterval()
    if (primary) return (settingsState.refreshInterval || Math.round(intervalMs / 1000)) * 1000
    return intervalMs
  }

  function syncGlobal() {
    if (!primary) return
    globalPollingState.countdown = countdown.value
    globalPollingState.refreshing = refreshing.value
  }

  async function refresh() {
    refreshing.value = true
    syncGlobal()
    try {
      await fetcher()
    } catch (e) {
      // 错误由页面自行展示，这里仅重置计时
    } finally {
      refreshing.value = false
      countdown.value = Math.round(getInterval() / 1000)
      const d = new Date()
      const p = (n) => String(n).padStart(2, '0')
      lastUpdated.value = `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
      syncGlobal()
    }
  }

  function onVisibilityChange() {
    if (document.hidden) {
      if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
    } else {
      if (!tickTimer) {
        refresh()
        tickTimer = setInterval(() => {
          countdown.value -= 1
          if (countdown.value <= 0) refresh()
          syncGlobal()
        }, 1000)
      }
    }
  }

  function start() {
    stop()
    if (primary) primaryRefreshFn = refresh
    if (immediate) refresh()
    if (!document.hidden) {
      tickTimer = setInterval(() => {
        countdown.value -= 1
        if (countdown.value <= 0) refresh()
        syncGlobal()
      }, 1000)
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
  }

  function stop() {
    document.removeEventListener('visibilitychange', onVisibilityChange)
    if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
    if (primary && primaryRefreshFn === refresh) primaryRefreshFn = null
  }

  onMounted(start)
  onUnmounted(stop)

  return { countdown, lastUpdated, refreshing, refresh, start, stop }
}

