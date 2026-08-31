<template>
  <div>
    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'board' }" @click="tab = 'board'">游资榜单</button>
      <button class="tab" :class="{ active: tab === 'moves' }" @click="tab = 'moves'">游资动向</button>
    </div>

    <!-- ═══ 游资榜单：管理 + 筛选 ═══ -->
    <div v-if="tab === 'board'">
      <div class="card">
        <div class="card-title">
          游资榜单管理
          <span class="setting-value">{{ seatCount }} 条席位 / {{ seatGroups.length }} 位游资</span>
        </div>
        <div class="filter-bar">
          <UiSelect v-model="filterTier" style="width:150px">
            <option value="">全部级别</option>
            <option value="legend">殿堂级</option>
            <option value="new_gen">新生代</option>
            <option value="regional">地方帮派</option>
            <option value="broker">普通</option>
          </UiSelect>
          <UiSelect v-model="filterPremium" style="width:150px">
            <option value="">全部属性</option>
            <option value="positive">正面</option>
            <option value="neutral_positive">偏正面</option>
            <option value="neutral">中性</option>
            <option value="negative">负面</option>
          </UiSelect>
          <UiInput v-model="filterKw" placeholder="搜索名称 / 席位" style="flex:1;min-width:160px" />
          <UiButton variant="subtle" @click="openSeatEditor()"><UiIcon name="plus" :size="14" /> 新增游资</UiButton>
          <UiButton variant="subtle" :disabled="seatSyncing" @click="syncSeats">{{ seatSyncing ? '同步中…' : '恢复内置字典' }}</UiButton>
        </div>
        <div class="setting-row" style="border:none">
          <span class="setting-label" style="font-size:12px;color:var(--text-dim);line-height:1.6">
            数据存于本地数据库，增删改即时生效；「恢复内置字典」仅重置内置种子、保留自定义。席位变动会在龙虎榜识别中即时生效。
          </span>
        </div>
      </div>

      <div class="card mt16">
        <div class="setting-row" style="border:none;padding-bottom:0">
          <span class="setting-label" style="font-size:12px;color:var(--text-dim)">近期活跃度 = 近30天该游资在龙虎榜中出现的次数</span>
          <div class="setting-control" style="margin-left:auto">
            <UiSelect v-model="sortMode" style="width:160px" @change="applySeatSort">
              <option value="activity">按活跃度排序</option>
              <option value="name">按名称排序</option>
            </UiSelect>
          </div>
        </div>
        <table class="seat-table">
          <thead>
            <tr>
              <th>名称</th><th>实名</th><th>级别</th><th>风格</th><th>属性</th>
              <th>近期活跃度</th><th>席位（营业部）</th><th>来源</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="g in filteredSeatGroups" :key="g.nickname">
              <td class="seat-nick-cell"><b class="seat-nick-link" :title="`查看 ${g.nickname} 买入汇总`" @click="filterByNick(g.nickname)">{{ g.nickname }}</b></td>
              <td>{{ g.real_name || '-' }}</td>
              <td><span class="seat-tag" :class="'tier-' + g.tier">{{ tierLabel(g.tier) }}</span></td>
              <td class="seat-style">{{ g.style || '-' }}</td>
              <td>{{ premiumLabel(g.premium) }}</td>
              <td><span class="seat-activity" :class="{ hot: g.activity > 0 }">{{ g.activity || 0 }}</span></td>
              <td>
                <template v-if="g.custom_seats.length">
                  <div class="seat-real-title">自定义席位（{{ g.custom_seats.length }}）</div>
                  <div v-for="s in g.custom_seats" :key="s" class="seat-line">{{ s }}</div>
                </template>
                <template v-if="g.builtin_seats.length">
                  <div class="seat-real-title seat-builtin-title">内置规则席位（{{ g.builtin_seats.length }}）</div>
                  <div v-for="s in g.builtin_seats" :key="s" class="seat-line seat-builtin">{{ s }}</div>
                </template>
                <template v-if="g.real_seats && g.real_seats.length">
                  <div class="seat-real-title">实际出现（{{ g.real_seats.length }}）</div>
                  <div v-for="rs in g.real_seats" :key="rs.name" class="seat-line seat-real" :title="'最近 ' + rs.last_date">
                    {{ rs.name }}<span class="seat-real-date">{{ rs.last_date }}</span>
                  </div>
                </template>
              </td>
              <td>
                <span v-if="g.source === 'builtin'" class="src-builtin">内置</span>
                <span v-else-if="g.source === 'mixed'" class="src-mixed">内置+自定义</span>
                <span v-else class="src-custom">自定义</span>
              </td>
              <td class="seat-ops">
                <UiButton size="sm" variant="subtle" @click="openSeatEditor(g)">编辑</UiButton>
                <UiButton size="sm" variant="danger" @click="removeSeatGroup(g)">删除</UiButton>
              </td>
            </tr>
            <tr v-if="!filteredSeatGroups.length"><td colspan="8" class="empty">无匹配游资</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ═══ 游资动向：买入记录 ═══ -->
    <div v-else>
      <div class="card">
        <div class="card-title">查询与同步</div>
        <div class="setting-row">
          <span class="setting-label">按游资筛选</span>
          <div class="setting-control">
            <UiSelect v-model="filterNick" style="width:160px" @change="onFilterNick">
              <option value="">全部（按日期查看当日）</option>
              <option v-for="g in seatGroups" :key="g.nickname" :value="g.nickname">
                {{ g.nickname }}（{{ tierLabel(g.tier) }}）
              </option>
            </UiSelect>
            <span v-if="filterNick" style="color:var(--text-dim);font-size:12px">{{ nickItems.length }} 只股票</span>
          </div>
        </div>
        <div class="setting-row">
          <span class="setting-label">交易日</span>
          <div class="setting-control">
            <UiInput type="date" v-model="movesDate" style="width:160px" @change="loadMoves()" />
            <span style="color:var(--text-dim);font-size:12px">{{ syncedDates.length }} 天已同步</span>
          </div>
        </div>
        <div class="setting-row" v-if="syncedDates.length">
          <span class="setting-label">快捷日期</span>
          <div class="chip-row">
            <span
              v-for="d in syncedDates.slice(0, 10)"
              :key="d"
              class="chip"
              :class="{ on: d === movesDate }"
              @click="selectDate(d)"
            >{{ d.slice(5) }}</span>
          </div>
        </div>
        <div class="setting-row">
          <span class="setting-label">同步日期范围</span>
          <div class="setting-control">
            <UiInput type="date" v-model="syncStart" style="width:160px" />
            <span style="color:var(--text-dim)">至</span>
            <UiInput type="date" v-model="syncEnd" style="width:160px" />
            <UiButton variant="subtle" :disabled="movesSyncing" @click="doMovesSync">{{ movesSyncing ? '同步中…' : '同步' }}</UiButton>
          </div>
        </div>
        <div class="setting-row" v-if="movesSyncing || movesSyncMsg">
          <span class="setting-label">同步进度</span>
          <div class="progress-wrap">
            <div class="progress"><i :style="{ width: movesSyncPct + '%' }"></i></div>
            <div class="progress-msg">{{ movesSyncMsg || '准备中…' }} · {{ movesSyncPct }}%</div>
          </div>
        </div>
        <div class="setting-row">
          <div>
            <span class="setting-label">每日定时梯次自动同步</span>
            <div style="font-size:11px;color:var(--text-dim);margin-top:2px">
              交易日 16:45（初榜尝鲜）、17:05（全市场放榜）、18:00（晚间复核）、19:00（夜间归档）多波段自动同步
            </div>
          </div>
          <div class="setting-control">
            <div class="tab" :class="{ active: autoSync }" @click="setAutoSync(true)">开启</div>
            <div class="tab" :class="{ active: !autoSync }" @click="setAutoSync(false)">关闭</div>
          </div>
        </div>
      </div>

      <div class="card mt16">
        <div class="card-title" style="display:flex;align-items:center;gap:8px">
          {{ filterNick ? `游资 · ${filterNick} 买入汇总` : `当日席位明细 · ${movesDate || '未选择'}` }}
          <div class="tabs mini-tabs" style="margin-left:auto" v-if="!filterNick">
            <div class="tab" :class="{ active: movesSide === 'buy' }" @click="setSide('buy')">买入</div>
            <div class="tab" :class="{ active: movesSide === 'sell' }" @click="setSide('sell')">卖出</div>
          </div>
        </div>
        <div class="table-wrap" style="max-height: 560px; overflow-y: auto;">
          <table v-if="!filterNick" class="seat-table">
            <thead>
              <tr><th>股票</th><th>净额</th><th>游资席位</th><th>上榜原因</th></tr>
            </thead>
            <tbody>
              <template v-for="it in dateItems" :key="it.code">
                <tr
                  class="seat-stock-row"
                  :class="{ 'row-expanded': expandedCode === it.code }"
                  @click="toggleExpand(it.code)"
                >
                  <td class="stock-cell"><a @click.stop="openStock(it)">{{ it.name || it.code }}</a></td>
                  <td :class="netClass(it.net)">{{ fmtAmount(it.net) }}</td>
                  <td>
                    <span v-if="it.seats.length" class="youzi-list">
                      <span
                        v-for="s in it.seats"
                        :key="s.seat_name + s.nickname"
                        class="youzi-chip"
                        :class="'seat-' + s.type"
                        :data-tip="seatTip(s)"
                        @click.stop="filterByNick(s.nickname)"
                      >{{ s.nickname }}</span>
                    </span>
                    <span v-else style="color:var(--text-dim)">—</span>
                  </td>
                  <td class="seat-style">{{ it.reason || '—' }}</td>
                </tr>
                <PoolExpandRow
                  v-if="expandedCode === it.code"
                  :code="it.code"
                  :name="it.name"
                  :colspan="4"
                />
              </template>
              <tr v-if="!dateItems.length"><td colspan="4" class="empty">暂无数据，请先在「同步日期范围」拉取该日席位</td></tr>
            </tbody>
          </table>
          <table v-else class="seat-table nick-summary-table">
            <thead>
              <tr>
                <th class="col-stock">股票</th>
                <th class="col-date">首次买入</th>
                <th class="col-date">最近买入</th>
                <th class="col-count">次数</th>
                <th class="col-amount">累计买入</th>
                <th class="col-detail">逐次明细</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="m in nickItems" :key="m.code">
                <tr
                  class="seat-stock-row"
                  :class="{ 'row-expanded': expandedCode === m.code }"
                  @click="toggleExpand(m.code)"
                >
                  <td class="stock-cell"><a @click.stop="openStock(m)">{{ m.name || m.code }}</a></td>
                  <td class="col-date">{{ m.first_date }}</td>
                  <td class="col-date">{{ m.last_date }}</td>
                  <td class="col-count">{{ m.count }}</td>
                  <td class="col-amount">{{ fmtAmount(m.total_buy) }}</td>
                  <td class="col-detail" @click.stop>
                    <details>
                      <summary class="record-summary">展开</summary>
                      <div v-for="rc in sortedRecords(m.records)" :key="rc.date" class="record-line">
                        {{ rc.date }} 买{{ fmtAmount(rc.buy) }} / 净<span :class="netClass(rc.net)">{{ fmtAmount(rc.net) }}</span>
                      </div>
                    </details>
                  </td>
                </tr>
                <PoolExpandRow
                  v-if="expandedCode === m.code"
                  :code="m.code"
                  :name="m.name"
                  :colspan="6"
                />
              </template>
              <tr v-if="!nickItems.length"><td colspan="6" class="empty">该游资暂无买入记录</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 游资编辑弹窗 -->
    <div v-if="showSeatEditor" class="seat-modal-mask" @click.self="closeSeatEditor">
      <div class="seat-modal">
        <div class="seat-modal-title">{{ editingSeatNick ? '编辑游资：' + editingSeatNick : '新增游资' }}</div>
        <label class="seat-form-row">名称
          <UiInput v-model="seatForm.nickname" :disabled="!!editingSeatNick" placeholder="如：章盟主" full />
        </label>
        <label class="seat-form-row">实名
          <UiInput v-model="seatForm.real_name" placeholder="可选" full />
        </label>
        <div class="seat-form-row">
          <span class="seat-form-label">级别</span>
          <UiSelect v-model="seatForm.tier" full>
            <option value="legend">殿堂级</option>
            <option value="new_gen">新生代</option>
            <option value="regional">地方帮派</option>
            <option value="broker">普通</option>
          </UiSelect>
        </div>
        <label class="seat-form-row">风格
          <UiInput v-model="seatForm.style" placeholder="如：打板，龙头接力" full />
        </label>
        <div class="seat-form-row">
          <span class="seat-form-label">属性</span>
          <UiSelect v-model="seatForm.premium" full>
            <option value="positive">正面</option>
            <option value="neutral_positive">偏正面</option>
            <option value="neutral">中性</option>
            <option value="negative">负面</option>
          </UiSelect>
        </div>
        <div v-if="editingSeat && editingSeat.builtin_seats.length" class="seat-form-row seat-form-textarea seat-builtin-block">
          <div class="seat-form-col">
            <span class="seat-form-label-block">内置规则席位（{{ editingSeat.builtin_seats.length }}）· 自动保留，不可删改</span>
            <div class="seat-builtin-list">
              <div v-for="s in editingSeat.builtin_seats" :key="s" class="seat-line seat-builtin">{{ s }}</div>
            </div>
          </div>
        </div>
        <label class="seat-form-row seat-form-textarea">自定义席位（每行一个营业部名称，可自由增删改）
          <UiTextarea v-model="seatForm.customSeatsText" :rows="5" placeholder="每行一个营业部名称，如：&#10;国泰君安证券股份有限公司上海江苏路证券营业部" full />
        </label>
        <div class="seat-modal-ops">
          <UiButton variant="ghost" @click="closeSeatEditor">取消</UiButton>
          <UiButton variant="primary" :disabled="seatSaving" @click="saveSeatGroup">{{ seatSaving ? '保存中…' : '保存' }}</UiButton>
        </div>
      </div>
    </div>

    <!-- 某游资买入汇总弹窗已并入主视图（按游资筛选） -->

  </div>
