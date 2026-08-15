<template>
  <div class="card">
    <div class="card-title">五档盘口</div>
    <div class="orderbook" v-if="orderbook">
      <div class="ob-col">
        <div class="ob-title">买盘（外盘 {{ fmtNum(outer, 0) }}）</div>
        <div v-for="(b, i) in orderbook.bid" :key="'b' + i" class="ob-row bid">
          <span>买{{ i + 1 }}　{{ fmtPrice(b.price) }}</span><span>{{ fmtNum(b.volume, 0) }}手</span>
        </div>
      </div>
      <div class="ob-col">
        <div class="ob-title">卖盘（内盘 {{ fmtNum(inner, 0) }}）</div>
        <div v-for="(a, i) in orderbook.ask" :key="'a' + i" class="ob-row ask">
          <span>卖{{ i + 1 }}　{{ fmtPrice(a.price) }}</span><span>{{ fmtNum(a.volume, 0) }}手</span>
        </div>
      </div>
    </div>
    <div class="empty" v-else>盘口暂不可用</div>
  </div>
</template>

<script setup>
/**
 * 五档盘口
 * @author ygw
 */
import { fmtPrice, fmtNum } from '../../utils.js'

defineProps({
  orderbook: { type: Object, default: null },
  outer: { type: [Number, String], default: null },
  inner: { type: [Number, String], default: null },
})
</script>
