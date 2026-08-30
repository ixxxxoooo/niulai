<template>
  <div>
    <ToolNavTabs current-tab="alerts" />
    <div class="error-banner" v-if="error">{{ error }}</div>

    <div class="card mb12 perm-card" v-if="perm !== 'granted'">
      <div class="perm-row">
        <div>
          <div class="perm-title">桌面通知权限：{{ permLabel }}</div>
          <div class="perm-hint">需允许本站发送通知；Chrome 在系统设置里也要开启通知</div>
        </div>
        <UiButton @click="askPerm">开启通知</UiButton>
      </div>
    </div>

    <!-- 新建：纵向表单 + 搜索选股 -->
    <div class="card">
      <div class="card-title">添加监控</div>

      <div class="form-grid">
        <div class="form-item">
          <label class="form-label">监控对象</label>
          <div class="tabs mini-tabs">
            <div class="tab" :class="{ active: form.target_type === 'stock' }" @click="switchType('stock')">个股</div>
            <div class="tab" :class="{ active: form.target_type === 'index' }" @click="switchType('index')">指数</div>
          </div>
        </div>

        <div class="form-item" v-if="form.target_type === 'stock'">
          <label class="form-label">搜索股票</label>
          <SearchSuggest placeholder="代码 / 名称 / 拼音（首字母或全拼），如 600519、茅台、gzmt、maotai" @select="onPickStock" />
          <div class="picked" v-if="form.code">
            已选 <b>{{ form.name || form.code }}</b>
            <span class="picked-code">{{ form.code }}</span>
            <UiButton size="sm" variant="ghost" @click="clearTarget">清除</UiButton>
          </div>
        </div>

        <div class="form-item" v-else>
          <label class="form-label">选择指数</label>
          <div class="quick-indexes">
            <button type="button" class="chip" :class="{ on: form.code === '1.000001' }" @click="pickIndex('1.000001','上证指数')">上证</button>
            <button type="button" class="chip" :class="{ on: form.code === '0.399006' }" @click="pickIndex('0.399006','创业板指')">创业板</button>
            <button type="button" class="chip" :class="{ on: form.code === '1.000688' }" @click="pickIndex('1.000688','科创50')">科创50</button>
            <button type="button" class="chip" :class="{ on: form.code === '0.399001' }" @click="pickIndex('0.399001','深证成指')">深成</button>
          </div>
          <div class="picked" v-if="form.code">
            已选 <b>{{ form.name || form.code }}</b>
            <span class="picked-code">{{ form.code }}</span>
          </div>
        </div>

        <div class="form-item">
          <label class="form-label">监控指标</label>
          <div class="seg">
            <button type="button" class="seg-btn" :class="{ on: form.metric === 'price' }" @click="form.metric = 'price'" v-if="form.target_type === 'stock'">价格</button>
            <button type="button" class="seg-btn" :class="{ on: form.metric === 'points' }" @click="form.metric = 'points'" v-if="form.target_type === 'index'">点数</button>
            <button type="button" class="seg-btn" :class="{ on: form.metric === 'change_pct' }" @click="form.metric = 'change_pct'">涨跌幅%</button>
            <button type="button" class="seg-btn" :class="{ on: form.metric === 'zhangsu' }" @click="form.metric = 'zhangsu'" v-if="form.target_type === 'stock'">涨速%</button>
          </div>
        </div>

        <div class="form-item">
          <label class="form-label">触发条件</label>
          <div class="seg">
            <button type="button" class="seg-btn" :class="{ on: form.op === 'lte' }" @click="form.op = 'lte'">≤ 跌到 / 低于</button>
            <button type="button" class="seg-btn" :class="{ on: form.op === 'gte' }" @click="form.op = 'gte'">≥ 涨到 / 高于</button>
          </div>
        </div>

        <div class="form-row-2">
          <div class="form-item">
            <label class="form-label">阈值</label>
            <UiInput v-model="form.threshold" type="number" step="any" full :placeholder="thresholdPlaceholder" />
          </div>
          <div class="form-item">
            <label class="form-label">备注（可选）</label>
            <UiInput v-model="form.note" full placeholder="例如：止损提醒" />
          </div>
        </div>
      </div>

      <div class="preview" v-if="previewText">
        <span class="preview-label">预览</span>
        {{ previewText }}
      </div>

      <div class="form-actions">
        <UiButton variant="primary" :disabled="saving || !canSubmit" @click="add">{{ saving ? '添加中…' : '添加监控' }}</UiButton>
        <span class="form-tip">触发后默认冷却 5 分钟，避免重复轰炸</span>
      </div>
    </div>

    <!-- 列表 -->
    <div class="card mt16">
      <div class="card-title">
        <span>已设监控（{{ rows.length }}）</span>
        <UiButton size="sm" variant="ghost" @click="load">刷新</UiButton>
      </div>
      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>目标</th><th>指标</th><th>条件</th><th>阈值</th><th>冷却</th><th>状态</th><th>上次触发</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id">
              <td>
                <a @click="openTarget(r)">{{ r.name || r.code }}</a>
                <span class="dim">{{ r.code }}</span>
              </td>
              <td>{{ metricLabel(r.metric) }}</td>
              <td>{{ r.op === 'gte' ? '≥' : '≤' }}</td>
              <td>{{ fmtThreshold(r) }}</td>
              <td>{{ Math.round((r.cooldown_sec || 300) / 60) }}分钟</td>
              <td>
                <span :class="r.enabled ? 'up' : 'flat'">{{ r.enabled ? '启用' : '停用' }}</span>
              </td>
              <td class="dim">{{ r.last_triggered_at || '-' }}</td>
              <td>
                <div class="td-actions">
                  <UiButton size="sm" variant="ghost" @click="toggle(r)">{{ r.enabled ? '停用' : '启用' }}</UiButton>
                  <UiButton size="sm" variant="ghost" @click="remove(r)">删除</UiButton>
                </div>
              </td>
            </tr>
            <tr v-if="!rows.length"><td colspan="8" class="empty">暂无监控，上方添加一条试试</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 价格/点数/跌幅监控管理页
 * @author ygw
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../api.js'
import { navigate } from '../router.js'
import { openStock } from '../composables/useStockMeta.js'
import { requestNotifyPermission } from '../composables/useAlertNotify.js'
import { showConfirm } from '../composables/useConfirm.js'
import SearchSuggest from '../components/SearchSuggest.vue'
import ToolNavTabs from '../components/ToolNavTabs.vue'