</template>

<script setup>
// @author ygw
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { openStock } from '../composables/useStockMeta.js'
import { usePageTab } from '../composables/usePageTab.js'
import { showConfirm } from '../composables/useConfirm.js'
import { showToast } from '../composables/useToast.js'
import PoolExpandRow from '../components/PoolExpandRow.vue'

const tab = usePageTab('seats', 'moves')

// 展开分时/日K/评分
const expandedCode = ref('')
function toggleExpand(code) {
  if (!code) return
  expandedCode.value = expandedCode.value === code ? '' : code
}

function sortedRecords(records) {
  if (!records || !records.length) return []
  return [...records].sort((a, b) => (b.date || '').localeCompare(a.date || ''))
}

// ── 游资榜单 ──
const seatCount = ref(0)
const seatSyncing = ref(false)
const seatGroups = ref([])
const sortMode = ref('activity')

function sortSeatGroups() {
  const arr = seatGroups.value
  if (sortMode.value === 'activity') {
    arr.sort((a, b) => (b.activity || 0) - (a.activity || 0) || a.nickname.localeCompare(b.nickname, 'zh'))
  } else {
    arr.sort((a, b) => a.nickname.localeCompare(b.nickname, 'zh'))
  }
}

function applySeatSort() {
  sortSeatGroups()
}
const showSeatEditor = ref(false)
const seatSaving = ref(false)
const editingSeatNick = ref('')
const editingSeat = ref(null)
const seatForm = reactive({ nickname: '', real_name: '', tier: 'new_gen', style: '', premium: 'neutral', customSeatsText: '' })
const filterTier = ref('')
const filterPremium = ref('')
const filterKw = ref('')

