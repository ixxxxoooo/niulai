<template>
  <div>
    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'ladder' }" @click="tab = 'ladder'">连板梯队</button>
      <button class="tab" :class="{ active: tab === 'reason' }" @click="tab = 'reason'">涨停原因</button>
    </div>

    <template v-if="tab === 'ladder'">
      <div class="error-banner" v-if="error">{{ error }}</div>
      <div class="card" ref="ladderCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>按连板数分层（上高下低 · 共 {{ filtered.length }} 家涨停）</span>
        <span style="display:flex;align-items:center;gap:8px">
          <a class="source-link" href="https://quote.eastmoney.com/ztb/detail#type=ztgc" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
          <button class="btn-screenshot" @click="doScreenshotLadder" title="截图连板梯队"><UiIcon name="screenshot" :size="14" /></button>
        </span>
      </div>
      <div class="floor-wrap">
        <div v-for="g in floors" :key="g.lbc" class="floor">
          <div class="floor-head">
            <span class="floor-title">{{ g.title }}</span>
            <span class="floor-count">{{ g.items.length }}</span>
          </div>
          <div class="floor-chips">
            <span
              v-for="p in g.items"
              :key="p.code"
              class="chip"
              :class="{ zb: p.zb_count > 0 }"
              @click="openFromLadder(p)"
            >
              <span class="chip-name">
                <MiniTrend :code="p.code" :name="p.name"><span>{{ p.name }}</span></MiniTrend>
                <BoardBadges :row="p" />
                <LeaderBadge :code="p.code" />
                <LadderYouzi :youzi="p.youzi" />
                <span v-if="p.zb_count" class="zb-tag">炸{{ p.zb_count }}</span>
              </span>
              <span class="chip-ind">{{ p.industry || '—' }}</span>
              <span class="chip-meta">
                {{ p.first_time || '-' }}
              </span>
            </span>
            <span v-if="!g.items.length" class="empty">暂无</span>
          </div>
        </div>
        <div v-if="!floors.length" class="empty" style="padding: 24px">暂无涨停数据</div>
      </div>
    </div>

    <div class="card mt16" ref="zbCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>今日炸板（{{ zbFiltered.length }} 家 · 曾封板后打开）</span>
        <span style="display:flex;align-items:center;gap:8px">
          <a class="source-link" href="https://quote.eastmoney.com/ztb/detail#type=zbgc" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
          <button class="btn-screenshot" @click="doScreenshotZb" title="截图今日炸板"><UiIcon name="screenshot" :size="14" /></button>
        </span>
      </div>
      <div class="floor-chips" style="padding: 4px 0 8px">
        <span
          v-for="p in zbFiltered"
          :key="p.code"
          class="chip zb"
          @click="openFromZb(p)"
        >
          <span class="chip-name">
            <MiniTrend :code="p.code" :name="p.name"><span>{{ p.name }}</span></MiniTrend>
            <BoardBadges :row="p" />
            <LeaderBadge :code="p.code" />
            <LadderYouzi :youzi="p.youzi" />
            <span class="zb-tag">炸{{ p.zb_count || 1 }}</span>
          </span>
          <span class="chip-ind">{{ p.industry || '—' }}</span>
          <span class="chip-meta">
            {{ fmtPct(p.change_pct) }}
          </span>
        </span>
        <span v-if="!zbFiltered.length" class="empty">暂无炸板</span>
      </div>
    </div>
    </template>

    <template v-else>
      <div class="card">
        <div class="card-title" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
          <span>涨停原因 · 题材聚合{{ kplDate ? `（${kplDate} · 共 ${kplSummary.limit_up_count ?? '-'} 家涨停）` : '' }}</span>
          <span class="kpl-sum" v-if="kplSummary.limit_up_count != null">
            <span>涨停 <b class="up">{{ kplSummary.limit_up_count }}</b></span>
            <span>跌停 <b class="down">{{ kplSummary.limit_down_count }}</b></span>
            <span>上涨 <b class="up">{{ kplSummary.up_count }}</b></span>
            <span>下跌 <b class="down">{{ kplSummary.down_count }}</b></span>
            <span>涨跌比 <b>{{ kplSummary.up_down_ratio }}</b></span>
          </span>
        </div>
        <div class="empty" v-if="kplError">{{ kplError }}</div>
        <div class="empty" v-else-if="!kplSectors.length">数据更新中，请稍后刷新</div>
        <div class="kpl-sectors" v-else>
          <div v-for="sec in kplSectors" :key="sec.code" class="kpl-sector">
            <div class="kpl-sector-head">
              <span class="kpl-sector-name">{{ sec.name }}</span>
              <span class="kpl-sector-count">{{ sec.stock_count }} 家涨停</span>
            </div>
            <table class="data-table kpl-table">
              <thead><tr><th>名称</th><th>连板</th><th>封板</th><th>封单额</th><th>主力资金</th><th>涨停原因</th></tr></thead>
              <tbody>
                <template v-for="st in sec.stocks" :key="st.code">
                  <tr
                    :class="{ 'row-expanded': expandedCode === st.code }"
                    @click="toggleExpand(st.code)"
                  >
                    <td class="stock-name up">
                      <span class="name-cell" @click.stop="openKplStock(sec, st)">{{ st.name }}</span>
                      <span class="kpl-role" :class="roleClass(st.role)" v-if="st.role && st.role !== '首板'">{{ st.role }}</span>
                      <span class="kpl-concepts" v-if="st.concepts">{{ st.concepts }}</span>
                    </td>
                    <td><span class="kpl-lb" :class="{ first: st.is_first }">{{ st.lbc || '首板' }}</span></td>
                    <td>{{ st.seal_time || '-' }}</td>
                    <td :class="pctClass(st.seal_amount)">{{ fmtAmount(st.seal_amount) }}</td>
                    <td :class="pctClass(st.main_inflow)">{{ fmtAmount(st.main_inflow) }}</td>
                    <td class="kpl-reason" :title="st.reason">{{ st.reason || '-' }}</td>
                  </tr>
                  <PoolExpandRow
                    v-if="expandedCode === st.code"
                    :code="st.code"
                    :name="st.name"
                    :colspan="6"
                  />
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// 连板梯队：楼层排列，最高连板在上
// @author ygw
import { computed, ref, watch } from 'vue'
import { api } from '../api.js'
import { fmtPct, fmtAmount, pctClass } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { usePageTab } from '../composables/usePageTab.js'
import { applyListFilter } from '../composables/useListFilter.js'
import { openStock } from '../composables/useStockMeta.js'
import MiniTrend from '../components/MiniTrend.vue'
import BoardBadges from '../components/BoardBadges.vue'
import LadderYouzi from '../components/LadderYouzi.vue'
import PoolExpandRow from '../components/PoolExpandRow.vue'
import { captureElement } from '../composables/useScreenshot.js'

