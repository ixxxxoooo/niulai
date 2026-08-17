// 设置（SQLite），启动时从后端拉取；变更同时写后端
// @author ygw
import { reactive } from 'vue'
import { api } from '../api.js'
import { logAction } from './useActionLog.js'

export const settingsState = reactive({
  theme: 'light',
  navMode: 'top',
  refreshInterval: 5,
  offMarketInterval: 30000,
  chartTopN: 20,
  // 分时坐标：normal=普通对称自适应 / fill=满占 / limit=涨停板固定
  trendYScale: 'normal',
  // K线坐标：auto=可见高低+边距 / fixed=首价对称固定
  klineYScale: 'auto',
  hideKcb: false,
  hideCyb: false,
  hideSt: false,
  hideBse: false,
  autoSyncHours: 0,
  aiEnabled: false,
  aiApiKey: '',
  aiModel: 'deepseek-chat',
  aiBaseUrl: 'https://api.deepseek.com',
  loaded: false,
})

/**
 * 从后端加载设置并应用到内存状态
 */
export async function loadSettings() {
  try {
    const r = await api.settings()
    const items = r.items || {}
    if (items.theme) settingsState.theme = items.theme
    if (items.navMode && ['top', 'side'].includes(items.navMode)) settingsState.navMode = items.navMode
    if (items.refreshInterval) settingsState.refreshInterval = parseInt(items.refreshInterval, 10) || 5
    if (items.offMarketInterval) settingsState.offMarketInterval = parseInt(items.offMarketInterval, 10) || 30000
    if (items.chartTopN) settingsState.chartTopN = parseInt(items.chartTopN, 10) || 20
    if (items.trendYScale && ['normal', 'fill', 'limit'].includes(items.trendYScale)) {
      settingsState.trendYScale = items.trendYScale
    }
    if (items.klineYScale && ['auto', 'fixed'].includes(items.klineYScale)) {
      settingsState.klineYScale = items.klineYScale
    }
    settingsState.hideKcb = items.hideKcb === '1'
    settingsState.hideCyb = items.hideCyb === '1'
    settingsState.hideSt = items.hideSt === '1'
    settingsState.hideBse = items.hideBse === '1'
    if (items.autoSyncHours) settingsState.autoSyncHours = parseInt(items.autoSyncHours, 10) || 0
    settingsState.aiEnabled = items.aiEnabled === '1'
    if (items.aiApiKey) settingsState.aiApiKey = items.aiApiKey
    if (items.aiModel) settingsState.aiModel = items.aiModel
    if (items.aiBaseUrl) settingsState.aiBaseUrl = items.aiBaseUrl
    settingsState.loaded = true
  } catch (e) { /* 后端未就绪时保留默认 */ }
  return settingsState
}

/**
 * 主题模式生效时的亮色判断：light=true / dark=false / system=跟随系统
 * @param {string} mode
 * @returns {boolean}
 */
export function resolveThemeLight(mode) {
  if (mode === 'light') return true
  if (mode === 'dark') return false
  try {
    return window.matchMedia('(prefers-color-scheme: light)').matches
  } catch (e) {
    return false
  }
}

/**
 * 应用主题模式（dark/light/system），同步 body class + localStorage + 内存状态 + 事件
 * @param {string} mode
 * @returns {boolean} 生效的亮色
 */
export function applyThemeMode(mode = 'system') {
  const m = ['light', 'dark', 'system'].includes(mode) ? mode : 'system'
  const light = resolveThemeLight(m)
  document.body.classList.toggle('light', light)
  localStorage.setItem('theme', m)
  settingsState.theme = m
  window.dispatchEvent(new CustomEvent('theme-change', { detail: { light, mode: m } }))
  return light
}

/**
 * 写入单条设置
 * @param {string} key
 * @param {string|number} value
 */
export async function saveSetting(key, value) {
  const cur = settingsState[key]
  if (typeof cur === 'boolean') settingsState[key] = value === true || value === '1' || value === 1
  else if (typeof cur === 'number') settingsState[key] = Number(value)
  else settingsState[key] = value
  logAction('setting_change', key, String(value))
  try {
    const stored = typeof value === 'boolean' ? (value ? '1' : '0') : value
    await api.setSetting(key, stored)
  } catch (e) { /* 失败时内存值仍生效 */ }
  // 图表坐标变更通知各页面重绘
  if (key === 'trendYScale' || key === 'klineYScale') {
    window.dispatchEvent(new CustomEvent('chart-scale-change', { detail: { key, value: settingsState[key] } }))
  }
}

/**
 * 将浏览器 localStorage 中的旧配置/自选迁移到 SQLite（只执行一次）
 */
export async function migrateFromLocalStorage() {
  if (localStorage.getItem('sqliteMigrated') === '1') return
  const items = {}
  const keys = ['theme', 'refreshInterval', 'offMarketInterval', 'chartTopN']
  for (const k of keys) {
    const v = localStorage.getItem(k)
    if (v != null) items[k] = v
  }
  try {
    if (Object.keys(items).length) await api.setSettingsBulk(items)
    const raw = localStorage.getItem('watchlist')
    if (raw) {
      const codes = JSON.parse(raw)
      if (Array.isArray(codes) && codes.length) {
        await api.watchlistImport(codes.filter(c => /^\d{6}$/.test(c)))
      }
      localStorage.removeItem('watchlist')
    }
    localStorage.setItem('sqliteMigrated', '1')
    logAction('migrate_localstorage', '', JSON.stringify(Object.keys(items)))
  } catch (e) {
    logAction('migrate_failed', '', e.message || String(e))
  }
}
