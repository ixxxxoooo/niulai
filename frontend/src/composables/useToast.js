/**
 * 全局轻提示（toast）：右上角 flash 消息。
 * 用法：showToast('截图成功') / showToast('截图失败', 'error')
 * @author ygw
 */
import { reactive } from 'vue'

export const toastState = reactive({
  items: [],
  _id: 0,
})

/**
 * 展示一条 flash 消息
 * @param {string} message 提示文本
 * @param {string} [type='success'] success | error
 * @param {number} [duration=2500] 展示时长（毫秒）
 */
export function showToast(message, type = 'success', duration = 2500) {
  const id = ++toastState._id
  toastState.items.push({ id, message, type })
  setTimeout(() => {
    const idx = toastState.items.findIndex((t) => t.id === id)
    if (idx !== -1) toastState.items.splice(idx, 1)
  }, duration)
}

export function clearToasts() {
  toastState.items.splice(0, toastState.items.length)
}