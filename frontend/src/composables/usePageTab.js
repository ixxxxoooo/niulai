// 页面级 Tab 状态管理：同页刷新保持，跨路由离开再返回时回到默认 Tab
// @author ygw
import { ref, watch } from 'vue'

let currentRouteName = ''

if (typeof window !== 'undefined') {
  function getRouteName() {
    const h = (window.location.hash || '').replace(/^#/, '') || '/'
    const [path] = h.split('?')
    const segs = path.split('/').filter(Boolean)
    return segs[0] || 'overview'
  }

  currentRouteName = getRouteName()

  window.addEventListener('hashchange', () => {
    const newRoute = getRouteName()
    if (newRoute !== currentRouteName) {
      // 路由离开当前页面：清理该页面的 Tab 缓存
      try {
        if (currentRouteName) {
          sessionStorage.removeItem('page_tab_' + currentRouteName)
        }
      } catch (e) { /* ignore */ }
      currentRouteName = newRoute
    }
  })
}

/**
 * 页面级 Tab 状态管理：
 * - 在当前页面刷新（F5 / Reload）时：保持当前 Tab 状态
 * - 切换走其他页面再回来时：自动恢复为 defaultTab
 *
 * @param {string} pageKey 页面标识（如 'watchlist', 'ladder', 'settings', 'sectors', 'seats'）
 * @param {string} defaultTab 默认 Tab 值
 * @returns {import('vue').Ref<string>}
 */
export function usePageTab(pageKey, defaultTab) {
  let initial = defaultTab
  const storageKey = 'page_tab_' + pageKey
  try {
    const saved = sessionStorage.getItem(storageKey)
    if (saved) initial = saved
  } catch (e) { /* ignore */ }

  const tab = ref(initial)

  watch(tab, (val) => {
    try {
      if (val && val !== defaultTab) {
        sessionStorage.setItem(storageKey, val)
      } else {
        sessionStorage.removeItem(storageKey)
      }
    } catch (e) { /* ignore */ }
  })

  return tab
}
