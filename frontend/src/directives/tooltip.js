/**
 * 全局统一瞬时响应 Tooltip 浮窗指令与事件监听器
 * 80ms 极速响应，统一项目金融主题视觉，避免系统原生 title 延迟与样式冲突
 */
let tooltipEl = null
let showTimer = null
let hideTimer = null
let activeTarget = null

function ensureTooltipEl() {
  if (tooltipEl && document.body.contains(tooltipEl)) return tooltipEl
  tooltipEl = document.createElement('div')
  tooltipEl.className = 'global-ui-tooltip'
  document.body.appendChild(tooltipEl)
  return tooltipEl
}

function renderFormattedTooltip(text) {
  if (!text) return ''
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  
  // 支持 【标题】 高亮
  const formatted = escaped
    .replace(/【([^】]+)】/g, '<strong class="tip-title">【$1】</strong>')
    .replace(/\n/g, '<br/>')
  return formatted
}

function showTooltip(el, text) {
  if (!text) return
  const tip = ensureTooltipEl()
  tip.innerHTML = renderFormattedTooltip(text)
  tip.style.display = 'block'
  tip.style.opacity = '0'
  tip.style.transform = 'translateY(4px) scale(0.98)'

  const rect = el.getBoundingClientRect()
  const tipRect = tip.getBoundingClientRect()

  // 优先在元素上方居中显示
  let top = rect.top - tipRect.height - 8
  let left = rect.left + (rect.width - tipRect.width) / 2

  // 顶部空间不足，翻转到下方
  if (top < 10) {
    top = rect.bottom + 8
  }

  // 左右视口边缘吸附
  if (left < 10) left = 10
  if (left + tipRect.width > window.innerWidth - 10) {
    left = window.innerWidth - tipRect.width - 10
  }

  tip.style.top = `${Math.round(top)}px`
  tip.style.left = `${Math.round(left)}px`

  requestAnimationFrame(() => {
    tip.style.opacity = '1'
    tip.style.transform = 'translateY(0) scale(1)'
  })
}

function hideTooltip() {
  if (!tooltipEl) return
  tooltipEl.style.opacity = '0'
  tooltipEl.style.transform = 'translateY(4px) scale(0.98)'
  clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    if (tooltipEl && tooltipEl.style.opacity === '0') {
      tooltipEl.style.display = 'none'
    }
  }, 120)
}

export function initGlobalTooltip() {
  // 委托监听全局 data-tooltip 和 title 属性
  document.addEventListener('mouseover', (e) => {
    const target = e.target.closest('[data-tooltip], [title]')
    if (!target) return

    // 自动接管原生 title，防止浏览器自带的白/黄框延迟 800ms 弹出
    if (target.hasAttribute('title')) {
      const t = target.getAttribute('title')
      if (t) {
        target.setAttribute('data-tooltip', t)
      }
      target.removeAttribute('title')
    }

    const text = target.getAttribute('data-tooltip')
    if (!text) return

    activeTarget = target
    clearTimeout(showTimer)
    clearTimeout(hideTimer)

    // 80ms 瞬时灵敏响应，丝滑无感知延迟
    showTimer = setTimeout(() => {
      if (activeTarget === target) {
        showTooltip(target, text)
      }
    }, 80)
  }, { passive: true })

  document.addEventListener('mouseout', (e) => {
    const target = e.target.closest('[data-tooltip]')
    if (!target || target !== activeTarget) return
    activeTarget = null
    clearTimeout(showTimer)
    hideTooltip()
  }, { passive: true })

  window.addEventListener('scroll', () => {
    if (activeTarget) {
      activeTarget = null
      clearTimeout(showTimer)
      hideTooltip()
    }
  }, { passive: true })
}

export const vTooltip = {
  mounted(el, binding) {
    if (binding.value) {
      el.setAttribute('data-tooltip', binding.value)
    }
  },
  updated(el, binding) {
    if (binding.value) {
      el.setAttribute('data-tooltip', binding.value)
    } else {
      el.removeAttribute('data-tooltip')
    }
  },
  unmounted(el) {
    el.removeAttribute('data-tooltip')
  }
}
