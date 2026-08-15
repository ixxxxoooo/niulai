// 个股详情左右切换上下文：按进入入口保存列表与返回页
// @author ygw
import { reactive } from 'vue'
import { navigate } from '../router.js'

const STORAGE_KEY = 'stock_nav_ctx'

/** @type {{ origin: string, originLabel: string, codes: string[] }} */
export const stockNavState = reactive({
  origin: '',
  originLabel: '返回',
  codes: [],
})

/**
 * 从 sessionStorage 恢复导航上下文。
 */
export function loadStockNav() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    stockNavState.origin = data.origin || ''
    stockNavState.originLabel = data.originLabel || '返回'
    stockNavState.codes = Array.isArray(data.codes) ? data.codes.map(c => String(c).toUpperCase()) : []
  } catch (e) {
    clearStockNav()
  }
}

/**
 * 持久化导航上下文。
 */
function persist() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      origin: stockNavState.origin,
      originLabel: stockNavState.originLabel,
      codes: stockNavState.codes,
    }))
  } catch (e) { /* ignore */ }
}

/**
 * 设置进入个股详情时的切换列表与返回页。
 * @param {{ origin?: string, originLabel?: string, list?: Array<object|string> }} ctx
 */
export function setStockNav(ctx = {}) {
  const codes = []
  const seen = new Set()
  for (const item of (ctx.list || [])) {
    const code = typeof item === 'string' ? item : item?.code
    if (!code) continue
    const c = String(code).toUpperCase()
    if (seen.has(c)) continue
    seen.add(c)
    codes.push(c)
  }
  stockNavState.origin = ctx.origin || ''
  stockNavState.originLabel = ctx.originLabel || '返回'
  stockNavState.codes = codes
  persist()
}

/** 清空导航上下文 */
export function clearStockNav() {
  stockNavState.origin = ''
  stockNavState.originLabel = '返回'
  stockNavState.codes = []
  try { sessionStorage.removeItem(STORAGE_KEY) } catch (e) { /* ignore */ }
}

/**
 * 当前代码在列表中的位置与是否可左右切换。
 * @param {string} code
 */
export function stockNavIndex(code) {
  const c = String(code || '').toUpperCase()
  const idx = stockNavState.codes.indexOf(c)
  return {
    index: idx,
    total: stockNavState.codes.length,
    canPrev: idx > 0,
    canNext: idx >= 0 && idx < stockNavState.codes.length - 1,
    hasList: stockNavState.codes.length > 1 && idx >= 0,
  }
}

/**
 * 切换到同列表上一只 / 下一只；使用 replace，返回仍回到入口页。
 * @param {string} code 当前代码
 * @param {number} delta -1 上一只 / +1 下一只
 */
export function switchSiblingStock(code, delta) {
  const { index, canPrev, canNext } = stockNavIndex(code)
  if (delta < 0 && !canPrev) return false
  if (delta > 0 && !canNext) return false
  const next = stockNavState.codes[index + delta]
  if (!next) return false
  navigate('/stock/' + next, { replace: true })
  return true
}

/**
 * 返回进入详情前的入口页（优先 origin，否则 history.back）。
 * @param {string} [fallback='/']
 */
export function backFromStock(fallback = '/') {
  if (stockNavState.origin) {
    navigate(stockNavState.origin)
    return
  }
  if (history.length > 1) history.back()
  else navigate(fallback)
}

loadStockNav()