const tab = usePageTab('ladder', 'ladder')
const expandedCode = ref('')

function toggleExpand(code) {
  expandedCode.value = expandedCode.value === code ? '' : code
}


// ── 涨停原因 · 题材聚合（开盘啦，容错降级） ──
const kplSectors = ref([])
const kplSummary = ref({})
const kplDate = ref('')
const kplError = ref('')

async function loadKpl() {
  try {
    const d = await api.kaipanlaLimitUpSectors()
    kplSectors.value = d.sectors || []
    kplSummary.value = d.summary || {}
    kplDate.value = d.date || ''
    kplError.value = ''
  } catch (e) {
    kplSectors.value = []
    kplSummary.value = {}
    kplDate.value = ''
    kplError.value = '涨停原因数据暂不可用（开盘啦接口未更新或已停用）'
  }
}

function openKplStock(sec, st) {
  openStock({ code: st.code, name: st.name }, {
    list: sec.stocks.map(x => ({ code: x.code, name: x.name })),
    origin: '/ladder',
    originLabel: '返回梯队',
  })
}

function roleClass(role) {
  if (role === '龙头') return 'role-leader'
  if (role === '副龙头') return 'role-sub'
  return 'role-follow'
}

/**
 * 连板梯队：在当前楼层内切换。
 * @param {object} p
 * @author ygw
 */
function openFromLadder(p) {
  const floor = floors.value.find(g => g.items.some(x => x.code === p.code))
  openStock(p, {
    list: floor?.items || filtered.value,
    origin: '/ladder',
    originLabel: '返回梯队',
  })
}

/**
 * 炸板列表内切换。
 * @param {object} p
 */
function openFromZb(p) {
  openStock(p, {
    list: zbFiltered.value,
    origin: '/ladder',
    originLabel: '返回梯队',
  })
}

const rows = ref([])
const zbRows = ref([])
const error = ref('')
const ladderCard = ref(null)
const zbCard = ref(null)
const filtered = computed(() => applyListFilter(rows.value))
const zbFiltered = computed(() => applyListFilter(zbRows.value))

const floors = computed(() => {
  const map = new Map()
  for (const p of filtered.value) {
    const n = p.lbc || 1
    if (!map.has(n)) map.set(n, [])
    map.get(n).push(p)
  }
  return [...map.keys()].sort((a, b) => b - a).map(n => ({
    lbc: n,
    title: n <= 1 ? '首板' : `${n}连板`,
    items: map.get(n) || [],
  }))
})

