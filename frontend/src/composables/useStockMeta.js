// 个股名称/标签内存缓存，避免详情页先闪代码再出名称
// @author ygw
import { reactive } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { setStockNav, clearStockNav } from './useStockNav.js'

export const stockMetaCache = reactive({})

/**
 * 记住列表里的名称，进入详情页立刻展示。
 * @param {object} row
 */
export function rememberStock(row) {
  if (!row || !row.code) return
  const prev = stockMetaCache[row.code] || {}
  stockMetaCache[row.code] = {
    code: row.code,
    name: row.name || prev.name || '',
    industry: row.industry || prev.industry || '',
    concepts: row.concepts || prev.concepts || '',
    board: row.board || prev.board,
    is_st: row.is_st != null ? row.is_st : prev.is_st,
    classify: row.classify || prev.classify || '',
  }
}

export function peekMeta(code) {
  return stockMetaCache[code] || null
}

/**
 * 从 SQLite 拉取本地标签（快）。
 * @param {string} code
 */
export async function lookupMeta(code) {
  if (!code) return null
  if (stockMetaCache[code]?.name) return stockMetaCache[code]
  try {
    const m = await api.metaLookup(code)
    if (m) rememberStock(m)
    return m
  } catch (e) {
    return peekMeta(code)
  }
}

/**
 * 当前 hash 路径（不含 #），用于作为返回 origin。
 * @returns {string}
 */
function currentOriginPath() {
  return (location.hash || '#/').replace(/^#/, '') || '/'
}

/**
 * 记住并跳转个股详情；可选带入同列表切换上下文。
 * @param {object|string} row
 * @param {{ list?: Array<object|string>, origin?: string, originLabel?: string }} [ctx]
 */
export function openStock(row, ctx = {}) {
  if (!row) return
  const code = typeof row === 'string' ? row : row.code
  if (!code) return
  if (typeof row === 'object') rememberStock(row)

  const list = ctx.list
  if (list && list.length) {
    for (const item of list) {
      if (item && typeof item === 'object') rememberStock(item)
    }
    setStockNav({
      list,
      origin: ctx.origin || currentOriginPath(),
      originLabel: ctx.originLabel || '返回',
    })
  } else if (ctx.origin) {
    setStockNav({
      list: [code],
      origin: ctx.origin,
      originLabel: ctx.originLabel || '返回',
    })
  } else {
    clearStockNav()
  }

  navigate('/stock/' + code)
}