const TIER_LABELS = { legend: '殿堂级', new_gen: '新生代', regional: '地方帮派', broker: '普通' }
const PREMIUM_LABELS = { positive: '正面', neutral_positive: '偏正面', neutral: '中性', negative: '负面' }

function tierLabel(t) { return TIER_LABELS[t] || t || '-' }
function premiumLabel(p) { return PREMIUM_LABELS[p] || p || '-' }

function seatTip(s) {
  const g = seatGroups.value.find(x => x.nickname === s.nickname)
  const lines = []
  lines.push(`属性：${premiumLabel(s.premium || g?.premium)}`)
  lines.push(`风格：${(g && g.style) ? g.style : '待补充'}`)
  return lines.join('\n')
}

const filteredSeatGroups = computed(() => {
  let g = seatGroups.value
  if (filterTier.value) g = g.filter(x => x.tier === filterTier.value)
  if (filterPremium.value) g = g.filter(x => x.premium === filterPremium.value)
  const kw = filterKw.value.trim()
  if (kw) g = g.filter(x => x.nickname.includes(kw) || x.seats.some(s => s.includes(kw)))
  return g
})

async function loadSeatGroups() {
  try {
    const res = await api.lhbSeats()
    seatCount.value = res.count || 0
    const map = new Map()
    for (const s of (res.seats || [])) {
      const k = s.nickname
      if (!map.has(k)) map.set(k, { nickname: k, real_name: '', tier: s.tier, style: '', premium: 'neutral', source: 'custom', activity: 0, seats: [], builtin_seats: [], custom_seats: [], real_seats: [] })
      const g = map.get(k)
      if (!g.real_name && s.real_name) g.real_name = s.real_name
      if ((s.activity || 0) > g.activity) g.activity = s.activity
      g.seats.push(s.seat_name)
      if (s.source === 'builtin') g.builtin_seats.push(s.seat_name)
      else g.custom_seats.push(s.seat_name)
      for (const rs of (s.real_seats || [])) {
        if (!g.real_seats.some(x => x.name === rs.name)) g.real_seats.push(rs)
      }
    }
    for (const g of map.values()) {
      if (g.builtin_seats.length && g.custom_seats.length) g.source = 'mixed'
      else if (g.builtin_seats.length) g.source = 'builtin'
      else g.source = 'custom'
    }
    seatGroups.value = [...map.values()]
    sortSeatGroups()
  } catch (e) { /* ignore */ }
}