async function load() {
  try {
    const [zt, zb] = await Promise.all([
      api.limitUp(300),
      api.limitBreak(100).catch(() => []),
    ])
    rows.value = zt
    zbRows.value = zb
    error.value = ''
  } catch (e) {
    error.value = '连板梯队加载失败：' + e.message
  }
}

async function doScreenshotLadder() {
  await captureElement(ladderCard, '连板梯队.png')
}

async function doScreenshotZb() {
  await captureElement(zbCard, '今日炸板.png')
}

usePolling(load, 5000)

watch(tab, (t) => { if (t === 'reason') loadKpl() })
</script>

<style scoped>
.floor-wrap { display: flex; flex-direction: column; gap: 10px; }
.floor {
  background: var(--kv-bg); border: 1px solid var(--border); border-radius: 8px;
  padding: 10px 12px;
}
.floor-head {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
}
.floor-title {
  font-weight: 700; color: var(--up); font-size: 13px;
  min-width: 48px;
}
.floor-count {
  font-size: 12px; background: var(--up-bg); color: var(--up);
  padding: 1px 8px; border-radius: 10px;
}
.floor-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-flex; flex-direction: column; gap: 3px;
  padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px;
  cursor: pointer; background: var(--bg-card); min-width: 128px;
  transition: border-color .15s, background .15s;
}
.chip:hover { background: var(--bg-hover); border-color: var(--up); }
.chip.zb { border-color: rgba(227, 179, 65, 0.45); }
.chip-name { font-weight: 600; color: var(--up); font-size: 13px; display: inline-flex; align-items: center; gap: 4px; }
.chip-ind { font-size: 11px; color: var(--accent); }
.chip-meta { font-size: 11px; color: var(--text-dim); display: flex; align-items: center; gap: 4px; }
.zb-tag {
  font-size: 10px; font-weight: 700; color: var(--yellow);
  background: rgba(227, 179, 65, 0.16); border-radius: 3px; padding: 0 4px;
}
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; color: var(--text-dim);
  padding: 2px 6px; border-radius: 4px; opacity: .7;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }

/* 页签导航 */
.settings-nav {
  display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px;
}
.sn-item {
  padding: 6px 16px; border-radius: 8px; font-size: 13px;
  color: var(--text-dim); cursor: pointer; border: 1px solid var(--border);
  background: var(--bg-card); user-select: none;
}
.sn-item:hover { color: var(--text); border-color: var(--accent); }
.sn-item.active { color: var(--accent); background: var(--accent-bg); border-color: var(--accent); font-weight: 600; }

/* 涨停原因 · 题材聚合 */
.kpl-sum { display: flex; gap: 12px; font-size: 12px; color: var(--text-dim); }
.kpl-sum b { font-variant-numeric: tabular-nums; }
.kpl-sectors { display: flex; flex-direction: column; gap: 12px; }
.kpl-sector {
  border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
}
.kpl-sector-head {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; background: var(--bg-hover);
  border-bottom: 1px solid var(--border);
}
.kpl-sector-name { font-weight: 700; font-size: 14px; color: var(--accent); }
.kpl-sector-count { font-size: 12px; color: var(--text-dim); }
.kpl-table { margin: 0; }
.kpl-table th, .kpl-table td { padding: 6px 12px; }
.kpl-table tbody tr { cursor: pointer; transition: background .12s; }
.kpl-table tbody tr:hover { background: var(--bg-hover); }
.kpl-table tbody tr.row-expanded { background: var(--bg-hover); }
.kpl-table .stock-name { white-space: nowrap; }
.kpl-table .name-cell { cursor: pointer; font-weight: 600; }
.kpl-table .name-cell:hover { text-decoration: underline; color: var(--accent); }
.kpl-concepts { display: block; font-size: 11px; color: var(--text-dim); font-weight: 400; }
.kpl-lb {
  display: inline-block; font-size: 11px; font-weight: 700; white-space: nowrap;
  padding: 1px 8px; border-radius: 10px; color: var(--up);
  background: var(--up-bg); border: 1px solid var(--up);
}
.kpl-lb.first { color: var(--text-dim); background: var(--bg-hover); border-color: var(--border); }
.kpl-reason { max-width: 340px; color: var(--text-dim); font-size: 12px; }
.kpl-role {
  display: inline-block; font-size: 11px; font-weight: 700;
  border-radius: 10px; padding: 1px 8px; margin-left: 4px; white-space: nowrap;
}
.role-leader { color: var(--up); background: var(--up-bg); border: 1px solid var(--up); }
.role-sub { color: var(--yellow); background: rgba(227,179,65,.14); border: 1px solid rgba(227,179,65,.45); }
.role-follow { color: var(--text-dim); background: var(--bg-hover); border: 1px solid var(--border); }
</style>
