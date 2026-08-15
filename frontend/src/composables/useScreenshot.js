/**
 * DOM 元素截图：优先复制图片到剪贴板，失败自动降级为下载 PNG。
 * 不改动页面 DOM（避免截图时布局闪缩）；边框/留白在 canvas 后处理中绘制。
 * @author ygw
 */
import { showToast } from './useToast.js'

function cssVar(name, fallback) {
  return getComputedStyle(document.body).getPropertyValue(name).trim() || fallback
}

function cardBg() {
  return cssVar('--bg-card', '#1a1b26')
}

function pageBg() {
  return cssVar('--bg', '') || getComputedStyle(document.body).backgroundColor || '#0d1117'
}

function borderColor() {
  return cssVar('--border', '#30363d')
}

async function loadHtml2canvas() {
  const { default: html2canvas } = await import('html2canvas')
  return html2canvas
}

/**
 * 将 canvas 写入剪贴板；不支持/失败时降级为下载 PNG。
 * @param {HTMLCanvasElement} canvas
 * @param {string} filename 降级下载时的文件名
 * @returns {Promise<boolean>} true=已复制到剪贴板，false=降级为下载
 */
export async function copyCanvas(canvas, filename) {
  if (typeof ClipboardItem !== 'undefined' && navigator.clipboard && navigator.clipboard.write) {
    try {
      const blob = await new Promise((res, rej) => {
        canvas.toBlob((b) => (b ? res(b) : rej(new Error('toBlob 返回 null'))), 'image/png')
      })
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
      return true
    } catch (e) { /* 继续降级下载 */ }
  }
  const url = canvas.toDataURL('image/png')
  const a = document.createElement('a')
  a.href = url
  a.download = filename || '截图.png'
  document.body.appendChild(a)
  a.click()
  a.remove()
  return false
}

/**
 * 在截图外绘制留白 + 圆角描边（纯 canvas，不碰页面）。
 * @param {HTMLCanvasElement} src
 * @param {number} padCss 外边距（CSS 像素）
 * @param {number} scale
 * @returns {HTMLCanvasElement}
 */
function frameCanvas(src, padCss, scale) {
  const pad = Math.round(padCss * scale)
  const radius = Math.round(10 * scale)
  const line = Math.max(1, Math.round(scale))
  const out = document.createElement('canvas')
  out.width = src.width + pad * 2
  out.height = src.height + pad * 2
  const ctx = out.getContext('2d')
  ctx.fillStyle = pageBg()
  ctx.fillRect(0, 0, out.width, out.height)

  const x = pad
  const y = pad
  const w = src.width
  const h = src.height

  // 圆角裁剪后贴图
  ctx.save()
  roundedRect(ctx, x, y, w, h, radius)
  ctx.clip()
  ctx.fillStyle = cardBg()
  ctx.fillRect(x, y, w, h)
  ctx.drawImage(src, x, y)
  ctx.restore()

  // 描边轮廓
  ctx.beginPath()
  roundedRect(ctx, x + line / 2, y + line / 2, w - line, h - line, Math.max(0, radius - line / 2))
  ctx.strokeStyle = borderColor()
  ctx.lineWidth = line
  ctx.stroke()
  return out
}

function roundedRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2)
  ctx.moveTo(x + rr, y)
  ctx.arcTo(x + w, y, x + w, y + h, rr)
  ctx.arcTo(x + w, y + h, x, y + h, rr)
  ctx.arcTo(x, y + h, x, y, rr)
  ctx.arcTo(x, y, x + w, y, rr)
  ctx.closePath()
}

/**
 * 对 DOM 元素截图，结果复制到剪贴板（降级下载），并弹出 toast。
 * 页面零改动；可选在结果图上加卡片轮廓留白。
 * @param {HTMLElement|Ref} el
 * @param {string} filename
 * @param {{ withFrame?: boolean }} [opts] withFrame 默认 true
 * @returns {Promise<boolean>}
 * @author ygw
 */
export async function captureElement(el, filename, opts = {}) {
  const node = el && el.value !== undefined ? el.value : el
  if (!node) { showToast('截图失败', 'error'); return false }
  const withFrame = opts.withFrame !== false

  try {
    const html2canvas = await loadHtml2canvas()
    const scale = Math.min(2, window.devicePixelRatio || 1.5)
    let canvas = await html2canvas(node, {
      backgroundColor: cardBg(),
      scale,
      useCORS: true,
      logging: false,
      onclone: (doc) => {
        doc.querySelectorAll('.btn-screenshot').forEach((n) => n.remove())
      },
    })
    if (withFrame) canvas = frameCanvas(canvas, 14, scale)

    const copied = await copyCanvas(canvas, filename)
    showToast(copied ? '截图成功，已复制到剪贴板' : `截图成功，已下载 ${filename || '截图.png'}`, 'success')
    return copied
  } catch (e) {
    console.error('[截图]', e)
    showToast('截图失败', 'error')
    return false
  }
}
