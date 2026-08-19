// 通用表格列头排序组合式函数
// @author ygw
import { ref, computed, reactive } from 'vue'
import { logAction } from './useActionLog.js'

export function useTableSort(rowsRef, storageKey = '') {
  let initialKey = null
  let initialDir = -1

  if (storageKey) {
    try {
      const saved = localStorage.getItem('table_sort_' + storageKey)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed && parsed.key) {
          initialKey = parsed.key
          initialDir = parsed.dir === 1 ? 1 : -1
        }
      }
    } catch (e) { /* ignore */ }
  }

  const sortKey = ref(initialKey)
  const sortDir = ref(initialDir)

  function save() {
    if (!storageKey) return
    try {
      if (sortKey.value) {
        localStorage.setItem('table_sort_' + storageKey, JSON.stringify({ key: sortKey.value, dir: sortDir.value }))
      } else {
        localStorage.removeItem('table_sort_' + storageKey)
      }
    } catch (e) { /* ignore */ }
  }

  function toggleSort(key) {
    if (sortKey.value === key) {
      if (sortDir.value === -1) {
        sortDir.value = 1
        logAction('table_sort', key, 'asc')
      } else {
        sortKey.value = null
        sortDir.value = -1
        logAction('table_sort', key, 'none')
      }
    } else {
      sortKey.value = key
      sortDir.value = -1
      logAction('table_sort', key, 'desc')
    }
    save()
  }

  const sorted = computed(() => {
    const list = rowsRef?.value || []
    if (!sortKey.value) return list
    const k = sortKey.value
    return [...list].sort((a, b) => {
      const va = a[k]
      const vb = b[k]
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      const cmp = typeof va === 'string' ? String(va).localeCompare(String(vb), 'zh') : Number(va) - Number(vb)
      return cmp * sortDir.value
    })
  })

  return reactive({ sortKey, sortDir, toggleSort, sorted })
}

