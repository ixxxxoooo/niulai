<template>
  <div>
    <MarketNavTabs current-tab="global" />
    <div class="error-banner" v-if="error">{{ error }}</div>

    <!-- 全球指数（卡片块） -->
    <div class="card" ref="idxCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>全球指数</span>
        <button class="btn-screenshot" @click="captureElement(idxCard, '全球指数.png')" title="截图"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div class="index-grid us-grid">
        <div v-for="q in usIndices" :key="q.secid || q.code" class="card index-card" @click="goIndex(q)">
          <div class="index-name">{{ q.name }}</div>
          <div class="index-price" :class="pctClass(q.change_pct)">{{ fmtPrice(q.price) }}</div>
          <div class="index-pct" :class="pctClass(q.change_pct)">
            {{ fmtPct(q.change_pct) }}
            <span style="font-size:12px;font-weight:400">{{ fmtNum(q.change) }}</span>
          </div>
          <IndexSpark :trend="trendOf(q)" />
        </div>
      </div>
      <div class="index-grid ap-grid mt12">
        <div v-for="q in apIndices" :key="q.secid || q.code" class="card index-card" @click="goIndex(q)">
          <div class="index-name">{{ q.name }}</div>
          <div class="index-price" :class="pctClass(q.change_pct)">{{ fmtPrice(q.price) }}</div>
          <div class="index-pct" :class="pctClass(q.change_pct)">
            {{ fmtPct(q.change_pct) }}
            <span style="font-size:12px;font-weight:400">{{ fmtNum(q.change) }}</span>
          </div>
          <IndexSpark :trend="trendOf(q)" />
        </div>
      </div>
    </div>

    <!-- 美股题材 -->
    <div class="card mt16" ref="usCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>美股题材</span>
        <button class="btn-screenshot" @click="captureElement(usCard, '美股题材.png')" title="截图"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div class="theme-grid">
        <div v-for="b in usBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-pop">
            <div v-for="s in b.stocks" :key="s.secid" class="pop-row">
              <span class="pop-name">{{ s.name }}</span>
              <span class="pop-pct" :class="pctClass(s.change_pct)">{{ s.change_pct != null ? fmtPct(s.change_pct) : '—' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日股题材 -->
    <div class="card mt16" ref="jpCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>日股题材</span>
        <button class="btn-screenshot" @click="captureElement(jpCard, '日股题材.png')" title="截图"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div class="theme-grid">
        <div v-for="b in jpBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-pop">
            <div v-for="s in b.stocks" :key="s.secid" class="pop-row">
              <span class="pop-name">{{ s.name }}</span>
              <span class="pop-pct" :class="pctClass(s.change_pct)">{{ s.change_pct != null ? fmtPct(s.change_pct) : '—' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 韩股题材 -->
    <div class="card mt16" ref="krCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>韩股题材</span>
        <button class="btn-screenshot" @click="captureElement(krCard, '韩股题材.png')" title="截图"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div class="theme-grid">
        <div v-for="b in krBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-pop">
            <div v-for="s in b.stocks" :key="s.secid" class="pop-row">
              <span class="pop-name">{{ s.name }}</span>
              <span class="pop-pct" :class="pctClass(s.change_pct)">{{ s.change_pct != null ? fmtPct(s.change_pct) : '—' }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 贵金属 / 工业金属 -->
    <div class="card mt16" ref="metalCard">
      <div class="card-title" style="display:flex;align-items:center;justify-content:space-between">
        <span>贵金属 / 工业金属</span>
        <button class="btn-screenshot" @click="captureElement(metalCard, '贵金属工业金属.png')" title="截图"><UiIcon name="screenshot" :size="14" /></button>
      </div>
      <div class="theme-grid">
        <div v-for="b in metalBoards" :key="b.key" class="theme-item">
          <div class="theme-name">{{ b.name }}</div>
          <div class="theme-pct" :class="pctClass(b.change_pct)">{{ fmtPct(b.change_pct) }}</div>
          <div class="theme-pop">
            <div v-for="s in b.stocks" :key="s.secid" class="pop-row">
              <span class="pop-name">{{ s.name }}</span>
              <span class="pop-pct" :class="pctClass(s.change_pct)">{{ s.change_pct != null ? fmtPct(s.change_pct) : '—' }}</span>
            </div>
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
import MarketNavTabs from '../components/MarketNavTabs.vue'
import IndexSpark from '../components/IndexSpark.vue'

const idxCard = ref(null)
const usCard = ref(null)
const jpCard = ref(null)
const krCard = ref(null)
const metalCard = ref(null)

const indices = ref([])
const allBoards = ref([])
const error = ref('')

let _cachedGlobalTrends = null
const globalTrends = ref({ ...(_cachedGlobalTrends || {}) })

function trendOf(q) {
  const items = globalTrends.value?.items || []
  return items.find(t => t.secid === q.secid || t.code === q.code) || null
}

async function loadTrends() {
  try {
    const res = await api.globalIndicesTrends()
    if (res && res.items) {
      globalTrends.value = res
      _cachedGlobalTrends = res
    }
  } catch (e) { /* ignore */ }
}

// 全球指数分组：美股一排，日韩/港股一排
const usIndices = computed(() => indices.value.filter(q => q.region === '美股'))
const apIndices = computed(() => indices.value.filter(q => q.region !== '美股'))

const usBoards = computed(() => allBoards.value.filter(b => b.region === 'us'))
const jpBoards = computed(() => allBoards.value.filter(b => b.region === 'jp'))
const krBoards = computed(() => allBoards.value.filter(b => b.region === 'kr'))
const metalBoards = computed(() => allBoards.value.filter(b => b.region === 'metal'))

function goIndex(q) {
  const secid = q.secid
  if (secid) navigate('/index/' + secid)
}

async function load() {
  try {
    const [gi, gs] = await Promise.all([api.globalIndices(), api.globalSectors(), loadTrends()])
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
/* 全球指数：每排固定 4 个 */
.us-grid, .ap-grid {
  grid-template-columns: repeat(4, 1fr);
}
@media (max-width: 900px) {
  .us-grid, .ap-grid { grid-template-columns: repeat(2, 1fr); }
}
.theme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}
.theme-item {
  position: relative;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  background: var(--bg);
  cursor: default;
  transition: border-color 0.12s;
}
.theme-item:hover { border-color: var(--accent); }
.theme-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.theme-pct {
  font-size: 20px;
  font-weight: 700;
  margin-top: 2px;
}
/* 悬浮弹层：显示成分股涨跌 */
.theme-pop {
  display: none;
  position: absolute;
  left: 0;
  top: calc(100% + 6px);
  z-index: 50;
  min-width: 175px;
  max-height: 280px;
  overflow-y: auto;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
body.light .theme-pop { box-shadow: 0 8px 24px rgba(27, 31, 35, 0.12); }
.theme-item:hover .theme-pop { display: block; }
.pop-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  line-height: 1.9;
  white-space: nowrap;
}
.pop-name { color: var(--text); }
.pop-pct { font-weight: 600; }
</style>
