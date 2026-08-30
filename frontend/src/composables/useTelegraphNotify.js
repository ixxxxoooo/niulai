/**
 * 7x24 全局财经电报后台监控服务：
 * 全局后台静默运行（即使不在 /telegraph 页面），
 * 收到新电报/加红电报时即时触发系统桌面通知与声音提示。
 * @author ygw
 */
import { api } from '../api.js'

let pollTimer = null
let lastSeenId = null
let isFirstCheck = true
let audioCtx = null

export function isTelegraphNotifyEnabled() {
  return localStorage.getItem('niulai_telegraph_notify') === '1'
}

export function isTelegraphAudioEnabled() {
  return localStorage.getItem('niulai_telegraph_audio') === '1'
}

export function playTelegraphBeep() {
  if (!isTelegraphAudioEnabled()) return
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume()
    }
    const osc = audioCtx.createOscillator()
    const gain = audioCtx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(880, audioCtx.currentTime) // A5
    osc.frequency.exponentialRampToValueAtTime(1320, audioCtx.currentTime + 0.12)
    gain.gain.setValueAtTime(0.2, audioCtx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2)
    osc.connect(gain)
    gain.connect(audioCtx.destination)
    osc.start()
    osc.stop(audioCtx.currentTime + 0.22)
  } catch (e) {
    // 忽略音频自动播放策略限制
  }
}

export async function requestTelegraphNotifyPermission() {
  if (typeof Notification === 'undefined') return false
  if (Notification.permission === 'granted') return true
  try {
    const p = await Notification.requestPermission()
    return p === 'granted'
  } catch (e) {
    return false
  }
}

export function sendTelegraphNotification(item) {
  if (!isTelegraphNotifyEnabled()) return
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return

  try {
    const isRed = !!item.is_red
    const title = isRed
      ? `🔴【重要电报】${item.title || '7×24 实时快讯'}`
      : `⚡【财经快讯】${item.title || '7×24 实时快讯'}`

    const body = (item.content || '').slice(0, 120) || '点击进入系统查看快讯详情'

    const n = new Notification(title, {
      body,
      tag: `telegraph-${item.id}`,
      icon: '/niulai.png',
      requireInteraction: isRed, // 加红电报保持在屏幕上直至用户查看
    })

    n.onclick = () => {
      window.focus()
      location.hash = '/telegraph'
      n.close()
    }
  } catch (e) {
    // 忽略通知发送失败
  }
}

async function checkTelegraph() {
  try {
    const notifyOn = isTelegraphNotifyEnabled()
    const audioOn = isTelegraphAudioEnabled()
    const isTelegraphPage = location.hash.startsWith('#/telegraph')

    // 若未开启桌面通知也未开启声音，且不在电报页面，则跳过后台轮询
    if (!notifyOn && !audioOn && !isTelegraphPage) {
      return
    }

    const res = await api.telegraph('all', null, 20)
    const items = (res && res.items) || []
    if (!items.length) return

    const newest = items[0]
    if (isFirstCheck || !lastSeenId) {
      lastSeenId = newest.id
      isFirstCheck = false
      return
    }

    if (newest.id !== lastSeenId) {
      // 提取所有新到达的电报
      const newItems = []
      for (const it of items) {
        if (it.id === lastSeenId) break
        newItems.push(it)
      }
      lastSeenId = newest.id

      // 按发生顺序触发提醒
      for (const it of newItems.reverse()) {
        if (it.is_red) {
          playTelegraphBeep()
        }
        sendTelegraphNotification(it)
        window.dispatchEvent(new CustomEvent('global-new-telegraph', { detail: it }))
      }
    }
  } catch (e) {
    // 失败静默
  }
}

export function startTelegraphWatcher(intervalMs = 6000) {
  stopTelegraphWatcher()
  checkTelegraph()
  pollTimer = setInterval(checkTelegraph, intervalMs)
}

export function stopTelegraphWatcher() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
