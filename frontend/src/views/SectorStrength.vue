<template>
  <div>
    <div class="error-banner" v-if="error">{{ error }}</div>
    <div class="card" ref="strengthCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <span>板块强度榜 · 开盘啦{{ kplDate ? `（${kplDate} · 当日涨停相关板块）` : '' }}</span>
        <span style="display:flex;align-items:center;gap:10px">
          <span style="font-weight:400;color:var(--text-dim);font-size:12px" data-tip="开盘啦板块强度指标，数值越高代表该板块资金与连板情绪越强。仅统计当日有涨停的板块。">强度说明</span>
          <button class="btn-screenshot" @click="doScreenshot" title="截图">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </span>
      </div>
      <div class="empty" v-if="!items.length">{{ error || '暂无数据' }}</div>
      <div class="table-wrap" v-else>
        <table class="data-table">
          <thead>
            <tr>
              <th>#</th><th>板块</th><th>强度</th><th>涨停</th><th>主力净额</th><th>领涨股</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(it, i) in items" :key="it.code">
              <td class="kpl-rank" :class="rankClass(i)">{{ i + 1 }}</td>
              <td class="stock-name">{{ it.name }}</td>
              <td><span class="kpl-strength" :class="strengthClass(it.strength)">{{ it.strength != null ? it.strength.toFixed(0) : '—' }}</span></td>
              <td><span class="kpl-lb">{{ it.limit_up_count }}</span></td>
              <td :class="pctClass(it.main_inflow)">{{ fmtAmount(it.main_inflow) }}</td>
              <td>
                <span
                  v-for="s in it.top_stocks"
                  :key="s.code"
                  class="kpl-leader"
                  :title="`查看 ${s.name}`"
                  @click="openFromStrength(s)"
                >{{ s.name }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
// 板块强度榜：开盘啦涨停相关板块按强度降序
// @author ygw
import { ref } from 'vue'
import { api } from '../api.js'
import { fmtAmount, pctClass } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock } from '../composables/useStockMeta.js'
import { captureElement } from '../composables/useScreenshot.js'

const items = ref([])
const kplDate = ref('')
const error = ref('')
const strengthCard = ref(null)

async function doScreenshot() {
  await captureElement(strengthCard, '板块强度榜.png')
}

async function load() {
  try {
    const d = await api.kaipanlaSectorStrengths()
    items.value = d.items || []
    kplDate.value = d.date || ''
    error.value = ''
  } catch (e) {
    items.value = []
    error.value = '板块强度数据暂不可用（开盘啦接口未更新或已停用）'
  }
}

function rankClass(i) { return i < 3 ? 'top' : '' }
function strengthClass(v) {
  if (v == null) return ''
  if (v >= 7000) return 's-hi'
  if (v >= 5000) return 's-mid'
  if (v >= 3000) return 's-low'
  return ''
}

function openFromStrength(st) {
  if (st && st.code) openStock({ code: st.code, name: st.name }, { origin: '/sectors/strength', originLabel: '返回板块强度' })
}

usePolling(load, 30000)
</script>

<style scoped>
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; color: var(--text-dim);
  padding: 2px 6px; border-radius: 4px; opacity: .7;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }
.table-wrap { overflow-x: auto; }
.kpl-rank { font-weight: 700; color: var(--text-dim); font-variant-numeric: tabular-nums; }
.kpl-rank.top { color: var(--yellow); }
.kpl-strength { font-weight: 700; font-size: 15px; font-variant-numeric: tabular-nums; }
.kpl-strength.s-hi { color: var(--up); }
.kpl-strength.s-mid { color: #e3b341; }
.kpl-strength.s-low { color: var(--text-dim); }
.kpl-lb {
  display: inline-block; font-size: 11px; font-weight: 700;
  padding: 1px 8px; border-radius: 10px; color: var(--up);
  background: var(--up-bg); border: 1px solid var(--up);
}
.kpl-leader {
  display: inline-block; font-size: 12px; padding: 1px 8px; margin: 1px 4px 1px 0;
  border-radius: 10px; background: var(--bg-hover); color: var(--accent);
  cursor: pointer; white-space: nowrap; border: 1px solid transparent;
}
.kpl-leader:hover { border-color: var(--accent); }
</style>