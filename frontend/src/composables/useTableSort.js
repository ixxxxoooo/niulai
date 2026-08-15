// 通用表格列头排序组合式函数
// @author ygw
import { ref, computed, reactive } from 'vue'
import { logAction } from './useActionLog.js'

export function useTableSort(rowsRef) {
  const sortKey = ref(null)
  const sortDir = ref(-1)

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
  }

  const sorted = computed(() => {
    if (!sortKey.value) return rowsRef.value
    const k = sortKey.value
    return [...rowsRef.value].sort((a, b) => {
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