const rows = ref([])
const error = ref('')
const saving = ref(false)
const perm = ref(typeof Notification !== 'undefined' ? Notification.permission : 'unsupported')

const form = reactive({
  target_type: 'stock',
  code: '',
  name: '',
  metric: 'price',
  op: 'lte',
  threshold: null,
  note: '',
})

const permLabel = computed(() => ({
  granted: '已授权',
  denied: '已拒绝（请在浏览器/系统设置中重新允许）',
  default: '未授权',
  unsupported: '当前环境不支持 Notification API',
}[perm.value] || perm.value))

const thresholdPlaceholder = computed(() => {
  if (form.metric === 'change_pct') return '如 -5 或 3.5'
  if (form.metric === 'zhangsu') return '如 1.5（5分钟涨速%）'
  if (form.metric === 'points') return '如 3200'
  return '如 1800'
})

const canSubmit = computed(() => {
  return !!(form.code && form.threshold != null && form.threshold !== '')
})

const previewText = computed(() => {
  if (!form.code || form.threshold == null || form.threshold === '') return ''
  const name = form.name || form.code
  const metric = metricLabel(form.metric)
  const op = form.op === 'gte' ? '≥' : '≤'
  const th = (form.metric === 'change_pct' || form.metric === 'zhangsu')
    ? `${Number(form.threshold)}%`
    : String(form.threshold)
  return `当「${name}」的${metric} ${op} ${th} 时发送桌面通知`
})

function metricLabel(m) {
  return { price: '价格', points: '点数', change_pct: '涨跌幅%', zhangsu: '涨速%' }[m] || m
}
function fmtThreshold(r) {
  if (r.metric === 'change_pct' || r.metric === 'zhangsu') return Number(r.threshold).toFixed(2) + '%'
  return Number(r.threshold).toFixed(2)
}

/**
 * 切换个股/指数时重置指标默认值
 * @param {'stock'|'index'} t
 */
function switchType(t) {
  form.target_type = t
  form.code = ''
  form.name = ''
  form.metric = t === 'index' ? 'points' : 'price'
}

function pickIndex(code, name) {
  form.code = code
  form.name = name
  form.metric = 'points'
}

/**
 * 搜索选中股票填入表单
 * @param {object} s
 */
function onPickStock(s) {
  if (!s?.code) return
  form.code = s.code
  form.name = s.name || ''
  form.target_type = 'stock'
  if (form.metric === 'points') form.metric = 'price'
}

function clearTarget() {
  form.code = ''
  form.name = ''
}

