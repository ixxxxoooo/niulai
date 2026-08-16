<template>
  <div>
    <div class="page-title">连板梯队</div>
    <div class="error-banner" v-if="error">{{ error }}</div>
    <div class="card" ref="ladderCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>按连板数分层（上高下低 · 共 {{ filtered.length }} 家涨停）</span>
        <button class="btn-screenshot" @click="doScreenshotLadder" title="截图连板梯队">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
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
                <BoardBadges :row="p" />
                <MiniTrend :code="p.code" :name="p.name"><span>{{ p.name }}</span></MiniTrend>
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
        <button class="btn-screenshot" @click="doScreenshotZb" title="截图今日炸板">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
      <div class="floor-chips" style="padding: 4px 0 8px">
        <span
          v-for="p in zbFiltered"
          :key="p.code"
          class="chip zb"
          @click="openFromZb(p)"
        >
          <span class="chip-name">
            <BoardBadges :row="p" />
            <MiniTrend :code="p.code" :name="p.name"><span>{{ p.name }}</span></MiniTrend>
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
  </div>
</template>

<script setup>
// 连板梯队：楼层排列，最高连板在上
// @author ygw
import { computed, ref } from 'vue'
import { api } from '../api.js'
import { fmtPct } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { applyListFilter } from '../composables/useListFilter.js'
import { openStock } from '../composables/useStockMeta.js'
import MiniTrend from '../components/MiniTrend.vue'
import BoardBadges from '../components/BoardBadges.vue'
import LadderYouzi from '../components/LadderYouzi.vue'
import { captureElement } from '../composables/useScreenshot.js'

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
</style>
