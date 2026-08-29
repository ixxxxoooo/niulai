<template>
  <div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th
            v-for="c in columns"
            :key="c.key"
            :class="{ sortable: c.sortable, sorted: sortKey === c.key }"
            :data-tip="c.tip || colTip(c.key)"
            @click="onHeaderClick(c)"
          >
            {{ c.label }}
            <span v-if="c.sortable" class="sort-ind">
              <svg v-if="sortKey === c.key && sortDir === 1" viewBox="0 0 8 8" width="8" height="8"><path d="M4 0 L8 6 L0 6 Z" fill="currentColor" /></svg>
              <svg v-else-if="sortKey === c.key && sortDir === -1" viewBox="0 0 8 8" width="8" height="8"><path d="M4 8 L8 2 L0 2 Z" fill="currentColor" /></svg>
              <svg v-else viewBox="0 0 8 8" width="8" height="8" opacity="0.35"><path d="M2 3 L4 6 L6 3 Z" fill="currentColor" /></svg>
            </span>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="row in sortedRows" :key="row.code || row.name">
          <tr
            :class="{ 'row-expanded': expandable && expandedCode === row.code }"
            @click="handleRowClick(row)"
            @dblclick.stop="$emit('row-click', row)"
          >
            <td>
              <MiniTrend :code="row.code" :name="row.name">
                <span class="name-cell" @click.stop="$emit('row-click', row)" title="点击查看个股详情">
                  <BoardBadges :row="row" />
                  <span class="stock-name" :class="pctClass(row.change_pct)">{{ row.name || '-' }}</span>
                  <LeaderBadge :code="row.code" />
                </span>
              </MiniTrend>
            </td>
            <td v-for="c in columns.slice(1)" :key="c.key" :class="cellClass(row, c)">
              <template v-if="c.key === 'volume_ratio'">
                {{ fmtCell(row, c) }}
                <span v-if="row.volume_ratio != null && row.volume_ratio > 1.5" class="vol-tag up">放量</span>
                <span v-else-if="row.volume_ratio != null && row.volume_ratio < 0.8" class="vol-tag down">缩量</span>
              </template>
              <template v-else-if="c.key === 'industry'">
                <span class="industry-link" :class="pctClass(row.change_pct)" @click.stop="gotoIndustry(row)">{{ row.industry || '-' }}</span>
              </template>
              <template v-else>{{ fmtCell(row, c) }}</template>
            </td>
          </tr>
          <PoolExpandRow
            v-if="expandable && row.code && expandedCode === row.code"
            :code="row.code"
            :name="row.name"
            :colspan="columns.length"
          />
        </template>
        <tr v-if="!sortedRows.length">
          <td :colspan="columns.length" class="empty">暂无数据</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { fmtAmount, fmtPrice, fmtPct, fmtNum, pctClass } from '../utils.js'
import { tip } from '../indicatorTips.js'
import { logAction } from '../composables/useActionLog.js'
import { applyListFilter } from '../composables/useListFilter.js'
import { navigate } from '../router.js'
import { api } from '../api.js'
import MiniTrend from './MiniTrend.vue'
import BoardBadges from './BoardBadges.vue'
import PoolExpandRow from './PoolExpandRow.vue'

async function gotoIndustry(row) {
  const name = row.industry
  if (!name) return
  try {
    const res = await api.sectorConceptCode(name, 'industry')
    if (res && res.code) navigate(`/sector/${res.code}`)
  } catch (e) { /* 无映射时忽略 */ }
}

function colTip(key) { return tip(key) }

const props = defineProps({
  rows: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  noFilter: { type: Boolean, default: false },
  storageKey: { type: String, default: '' },
  expandable: { type: Boolean, default: true },
})
const emit = defineEmits(['row-click'])

const expandedCode = ref('')

function handleRowClick(row) {
  if (props.expandable && row && row.code) {
    expandedCode.value = expandedCode.value === row.code ? '' : row.code
  } else {
    emit('row-click', row)
  }
}

