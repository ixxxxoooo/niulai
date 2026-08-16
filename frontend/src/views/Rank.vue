<template>
  <div>
    <div class="page-title">热门股与资金流向</div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <div class="tabs">
      <div class="tab" :class="{ active: tab === 'zhangsu' }" @click="switchTab('zhangsu')">涨速榜</div>
      <div class="tab" :class="{ active: tab === 'moneyflow' }" @click="switchTab('moneyflow')">主力净流入</div>
      <div class="tab" :class="{ active: tab === 'hot' }" @click="switchTab('hot')">热门股</div>
      <div class="tab" :class="{ active: tab === 'zt' }" @click="switchTab('zt')">涨停池</div>
      <div class="tab" :class="{ active: tab === 'etf' }" @click="switchTab('etf')">ETF排行</div>
      <div class="tab" :class="{ active: tab === 'ths' }" @click="switchTab('ths')">同花顺热榜</div>
      <div class="tab" :class="{ active: tab === 'lhb' }" @click="switchTab('lhb')">龙虎榜</div>
      <div class="tab" :class="{ active: tab === 'changes' }" @click="switchTab('changes')">盘中异动</div>
    </div>

    <div class="tabs" v-if="tab === 'ths'">
      <div class="tab" :class="{ active: thsType === 'hour' }" @click="thsType = 'hour'; load()">小时榜</div>
      <div class="tab" :class="{ active: thsType === 'day' }" @click="thsType = 'day'; load()">日榜</div>
    </div>

    <div class="card">
      <template v-if="tab === 'zhangsu'">
        <div class="card-title">5 分钟涨速排行（捕捉盘中异动拉升）</div>
        <StockTable :rows="rows" :columns="zhangsuCols" @row-click="openFromRank" />
      </template>

      <template v-else-if="tab === 'moneyflow'">
        <div class="card-title">个股主力净流入排行（大单+超大单）</div>
        <StockTable :rows="rows" :columns="flowCols" @row-click="openFromRank" />
      </template>

      <template v-else-if="tab === 'hot'">
        <div class="card-title">热门股（点击列名排序 · 再点取消）</div>
        <StockTable :rows="rows" :columns="hotCols" @row-click="openFromRank" />
      </template>

      <template v-else-if="tab === 'zt'">
        <div class="card-title">今日涨停（{{ ztRows.length }} 家）</div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'name' }" @click="ztSort.toggleSort('name')">名称</th>
              <th>代码</th>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'price' }" @click="ztSort.toggleSort('price')">现价</th>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'change_pct' }" @click="ztSort.toggleSort('change_pct')">涨幅</th>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'lbc' }" @click="ztSort.toggleSort('lbc')">连板</th>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'zb_count' }" @click="ztSort.toggleSort('zb_count')">炸板</th>
              <th>行业</th>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'seal_amount' }" @click="ztSort.toggleSort('seal_amount')">封单额</th>
              <th class="sortable" :class="{ sorted: ztSort.sortKey === 'first_time' }" @click="ztSort.toggleSort('first_time')">首次封板</th>
            </tr></thead>
            <tbody>
              <tr v-for="p in ztSort.sorted" :key="p.code" @click="openFromRank(p)">
                <td class="stock-name up">
                  <MiniTrend :code="p.code" :name="p.name">
                    <span class="name-cell"><BoardBadges :row="p" />{{ p.name }}</span>
                  </MiniTrend>
                </td>
                <td>{{ p.code }}</td>
                <td>{{ fmtPrice(p.price) }}</td>
                <td class="up">{{ fmtPct(p.change_pct) }}</td>
                <td><span class="zt-lb-badge" :title="`连板数：${p.lbc}，点击查看连板梯队`" @click.stop="goLadder()">{{ lbcLabel(p.lbc) }}</span></td>
                <td>{{ p.zb_count ? p.zb_count + '次' : '-' }}</td>
                <td>{{ p.industry || '-' }}</td>
                <td :class="pctClass(p.seal_amount)">{{ fmtAmount(p.seal_amount) }}</td>
                <td>{{ p.first_time || '-' }}</td>
              </tr>
              <tr v-if="!ztSort.sorted.length"><td colspan="9" class="empty">暂无数据</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <template v-else-if="tab === 'etf'">
        <div class="card-title">ETF 排行（共 {{ etfTotal }} 只 · 点击列名排序）</div>
        <StockTable :rows="rows" :columns="etfCols" @row-click="openFromRank" />
      </template>

      <template v-else-if="tab === 'ths'">
        <div class="card-title">同花顺热榜 · {{ thsType === 'day' ? '日榜' : '小时榜' }}
          <span style="font-weight:400;color:var(--text-dim);font-size:12px">解读来自同花顺；无正文时显示标题或概念标签</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr><th>排名</th><th>名称</th><th>代码</th><th>涨跌幅</th><th>热度</th><th>解读</th></tr></thead>
            <tbody>
              <tr v-for="p in thsRows" :key="p.code" @click="openFromRank(p)">
                <td>{{ p.rank }}</td>
                <td class="stock-name" :class="pctClass(p.change_pct)">
                  <MiniTrend :code="p.code" :name="p.name">
                    <span class="name-cell"><BoardBadges :row="p" />{{ p.name }}</span>
                  </MiniTrend>
                </td>
                <td>{{ p.code }}</td>
                <td :class="pctClass(p.change_pct)">{{ fmtPct(p.change_pct) }}</td>
                <td>{{ p.heat != null ? Number(p.heat).toFixed(0) : '-' }}</td>
                <td class="analyse">{{ p.analyse || '-' }}</td>
              </tr>
              <tr v-if="!thsRows.length"><td colspan="6" class="empty">暂无数据</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <template v-else-if="tab === 'changes'">
        <div class="card-title">盘中个股异动（大笔买卖 / 急速拉升跳水 / 封板等）</div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr><th>时间</th><th>名称</th><th>代码</th><th>异动类型</th><th>涨跌幅</th><th>现价</th></tr></thead>
            <tbody>
              <tr v-for="(p, i) in changesRows" :key="i" @click="openFromRank(p)">
                <td>{{ p.time }}</td>
                <td class="stock-name" :class="pctClass(p.change_pct)">
                  <span class="name-cell"><BoardBadges :row="p" />{{ p.name }}</span>
                </td>
                <td>{{ p.code }}</td>
                <td><span :class="['change-tag', changeTagClass(p.type_name)]">{{ p.type_name }}</span></td>
                <td :class="pctClass(p.change_pct)">{{ p.change_pct != null ? fmtPct(p.change_pct) : '-' }}</td>
                <td>{{ p.price || '-' }}</td>
              </tr>
              <tr v-if="!changesRows.length"><td colspan="6" class="empty">暂无异动数据（非交易时段无数据）</td></tr>
            </tbody>
          </table>
        </div>
      </template>

      <template v-else-if="tab === 'lhb'">
        <div class="card-title">龙虎榜{{ lhbDate ? ' · ' + lhbDate : '' }}</div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr>
              <th>名称</th><th>代码</th><th>现价</th><th>涨跌幅</th>
              <th data-tip="净买额 = 当日上榜买入金额 − 卖出金额。为正说明当日买盘资金占优（抢筹强），为负说明以卖出为主（获利了结/减仓）。">净买额</th>
              <th data-tip="买入 = 当日龙虎榜买入席位成交总额，代表游资/机构等买盘抢筹资金。数值大说明有大资金进场。">买入</th>
              <th data-tip="卖出 = 当日龙虎榜卖出席位成交总额，代表获利了结/减仓资金。数值大说明抛压大。">卖出</th>
              <th data-tip="上榜原因：满足龙虎榜上榜条件（日涨跌幅、换手、振幅、净买入额等）的具体触发条目。">上榜原因</th>
              <th data-tip="当日该股上榜席位中命中的知名游资（如章盟主）。红色徽章=拉萨天团，属反向指标需谨慎。">游资</th>
            </tr></thead>
            <tbody>
              <tr v-for="p in lhbRows" :key="p.code" @click="openFromRank(p)">
                <td class="stock-name" :class="pctClass(p.change_pct)">
                  <MiniTrend :code="p.code" :name="p.name">
                    <span class="name-cell"><BoardBadges :row="p" />{{ p.name }}</span>
                  </MiniTrend>
                </td>
                <td>{{ p.code }}</td>
                <td>{{ fmtPrice(p.price) }}</td>
                <td :class="pctClass(p.change_pct)">{{ fmtPct(p.change_pct) }}</td>
                <td :class="pctClass(p.net)">{{ fmtAmount(p.net) }}</td>
                <td class="up">{{ fmtAmount(p.buy) }}</td>
                <td class="down">{{ fmtAmount(p.sell) }}</td>
                <td class="analyse">{{ p.reason || '-' }}</td>
                <td>
                  <span v-for="y in (p.youzi || [])" :key="y.nickname" class="youzi-badge" :class="{ lhasa: y.nickname.includes('拉萨') }" :data-tip="youziTip(y)" @click.stop="goSeat(y.nickname)">{{ y.nickname }}</span>
                  <span v-if="!(p.youzi || []).length" class="seat-no">—</span>
                </td>
              </tr>
              <tr v-if="!lhbRows.length"><td colspan="9" class="empty">暂无龙虎榜数据</td></tr>
            </tbody>
          </table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
