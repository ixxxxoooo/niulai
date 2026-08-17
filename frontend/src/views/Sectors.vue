<template>
  <div>
    <div class="page-title">板块分析</div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <div class="tabs">
      <div class="tab" :class="{ active: stype === 'industry' }" @click="switchType('industry')">行业板块</div>
      <div class="tab" :class="{ active: stype === 'concept' }" @click="switchType('concept')">概念板块</div>
      <div class="tab" :class="{ active: stype === 'range' }" @click="switchType('range')">区间统计</div>
      <span style="color: var(--text-dim); font-size: 12px; margin-left: auto">
        <template v-if="stype === 'range'">
          <label class="range-days">
            最近
            <select v-model="rangeDays" @change="load()">
              <option :value="5">5</option>
              <option :value="10">10</option>
              <option :value="20">20</option>
            </select>
            个交易日 · 共 {{ rangeSummary }}
          </label>
        </template>
        <template v-else>点击列名排序 · 点击板块进入成分股</template>
      </span>
      <a class="source-link" href="https://data.eastmoney.com/bkzj/hy.html" target="_blank" rel="noopener">数据来源 <UiIcon name="external" :size="11" /></a>
    </div>

    <div class="card">
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr v-if="stype !== 'range'">
              <th>板块</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'change_pct' }" @click="ts.toggleSort('change_pct')">涨跌幅</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'amount' }" @click="ts.toggleSort('amount')">成交额</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'main_inflow' }" @click="ts.toggleSort('main_inflow')">主力净流入</th>
              <th>涨/跌家数</th><th>领涨股</th>
            </tr>
            <tr v-else>
              <th>板块</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'avg_strength' }" @click="ts.toggleSort('avg_strength')">日均强度</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'limit_up_count' }" @click="ts.toggleSort('limit_up_count')">涨停家数</th>
              <th class="sortable" :class="{ sorted: ts.sortKey === 'main_inflow' }" @click="ts.toggleSort('main_inflow')">主力净流入</th>
              <th>天数</th><th></th>
            </tr>
          </thead>
          <tbody>
            <template v-if="stype !== 'range'">
              <tr v-for="s in ts.sorted" :key="s.code" @click="openSector(s.code)">
                <td class="stock-name">{{ s.name }} <span style="color: var(--text-dim); font-weight: 400; font-size: 12px">{{ s.code }}</span></td>
                <td><span class="pct-badge" :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</span></td>
                <td>{{ fmtAmount(s.amount) }}</td>
                <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
                <td><span class="up">{{ s.up_count ?? '-' }}</span> / <span class="down">{{ s.down_count ?? '-' }}</span></td>
                <td>
                  <a v-if="s.leader_code" class="leader-chip" @click.stop="openStock(s.leader_code)">
                    <span v-for="b in boardBadges({code:s.leader_code,name:s.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span>{{ s.leader_name || '-' }} <span class="up">{{ s.leader_pct != null ? fmtPct(s.leader_pct) : '' }}</span>
                  </a>
                </td>
              </tr>
              <tr v-if="!ts.sorted.length"><td colspan="6" class="empty">暂无数据</td></tr>
            </template>
            <template v-else>
              <tr v-for="s in ts.sorted" :key="s.code" @click="openSector(s.code)">
                <td class="stock-name">{{ s.name }} <span style="color: var(--text-dim); font-weight: 400; font-size: 12px">{{ s.code }}</span></td>
                <td class="up">{{ s.avg_strength }}</td>
                <td><span class="up">{{ s.limit_up_count }}</span></td>
                <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
                <td><span style="color: var(--text-dim)">{{ s.days }} 天</span></td>
                <td></td>
              </tr>
              <tr v-if="!ts.sorted.length"><td colspan="6" class="empty">暂无数据</td></tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPct, pctClass, boardBadges } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { useTableSort } from '../composables/useTableSort.js'
import { openStock as goStock } from '../composables/useStockMeta.js'

const stype = ref('industry')
const sort = ref('change_pct')
const sectors = ref([])
const rangeDays = ref(5)
const rangeSummary = ref('')
const error = ref('')
const ts = useTableSort(sectors)

function switchType(t) { stype.value = t; load() }
function switchSort(s) { sort.value = s; load() }
function openSector(code) { navigate('/sector/' + code) }
function openStock(code) {
  if (!code) return
  goStock({ code }, { origin: '/sectors', originLabel: '返回板块' })
}

async function load() {
  try {
    if (stype.value === 'range') {
      const r = await api.sectorsRangeStats(rangeDays.value)
      sectors.value = (r && r.items) || []
      rangeSummary.value = r && r.days ? `${r.days} 天` : ''
    } else {
      sectors.value = await api.sectors(stype.value, sort.value, 100)
    }
    error.value = ''
  } catch (e) {
    error.value = '板块数据加载失败：' + e.message
  }
}

const poll = usePolling(load, 5000)
</script>

<style scoped>
.range-days select {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 6px;
  color: var(--text); font-size: 12px; padding: 2px 4px; margin: 0 4px;
}
</style>