function getAutoStorageKey() {
  if (props.storageKey) return props.storageKey
  const hash = (window.location.hash || '').split('?')[0].replace('#/', '').replace(/\//g, '_')
  return hash ? `stock_table_${hash}` : ''
}

// ---------- 列头排序（支持持久化） ----------
let initialKey = null
let initialDir = -1
try {
  const sk = getAutoStorageKey()
  if (sk) {
    const saved = localStorage.getItem('table_sort_' + sk)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (parsed && parsed.key) {
        initialKey = parsed.key
        initialDir = parsed.dir === 1 ? 1 : -1
      }
    }
  }
} catch (e) { /* ignore */ }

const sortKey = ref(initialKey)
const sortDir = ref(initialDir)

function saveSort() {
  const sk = getAutoStorageKey()
  if (!sk) return
  try {
    if (sortKey.value) {
      localStorage.setItem('table_sort_' + sk, JSON.stringify({ key: sortKey.value, dir: sortDir.value }))
    } else {
      localStorage.removeItem('table_sort_' + sk)
    }
  } catch (e) { /* ignore */ }
}

function onHeaderClick(c) {
  if (!c.sortable) return
  if (sortKey.value === c.key) {
    if (sortDir.value === -1) sortDir.value = 1
    else { sortKey.value = null; sortDir.value = -1 }
  } else {
    sortKey.value = c.key
    sortDir.value = -1
  }
  saveSort()
  logAction('table_sort', c.key, sortKey.value ? (sortDir.value === -1 ? 'desc' : 'asc') : 'none')
}


const sortedRows = computed(() => {
  const src = props.noFilter ? props.rows : applyListFilter(props.rows)
  if (!sortKey.value) return src
  const k = sortKey.value
  return [...src].sort((a, b) => {
    const va = a[k]
    const vb = b[k]
    if (va == null && vb == null) return 0
    if (va == null) return 1
    if (vb == null) return -1
    const cmp = typeof va === 'string' ? String(va).localeCompare(String(vb), 'zh') : Number(va) - Number(vb)
    return cmp * sortDir.value
  })
})

// ---------- 格式化 ----------
function fmtCell(row, c) {
  const v = row[c.key]
  switch (c.fmt) {
    case 'price': return fmtPrice(v)
    case 'pct': return fmtPct(v)
    case 'amount': return fmtAmount(v)
    case 'num': return fmtNum(v)
    default: return v == null || v === '' ? '-' : v
  }
}
function cellClass(row, c) {
  if (c.key === 'change_pct' || c.key === 'zhangsu' || c.key === 'main_inflow') {
    return pctClass(row[c.key])
  }
  if (c.key === 'main_inflow_pct') return pctClass(row[c.key])
  return ''
}
</script>

<style scoped>
th.sortable { cursor: pointer; user-select: none; }
th.sortable:hover { color: var(--accent); }
th.sorted { color: var(--accent); }
.sort-ind { display: inline-block; margin-left: 3px; vertical-align: middle; }
.name-cell {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  cursor: pointer;
}
.name-cell:hover .stock-name {
  text-decoration: underline;
  text-underline-offset: 3px;
}
.vol-tag {
  display: inline-block; font-size: 10px; font-weight: 700;
  border-radius: 3px; padding: 0 4px; margin-left: 4px; vertical-align: 1px;
}
.vol-tag.up { background: var(--up-bg); color: var(--up); }
.vol-tag.down { background: var(--down-bg); color: var(--down); }
.industry-link {
  font-weight: 700; cursor: pointer; white-space: nowrap;
  color: var(--accent);
}
.industry-link:hover { filter: brightness(1.15); }
.data-table tbody tr { cursor: pointer; }
.row-expanded {
  background: var(--bg-hover) !important;
  border-bottom-color: transparent;
}
</style>
