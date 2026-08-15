// 极简 hash 路由
export function parseHash() {
  const h = (location.hash || '').replace(/^#/, '') || '/'
  const [path] = h.split('?')
  const segs = path.split('/').filter(Boolean)
  if (segs[0] === 'stock' && segs[1]) return { name: 'stock', code: segs[1].toUpperCase() }
  if (segs[0] === 'sector' && segs[1]) return { name: 'sector', code: segs[1].toUpperCase() }
  if (segs[0] === 'sectors') return { name: 'sectors', sector: (segs[1] || '').toUpperCase() || null }
  if (segs[0] === 'index' && segs[1]) return { name: 'index', secid: segs[1].toUpperCase() }
  if (segs[0] === 'sector-moves') return { name: 'sectorMoves' }
  if (segs[0] === 'rank') return { name: 'rank', tab: segs[1] || '' }
  if (segs[0] === 'ladder') return { name: 'ladder' }
  if (segs[0] === 'watchlist') return { name: 'watchlist' }
  if (segs[0] === 'alerts') return { name: 'alerts' }
  if (segs[0] === 'settings') return { name: 'settings' }
  return { name: 'overview' }
}

/**
 * 路由跳转。
 * @param {string} path hash 路径，如 /stock/600519
 * @param {{ replace?: boolean }} [opts] replace=true 时不新增 history，用于同列表左右切换后「返回」仍回入口页
 * @author ygw
 */
export function navigate(path, opts = {}) {
  const hash = '#' + path
  if (opts.replace) {
    const url = location.pathname + location.search + hash
    if (location.hash === hash) {
      window.dispatchEvent(new HashChangeEvent('hashchange'))
    } else {
      history.replaceState(null, '', url)
      window.dispatchEvent(new HashChangeEvent('hashchange'))
    }
    return
  }
  if (location.hash === hash) {
    window.dispatchEvent(new HashChangeEvent('hashchange'))
  } else {
    location.hash = path
  }
}
