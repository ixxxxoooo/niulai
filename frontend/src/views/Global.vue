<template>
  <div>
    <div class="page-title">全球市场</div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <!-- 全球指数 -->
    <div class="card" ref="idxCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>全球指数</span>
        <button class="btn-screenshot" @click="captureElement(idxCard, '全球指数.png')" title="截图">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
      <div class="scroll-list">
        <table class="data-table">
          <thead><tr><th>指数</th><th>最新</th><th>涨跌幅</th><th>涨跌</th></tr></thead>
          <tbody>
            <tr v-for="q in indices" :key="q.secid || q.code" @click="goIndex(q)">
              <td class="stock-name">{{ q.name }}</td>
              <td :class="pctClass(q.change_pct)">{{ fmtPrice(q.price) }}</td>
              <td :class="pctClass(q.change_pct)">{{ fmtPct(q.change_pct) }}</td>
              <td :class="pctClass(q.change_pct)">{{ fmtNum(q.change) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 美股题材 -->
    <div class="card mt16" ref="usCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>美股题材</span>
        <button class="btn-screenshot" @click="captureElement(usCard, '美股题材.png')" title="截图">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
      <div class="theme-grid">
        <div v-for="b in usBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-stocks">
            <span v-for="s in b.stocks" :key="s.secid" class="theme-stock" :class="pctClass(s.change_pct)">
              {{ s.name }}
              <span class="theme-stock-pct">{{ s.change_pct != null ? fmtPct(s.change_pct) : '' }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 日股题材 -->
    <div class="card mt16" ref="jpCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>日股题材</span>
        <button class="btn-screenshot" @click="captureElement(jpCard, '日股题材.png')" title="截图">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
      <div class="theme-grid">
        <div v-for="b in jpBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-stocks">
            <span v-for="s in b.stocks" :key="s.secid" class="theme-stock" :class="pctClass(s.change_pct)">
              {{ s.name }}
              <span class="theme-stock-pct">{{ s.change_pct != null ? fmtPct(s.change_pct) : '' }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 韩股题材 -->
    <div class="card mt16" ref="krCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>韩股题材</span>
        <button class="btn-screenshot" @click="captureElement(krCard, '韩股题材.png')" title="截图">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
        </button>
      </div>
      <div class="theme-grid">
        <div v-for="b in krBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-stocks">
            <span v-for="s in b.stocks" :key="s.secid" class="theme-stock" :class="pctClass(s.change_pct)">
              {{ s.name }}
              <span class="theme-stock-pct">{{ s.change_pct != null ? fmtPct(s.change_pct) : '' }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { api } from '../api.js'
import { fmtPrice, fmtPct, fmtNum, pctClass } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { captureElement } from '../composables/useScreenshot.js'

const idxCard = ref(null)
const usCard = ref(null)
const jpCard = ref(null)
const krCard = ref(null)

const indices = ref([])
const allBoards = ref([])
const error = ref('')

const usBoards = computed(() => allBoards.value.filter(b => b.region === 'us'))
const jpBoards = computed(() => allBoards.value.filter(b => b.region === 'jp'))
const krBoards = computed(() => allBoards.value.filter(b => b.region === 'kr'))

function goIndex(q) {
  const secid = q.secid
  if (secid) navigate('/index/' + secid)
}

async function load() {
  try {
    const [gi, gs] = await Promise.all([api.globalIndices(), api.globalSectors()])
    indices.value = gi
    allBoards.value = gs
    error.value = ''
  } catch (e) {
    error.value = '数据加载失败：' + e.message
  }
}

const poll = usePolling(load, 10000)
</script>

<style scoped>
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}
.theme-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--bg);
}
.theme-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.theme-pct {
  font-size: 18px;
  font-weight: 700;
  margin: 2px 0 8px;
}
.theme-stocks {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
}
.theme-stock {
  font-size: 12px;
  color: var(--text);
}
.theme-stock-pct {
  margin-left: 2px;
  font-weight: 600;
}
</style>