function openTarget(r) {
  if (r.target_type === 'index') navigate('/index/' + (r.code.includes('.') ? r.code : r.code))
  else openStock({ code: r.code, name: r.name }, { origin: '/alerts', originLabel: '返回监控' })
}

async function askPerm() {
  const ok = await requestNotifyPermission()
  perm.value = typeof Notification !== 'undefined' ? Notification.permission : 'unsupported'
  if (!ok) error.value = '未能获得通知权限，请检查浏览器与 macOS「系统设置 → 通知」'
  else error.value = ''
}

async function load() {
  try {
    rows.value = await api.alerts()
    error.value = ''
  } catch (e) {
    error.value = '加载失败：' + e.message
  }
}

async function add() {
  if (!canSubmit.value) {
    error.value = '请选择标的并填写阈值'
    return
  }
  saving.value = true
  try {
    await api.alertCreate({
      target_type: form.target_type,
      code: String(form.code).trim(),
      name: (form.name || '').trim(),
      metric: form.metric,
      op: form.op,
      threshold: Number(form.threshold),
      note: (form.note || '').trim(),
      cooldown_sec: 300,
    })
    form.threshold = null
    form.note = ''
    await load()
    if (perm.value !== 'granted') await askPerm()
  } catch (e) {
    error.value = '添加失败：' + e.message
  } finally {
    saving.value = false
  }
}

async function toggle(r) {
  try {
    await api.alertUpdate(r.id, { enabled: !r.enabled })
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(r) {
  const confirmed = await showConfirm({
    title: '删除监控确认',
    message: `确定删除对「${r.name || r.code}」的盯盘监控条件吗？`,
    confirmText: '确认删除',
    variant: 'danger',
  })
  if (!confirmed) return
  try {
    await api.alertDelete(r.id)
    await load()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<style scoped>
.page-sub {
  font-size: 13px; font-weight: 400; color: var(--text-dim); margin-left: 10px;
}
.mb12 { margin-bottom: 12px; }
.perm-card { padding: 14px 16px; }
.perm-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.perm-title { font-size: 14px; color: var(--text); }
.perm-hint { font-size: 12px; color: var(--text-dim); margin-top: 4px; }

.mini-tabs { margin-bottom: 0; }
.mini-tabs .tab { padding: 4px 14px; font-size: 13px; }

.form-grid { display: flex; flex-direction: column; gap: 14px; }
.form-item { display: flex; flex-direction: column; gap: 8px; }
.form-label { font-size: 12px; color: var(--text-dim); }
.form-row-2 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
@media (max-width: 720px) {
  .form-row-2 { grid-template-columns: 1fr; }
}

.seg { display: flex; flex-wrap: wrap; gap: 8px; }
.seg-btn {
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
  border-radius: 8px; padding: 7px 12px; font-size: 13px; cursor: pointer;
}
.seg-btn.on {
  border-color: var(--accent); background: var(--accent-bg, rgba(99,102,241,.12));
  color: var(--accent); font-weight: 600;
}

.quick-indexes { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
  border-radius: 999px; padding: 6px 12px; font-size: 13px; cursor: pointer;
}
.chip.on {
  border-color: var(--accent); color: var(--accent);
  background: var(--accent-bg, rgba(99,102,241,.12)); font-weight: 600;
}

.picked {
  font-size: 13px; color: var(--text); display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 10px; border-radius: 8px; background: var(--kv-bg);
}
.picked-code { color: var(--text-dim); font-size: 12px; }
.btn-mini { padding: 2px 8px; font-size: 12px; }

.input {
  height: 36px; padding: 0 12px; border-radius: 8px;
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
  font-size: 13px; outline: none;
}
.input.full { width: 100%; box-sizing: border-box; }
.input:focus { border-color: var(--accent); }

.preview {
  margin-top: 14px; padding: 10px 12px; border-radius: 8px;
  background: var(--kv-bg); font-size: 13px; color: var(--text); line-height: 1.5;
}
.preview-label {
  display: inline-block; margin-right: 8px; font-size: 11px; font-weight: 600;
  color: var(--accent); padding: 1px 6px; border-radius: 4px;
  background: var(--accent-bg, rgba(99,102,241,.12));
}

.form-actions {
  margin-top: 14px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}
.td-actions { display: inline-flex; align-items: center; gap: 8px; }
.form-tip { font-size: 12px; color: var(--text-dim); }
.dim { color: var(--text-dim); font-size: 12px; margin-left: 4px; }
</style>
