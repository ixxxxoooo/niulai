// 前端行为日志：批量防抖上报，不阻塞 UI
// @author ygw
import { api } from '../api.js'

const queue = []
let timer = null

/**
 * 记录用户操作（页面切换、搜索、排序、自选增删等）
 * @param {string} action 行为类型
 * @param {string} [target] 目标（代码/页面名）
 * @param {string} [detail] 补充说明
 */
export function logAction(action, target = '', detail = '') {
  queue.push({
    action,
    target: String(target || ''),
    detail: String(detail || ''),
    ts: new Date().toISOString().replace('T', ' ').slice(0, 19),
  })
  if (queue.length >= 8) flush()
  else if (!timer) timer = setTimeout(flush, 1500)
}

function flush() {
  if (timer) { clearTimeout(timer); timer = null }
  if (!queue.length) return
  const items = queue.splice(0, queue.length)
  api.logActions(items).catch(() => { /* 上报失败不影响使用 */ })
}

if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', flush)
}
