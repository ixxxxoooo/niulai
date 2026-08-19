<template>
  <div class="risk-modal-mask" @click.self="$emit('close')">
    <div class="risk-modal">
      <div class="risk-head">
        <div class="risk-title-box">
          <span class="shield-icon">🛡️</span>
          <span class="risk-title">{{ stockName || code }} ({{ code }}) 智能排雷诊断</span>
        </div>
        <button class="modal-close" @click="$emit('close')">✕</button>
      </div>

      <div class="loading-box" v-if="loading">
        <UiIcon name="refresh" :size="18" class="rotating" /> 正在诊断排雷数据…
      </div>
      <div class="error-banner" v-else-if="error">{{ error }}</div>

      <div v-else class="risk-body">
        <!-- 核心风险等级卡片 -->
        <div class="risk-score-card" :class="'risk-' + (diagnosis.risk_level || 'safe')">
          <div class="score-left">
            <div class="score-level-badge">
              {{ levelLabel(diagnosis.risk_level) }}
            </div>
            <div class="score-val">
              风险指数：<strong>{{ diagnosis.risk_score || 0 }}</strong> / 100
            </div>
          </div>
          <div class="score-right">
            <div class="summary-line">
              未来 30 天解禁：<strong>{{ diagnosis.unlock_summary?.total_30d_ratio || 0 }}%</strong>
              （{{ diagnosis.unlock_summary?.count_30d || 0 }} 批）
            </div>
            <div class="summary-sub" v-if="diagnosis.unlock_summary?.next_unlock">
              最近解禁：{{ diagnosis.unlock_summary.next_unlock.date }} ·
              {{ diagnosis.unlock_summary.next_unlock.share_type }}
            </div>
          </div>
        </div>

        <!-- 风险标签与描述 -->
        <div class="risk-tags-sec mt12">
          <div class="sec-hd">排雷风险诊断明细</div>
          <div class="risk-tags-list">
            <div
              v-for="(tag, idx) in diagnosis.risk_tags"
              :key="idx"
              class="risk-tag-item"
              :class="'tag-level-' + tag.level"
            >
              <div class="tag-title">
                <span class="tag-dot"></span>
                <span>{{ tag.text }}</span>
              </div>
              <div class="tag-desc">{{ tag.desc }}</div>
            </div>
          </div>
        </div>

        <!-- 解禁计划与历史表 -->
        <div class="risk-unlock-sec mt16" v-if="diagnosis.all_unlocks && diagnosis.all_unlocks.length">
          <div class="sec-hd">限售解禁时间表 ({{ diagnosis.all_unlocks.length }} 批)</div>
          <div class="table-wrap">
            <table class="data-table mini-table">
              <thead>
                <tr>
                  <th>解禁日期</th>
                  <th>解禁类型</th>
                  <th>解禁市值</th>
                  <th>占总股本</th>
                  <th>占流通盘</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(u, idx) in diagnosis.all_unlocks" :key="idx">
                  <td><strong>{{ u.date }}</strong></td>
                  <td>{{ u.share_type }}</td>
                  <td>{{ fmtAmount(u.market_cap) }}</td>
                  <td :class="{ 'text-danger': u.ratio_total >= 5 }">{{ u.ratio_total ? u.ratio_total.toFixed(2) + '%' : '-' }}</td>
                  <td>{{ u.ratio_float ? u.ratio_float.toFixed(2) + '%' : '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 业绩预告与预警 -->
        <div class="risk-fc-sec mt16" v-if="diagnosis.forecasts && diagnosis.forecasts.length">
          <div class="sec-hd">业绩预告与财报预警</div>
          <div class="fc-list">
            <div v-for="(fc, idx) in diagnosis.forecasts" :key="idx" class="fc-card">
              <div class="fc-hd">
                <span class="fc-date">{{ fc.report_date }} (公告: {{ fc.notice_date }})</span>
                <span class="fc-type" :class="fcTypeClass(fc.predict_type)">{{ fc.predict_type || '业绩预告' }}</span>
              </div>
              <div class="fc-content" v-if="fc.content">{{ fc.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 智能排雷诊断弹窗
 * @author ygw
 */
import { ref, onMounted } from 'vue'
import { api } from '../api.js'
import { fmtAmount } from '../utils.js'

const props = defineProps({
  code: { type: String, required: true },
  stockName: { type: String, default: '' },
})

defineEmits(['close'])

const loading = ref(true)
const error = ref('')
const diagnosis = ref({})

function levelLabel(lvl) {
  if (lvl === 'high') return '🚨 高危风险'
  if (lvl === 'medium') return '⚠️ 中度预警'
  if (lvl === 'low') return 'ℹ️ 关注'
  return '✅ 暂无排雷风险'
}

function fcTypeClass(typeStr) {
  if (!typeStr) return 'flat'
  if (typeStr.includes('亏') || typeStr.includes('减')) return 'down'
  if (typeStr.includes('增') || typeStr.includes('扭亏')) return 'up'
  return 'flat'
}

async function load() {
  loading.value = true
  try {
    diagnosis.value = await api.stockRiskDiagnosis(props.code)
    error.value = ''
  } catch (e) {
    error.value = '排雷数据加载失败：' + e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.risk-modal-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.risk-modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 600px;
  max-width: 94vw;
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.risk-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
}
.risk-title-box {
  display: flex; align-items: center; gap: 8px;
}
.shield-icon { font-size: 18px; }
.risk-title { font-size: 15px; font-weight: 700; color: var(--text); }
.modal-close {
  border: none; background: transparent; cursor: pointer;
  font-size: 15px; color: var(--text-dim); padding: 4px 8px; border-radius: var(--radius-sm);
}
.modal-close:hover { color: var(--text); background: var(--bg-hover); }

.risk-body {
  padding: 16px 18px;
  overflow-y: auto;
}
.loading-box {
  padding: 30px; text-align: center; color: var(--text-dim); font-size: 13px;
  display: flex; align-items: center; justify-content: center; gap: 8px;
}
.rotating { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 评分卡片 */
.risk-score-card {
  border-radius: var(--radius-md);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  border: 1px solid var(--border);
}
.risk-score-card.risk-high {
  background: var(--up-bg);
  border-color: var(--up);
}
.risk-score-card.risk-medium {
  background: var(--yellow-bg);
  border-color: var(--yellow);
}
.risk-score-card.risk-safe, .risk-score-card.risk-low {
  background: var(--down-bg);
  border-color: var(--down);
}
.score-level-badge {
  font-size: 15px; font-weight: 800; color: var(--text);
}
.score-val {
  font-size: 12px; color: var(--text-dim); margin-top: 4px;
}
.score-val strong { color: var(--text); font-size: 14px; }
.score-right { text-align: right; font-size: 12px; color: var(--text-dim); }
.score-right strong { color: var(--up); font-size: 13px; }
.summary-sub { font-size: 11px; margin-top: 3px; }

/* 风险标签清单 */
.sec-hd {
  font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 8px;
}
.risk-tags-list {
  display: flex; flex-direction: column; gap: 8px;
}
.risk-tag-item {
  padding: 8px 12px; border-radius: var(--radius-sm);
  background: var(--kv-bg); border: 1px solid var(--border);
}
.risk-tag-item.tag-level-high {
  border-left: 3px solid var(--up);
}
.risk-tag-item.tag-level-medium {
  border-left: 3px solid var(--yellow);
}
.risk-tag-item.tag-level-safe, .risk-tag-item.tag-level-good {
  border-left: 3px solid var(--down);
}
.tag-title {
  font-size: 13px; font-weight: 700; color: var(--text);
}
.tag-desc {
  font-size: 12px; color: var(--text-dim); margin-top: 2px; line-height: 1.4;
}

/* 解禁表 */
.mini-table th, .mini-table td {
  padding: 6px 8px; font-size: 12px;
}
.text-danger { color: var(--up); font-weight: 700; }

/* 业绩预告卡片 */
.fc-list { display: flex; flex-direction: column; gap: 8px; }
.fc-card {
  padding: 8px 12px; border-radius: var(--radius-sm);
  background: var(--kv-bg); border: 1px solid var(--border);
}
.fc-hd {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;
}
.fc-date { font-size: 12px; color: var(--text-dim); }
.fc-type { font-size: 12px; font-weight: 700; }
.fc-content { font-size: 12px; color: var(--text); line-height: 1.4; }
</style>
