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
              <th>#</th><th>板块</th><th>强度</th><th>涨跌幅</th><th>涨停</th><th>主力净额</th><th>领涨股</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(it, i) in items" :key="it.code">
              <tr>
                <td class="kpl-rank" :class="rankClass(i)">{{ i + 1 }}</td>
                <td class="stock-name">
                  {{ it.name }}
                  <span
                    v-if="it.sub_sectors && it.sub_sectors.length"
                    class="sub-toggle"
                    :class="{ open: it._open }"
                    :title="it._open ? '收起子板块' : '展开子板块'"
                    @click="toggleSub(it)"
                  >▾</span>
                </td>
                <td><span class="kpl-strength" :class="strengthClass(it.strength)">{{ it.strength != null ? it.strength.toFixed(0) : '—' }}</span></td>
                <td :class="pctClass(it.change_pct)">{{ it.change_pct != null ? fmtPct(it.change_pct) : '—' }}</td>
                <td><span class="kpl-lb">{{ it.limit_up_count }}</span></td>
                <td :class="pctClass(it.main_inflow)">{{ fmtAmount(it.main_inflow) }}</td>
                <td>
                  <span
                    v-for="s in it.top_stocks"
                    :key="s.code"
                    class="kpl-leader-host"
                  >
                    <MiniTrend :code="s.code" :name="s.name">
                      <span class="kpl-leader" :title="`查看 ${s.name}`" @click="openFromStrength(s)">{{ s.name }}</span>
                    </MiniTrend>
                  </span>
                </td>
              </tr>
              <tr v-if="it._open" class="kpl-sub-row">
                <td colspan="7">
                  <div class="kpl-sub-wrap">
                    <span
                      v-for="sub in (it.sub_sectors || [])"
                      :key="sub.name"
                      class="sub-chip"
                      :class="{ on: it._activeSub === sub.name }"
                      @click="toggleSubStock(it, sub)"
                    >{{ sub.name }} <b>×{{ sub.count }}</b></span>
                    <div v-if="it._activeSub" class="sub-stocks">
                      <span
                        v-for="st in subStocks(it, it._activeSub)"
                        :key="st.code"
                        class="kpl-leader-host"
                      >
                        <MiniTrend :code="st.code" :name="st.name">
                          <span class="kpl-leader" :title="`查看 ${st.name}`" @click="openFromStrength(st)">{{ st.name }}</span>
                        </MiniTrend>
                      </span>
                    </div>
                    <div v-else class="kpl-sub-tip">点击上方子板块查看对应涨停股</div>
                  </div>
                </td>
              </tr>
            </template>
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
import { fmtAmount, fmtPct, pctClass } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock } from '../composables/useStockMeta.js'
import MiniTrend from '../components/MiniTrend.vue'
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

function toggleSub(it) {
  it._open = !it._open
  if (!it._open) it._activeSub = ''
}
function toggleSubStock(it, sub) {
  it._activeSub = it._activeSub === sub.name ? '' : sub.name
}
function subStocks(it, subName) {
  return (it.stocks || []).filter(st => (st.concepts || '').includes(subName))
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
.kpl-leader-host { display: inline-block; }
.kpl-leader {
  display: inline-block; font-size: 12px; padding: 1px 8px; margin: 1px 4px 1px 0;
  border-radius: 10px; background: var(--bg-hover); color: var(--accent);
  cursor: pointer; white-space: nowrap; border: 1px solid transparent;
}
.kpl-leader:hover { border-color: var(--accent); }
.sub-toggle {
  cursor: pointer; color: var(--text-dim); margin-left: 4px;
  display: inline-block; font-size: 12px; transition: transform .15s, color .15s;
}
.sub-toggle:hover { color: var(--accent); }
.sub-toggle.open { transform: rotate(180deg); color: var(--accent); }
.kpl-sub-row td { background: var(--bg-hover); padding: 8px 12px; }
.kpl-sub-wrap { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.sub-chip {
  display: inline-block; font-size: 12px; padding: 2px 10px; margin: 2px 2px 2px 0;
  border-radius: 12px; background: var(--bg-card); border: 1px solid var(--border);
  cursor: pointer; white-space: nowrap; transition: border-color .15s, color .15s;
}
.sub-chip:hover { border-color: var(--accent); color: var(--accent); }
.sub-chip.on { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600; }
.sub-chip b { font-variant-numeric: tabular-nums; }
.sub-stocks { display: flex; flex-wrap: wrap; width: 100%; margin-top: 6px; padding-top: 6px; border-top: 1px dashed var(--border); }
.kpl-sub-tip { width: 100%; font-size: 11px; color: var(--text-dim); padding: 4px 0 0; }
</style>