function openSeatEditor(g) {
  if (g) {
    editingSeatNick.value = g.nickname
    editingSeat.value = g
    seatForm.nickname = g.nickname
    seatForm.real_name = g.real_name
    seatForm.tier = g.tier
    seatForm.style = g.style
    seatForm.premium = g.premium
    seatForm.customSeatsText = (g.custom_seats || []).join('\n')
  } else {
    editingSeatNick.value = ''
    editingSeat.value = null
    seatForm.nickname = ''
    seatForm.real_name = ''
    seatForm.tier = 'new_gen'
    seatForm.style = ''
    seatForm.premium = 'neutral'
    seatForm.customSeatsText = ''
  }
  showSeatEditor.value = true
}

function closeSeatEditor() { showSeatEditor.value = false }

async function saveSeatGroup() {
  const seats = seatForm.customSeatsText.split('\n').map(s => s.trim()).filter(Boolean)
  const nick = seatForm.nickname.trim()
  if (!nick) return showToast('请填写游资名称', 'error')
  if (!seats.length) return showToast('请至少填写一个自定义席位', 'error')
  seatSaving.value = true
  try {
    const body = { real_name: seatForm.real_name.trim(), tier: seatForm.tier, style: seatForm.style.trim(), premium: seatForm.premium, seats }
    if (editingSeatNick.value) await api.lhbSeatUpdate(editingSeatNick.value, body)
    else await api.lhbSeatCreate({ nickname: nick, ...body })
    showSeatEditor.value = false
    await loadSeatGroups()
    showToast(`游资「${nick}」保存成功`)
  } catch (e) {
    showToast('保存失败：' + (e.message || e), 'error')
  } finally {
    seatSaving.value = false
  }
}

