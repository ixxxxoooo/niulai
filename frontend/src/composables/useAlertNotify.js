/**
 * 价格监控 + 持仓异动监控：
 * 轮询后端 /alerts/check 和 /alerts/check-changes，
 * 触发时发 Chrome/macOS 桌面通知。
 * @author ygw
 */
import { api } from '../api.js'

let timer = null
let permissionAsked = false
const notifiedIds = new Set()
const changeNotifiedKeys = new Set()

const METRIC_LABEL = {
  price: '价格',
  points: '点数',
  change_pct: '涨跌幅',
}

function fmtVal(metric, v) {
  if (v == null || Number.isNaN(v)) return '-'
  if (metric === 'change_pct') return (v > 0 ? '+' : '') + Number(v).toFixed(2) + '%'
  return Number(v).toFixed(metric === 'points' ? 2 : 2)
}

async function ensurePermission() {
  if (!('Notification' in window)) return false
  if (Notification.permission === 'granted') return true
  if (Notification.permission === 'denied') return false
  if (permissionAsked) return false
  permissionAsked = true
  try {
    const p = await Notification.requestPermission()
    return p === 'granted'
  } catch (e) {
    return false
  }
}

function fireNotify(item) {
  const key = `${item.id}:${item.current}:${item.checked_at || ''}`
  if (notifiedIds.has(key)) return
  notifiedIds.add(key)
  if (notifiedIds.size > 80) {
    const first = notifiedIds.values().next().value
    notifiedIds.delete(first)
  }
  const opLabel = item.op === 'gte' ? '≥' : '≤'
  const mLabel = METRIC_LABEL[item.metric] || item.metric
  const title = `牛来提醒 · ${item.name}`
  const body = `${mLabel} ${fmtVal(item.metric, item.current)} ${opLabel} ${fmtVal(item.metric, item.threshold)}`
    + (item.change_pct != null ? `（涨跌 ${fmtVal('change_pct', item.change_pct)}）` : '')
    + (item.note ? `\n${item.note}` : '')
  try {
    const n = new Notification(title, {
      body,
      tag: `alert-${item.id}`,
      requireInteraction: false,
    })
    n.onclick = () => {
      window.focus()
      const path = item.target_type === 'index'
        ? '/index/' + (item.code.includes('.') ? item.code : item.code)
        : '/stock/' + item.code
      location.hash = path
      n.close()
    }
  } catch (e) { /* ignore */ }
}

/**
 * 持仓异动桌面通知
 * @param {Object} item - 后端返回的异动项
 */
function fireChangeNotify(item) {
  const key = `${item.code}:${item.type_code}:${item.time || ''}`
  if (changeNotifiedKeys.has(key)) return
  changeNotifiedKeys.add(key)
  if (changeNotifiedKeys.size > 200) {
    const first = changeNotifiedKeys.values().next().value
    changeNotifiedKeys.delete(first)
  }

  const name = item.name || item.code
  const typeName = item.type_name || '异动'
  const pct = item.change_pct
  const pctStr = pct != null ? `（涨跌 ${pct > 0 ? '+' : ''}${Number(pct).toFixed(2)}%）` : ''
  const title = `牛来异动 · ${name}`
  const body = `${typeName}${pctStr}\n时间 ${item.time || '-'}`

  try {
    const n = new Notification(title, {
      body,
      tag: `change-${item.code}-${item.type_code}`,
      requireInteraction: true,
    })
    n.onclick = () => {
      window.focus()
      location.hash = '/stock/' + item.code
      n.close()
    }
  } catch (e) { /* ignore */ }
}

async function tick() {
  try {
    const ok = await ensurePermission()
    if (!ok) return

    // 价格告警
    const res = await api.alertsCheck()
    const list = (res && res.triggered) || []
    for (const it of list) {
      it.checked_at = res.checked_at
      fireNotify(it)
    }

    // 持仓异动
    try {
      const cr = await api.alertsCheckChanges()
      const changes = (cr && cr.changes) || []
      for (const c of changes) {
        fireChangeNotify(c)
      }
    } catch (_) { /* 静默 */ }
  } catch (e) { /* 静默 */ }
}

/** 启动全局监控轮询（App 挂载时调用一次） */
export function startAlertWatcher(intervalMs = 8000) {
  stopAlertWatcher()
  ensurePermission()
  tick()
  timer = setInterval(tick, intervalMs)
}

export function stopAlertWatcher() {
  if (timer) { clearInterval(timer); timer = null }
}

export async function requestNotifyPermission() {
  permissionAsked = false
  return ensurePermission()
}
