<template>
  <div v-if="open" class="modal-mask" @click.self="close">
    <div class="modal-card">
      <div class="modal-hd">
        <span>添加监控 · {{ name || code }}</span>
        <button class="btn-ghost" @click="close">关闭</button>
      </div>
      <div class="modal-bd">
        <div class="kv-grid mb12">
          <div class="kv"><span class="k">代码</span><span class="v">{{ code }}</span></div>
          <div class="kv" v-if="price != null"><span class="k">现价</span><span class="v">{{ Number(price).toFixed(2) }}</span></div>
          <div class="kv" v-if="changePct != null"><span class="k">涨跌幅</span><span class="v" :class="changePct >= 0 ? 'up' : 'down'">{{ (changePct > 0 ? '+' : '') + Number(changePct).toFixed(2) }}%</span></div>
        </div>
        <div class="alert-form">
          <select v-model="form.metric" class="input">
            <option value="price">{{ targetType === 'index' ? '点数' : '价格' }}</option>
            <option v-if="targetType === 'index'" value="points">点数</option>
            <option value="change_pct">涨跌幅%</option>
            <option v-if="targetType === 'stock'" value="zhangsu">涨速%</option>
          </select>
          <select v-model="form.op" class="input">
            <option value="lte">≤ 跌到/低于</option>
            <option value="gte">≥ 涨到/高于</option>
          </select>
          <input v-model.number="form.threshold" type="number" step="any" class="input" placeholder="阈值" />
        </div>
        <div class="quick-row">
          <button class="btn-ghost" @click="preset('price', 'lte', price)">跌破现价</button>
          <button class="btn-ghost" @click="preset('price', 'gte', price)">涨过现价</button>
          <button class="btn-ghost" @click="preset('change_pct', 'lte', -3)">跌幅≤-3%</button>
          <button class="btn-ghost" @click="preset('change_pct', 'lte', -5)">跌幅≤-5%</button>
          <button class="btn-ghost" @click="preset('change_pct', 'gte', 5)">涨幅≥5%</button>
          <button v-if="targetType === 'stock'" class="btn-ghost" @click="preset('zhangsu', 'gte', 1.5)">涨速≥1.5%</button>
        </div>
        <input v-model="form.note" class="input mt8" placeholder="备注（可选）" style="width:100%" />
        <div class="error-banner mt8" v-if="error">{{ error }}</div>
        <div class="modal-actions">
          <button class="btn" :disabled="saving" @click="save">{{ saving ? '保存中…' : '确认添加' }}</button>
          <a class="source-link" @click="goAlerts">管理全部监控 →</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 个股 / 指数详情页快捷监控弹窗
 * @author ygw
 */
import { reactive, ref, watch } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { requestNotifyPermission } from '../composables/useAlertNotify.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  targetType: { type: String, default: 'stock' }, // stock | index
  code: { type: String, default: '' },
  name: { type: String, default: '' },
  price: { type: Number, default: null },
  changePct: { type: Number, default: null },
})
const emit = defineEmits(['close', 'saved'])

const saving = ref(false)
const error = ref('')
const form = reactive({
  metric: 'price',
  op: 'lte',
  threshold: null,
  note: '',
})

watch(() => props.open, (v) => {
  if (v) {
    error.value = ''
    form.metric = props.targetType === 'index' ? 'points' : 'price'
    form.op = 'lte'
    form.threshold = props.price != null ? Number(Number(props.price).toFixed(2)) : null
    form.note = ''
  }
})

function close() { emit('close') }
function goAlerts() { close(); navigate('/alerts') }

function preset(metric, op, val) {
  if (val == null || Number.isNaN(val)) return
  form.metric = metric === 'price' && props.targetType === 'index' ? 'points' : metric
  form.op = op
  form.threshold = metric === 'change_pct' || metric === 'zhangsu' ? val : Number(Number(val).toFixed(2))
}

async function save() {
  if (!props.code || form.threshold == null || form.threshold === '') {
    error.value = '请填写阈值'
    return
  }
  saving.value = true
  error.value = ''
  try {
    await api.alertCreate({
      target_type: props.targetType,
      code: props.code,
      name: props.name || '',
      metric: form.metric,
      op: form.op,
      threshold: Number(form.threshold),
      note: form.note.trim(),
      cooldown_sec: 300,
    })
    await requestNotifyPermission()
    emit('saved')
    close()
  } catch (e) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-mask {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 16px;
}
.modal-card {
  width: min(480px, 100%);
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 12px; box-shadow: 0 16px 40px rgba(0,0,0,0.35);
}
.modal-hd {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px; border-bottom: 1px solid var(--border);
  font-weight: 600;
}
.modal-bd { padding: 16px; }
.alert-form { display: flex; flex-wrap: wrap; gap: 8px; }
.quick-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.modal-actions {
  display: flex; align-items: center; gap: 12px; margin-top: 14px;
}
.input {
  height: 32px; padding: 0 10px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
  font-size: 13px; outline: none; min-width: 100px;
}
.input:focus { border-color: var(--accent); }
.mt8 { margin-top: 8px; }
.mb12 { margin-bottom: 12px; }
</style>