async function removeSeatGroup(g) {
  const confirmed = await showConfirm({
    title: '删除游资确认',
    message: `确定删除游资「${g.nickname}」吗？`,
    confirmText: '确认删除',
    variant: 'danger',
  })
  if (!confirmed) return
  try {
    await api.lhbSeatDelete(g.nickname)
    await loadSeatGroups()
    showToast(`游资「${g.nickname}」已删除`)
  } catch (e) {
    showToast('删除失败：' + (e.message || e), 'error')
  }
}

async function syncSeats() {
  const confirmed = await showConfirm({
    title: '恢复内置字典',
    message: '确定恢复系统内置龙虎榜席位字典吗？（自定义席位将保留）',
    confirmText: '立即恢复',
    variant: 'primary',
  })
  if (!confirmed) return
  seatSyncing.value = true
  try {
    const res = await api.lhbSeatsSync(true)
    seatCount.value = res.count || 0
    await loadSeatGroups()
    showToast(`已恢复内置字典，共 ${seatCount.value} 条席位`)
  } catch (e) {
    showToast('同步失败：' + (e.message || e), 'error')
  } finally {
    seatSyncing.value = false
  }
}

// ── 游资动向 ──
const syncedDates = ref([])
const syncedSet = ref(new Set())
const movesDate = ref('')
const movesSide = ref('buy')
const dateItems = ref([])
const syncStart = ref('')
const syncEnd = ref('')
const movesSyncing = ref(false)
const movesSyncMsg = ref('')
const movesSyncPct = ref(0)
const autoSync = ref(true)
const filterNick = ref('')
const nickItems = ref([])
let movesTimer = null

