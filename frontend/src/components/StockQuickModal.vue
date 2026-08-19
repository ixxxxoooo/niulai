<template>
  <Teleport to="body">
    <div v-if="open" class="modal-mask" @click.self="close">
      <div class="modal-card stock-modal-card">
        <!-- 弹窗头部 -->
        <div class="modal-header">
          <div class="stock-title-group">
            <div class="stock-main-info">
              <span class="stock-name">{{ detail.name || name || '—' }}</span>
              <span class="stock-code">{{ code }}</span>
              <span class="stock-industry" v-if="detail.industry">{{ detail.industry }}</span>
            </div>
            <div class="stock-price-info" v-if="detail.price != null">
              <span class="price-val" :class="pctClass(detail.change_pct)">
                {{ fmtPrice(detail.price) }}
              </span>
              <span class="pct-val" :class="pctClass(detail.change_pct)">
                {{ detail.change_pct > 0 ? '+' : '' }}{{ fmtPct(detail.change_pct) }}
                ({{ detail.change_amount > 0 ? '+' : '' }}{{ fmtPrice(detail.change_amount) }})
              </span>
            </div>
          </div>

          <div class="header-actions">
            <button
              class="action-pill-btn"
              :class="{ watched: isWatched }"
              @click="toggleWatch"
              :title="isWatched ? '移出自选' : '加入自选'"
            >
              <UiIcon :name="isWatched ? 'star-filled' : 'star'" :size="13" />
              <span>{{ isWatched ? '已自选' : '加自选' }}</span>
            </button>

            <button class="action-pill-btn accent-pill" @click="goToDetail" title="进入个股完整行情页">
              <UiIcon name="external" :size="13" />
              <span>完整主页</span>
            </button>

            <button class="btn-close-modal" @click="close" title="关闭 (Esc)">✕</button>
          </div>
        </div>

        <!-- 关键数据速览条 -->
        <div class="snapshot-row" v-if="detail.price != null">
          <div class="snap-item"><span class="lbl">最高</span><span class="val" :class="pctClass(detail.high, detail.prev_close)">{{ fmtPrice(detail.high) }}</span></div>
          <div class="snap-item"><span class="lbl">最低</span><span class="val" :class="pctClass(detail.low, detail.prev_close)">{{ fmtPrice(detail.low) }}</span></div>
          <div class="snap-item"><span class="lbl">开盘</span><span class="val" :class="pctClass(detail.open, detail.prev_close)">{{ fmtPrice(detail.open) }}</span></div>
          <div class="snap-item"><span class="lbl">换手</span><span class="val">{{ fmtPct(detail.turnover) }}</span></div>
          <div class="snap-item"><span class="lbl">量比</span><span class="val">{{ detail.volume_ratio != null ? detail.volume_ratio.toFixed(2) : '—' }}</span></div>
          <div class="snap-item"><span class="lbl">成交额</span><span class="val">{{ fmtAmount(detail.amount) }}</span></div>
          <div class="snap-item"><span class="lbl">流通市值</span><span class="val">{{ fmtAmount(detail.float_mv) }}</span></div>
        </div>

        <!-- 弹窗内容区：图表与买卖盘口 -->
        <div class="modal-body">
          <div class="chart-section">
            <div class="chart-tab-bar">
              <div class="tab-group">
                <button
                  class="c-tab-btn"
                  :class="{ active: chartType === 'trend' }"
                  @click="chartType = 'trend'"
                >
                  分时图
                </button>
                <button
                  class="c-tab-btn"
                  :class="{ active: chartType === 'day' }"
                  @click="chartType = 'day'"
                >
                  日 K 线
                </button>
              </div>
              <span class="chart-tip" v-if="chartType === 'trend'">实时分时走势</span>
              <span class="chart-tip" v-else>包含 MA5 / MA10 / MA20 / MA60</span>
            </div>

            <!-- 图表容器 -->
            <div class="chart-box">
              <TrendChart
                v-if="chartType === 'trend'"
                :trend="trend"
                :detail="detail"
                :code="code"
                sub-ind="macd"
              />
              <KlineChart
                v-else
                period="day"
                :kline="kline"
                :detail="detail"
                sub-ind="macd"
              />
            </div>
          </div>

          <!-- 右侧盘口五档与信息 -->
          <div class="orderbook-section">
            <OrderBook :orderbook="detail.orderbook" :outer="detail.outer" :inner="detail.inner" />
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { fmtPrice, fmtPct, fmtAmount, pctClass } from '../utils.js'
import { showToast } from '../composables/useToast.js'
import { isWatched as checkWatched, addWatch, removeWatch } from '../composables/useWatchlist.js'
import UiIcon from './ui/UiIcon.vue'
import TrendChart from './stock/TrendChart.vue'
import KlineChart from './stock/KlineChart.vue'
import OrderBook from './stock/OrderBook.vue'