// @author ygw
import { ref, computed, watch } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPrice, fmtPct, pctClass } from '../utils.js'
import { navigate } from '../router.js'
import { usePolling } from '../composables/usePolling.js'
import { logAction } from '../composables/useActionLog.js'
import { applyListFilter } from '../composables/useListFilter.js'
import { useTableSort } from '../composables/useTableSort.js'
import { openStock } from '../composables/useStockMeta.js'
import StockTable from '../components/StockTable.vue'
import MiniTrend from '../components/MiniTrend.vue'
import BoardBadges from '../components/BoardBadges.vue'

/**
 * 从排行榜进入详情：在当前 Tab 列表内切换，返回当前排行页。
 * @param {object} row
 * @author ygw
 */
function openFromRank(row) {
  const list = tab.value === 'zt' ? ztSort.sorted.value
    : tab.value === 'ths' ? thsRows.value
    : tab.value === 'lhb' ? lhbRows.value
    : tab.value === 'changes' ? changesRows.value
    : rows.value
  openStock(row, {
    list,
    origin: '/rank/' + tab.value,
    originLabel: '返回排行',
  })
}

const props = defineProps({ tab: { type: String, default: '' } })
const VALID = ['zhangsu', 'moneyflow', 'hot', 'zt', 'etf', 'ths', 'lhb', 'changes']
const tab = ref(VALID.includes(props.tab) ? props.tab : 'zhangsu')
const thsType = ref('hour')
const PREMIUM_TEXT = { positive: '正面', neutral_positive: '偏正面', neutral: '中性', negative: '负面' }