function fmtAmount(v) {
  if (v == null || isNaN(v)) return '-'
  const n = Math.abs(v)
  if (n >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (n >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return String(Math.round(v))
}
function netClass(v) { return v == null || v > 0 ? 'up' : (v < 0 ? 'down' : 'flat') }

async function loadDates() {
  try {
    const res = await api.lhbMovesDates()
    syncedDates.value = (res.dates || []).map(d => d.date)
    syncedSet.value = new Set(syncedDates.value)
    if (!movesDate.value || !syncedSet.value.has(movesDate.value)) {
      movesDate.value = syncedDates.value[0] || ''
    }
  } catch (e) { /* ignore */ }
}

async function loadMoves() {
  if (!movesDate.value) { dateItems.value = []; return }
  try {
    const res = await api.lhbMoves(movesDate.value, movesSide.value)
    dateItems.value = res.items || []
  } catch (e) {
    dateItems.value = []
  }
}

function selectDate(d) { movesDate.value = d; loadMoves() }
function setSide(s) { movesSide.value = s; loadMoves() }

async function doMovesSync() {
  if (!syncStart.value || !syncEnd.value) return showToast('请选择同步日期范围', 'error')
  if (syncStart.value > syncEnd.value) return showToast('开始日期不能晚于结束日期', 'error')
  try {
    const res = await api.lhbMovesSync(syncStart.value, syncEnd.value)
    movesSyncing.value = true
    movesSyncMsg.value = res.message || '同步中…'
    startMovesPoll()
  } catch (e) {
    showToast('同步启动失败：' + (e.message || e), 'error')
  }
}

function startMovesPoll() {
  clearInterval(movesTimer)
  movesTimer = setInterval(async () => {
    try {
      const st = await api.lhbMovesSyncStatus()
      movesSyncPct.value = st.percent || 0
      movesSyncMsg.value = st.message || ''
      if (!st.running) {
        clearInterval(movesTimer)
        movesTimer = null
        movesSyncing.value = false
        await loadDates()
        await loadMoves()
        if (st.error) showToast('同步出错：' + st.error, 'error')
        else showToast('游资动向同步完成')
      }
    } catch (e) { /* ignore */ }
  }, 2000)
}

async function loadAutoSync() {
  try { autoSync.value = (await api.lhbMovesAutoGet()).enabled } catch (e) { /* ignore */ }
}

async function setAutoSync(v) {
  autoSync.value = v
  try { await api.lhbMovesAuto(v) } catch (e) { /* ignore */ }
}

async function onFilterNick() {
  if (!filterNick.value) { loadMoves(); return }
  nickItems.value = []
  try { nickItems.value = (await api.lhbMovesNick(filterNick.value)).items || [] } catch (e) { /* ignore */ }
}

function filterByNick(nickname) {
  tab.value = 'moves'
  filterNick.value = nickname
  onFilterNick()
}

function nickFromHash() {
  const m = location.hash.match(/[?&]nick=([^&]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

function onHashNick() {
  const n = nickFromHash()
  if (n && n !== filterNick.value) filterByNick(n)
}

onMounted(async () => {
  loadSeatGroups()
  await loadDates()
  await loadMoves()
  loadAutoSync()
  const n = nickFromHash()
  if (n) filterByNick(n)
  window.addEventListener('hashchange', onHashNick)
  const today = new Date()
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  const past = new Date(today.getTime() - 29 * 86400000)
  syncStart.value = iso(past)
  syncEnd.value = iso(today)
})

onUnmounted(() => {
  clearInterval(movesTimer)
  window.removeEventListener('hashchange', onHashNick)
})
</script>

<style scoped>
.settings-nav {
  position: sticky; top: 0; z-index: 50;
  display: flex; gap: 6px; flex-wrap: wrap;
  background: var(--bg); padding: 10px 0 12px;
  border-bottom: 1px solid var(--border); margin-bottom: 16px;
}
.sn-item {
  padding: 6px 16px; border-radius: 8px; font-size: 13px;
  color: var(--text-dim); cursor: pointer; border: 1px solid var(--border);
  background: var(--bg-card); user-select: none;
}
.sn-item:hover { color: var(--text); border-color: var(--accent); }
.sn-item.active { color: var(--accent); background: var(--accent-bg); border-color: var(--accent); font-weight: 600; }

.setting-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 0; border-bottom: 1px solid var(--border); gap: 10px;
}
.setting-row:last-child { border-bottom: none; }
.setting-label { font-size: 14px; color: var(--text); flex-shrink: 0; }
.setting-value { font-size: 13px; color: var(--text-dim); }
.setting-control { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.mini-tabs { margin-bottom: 0; }
.setting-input {
  padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--bg); color: var(--text); font-size: 13px; width: 320px; max-width: 50vw;
}
.setting-input:focus { outline: none; border-color: var(--accent); }

.filter-bar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; padding: 4px 0 12px; }
.filter-bar .setting-input { width: auto; }

/* 榜单表格 */
.seat-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.seat-table th, .seat-table td { padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; }
.seat-table th { color: var(--text-dim); font-weight: 500; white-space: nowrap; }
.seat-nick-cell { white-space: nowrap; }
.seat-nick-link { cursor: pointer; color: var(--accent); transition: color .15s; }
.seat-nick-link:hover { color: var(--accent-strong); text-decoration: underline; }
.seat-style { max-width: 260px; }
.seat-activity { font-weight: 700; color: var(--text-dim); }
.seat-activity.hot { color: var(--yellow); }
.seat-line { color: var(--text-dim); line-height: 1.5; }
.seat-real-title { margin-top: 6px; font-size: 12px; color: var(--accent); font-weight: 600; }
.seat-builtin-title { color: var(--text-dim); }
.seat-real { font-size: 12px; }
.seat-real-date { margin-left: 6px; font-size: 11px; color: var(--text-dim); }
.seat-builtin { color: var(--text-dim); opacity: .75; }
.seat-tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-pill); font-size: 12px; font-weight: 600; }
.seat-tag.tier-legend { background: var(--yellow-bg); color: var(--yellow); border: 1px solid var(--yellow); }
.seat-tag.tier-new_gen { background: var(--accent-bg); color: var(--accent); border: 1px solid var(--accent); }
.seat-tag.tier-regional { background: rgba(147, 51, 234, 0.15); color: #a855f7; border: 1px solid rgba(147, 51, 234, 0.35); }
.seat-tag.tier-broker { background: var(--bg-hover); color: var(--text-dim); border: 1px solid var(--border); }
.src-builtin { color: var(--text-dim); font-size: 12px; }
.src-custom { color: var(--yellow); font-size: 12px; }
.src-mixed { color: var(--accent); font-size: 12px; }
.seat-ops { white-space: nowrap; }
.seat-ops .ui-btn + .ui-btn { margin-left: 8px; }
.btn-sm { padding: 2px 10px; font-size: 12px; border-radius: var(--radius-sm); }
.btn-danger { color: var(--up); border-color: var(--up); border-radius: var(--radius-sm); }
.btn-danger:hover { background: var(--up); color: #fff; }

/* 弹窗 */
.seat-modal-mask { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 999; }
.seat-modal { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 20px 24px; width: 520px; max-width: 92vw; max-height: 86vh; overflow: auto; box-shadow: var(--shadow-lg); }

.seat-modal.wide { width: 720px; }
.seat-modal-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; }
.seat-form-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; font-size: 13px; color: var(--text); }
.seat-form-row .setting-input { width: auto; flex: 1; max-width: none; }
.seat-form-label { width: 56px; flex-shrink: 0; }
.seat-form-col { flex: 1; min-width: 0; }
.seat-form-label-block { font-size: 12px; color: var(--text-dim); margin-bottom: 6px; display: block; }
.seat-builtin-list {
  background: var(--bg-hover); border: 1px dashed var(--border); border-radius: 8px;
  padding: 8px 10px; max-height: 140px; overflow: auto;
}
.seat-builtin-block { display: flex; }
.seat-form-textarea { align-items: flex-start; }
.seat-form-textarea .ui-textarea { flex: 1; min-width: 0; max-width: none; }
.seat-form-textarea textarea { resize: vertical; min-height: 90px; font-family: inherit; }
.seat-modal-ops { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }

/* 动向 */
.chip-row { display: flex; gap: 6px; flex-wrap: wrap; }
.chip {
  padding: 3px 10px; border: 1px solid var(--border); border-radius: 12px;
  font-size: 12px; color: var(--text-dim); cursor: pointer; background: var(--bg-card);
}
.chip:hover { border-color: var(--accent); color: var(--accent); }
.chip.on { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); font-weight: 600; }
.progress-wrap { flex: 1; min-width: 200px; }
.progress { height: 6px; background: var(--bg-hover); border-radius: 3px; overflow: hidden; }
.progress i { display: block; height: 100%; background: var(--accent); transition: width .3s; }
.progress-msg { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
.stock-cell { white-space: nowrap; }
.youzi-list { display: flex; gap: 4px; flex-wrap: wrap; }
.youzi-chip {
  display: inline-block; font-size: 12px; padding: 1px 8px; border-radius: 10px;
  background: var(--accent-bg); color: var(--accent); cursor: pointer; border: 1px solid transparent;
}
.record-summary { cursor: pointer; font-size: 12px; color: var(--text-dim); user-select: none; }
.record-summary:hover { color: var(--accent); }
.record-line { font-size: 12px; color: var(--text-dim); line-height: 1.7; font-variant-numeric: tabular-nums; white-space: nowrap; }

/* 游资买入汇总表 - 固定列宽防止展开明细时抖动 */
.nick-summary-table {
  table-layout: fixed;
  width: 100%;
  min-width: 680px;
}
.nick-summary-table .col-stock { width: 120px; }
.nick-summary-table .col-date { width: 110px; font-variant-numeric: tabular-nums; }
.nick-summary-table .col-count { width: 65px; font-variant-numeric: tabular-nums; }
.nick-summary-table .col-amount { width: 110px; font-variant-numeric: tabular-nums; }
.nick-summary-table .col-detail { width: auto; }

.seat-stock-row {
  cursor: pointer;
  transition: background .15s;
}
.seat-stock-row:hover {
  background: var(--bg-hover);
}
.seat-stock-row.row-expanded {
  background: var(--bg-hover) !important;
}
</style>