// 自绘确认弹窗逻辑与状态管理，替代原生 window.confirm
// @author ygw
import { reactive } from 'vue'

export const confirmState = reactive({
  open: false,
  title: '操作确认',
  message: '',
  detail: '',
  confirmText: '确定',
  cancelText: '取消',
  variant: 'danger', // 'danger' | 'primary' | 'warning'
  resolve: null,
})

/**
 * 弹出符合牛来暗色金融 UI 规范的高颜值自绘确认弹窗
 * @param {object|string} options
 * @param {string} [options.title] 标题（默认：操作确认）
 * @param {string} [options.message] 核心提示信息
 * @param {string} [options.detail] 次要补充说明 / 提示文案
 * @param {string} [options.confirmText] 确认按钮文字（默认：确定 / 移出 / 删除）
 * @param {string} [options.cancelText] 取消按钮文字（默认：取消）
 * @param {string} [options.variant] 样式类别 'danger' | 'primary' | 'warning'（默认：danger）
 * @returns {Promise<boolean>} 用户确认返回 true，取消/关闭返回 false
 */
export function showConfirm(options = {}) {
  return new Promise((resolve) => {
    if (typeof options === 'string') {
      confirmState.title = '操作确认'
      confirmState.message = options
      confirmState.detail = ''
      confirmState.confirmText = '确定'
      confirmState.cancelText = '取消'
      confirmState.variant = 'danger'
    } else {
      confirmState.title = options.title || '操作确认'
      confirmState.message = options.message || ''
      confirmState.detail = options.detail || ''
      confirmState.confirmText = options.confirmText || '确定'
      confirmState.cancelText = options.cancelText || '取消'
      confirmState.variant = options.variant || 'danger'
    }
    confirmState.open = true
    confirmState.resolve = resolve
  })
}

export function handleConfirm() {
  confirmState.open = false
  if (confirmState.resolve) {
    confirmState.resolve(true)
    confirmState.resolve = null
  }
}

export function handleCancel() {
  confirmState.open = false
  if (confirmState.resolve) {
    confirmState.resolve(false)
    confirmState.resolve = null
  }
}
