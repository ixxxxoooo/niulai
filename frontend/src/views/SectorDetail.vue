<template>
  <div>
    <div class="stock-head">
      <BackButton label="返回板块" fallback="/sectors" />
      <span class="name">{{ sector ? sector.name : code }}</span>
      <span class="code">{{ code }}</span>
      <a class="source-link" :href="'https://data.eastmoney.com/bkzj/' + code + '.html'" target="_blank" rel="noopener">东财↗</a>
      <span class="quote-time" v-if="sector">
        <span :class="pctClass(sector.change_pct)">{{ fmtPct(sector.change_pct) }}</span>
        · 成交 {{ fmtAmount(sector.amount) }}
      </span>
    </div>

    <div class="error-banner" v-if="error">{{ error }}</div>

    <!-- 板块概览 -->
    <div class="sentiment" v-if="sector">
      <div class="item">
        <div class="label">涨跌幅</div>
        <div class="value" :class="pctClass(sector.change_pct)">{{ fmtPct(sector.change_pct) }}</div>
      </div>
      <div class="item">
        <div class="label">成交额</div>
        <div class="value">{{ fmtAmount(sector.amount) }}</div>
      </div>
      <div class="item">
        <div class="label">主力净流入</div>
        <div class="value" :class="pctClass(sector.main_inflow)">{{ fmtAmount(sector.main_inflow) }}</div>
      </div>
      <div class="item">
        <div class="label">上涨 / 下跌</div>
        <div class="value"><span class="up">{{ sector.up_count ?? '-' }}</span> / <span class="down">{{ sector.down_count ?? '-' }}</span></div>
      </div>
      <div class="item">
        <div class="label">领涨股</div>
        <div class="value">
          <a class="leader-chip" @click="openFromSector({ code: sector.leader_code, name: sector.leader_name })">
            <span v-for="b in boardBadges({code:sector.leader_code,name:sector.leader_name})" :key="b.t" :class="'badge-'+b.cls" class="board-badge">{{b.t}}</span>{{ sector.leader_name || '-' }} <span class="up">{{ sector.leader_pct != null ? fmtPct(sector.leader_pct) : '' }}</span>
          </a>
        </div>
      </div>
    </div>

    <!-- 成分股列表 -->
    <div class="card mt16">
      <div class="card-title">
        <span>板块成分股（{{ stocks.length }} 只 · 点击列名排序）</span>
      </div>
      <StockTable :rows="stocks" :columns="stockColumns" @row-click="openFromSector" />
    </div>
  </div>
</template>

<script setup>
// @author ygw
import { ref, watch } from 'vue'
import { api, briefColumns } from '../api.js'
import { fmtAmount, fmtPct, pctClass, boardBadges } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { openStock } from '../composables/useStockMeta.js'
import StockTable from '../components/StockTable.vue'
import BackButton from '../components/BackButton.vue'

const props = defineProps({ code: { type: String, default: '' } })
const code = ref(props.code || '')

const sector = ref(null)
const stocks = ref([])
const error = ref('')

const stockColumns = briefColumns.filter(c =>
  ['name', 'code', 'price', 'change_pct', 'zhangsu', 'amount', 'turnover', 'volume_ratio', 'main_inflow'].includes(c.key),
)

/**
 * 从板块成分进入个股：在成分内左右切换，返回本板块页。
 * @param {object} row
 */
function openFromSector(row) {
  if (!row?.code) return
  openStock(row, {
    list: stocks.value,
    origin: '/sector/' + code.value,
    originLabel: '返回板块',
  })
}

async function load() {
  if (!code.value) return
  try {
    const d = await api.sectorDetail(code.value, 100)
    sector.value = d.sector
    stocks.value = d.stocks
    error.value = ''
  } catch (e) {
    error.value = '板块数据加载失败：' + e.message
  }
}

watch(() => props.code, (n) => {
  if (n && n !== code.value) { code.value = n; load() }
})

usePolling(load, 5000)
</script>
