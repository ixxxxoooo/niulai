// 自选股（SQLite），内存缓存供搜索星标等即时展示
// @author ygw
import { reactive } from 'vue'
import { api } from '../api.js'
import { logAction } from './useActionLog.js'

export const watchState = reactive({
  codes: [],
  loaded: false,
})

/**
 * 从后端加载自选列表
 */
export async function loadWatchlist() {
  const r = await api.watchlist()
  watchState.codes = r.codes || []
  watchState.loaded = true
  return watchState.codes
}

export function isWatched(code) {
  return watchState.codes.includes(code)
}

/**
 * 加入自选
 * @param {string} code 6 位代码
 */
export async function addWatch(code) {
  if (!code) return
  await api.watchlistAdd(code)
  if (!watchState.codes.includes(code)) watchState.codes.push(code)
  logAction('watch_add', code)
}

/**
 * 删除自选
 * @param {string} code 6 位代码
 */
export async function removeWatch(code) {
  await api.watchlistRemove(code)
  watchState.codes = watchState.codes.filter(c => c !== code)
  logAction('watch_remove', code)
}

export async function toggleWatch(code) {
  if (isWatched(code)) await removeWatch(code)
  else await addWatch(code)
}

export async function clearWatch() {
  await api.watchlistClear()
  watchState.codes = []
  logAction('watch_clear')
}

export async function importWatch(codes) {
  const r = await api.watchlistImport(codes)
  watchState.codes = r.codes || []
  logAction('watch_import', '', `count=${watchState.codes.length}`)
  return watchState.codes
}