const props = defineProps({
  code: { type: String, default: '' },
  name: { type: String, default: '' },
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open'])

const detail = ref({})
const trend = ref(null)
const kline = ref(null)
const chartType = ref('trend')

const isWatched = computed(() => {
  if (!props.code) return false
  return checkWatched(props.code)
})

function close() {
  emit('update:open', false)
}

function goToDetail() {
  close()
  navigate(`/stock/${props.code}`)
}

async function toggleWatch() {
  if (!props.code) return
  const stockName = detail.value.name || props.name || props.code
  if (isWatched.value) {
    await removeWatch(props.code)
    showToast(`已将 ${stockName} 移出自选股`)
  } else {
    await addWatch(props.code)
    showToast(`已将 ${stockName} 加入自选股`)
  }
}

async function loadData() {
  if (!props.code || !props.open) return
  detail.value = {}
  trend.value = null
  kline.value = null

  try {
    const [d, t, k] = await Promise.all([
      api.stockDetail(props.code),
      api.stockTrends(props.code),
      api.stockKline(props.code, 'day', 120),
    ])
    detail.value = d || {}
    trend.value = t
    kline.value = k
  } catch (e) {
    console.error('加载股票浮窗数据失败', e)
  }
}

watch(() => props.open, (val) => {
  if (val) loadData()
})

watch(() => props.code, () => {
  if (props.open) loadData()
})

function onKeydown(e) {
  if (e.key === 'Escape' && props.open) {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  if (props.open) loadData()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.stock-modal-card {
  width: 95vw;
  max-width: 1020px;
  max-height: 90vh;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.55);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalIn .15s ease-out;
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}

/* 顶部头部 */
.modal-header {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--kv-bg);
  flex-wrap: wrap;
  gap: 12px;
}
.stock-title-group { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.stock-main-info { display: flex; align-items: center; gap: 8px; }
.stock-name { font-size: 20px; font-weight: 700; color: var(--text); }
.stock-code { font-size: 14px; color: var(--text-dim); font-variant-numeric: tabular-nums; }
.stock-industry {
  font-size: 11px; padding: 2px 7px; border-radius: 4px;
  background: var(--bg-hover); color: var(--text-dim);
}

.stock-price-info { display: flex; align-items: baseline; gap: 8px; font-variant-numeric: tabular-nums; }
.price-val { font-size: 22px; font-weight: 800; }
.pct-val { font-size: 14px; font-weight: 600; }

.header-actions { display: flex; align-items: center; gap: 10px; margin-left: auto; }
.action-pill-btn {
  display: inline-flex; align-items: center; gap: 5px; padding: 5px 12px;
  border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-dim); font-size: 12px;
  cursor: pointer; transition: all .15s;
}
.action-pill-btn:hover { border-color: var(--accent); color: var(--text); }
.action-pill-btn.watched { color: #eab308; border-color: rgba(234, 179, 8, 0.4); background: rgba(234, 179, 8, 0.08); }
.action-pill-btn.accent-pill {
  background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600;
}
.action-pill-btn.accent-pill:hover { background: var(--accent); color: #fff; }

.btn-close-modal {
  width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border);
  background: transparent; color: var(--text-dim); font-size: 14px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.btn-close-modal:hover { color: var(--text); background: var(--bg-hover); }

/* 数据快照行 */
.snapshot-row {
  display: flex; gap: 14px; padding: 8px 20px; background: var(--bg-hover);
  border-bottom: 1px solid var(--border); overflow-x: auto; font-size: 12px;
}
.snap-item { display: flex; align-items: center; gap: 6px; white-space: nowrap; }
.snap-item .lbl { color: var(--text-dim); }
.snap-item .val { font-weight: 600; font-variant-numeric: tabular-nums; }

/* 弹窗主体 */
.modal-body {
  display: grid;
  grid-template-columns: 1fr 240px;
  gap: 14px;
  padding: 16px 20px;
  overflow-y: auto;
  min-height: 440px;
}

@media (max-width: 768px) {
  .modal-body { grid-template-columns: 1fr; }
}

.chart-section { display: flex; flex-direction: column; gap: 10px; }
.chart-tab-bar { display: flex; justify-content: space-between; align-items: center; }
.tab-group { display: flex; gap: 6px; }
.c-tab-btn {
  padding: 4px 14px; border-radius: var(--radius-pill); border: 1px solid var(--border);
  background: var(--kv-bg); color: var(--text-dim); font-size: 12px; cursor: pointer;
  transition: all .15s;
}
.c-tab-btn:hover { color: var(--text); border-color: var(--accent); }
.c-tab-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 600; }
.chart-tip { font-size: 12px; color: var(--text-dim); }

.chart-box {
  flex: 1; min-height: 380px; border: 1px solid var(--border);
  border-radius: var(--radius-md); background: var(--kv-bg); overflow: hidden;
}

.orderbook-section { display: flex; flex-direction: column; }
</style>
