<template>
  <div class="card">
    <div class="card-title ot-head">
      <div class="tabs mini-tabs">
        <div class="tab" :class="{ active: tab === 'ob' }" @click="tab = 'ob'">五档盘口</div>
        <div class="tab" :class="{ active: tab === 'ticks' }" @click="tab = 'ticks'">成交明细</div>
      </div>
      <span v-if="tab === 'ob'" class="ot-hint">外盘 {{ fmtNum(outer, 0) }} · 内盘 {{ fmtNum(inner, 0) }}</span>
      <a v-if="tab === 'ticks'" class="source-link" style="margin-left:auto" :href="eastmoneyUrl" target="_blank" rel="noopener">东财 <UiIcon name="external" :size="11" /></a>
    </div>

    <div v-show="tab === 'ob'" class="orderbook">
      <div class="ob-col">
        <div class="ob-title">买盘（外盘 {{ fmtNum(outer, 0) }}）</div>
        <div v-for="(b, i) in (orderbook?.bid || [])" :key="'b' + i" class="ob-row bid">
          <span>买{{ i + 1 }}　{{ fmtPrice(b.price) }}</span><span>{{ fmtNum(b.volume, 0) }}手</span>
        </div>
        <div v-if="!orderbook || !orderbook.bid || !orderbook.bid.length" class="ob-empty">暂无买盘</div>
      </div>
      <div class="ob-col">
        <div class="ob-title">卖盘（内盘 {{ fmtNum(inner, 0) }}）</div>
        <div v-for="(a, i) in (orderbook?.ask || [])" :key="'a' + i" class="ob-row ask">
          <span>卖{{ i + 1 }}　{{ fmtPrice(a.price) }}</span><span>{{ fmtNum(a.volume, 0) }}手</span>
        </div>
        <div v-if="!orderbook || !orderbook.ask || !orderbook.ask.length" class="ob-empty">暂无卖盘</div>
      </div>
    </div>

    <div v-show="tab === 'ticks'" class="table-wrap ot-ticks">
      <table class="data-table">
        <thead><tr><th>时间</th><th>价格</th><th>数量(手)</th><th>金额</th><th>方向</th></tr></thead>
        <tbody>
          <tr v-for="(t, i) in ticks" :key="i">
            <td>{{ t.time }}</td>
            <td :class="pctClass(t.direction === 2 ? -1 : 1)">{{ fmtPrice(t.price) }}</td>
            <td>{{ fmtNum(t.volume, 0) }}</td>
            <td>{{ fmtAmount(t.amount) }}</td>
            <td>
              <span :class="t.direction === 1 ? 'up' : t.direction === 2 ? 'down' : 'flat'">
                {{ t.direction === 1 ? '买盘' : t.direction === 2 ? '卖盘' : '中性' }}
              </span>
            </td>
          </tr>
          <tr v-if="!ticks.length"><td colspan="5" class="empty">暂无数据</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
/**
 * 五档盘口 + 成交明细合并卡片（Tab 切换，默认五档）
 * @author ygw
 */
import { fmtPrice, fmtNum, fmtAmount, pctClass } from '../../utils.js'
import { usePageTab } from '../../composables/usePageTab.js'

defineProps({
  orderbook: { type: Object, default: null },
  outer: { type: [Number, String], default: null },
  inner: { type: [Number, String], default: null },
  ticks: { type: Array, default: () => [] },
  eastmoneyUrl: { type: String, default: '' },
})

const tab = usePageTab('stock-order', 'ob')
</script>

<style scoped>
.ot-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ot-head .mini-tabs { margin-bottom: 0; }
.ot-head .mini-tabs .tab { padding: 3px 12px; font-size: 12px; }
.ot-hint { font-size: 12px; color: var(--text-dim); margin-left: auto; }

.orderbook { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; height: 348px; }
.ob-col { display: flex; flex-direction: column; }
.ob-title { font-size: 12px; color: var(--text-dim); margin-bottom: 6px; }
.ob-row {
  flex: 1; display: flex; align-items: center; justify-content: space-between;
  padding: 5px 10px; border-radius: 6px; font-variant-numeric: tabular-nums; font-size: 13px;
  min-height: 0;
}
.ob-row + .ob-row { margin-top: 3px; }
.ob-row.bid { background: var(--up-bg); color: var(--up); }
.ob-row.ask { background: var(--down-bg); color: var(--down); }
.ob-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 13px; }

.ot-ticks { height: 348px; overflow-y: auto; }
.ot-ticks .data-table { font-size: 12px; }
.ot-ticks th { position: sticky; top: 0; z-index: 1; }
</style>