function youziTip(y) {
  const p = PREMIUM_TEXT[y.premium] ? `属性：${PREMIUM_TEXT[y.premium]}` : ''
  const s = y.style ? `风格：${y.style}` : '风格：待补充'
  return [p, s].filter(Boolean).join('\n')
}

function goSeat(nickname) {
  navigate('/seats?nick=' + encodeURIComponent(nickname))
}

function goLadder() {
  navigate('/ladder')
}

function lbcLabel(n) {
  const v = Number(n) || 0
  if (v <= 1) return '首板'
  return v + '连板'
}

const rows = ref([])
const etfTotal = ref(0)
const lhbDate = ref('')
const error = ref('')

watch(() => props.tab, (n) => {
  if (n && VALID.includes(n) && n !== tab.value) {
    tab.value = n
    load()
  }
})

const zhangsuCols = [
  { key: 'name', label: '名称' }, { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'zhangsu', label: '涨速', fmt: 'pct', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
  { key: 'main_inflow', label: '主力净流入', fmt: 'amount', sortable: true },
  { key: 'industry', label: '行业' },
]
const flowCols = [
  { key: 'name', label: '名称' }, { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'main_inflow', label: '主力净流入', fmt: 'amount', sortable: true },
  { key: 'main_inflow_pct', label: '净占比', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
  { key: 'industry', label: '行业' },
]
const hotCols = [
  { key: 'name', label: '名称' }, { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'zhangsu', label: '涨速', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
  { key: 'turnover', label: '换手率', fmt: 'pct', sortable: true },
  { key: 'volume_ratio', label: '量比', sortable: true },
  { key: 'industry', label: '行业' },
]
const etfCols = [
  { key: 'name', label: '名称' }, { key: 'code', label: '代码' },
  { key: 'price', label: '现价', fmt: 'price', sortable: true },
  { key: 'change_pct', label: '涨跌幅', fmt: 'pct', sortable: true },
  { key: 'amount', label: '成交额', fmt: 'amount', sortable: true },
  { key: 'turnover', label: '换手率', fmt: 'pct', sortable: true },
  { key: 'amplitude', label: '振幅', fmt: 'pct', sortable: true },
  { key: 'volume_ratio', label: '量比', sortable: true },
]

const ztRows = computed(() => applyListFilter(rows.value))
const thsRows = computed(() => applyListFilter(rows.value))
const lhbRows = computed(() => applyListFilter(rows.value))
const changesRows = computed(() => applyListFilter(rows.value))
const ztSort = useTableSort(ztRows)

function changeTagClass(typeName) {
  if (!typeName) return ''
  if (['火箭发射', '快速反弹', '大笔买入', '封涨停板', '有大买盘', '竞价上涨', '高开5%', '向上缺口', '尾盘拉升'].includes(typeName)) return 'tag-up'
  if (['加速下跌', '高台跳水', '大笔卖出', '封跌停板', '有大卖盘', '竞价下跌', '低开5%', '向下缺口', '尾盘跳水'].includes(typeName)) return 'tag-down'
  return 'tag-neutral'
}

function switchTab(t) {
  tab.value = t
  logAction('rank_tab', t)
  navigate('/rank/' + t)
  load()
}

async function load() {
  try {
    if (tab.value === 'zhangsu') rows.value = await api.zhangsu(80)
    else if (tab.value === 'moneyflow') rows.value = await api.moneyflow(80)
    else if (tab.value === 'hot') rows.value = await api.hot('change_pct', 80)
    else if (tab.value === 'zt') rows.value = await api.limitUp(100)
    else if (tab.value === 'etf') {
      rows.value = await api.etfRank('change_pct', 80)
      etfTotal.value = rows.value.length
    } else if (tab.value === 'ths') {
      rows.value = await api.thsHot(thsType.value, 50)
    } else if (tab.value === 'lhb') {
      const r = await api.lhb(80)
      lhbDate.value = r.date || ''
      rows.value = r.items || []
    } else if (tab.value === 'changes') {
      rows.value = await api.stockChanges(80)
    }
    error.value = ''
  } catch (e) {
    error.value = '榜单加载失败：' + e.message
  }
}

usePolling(load, 3000)
</script>

<style scoped>
.analyse {
  text-align: left; max-width: 420px; white-space: normal;
  font-size: 12px; color: var(--text-dim);
}
.name-cell { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.change-tag { display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 4px; white-space: nowrap; }
.tag-up { background: rgba(239,68,68,.15); color: var(--up-color, #ef4444); }
.tag-down { background: rgba(34,197,94,.15); color: var(--down-color, #22c55e); }
.tag-neutral { background: var(--border); color: var(--text-dim); }
.zt-lb-badge {
  display: inline-block; font-size: 11px; font-weight: 700;
  color: var(--up); background: var(--up-bg);
  border: 1px solid rgba(239,68,68,.35); border-radius: 10px;
  padding: 1px 8px; cursor: pointer; white-space: nowrap;
}
.zt-lb-badge:hover { filter: brightness(1.08); box-shadow: 0 0 0 1px var(--up); }
</style>
