<template>
  <div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <!-- A股指数 -->
    <div class="index-grid">
      <div v-for="q in overview.indices" :key="q.code" class="card index-card" @click="goIndex(q)">
        <div class="index-name">{{ q.name }}</div>
        <div class="index-price" :class="pctClass(q.change_pct)">{{ fmtPrice(q.price) }}</div>
        <div class="index-pct" :class="pctClass(q.change_pct)">
          {{ fmtPct(q.change_pct) }}
          <span style="font-size: 12px; font-weight: 400">{{ fmtNum(q.change) }}</span>
        </div>
        <IndexSpark :trend="trendOf(q)" />
      </div>
    </div>

    <!-- 市场情绪 -->
    <div class="sentiment">
      <div class="item">
        <div class="label">两市成交额</div>
        <div class="value">{{ fmtAmount(overview.total_amount) }}</div>
      </div>
      <div class="item">
        <div class="label">上涨 / 下跌</div>
        <div class="value"><span class="up">{{ overview.up_count ?? '-' }}</span> / <span class="down">{{ overview.down_count ?? '-' }}</span></div>
      </div>
      <div class="item">
        <div class="label">平盘 / 涨停</div>
        <div class="value"><span class="flat">{{ overview.flat_count ?? '-' }}</span> / <a class="up" @click="go('/rank/zt')">{{ overview.limit_up_count ?? '-' }}</a></div>
      </div>
      <div class="item">
        <div class="label" data-tip="两市今日总成交额比上一交易日多/少的金额。放量=资金大幅进场，缩量=观望为主。上涨放量健康，下跌放量要警惕。">两市量能</div>
        <div class="value" v-if="volume" :class="volume.ratio > 1.05 ? 'up' : volume.ratio < 0.95 ? 'down' : 'flat'">
          {{ volume.label }} {{ fmtAmount(volume.diff_amount) }}
        </div>
        <div class="value flat" v-else>—</div>
      </div>
    </div>

    <!-- 板块预览 -->
    <div class="grid-2 mt16">
      <div class="card">
        <div class="card-title">
          <span>行业板块 · 涨幅榜</span>
          <a @click="go('/sectors')">全部板块 <UiIcon name="arrowRight" :size="11" /></a>
        </div>
        <div class="scroll-list">
          <table class="data-table">
            <thead><tr><th>板块</th><th>涨跌幅</th><th>主力净流入</th><th>领涨股</th></tr></thead>
            <tbody>
              <tr v-for="s in industryTop" :key="s.code" @click="go('/sector/' + s.code)">
                <td class="stock-name">{{ s.name }}</td>
                <td :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</td>
                <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
                <td><a v-if="s.leader_code" class="leader-chip" @click.stop="openStock({ code: s.leader_code, name: s.leader_name }, { origin: '/', originLabel: '返回盘面' })"><span v-for="b in boardBadges({code:s.leader_code,name:s.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span>{{ s.leader_name || '-' }} <span class="up">{{ s.leader_pct != null ? fmtPct(s.leader_pct) : '' }}</span></a></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="card">
        <div class="card-title">
          <span>概念板块 · 涨幅榜</span>
          <a @click="go('/sectors')">全部板块 <UiIcon name="arrowRight" :size="11" /></a>
        </div>
        <div class="scroll-list">
          <table class="data-table">
            <thead><tr><th>板块</th><th>涨跌幅</th><th>主力净流入</th><th>领涨股</th></tr></thead>
            <tbody>
              <tr v-for="s in conceptTop" :key="s.code" @click="go('/sector/' + s.code)">
                <td class="stock-name">{{ s.name }}</td>
                <td :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</td>
                <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
                <td><a v-if="s.leader_code" class="leader-chip" @click.stop="openStock({ code: s.leader_code, name: s.leader_name }, { origin: '/', originLabel: '返回盘面' })"><span v-for="b in boardBadges({code:s.leader_code,name:s.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span>{{ s.leader_name || '-' }} <span class="up">{{ s.leader_pct != null ? fmtPct(s.leader_pct) : '' }}</span></a></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 盘中异动 · 涨速榜 -->
    <div class="card mt16">
      <div class="card-title">
        <span>盘中异动 · 涨速榜</span>
        <a @click="go('/rank')">完整榜单 <UiIcon name="arrowRight" :size="11" /></a>
      </div>
      <div class="scroll-list">
        <StockTable :rows="zhangsuTop" :columns="zhangsuColumns" @row-click="(r) => openFromOverview(r, zhangsuTop)" />
      </div>
    </div>

    <!-- ETF 涨幅榜 -->
    <div class="card mt16">
      <div class="card-title">
        <span>ETF 涨幅榜</span>
        <a @click="go('/rank/etf')">完整榜单 <UiIcon name="arrowRight" :size="11" /></a>
      </div>
      <div class="scroll-list">
        <StockTable :rows="etfTop" :columns="etfColumns" @row-click="(r) => openFromOverview(r, etfTop)" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPrice, fmtPct, fmtNum, pctClass, boardBadges } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock } from '../composables/useStockMeta.js'
