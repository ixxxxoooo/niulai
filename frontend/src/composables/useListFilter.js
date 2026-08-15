// 列表过滤：科创板 / 创业板 / 北交所 / ST
// @author ygw
import { computed } from 'vue'
import { settingsState } from './useSettings.js'

/**
 * 是否北交所代码
 * @param {string} code
 */
export function isBseCode(code) {
  return /^(43|83|87|88|92)/.test(String(code || ''))
}

/**
 * 行是否通过当前过滤（勾选表示隐藏该类）
 * @param {object} row
 */
export function matchListFilter(row) {
  if (!row) return false
  const code = String(row.code || '')
  const name = String(row.name || '')
  if (settingsState.hideSt && /ST/i.test(name)) return false
  if (settingsState.hideKcb && /^(688|689)/.test(code)) return false
  if (settingsState.hideCyb && /^(300|301)/.test(code)) return false
  if (settingsState.hideBse && isBseCode(code)) return false
  return true
}

/**
 * 过滤数组
 * @param {Array} rows
 */
export function applyListFilter(rows) {
  if (!Array.isArray(rows)) return []
  if (!settingsState.hideSt && !settingsState.hideKcb && !settingsState.hideCyb && !settingsState.hideBse) {
    return rows
  }
  return rows.filter(matchListFilter)
}

/**
 * 响应式过滤
 * @param {import('vue').Ref<Array>} rowsRef
 */
export function useFilteredRows(rowsRef) {
  return computed(() => applyListFilter(rowsRef.value || []))
}
