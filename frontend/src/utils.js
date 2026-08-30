// 格式化与颜色工具

export function fmtAmount(v, digits = 0) {
  if (v == null || isNaN(v)) return '-'
  const abs = Math.abs(v)
  if (abs >= 1e12) return (v / 1e12).toFixed(2) + '万亿'
  if (abs >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (abs >= 1e4) return (v / 1e4).toFixed(digits) + '万'
  return Number(v).toFixed(digits)
}

export function fmtPrice(v) {
  return v == null || isNaN(v) ? '-' : Number(v).toFixed(2)
}

export function fmtPct(v, digits = 2) {
  if (v == null || isNaN(v)) return '-'
  const n = Number(v)
  return (n > 0 ? '+' : '') + n.toFixed(digits) + '%'
}

export function fmtNum(v, digits = 2) {
  if (v == null || isNaN(v)) return '-'
  return Number(v).toFixed(digits)
}

export function pctClass(v) {
  if (v == null || isNaN(v) || v === 0) return 'flat'
  return v > 0 ? 'up' : 'down'
}

export function fmtTime(t) {
  if (!t) return '-'
  return String(t)
}

/** 科创 / 创业 / ST / 北交 徽标（单字） */
export function boardBadges(row = {}) {
  const code = String(row.code || '')
  const name = String(row.name || '')
  const board = row.board || ''
  const out = []
  if (row.is_st === 1 || row.is_st === true || /ST/i.test(name)) {
    out.push({ t: 'ST', cls: 'st' })
  }
  if (board === 'KCB' || /^(688|689)/.test(code)) out.push({ t: '科', cls: 'kcb' })
  else if (board === 'CYB' || /^(300|301)/.test(code)) out.push({ t: '创', cls: 'cyb' })
  else if (board === 'BSE' || /^(43|83|87|88|92)/.test(code)) out.push({ t: '北', cls: 'bse' })
  return out
}

export const INDEX_NAMES = {
  // A 股核心指数
  '1.000001': '上证指数',
  '0.399001': '深证成指',
  '0.399006': '创业板指',
  '1.000688': '科创50',
  '1.000300': '沪深300',
  // 美股核心指数
  '100.NDX': '纳斯达克',
  '100.SPX': '标普500',
  '100.DJIA': '道琼斯',
  // 亚太与日韩指数
  '100.HSI': '恒生指数',
  '100.N225': '日经225',
  '100.KS11': '韩国KOSPI',
}

// ---------------- 主题 ----------------

export function isLightTheme() {
  return typeof document !== 'undefined' && document.body.classList.contains('light')
}

/** 图表主题色（随 body.light 切换） */
export function themeColors() {
  if (isLightTheme()) {
    return {
      axis: '#6b7480',
      split: 'rgba(0, 0, 0, 0.08)',
      up: '#d92d20',
      down: '#0b8f63',
      avg: '#a9741a',
      accent: '#2563eb',
    }
  }
  return {
    axis: '#8b9099',
    split: 'rgba(39, 42, 49, 0.5)',
    up: '#f04444',
    down: '#2fbf8f',
    avg: '#e3b341',
    accent: '#4c9aff',
  }
}