import StockTable from '../components/StockTable.vue'
import IndexSpark from '../components/IndexSpark.vue'

/**
 * 盘面榜单进入详情：在当前榜内切换，返回盘面。
 * @param {object} row
 * @param {Array} list
 * @author ygw
 */
function openFromOverview(row, list) {
  openStock(row, { list, origin: '/', originLabel: '返回盘面' })
}

const overview = reactive({ indices: [], total_amount: null, up_count: null, down_count: null, flat_count: null, limit_up_count: null, is_trading_time: false, quote_time: '' })
const volume = ref(null) // 两市量能（独立 30s 慢轮询，避免每次刷新查指数K线）
const industryTop = ref([])
const conceptTop = ref([])
const zhangsuTop = ref([])
const etfTop = ref([])
const error = ref('')

const etfColumns = [
  { key: 'name', label: '名称' },
  { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
]

const zhangsuColumns = [
  { key: 'name', label: '名称' },
  { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'zhangsu', label: '涨速', fmt: 'pct', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
  { key: 'main_inflow', label: '主力净流入', fmt: 'amount', sortable: true },
]

function go(p) { navigate(p) }
function goIndex(q) {
  const map = { '000001': '1.000001', '399001': '0.399001', '399006': '0.399006', '000688': '1.000688', '000300': '1.000300' }
  const secid = q.secid || map[q.code]
  if (secid) go('/index/' + secid)
}

async function load() {
  try {
    const [ov, ind, con, zs, etf] = await Promise.all([
      api.overview(), api.sectors('industry', 'change_pct', 50),
      api.sectors('concept', 'change_pct', 50), api.zhangsu(30),
      api.etfRank('change_pct', 30),
    ])
    Object.assign(overview, ov)
    industryTop.value = ind
    conceptTop.value = con
    zhangsuTop.value = zs
    etfTop.value = etf
    error.value = ''
  } catch (e) {
    error.value = '数据加载失败：' + e.message
  }
}

const poll = usePolling(load, 5000)

// 指数分时缩略图：独立 30s 慢轮询（不随 5s load 高频拉取，后端 30s 缓存兜底）
const indexTrends = ref({ items: [] })
function trendOf(q) {
  const secid = q.secid
  const items = indexTrends.value?.items || []
  return items.find(t => t.secid === secid || t.code === q.code) || null
}
async function loadIndexTrends() {
  try {
    indexTrends.value = await api.indicesTrends()
  } catch (e) { /* 分时缩略图失败不影响总览 */ }
}

// 两市量能：30 秒慢轮询（后端 30s 缓存，变化慢无需高频）
async function loadVolume() {
  try {
    volume.value = await api.marketVolume()
  } catch (e) { /* 量能失败不阻塞总览 */ }
}
let volTimer = null
let trendTimer = null

onMounted(() => {
  loadVolume()
  volTimer = setInterval(loadVolume, 30000)
  loadIndexTrends()
  trendTimer = setInterval(loadIndexTrends, 30000)
})
onUnmounted(() => {
  clearInterval(volTimer)
  clearInterval(trendTimer)
})
</script>
