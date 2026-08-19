<template>
  <div>
    <div class="page-title">自选股</div>
    <div class="error-banner" v-if="error">{{ error }}</div>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'watch' }" @click="tab = 'watch'">自选（{{ watchRows.length }}）</button>
      <button class="tab" :class="{ active: tab === 'hold' }" @click="tab = 'hold'">持仓（{{ holdings.length }}）</button>
    </div>

    <!-- ===================== 自选（不含盈亏，持仓标记展示） ===================== -->
    <template v-if="tab === 'watch'">
      <div class="group-bar-container mt16">
        <div class="group-pills">
          <button
            class="group-pill"
            :class="{ active: currentGroupId === null }"
            @click="selectGroup(null)"
          >
            <span class="group-pill-name">全部</span>
            <span
              v-if="allAvgPct != null"
              class="group-pill-pct"
              :class="pctClass(allAvgPct)"
            >{{ fmtPct(allAvgPct) }}</span>
          </button>
          <button
            v-for="(g, idx) in watchState.groups"
            :key="g.id"
            class="group-pill"
            :class="{ active: currentGroupId === g.id, 'pill-dragging': pillDragIndex === idx, 'pill-drag-over': pillDragOverIndex === idx }"
            draggable="true"
            @dragstart="onPillDragStart(idx, $event)"
            @dragover.prevent="pillDragOverIndex = idx"
            @dragleave="pillDragOverIndex === idx ? (pillDragOverIndex = null) : null"
            @drop="onPillDrop(idx, $event)"
            @dragend="onPillDragEnd"
            @click="selectGroup(g.id)"
          >
            <span class="group-pill-icon">{{ groupIcon(g.name) }}</span>
            <span class="group-pill-name">{{ g.name }}</span>
            <span
              v-if="getGroupAvgPct(g) != null"
              class="group-pill-pct"
              :class="pctClass(getGroupAvgPct(g))"
            >{{ fmtPct(getGroupAvgPct(g)) }}</span>
          </button>
        </div>
        <!-- 分组卡片右下角设置按钮 -->
        <button
          class="group-settings-btn"
          title="自选分组管理与排序"
          @click="showGroupManage = true"
        >
          ⚙
        </button>
      </div>

      <div class="card mt12" ref="stockCard">
        <div class="card-title">
          <div class="card-title-left">
            <span class="card-title-text">{{ currentGroupName }}（{{ watchRows.length }}）</span>
            <!-- 持仓快捷筛选胶囊（红框位置） -->
            <button
              class="hold-filter-chip"
              :class="{ active: onlyHolding }"
              :title="onlyHolding ? '点击显示全部标的' : '点击仅筛选当前持仓标的'"
              @click="onlyHolding = !onlyHolding"
            >
              <span class="hold-filter-dot"></span>
              <span>持仓{{ currentGroupHeldCount > 0 ? ` (${currentGroupHeldCount})` : '' }}</span>
            </button>
          </div>
          <div class="card-title-actions">
            <!-- 快捷添加股票组件 -->
            <div class="quick-add-wrap" ref="quickAddRef" @click.stop>
              <button
                v-if="!quickAddOpen"
                class="btn-quick-add"
                :title="`添加股票到「${currentGroupName}」`"
                @click.stop="openQuickAdd"
              >
                <span class="plus-icon">+</span>
              </button>
              <div v-else class="quick-add-box" @click.stop>
                <span class="quick-add-icon">🔍</span>
                <input
                  ref="quickAddInput"
                  v-model="quickAddQuery"
                  type="text"
                  class="quick-add-input"
                  :placeholder="`添加股票到「${currentGroupName}」…代码/拼音/名称`"
                  @input="onQuickSearch"
                  @keydown.down.prevent="moveSuggest(1)"
                  @keydown.up.prevent="moveSuggest(-1)"
                  @keydown.enter.prevent="onQuickAddEnter"
                  @keydown.esc="closeQuickAdd"
                />
                <button class="quick-add-close" @click.stop="closeQuickAdd" title="关闭">✕</button>

                <!-- 搜索候选下拉浮层 -->
                <div v-if="suggestList.length && quickAddOpen" class="quick-suggest-pop" @click.stop>
                  <div
                    v-for="(item, sIdx) in suggestList"
                    :key="item.code"
                    class="suggest-item"
                    :class="{ active: suggestActiveIndex === sIdx }"
                    @mousedown.prevent="selectSuggest(item)"
                  >
                    <span class="suggest-code">{{ item.code }}</span>
                    <span class="suggest-name">{{ item.name }}</span>
                    <span class="suggest-type">{{ item.classify === 'Fund' ? 'ETF' : (item.industry || item.board || 'A股') }}</span>
                    <span v-if="isWatched(item.code)" class="suggest-tag">已在自选</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 截图按钮 -->
            <button class="btn-screenshot" @click="captureElement(stockCard, `${currentGroupName}自选.png`)" title="截图">
              <UiIcon name="screenshot" :size="14" />
            </button>
          </div>
        </div>

        <div class="table-wrap" v-if="watchRows.length">
          <table class="data-table">
            <thead>
              <tr>
                <th>名称</th><th>代码</th>
                <th class="sortable" :class="{ sorted: tsW.sortKey === 'price' }" @click="tsW.toggleSort('price')">现价</th>
                <th class="sortable" :class="{ sorted: tsW.sortKey === 'change_pct' }" @click="tsW.toggleSort('change_pct')">涨跌幅</th>
                <th class="sortable" :class="{ sorted: tsW.sortKey === 'zhangsu' }" @click="tsW.toggleSort('zhangsu')">涨速</th>
                <th class="sortable" :class="{ sorted: tsW.sortKey === 'amount' }" @click="tsW.toggleSort('amount')">成交额</th>
                <th class="sortable" :class="{ sorted: tsW.sortKey === 'main_inflow' }" @click="tsW.toggleSort('main_inflow')">主力净流入</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in tsW.sorted" :key="s.code" @click="openFromList(s, tsW.sorted, '返回自选')">
                <td class="stock-name">
                  <MiniTrend :code="s.code" :name="s.name">
                    <span class="name-cell">
                      <BoardBadges :row="s" />{{ s.name }}
                      <span v-if="s.shares" class="hold-tag">持仓</span>
                      <span
                        v-if="riskMap[s.code]?.badge_text"
                        class="risk-pill"
                        :class="'pill-' + riskMap[s.code].badge_level"
                        @click.stop="openRisk(s)"
                        :title="`智能排雷预警：${riskMap[s.code].badge_text}，点击查看诊断`"
                      >
                        🛡️ {{ riskMap[s.code].badge_text }}
                      </span>
                    </span>
                  </MiniTrend>
                </td>
                <td>{{ s.code }}</td>

                <td :class="pctClass(s.change_pct)">{{ fmtPrice(s.price) }}</td>
                <td><span class="pct-badge" :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</span></td>
                <td :class="pctClass(s.zhangsu)">{{ fmtPct(s.zhangsu) }}</td>
                <td>{{ fmtAmount(s.amount) }}</td>
                <td :class="pctClass(s.main_inflow)">{{ fmtAmount(s.main_inflow) }}</td>
                <td>
                  <div class="td-actions">
                    <UiButton size="sm" variant="ghost" @click.stop="openStockGroup(s)">分组</UiButton>
                    <UiButton size="sm" variant="ghost" @click.stop="edit(s)">{{ s.shares ? '改仓' : '录入' }}</UiButton>
                    <UiButton size="sm" variant="danger" @click.stop="removeStock(s)">{{ currentGroupId !== null ? '移出' : '删除' }}</UiButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="empty" v-else>
          <div class="empty-title">当前分组「{{ currentGroupName }}」暂无自选标的</div>
          <div class="empty-desc">可点击右上角「+」直接搜索添加代码，或点击右下角设置按钮导入预设。</div>
          <div class="empty-actions mt12">
            <UiButton size="sm" variant="primary" @click.stop="openQuickAdd">+ 立即添加股票</UiButton>
            <UiButton size="sm" variant="ghost" v-if="currentGroupId !== null" @click="selectGroup(null)">查看全部自选</UiButton>
          </div>
        </div>
      </div>
    </template>

    <!-- ===================== 持仓（盈亏 / 个股 ETF 分表） ===================== -->
    <template v-else>
      <div class="pnl-grid" v-if="hasPos">
        <div class="pnl-card">
          <div class="k">整体持仓 · 总市值</div>
          <div class="v">{{ fmtMoney(holdSum.market_value) }}</div>
          <div class="sub">持仓成本 {{ fmtMoney(holdSum.cost_value) }}</div>
        </div>
        <div class="pnl-card">
          <div class="k">整体持仓 · 浮动盈亏</div>
          <div class="v" :class="pctClass(holdSum.pnl)">{{ fmtSignedMoney(holdSum.pnl) }}</div>
          <div class="sub" :class="pctClass(holdSum.pnl_pct)">{{ fmtPct(holdSum.pnl_pct) }} · 盈亏比</div>
        </div>
        <div class="pnl-card">
          <div class="k">整体持仓 · 当日盈亏</div>
          <div class="v" :class="pctClass(holdDay.pnl)">{{ fmtSignedMoney(holdDay.pnl) }}</div>
          <div class="sub" :class="pctClass(holdDay.pct)">{{ fmtPct(holdDay.pct) }} · 随行情实时变动</div>
        </div>
      </div>

      <div class="card mt16" v-if="holdStocks.length" ref="holdStockCard">
        <div class="card-title">
          <span>个股持仓（{{ holdStocks.length }}）</span>
          <span class="card-title-sub">浮动盈亏 = (现价 − 成本价) × 数量 · 盈亏比 = (现价 − 成本价) ÷ 成本价</span>
          <button class="btn-screenshot" @click="captureElement(holdStockCard, '个股持仓.png')" title="截图">
            <UiIcon name="screenshot" :size="14" />
          </button>
        </div>
        <div class="table-wrap">
          <table class="data-table hold-table">
            <thead>
              <tr>
                <th>名称</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'pnl' }" @click="tsHS.toggleSort('pnl')">浮动盈亏</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'pnl_pct' }" @click="tsHS.toggleSort('pnl_pct')">盈亏比</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'price' }" @click="tsHS.toggleSort('price')">现价</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'cost' }" @click="tsHS.toggleSort('cost')">成本价</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'shares' }" @click="tsHS.toggleSort('shares')">持仓</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'change_pct' }" @click="tsHS.toggleSort('change_pct')">当日涨跌幅</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'day_pnl' }" @click="tsHS.toggleSort('day_pnl')">当日盈亏</th>
                <th class="sortable" :class="{ sorted: tsHS.sortKey === 'position_ratio' }" @click="tsHS.toggleSort('position_ratio')">仓位</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in tsHS.sorted" :key="s.code" @click="openFromList(s, tsHS.sorted, '返回自选')">
                <td class="stock-name">
                  <MiniTrend :code="s.code" :name="s.name">
                    <span class="name-cell" :class="pctClass(s.pnl)">
                      <BoardBadges :row="s" />{{ s.name }}
                      <span
                        v-if="riskMap[s.code]?.badge_text"
                        class="risk-pill"
                        :class="'pill-' + riskMap[s.code].badge_level"
                        @click.stop="openRisk(s)"
                        :title="`智能排雷预警：${riskMap[s.code].badge_text}，点击查看诊断`"
                      >
                        🛡️ {{ riskMap[s.code].badge_text }}
                      </span>
                    </span>
                  </MiniTrend>
                  <div class="name-mv">{{ fmtMoney(s.market_value) }}</div>
                </td>

                <td :class="pctClass(s.pnl)">{{ fmtSignedMoney(s.pnl) }}</td>
                <td :class="pctClass(s.pnl_pct)">{{ fmtPct(s.pnl_pct) }}</td>
                <td :class="pctClass(s.change_pct)">{{ fmtPrice(s.price) }}</td>
                <td>{{ fmtPrice(s.cost) }}</td>
                <td>{{ fmtShares(s.shares) }}</td>
                <td><span class="pct-badge" :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</span></td>
                <td :class="pctClass(s.day_pnl)">{{ fmtSignedMoney(s.day_pnl) }}</td>
                <td>
                  <div class="pos-ratio">
                    <div class="pos-ratio-track">
                      <div class="pos-ratio-bar" :class="s.position_ratio > 50 ? 'over' : ''" :style="{ width: Math.min(100, s.position_ratio) + '%' }"></div>
                    </div>
                    <span>{{ fmtPct(s.position_ratio) }}</span>
                  </div>
                </td>
                <td>
                  <div class="td-actions"><UiButton size="sm" variant="ghost" @click.stop="edit(s)">改仓</UiButton><UiButton size="sm" variant="danger" @click.stop="clearOne(s)">清仓</UiButton></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card mt16" v-if="holdEtfs.length" ref="holdEtfCard">
        <div class="card-title">
          <span>ETF 持仓（{{ holdEtfs.length }}）</span>
          <span class="card-title-sub">按市值排序 · 盈亏比 = (现价 − 成本价) ÷ 成本价</span>
          <button class="btn-screenshot" @click="captureElement(holdEtfCard, 'ETF持仓.png')" title="截图">
            <UiIcon name="screenshot" :size="14" />
          </button>
        </div>
        <div class="table-wrap">
          <table class="data-table hold-table">
            <thead>
              <tr>
                <th>名称</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'pnl' }" @click="tsHE.toggleSort('pnl')">浮动盈亏</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'pnl_pct' }" @click="tsHE.toggleSort('pnl_pct')">盈亏比</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'price' }" @click="tsHE.toggleSort('price')">现价</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'cost' }" @click="tsHE.toggleSort('cost')">成本价</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'shares' }" @click="tsHE.toggleSort('shares')">持仓</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'change_pct' }" @click="tsHE.toggleSort('change_pct')">当日涨跌幅</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'day_pnl' }" @click="tsHE.toggleSort('day_pnl')">当日盈亏</th>
                <th class="sortable" :class="{ sorted: tsHE.sortKey === 'position_ratio' }" @click="tsHE.toggleSort('position_ratio')">仓位</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in tsHE.sorted" :key="s.code" @click="openFromList(s, tsHE.sorted, '返回自选')">
                <td class="stock-name">
                  <MiniTrend :code="s.code" :name="s.name">
                    <span class="name-cell" :class="pctClass(s.pnl)"><BoardBadges :row="s" />{{ s.name }}</span>
                  </MiniTrend>
                  <div class="name-mv">{{ fmtMoney(s.market_value) }}</div>
                </td>
                <td :class="pctClass(s.pnl)">{{ fmtSignedMoney(s.pnl) }}</td>
                <td :class="pctClass(s.pnl_pct)">{{ fmtPct(s.pnl_pct) }}</td>
                <td :class="pctClass(s.change_pct)">{{ fmtPrice(s.price) }}</td>
                <td>{{ fmtPrice(s.cost) }}</td>
                <td>{{ fmtShares(s.shares) }}</td>
                <td><span class="pct-badge" :class="pctClass(s.change_pct)">{{ fmtPct(s.change_pct) }}</span></td>
                <td :class="pctClass(s.day_pnl)">{{ fmtSignedMoney(s.day_pnl) }}</td>
                <td>
                  <div class="pos-ratio">
                    <div class="pos-ratio-track">
                      <div class="pos-ratio-bar" :class="s.position_ratio > 50 ? 'over' : ''" :style="{ width: Math.min(100, s.position_ratio) + '%' }"></div>
                    </div>
                    <span>{{ fmtPct(s.position_ratio) }}</span>
                  </div>
                </td>
                <td>
                  <div class="td-actions"><UiButton size="sm" variant="ghost" @click.stop="edit(s)">改仓</UiButton><UiButton size="sm" variant="danger" @click.stop="clearOne(s)">清仓</UiButton></div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card" v-if="!hasPos">
        <div class="empty">暂无持仓。在「自选」页点「录入」填写数量与成本价即可。</div>
      </div>

      <!-- 收益记录（按日快照） -->
      <div class="card mt16" v-if="snapshots.length">
        <div class="card-title" style="display:flex;align-items:center;gap:10px">
          <span>收益记录（按日快照）</span>
          <UiButton size="sm" variant="ghost" @click="clearSnapshots">清空全部</UiButton>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead><tr><th>时间</th><th>范围</th><th>市值</th><th>成本</th><th>盈亏</th><th>盈亏%</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="r in snapshots" :key="r.id + '-' + r.kind" style="cursor:default">
                <td>{{ r.ts }}</td>
                <td>{{ kindLabel(r.kind) }}</td>
                <td>{{ fmtMoney(r.market_value) }}</td>
                <td>{{ fmtMoney(r.cost_value) }}</td>
                <td :class="pctClass(r.pnl)">{{ fmtSignedMoney(r.pnl) }}</td>
                <td :class="pctClass(r.pnl_pct)">{{ fmtPct(r.pnl_pct) }}</td>
                <td><UiButton size="sm" variant="danger" @click="deleteSnapshot(r)">删除</UiButton></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div class="modal-mask" v-if="form" @click.self="form = null">
      <div class="modal-card">
        <div class="modal-title">持仓录入 · {{ form.name }}</div>
        <label class="modal-field">
          <span>数量（股）· 默认 100，可 ±100 调整</span>
          <div class="modal-qty">
            <UiButton size="sm" variant="ghost" @click="form.shares = Math.max(0, (form.shares || 0) - 100)">−100</UiButton>
            <UiInput v-model="form.shares" type="number" min="0" step="100" />
            <UiButton size="sm" variant="ghost" @click="form.shares = (form.shares || 0) + 100">+100</UiButton>
          </div>
        </label>
        <label class="modal-field">
          <span>成本价（元）· 步进 0.01 / 默认当前价</span>
          <div class="modal-qty">
            <UiButton size="sm" variant="ghost" @click="nudgeCost(-1)">−</UiButton>
            <UiInput v-model="form.cost" type="number" min="0" step="0.01" />
            <UiButton size="sm" variant="ghost" @click="nudgeCost(1)">+</UiButton>
          </div>
        </label>
        <div class="modal-actions">
          <UiButton variant="ghost" v-if="form.shares" @click="clearPos">清空持仓</UiButton>
          <UiButton variant="ghost" @click="form = null">取消</UiButton>
          <UiButton variant="primary" @click="savePos">保存</UiButton>
        </div>
      </div>
    </div>

    <!-- 排雷诊断弹窗 -->
    <RiskModal
      v-if="showRisk"
      :code="riskCode"
      :stock-name="riskName"
      @close="showRisk = false"
    />

    <!-- 分组管理弹窗 -->
    <GroupManageModal
      :open="showGroupManage"
      @close="showGroupManage = false"
      @changed="onGroupsChanged"
    />

    <!-- 单股多分组设置弹窗 -->
    <StockGroupModal
      :open="showStockGroup"
      :code="stockGroupTarget?.code"
      :name="stockGroupTarget?.name"
      @close="showStockGroup = false"
      @saved="onStockGroupSaved"
    />
  </div>
</template>
<script setup>

// @author ygw
import { ref, computed, reactive, nextTick, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPrice, fmtPct, pctClass } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { useTableSort } from '../composables/useTableSort.js'
import { usePageTab } from '../composables/usePageTab.js'
import { loadWatchlist, removeWatch, addWatch, isWatched, watchState, setCurrentGroup, reorderGroups } from '../composables/useWatchlist.js'
import { applyListFilter } from '../composables/useListFilter.js'
import { openStock } from '../composables/useStockMeta.js'
import { captureElement } from '../composables/useScreenshot.js'
import { showConfirm } from '../composables/useConfirm.js'
import { showToast } from '../composables/useToast.js'
import MiniTrend from '../components/MiniTrend.vue'
import BoardBadges from '../components/BoardBadges.vue'
import RiskModal from '../components/RiskModal.vue'
import GroupManageModal from '../components/GroupManageModal.vue'
import StockGroupModal from '../components/StockGroupModal.vue'

/**
 * 从自选/持仓列表进入详情，带同表左右切换与返回自选。
 * @param {object} row
 * @param {Array} list
 * @param {string} label
 * @author ygw
 */
function openFromList(row, list, label) {
  openStock(row, { list, origin: '/watchlist', originLabel: label || '返回自选' })
}

// 页面 Tab：'watch' 自选 / 'hold' 持仓（同页刷新保持，离开重置）
const tab = usePageTab('watchlist', 'watch')

// 智能排雷状态
const riskMap = ref({})
const showRisk = ref(false)
const riskCode = ref('')
const riskName = ref('')

function openRisk(s) {
  riskCode.value = s.code
  riskName.value = s.name
  showRisk.value = true
}

// 分组弹窗与当前分组状态
const showGroupManage = ref(false)
const showStockGroup = ref(false)
const stockGroupTarget = ref(null)

// 快速添加股票到当前分组
const quickAddOpen = ref(false)
const quickAddQuery = ref('')
const quickAddRef = ref(null)
const quickAddInput = ref(null)
const suggestList = ref([])
const suggestActiveIndex = ref(0)
let searchTimer = null

function openQuickAdd() {
  quickAddOpen.value = true
  quickAddQuery.value = ''
  suggestList.value = []
  suggestActiveIndex.value = 0
  nextTick(() => {
    quickAddInput.value?.focus()
  })
}

function closeQuickAdd() {
  quickAddOpen.value = false
  quickAddQuery.value = ''
  suggestList.value = []
}

function moveSuggest(delta) {
  if (!suggestList.value.length) return
  const len = suggestList.value.length
  suggestActiveIndex.value = (suggestActiveIndex.value + delta + len) % len
}

function onQuickSearch() {
  clearTimeout(searchTimer)
  const q = quickAddQuery.value.trim()
  if (!q) {
    suggestList.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const res = await api.search(q, 8)
      suggestList.value = res || []
      suggestActiveIndex.value = 0
    } catch (e) {
      suggestList.value = []
    }
  }, 120)
}

async function selectSuggest(item) {
  if (!item || !item.code) return
  try {
    await addWatch(item.code, currentGroupId.value)
    closeQuickAdd()
    await load()
  } catch (e) {
    console.error('Add stock failed:', e)
  }
}

async function onQuickAddEnter() {
  if (suggestList.value.length > 0 && suggestList.value[suggestActiveIndex.value]) {
    await selectSuggest(suggestList.value[suggestActiveIndex.value])
    return
  }
  const q = quickAddQuery.value.trim()
  if (q.length === 6 && /^\d{6}$/.test(q)) {
    try {
      await addWatch(q, currentGroupId.value)
      closeQuickAdd()
      await load()
    } catch (e) {
      console.error('Add code failed:', e)
    }
  } else if (q) {
    try {
      const res = await api.search(q, 1)
      if (res && res.length) {
        await selectSuggest(res[0])
      }
    } catch (e) {
      console.error('Search on enter failed:', e)
    }
  }
}

function onWindowClick(e) {
  if (quickAddOpen.value && quickAddRef.value && !quickAddRef.value.contains(e.target)) {
    closeQuickAdd()
  }
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
})

onUnmounted(() => {
  window.removeEventListener('click', onWindowClick)
})

const pillDragIndex = ref(null)
const pillDragOverIndex = ref(null)

function onPillDragStart(idx, e) {
  pillDragIndex.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx))
  }
}

async function onPillDrop(idx, e) {
  if (pillDragIndex.value === null || pillDragIndex.value === idx) {
    onPillDragEnd()
    return
  }
  const list = [...watchState.groups]
  const [moved] = list.splice(pillDragIndex.value, 1)
  list.splice(idx, 0, moved)
  watchState.groups = list
  onPillDragEnd()
  try {
    await reorderGroups(list.map(g => g.id))
  } catch (err) {
    console.error('Pill reorder error:', err)
  }
}

function onPillDragEnd() {
  pillDragIndex.value = null
  pillDragOverIndex.value = null
}

const currentGroupId = computed(() => watchState.currentGroupId)

const allWatchCount = computed(() => {
  if (watchState.allCodes.length) return watchState.allCodes.length
  return watchState.codes.length
})

const currentGroupName = computed(() => {
  if (currentGroupId.value === null) return '全部自选'
  const g = watchState.groups.find(x => x.id === currentGroupId.value)
  return g ? g.name : '自选'
})

function groupIcon(name) {
  if (/ETF|基金/i.test(name)) return '📊'
  if (/光通信|CPO/i.test(name)) return '📡'
  if (/PCB|覆铜/i.test(name)) return '🖨️'
  if (/封装|Chiplet|HBM/i.test(name)) return '🧩'
  if (/存储|内存/i.test(name)) return '💾'
  if (/半导体|芯片|设备|自主可控/i.test(name)) return '🛡️'
  if (/AI硬件|算力|服务器/i.test(name)) return '🖥️'
  if (/AI软件|大模型|软件/i.test(name)) return '🌐'
  if (/消费电子|苹果|华为/i.test(name)) return '📱'
  if (/锂电|固态电池|电池/i.test(name)) return '🔋'
  if (/电网|特高压|电力设备|电力|绿电|水电|核电/i.test(name)) return '⚡'
  if (/光伏|储能|太阳能/i.test(name)) return '☀️'
  if (/券商|证券|互联网金融/i.test(name)) return '📈'
  if (/商业航天|卫星/i.test(name)) return '🛰️'
  if (/军工|航发|航空|船舶/i.test(name)) return '✈️'
  if (/贵金属|小金属|黄金|稀土|有色/i.test(name)) return '🥇'
  if (/化工|化纤|制冷剂/i.test(name)) return '🛢️'
  if (/创新药|医药|CXO|生物/i.test(name)) return '🧪'
  if (/白酒|酒|食品/i.test(name)) return '🍶'
  if (/银行/i.test(name)) return '🏦'
  if (/能源|石油|煤炭|油气/i.test(name)) return '⛽'
  if (/机器人|具身/i.test(name)) return '🤖'
  if (/低空|eVTOL|飞行/i.test(name)) return '🚁'
  return '📁'
}

function selectGroup(gid) {
  setCurrentGroup(gid)
}

function openStockGroup(s) {
  stockGroupTarget.value = s
  showStockGroup.value = true
}

async function onStockGroupSaved() {
  await load()
}

async function onGroupsChanged() {
  await load()
}

const list = ref([])
const posMap = reactive({})
const snapshots = ref([])
const error = ref('')
const form = ref(null)
const snapReady = ref(false)
const stockCard = ref(null)
const etfCard = ref(null)
const holdStockCard = ref(null)
const holdEtfCard = ref(null)

// 股票代码到行情的映射，用于各分组实时涨跌幅计算
const quotesMap = computed(() => {
  const map = {}
  for (const s of list.value) {
    if (s && s.code) map[s.code] = s
  }
  return map
})

/** 获取任意分组中成分股的平均涨跌幅百分比 */
function getGroupAvgPct(g) {
  if (!g || !g.codes || !g.codes.length) return null
  let total = 0
  let count = 0
  for (const code of g.codes) {
    const q = quotesMap.value[code]
    if (q && q.change_pct != null && !isNaN(q.change_pct)) {
      total += Number(q.change_pct)
      count++
    }
  }
  return count > 0 ? total / count : null
}

// 全部自选的平均涨跌幅
const allAvgPct = computed(() => {
  const rows = list.value.filter(s => s.change_pct != null && !isNaN(s.change_pct))
  if (!rows.length) return null
  const sum = rows.reduce((acc, s) => acc + Number(s.change_pct), 0)
  return sum / rows.length
})

// 股票到所属分组名称列表的反向映射，用于删除时提示
const stockGroupsMap = computed(() => {
  const map = {}
  for (const g of watchState.groups) {
    for (const c of (g.codes || [])) {
      if (!map[c]) map[c] = []
      map[c].push(g.name)
    }
  }
  return map
})

function isEtf(s) {
  return s.classify === 'Fund' || s.type === 'ETF' || /ETF/i.test(s.name || '') || /^(15|16|51|56|58)/.test(s.code || '')
}

/** 金额：千分位，固定两位小数，不换算 万/亿 */
function fmtMoney(v) {
  if (v == null || isNaN(v)) return '-'
  return Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 带符号金额：千分位，固定两位小数，不换算 万/亿 */
function fmtSignedMoney(v) {
  if (v == null || isNaN(v)) return '-'
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  return sign + Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 股数格式化：100 / 1.2万 */
function fmtShares(v) {
  if (!v) return '0'
  if (v >= 10000) return (v / 10000).toFixed(2) + '万'
  return Number(v).toFixed(0)
}

function withPos(rows) {
  return rows.map(s => {
    const p = posMap[s.code] || {}
    const shares = Number(p.shares || 0)
    const cost = Number(p.cost || 0)
    const price = s.price != null ? Number(s.price) : null
    const mv = shares && price != null ? shares * price : 0
    const cv = shares * cost
    // 当日盈亏 = (现价 − 昨收) × 股数；无昨收时用涨跌幅反推
    let day_pnl = null
    if (shares && price != null) {
      if (s.prev_close != null) day_pnl = shares * (price - Number(s.prev_close))
      else if (s.change_pct != null) day_pnl = mv * Number(s.change_pct) / (100 + Number(s.change_pct))
    }
    return {
      ...s,
      shares,
      cost,
      market_value: mv,
      cost_value: cv,
      pnl: shares ? mv - cv : null,
      pnl_pct: shares && cv ? (mv - cv) / cv * 100 : null,
      day_pnl,
    }
  })
}

// 仅看持仓快捷筛选
const onlyHolding = ref(false)

// 当前分组（或全部）内属于真实持仓的股票数量
const currentGroupHeldCount = computed(() => {
  return filtered.value.filter(s => watchState.codes.includes(s.code) && s.shares > 0).length
})

/** 自选 tab：展示当前分组股票；若开启「仅看持仓」，则只筛选有持仓的标的 */
const watchRows = computed(() => {
  const rows = filtered.value.filter(s => watchState.codes.includes(s.code))
  if (onlyHolding.value) {
    return rows.filter(s => s.shares > 0)
  }
  return rows
})

/** 持仓 tab：全部持仓（个股 / ETF 分表），按市值降序、附仓位占比 */
const holdings = computed(() => {
  const held = filtered.value.filter(s => s.shares > 0)
  const totalMv = held.reduce((a, s) => a + (s.market_value || 0), 0)
  return held
    .map(s => ({ ...s, position_ratio: totalMv ? (s.market_value || 0) / totalMv * 100 : 0 }))
    .sort((a, b) => (b.market_value || 0) - (a.market_value || 0))
})
const holdStocks = computed(() => holdings.value.filter(s => !isEtf(s)))
const holdEtfs = computed(() => holdings.value.filter(s => isEtf(s)))
const hasPos = computed(() => holdings.value.length > 0)

const tsW = useTableSort(watchRows, 'watchlist_stocks')
const tsHS = useTableSort(holdStocks, 'holdings_stocks')
const tsHE = useTableSort(holdEtfs, 'holdings_etfs')

function bucket(rows) {
  const held = rows.filter(s => s.shares > 0)
  const mv = held.reduce((a, s) => a + (s.market_value || 0), 0)
  const cv = held.reduce((a, s) => a + (s.cost_value || 0), 0)
  const pnl = mv - cv
  const dayHeld = held.filter(s => s.day_pnl != null && !isNaN(s.day_pnl))
  const day_pnl = dayHeld.reduce((a, s) => a + s.day_pnl, 0)
  return { market_value: mv, cost_value: cv, pnl, pnl_pct: cv ? pnl / cv * 100 : null, day_pnl, count: held.length }
}

function bucketDay(rows) {
  const held = rows.filter(s => s.shares > 0 && s.day_pnl != null && !isNaN(s.day_pnl))
  const pnl = held.reduce((a, s) => a + s.day_pnl, 0)
  const base = held.reduce((a, s) => a + ((s.market_value || 0) - s.day_pnl), 0)
  return { pnl, pct: base > 0 ? pnl / base * 100 : null }
}

const holdSum = computed(() => bucket(holdings.value))
const holdDay = computed(() => bucketDay(holdings.value))

function kindLabel(k) {
  return { all: '合计', stock: '个股', etf: 'ETF' }[k] || k
}

/** 成本价末位微调：步长固定 0.01，保留两位小数（56.01 → 减 → 56.00 → 55.99） */
function nudgeCost(dir) {
  if (!form.value) return
  const v = Number(form.value.cost) || 0
  form.value.cost = Number((v + dir * 0.01).toFixed(2))
}

function edit(s) {
  // 已有持仓：保留原数量与原成本；新增：默认 100 股、成本默认当前价
  const held = Number(s.shares || 0) > 0
  form.value = {
    code: s.code,
    name: s.name,
    shares: held ? s.shares : 100,
    cost: held ? (s.cost || s.price || 0) : (s.price || 0),
  }
}

async function loadSnapshots() {
  try {
    const sm = await api.positionsSummary()
    snapshots.value = (sm.snapshots || []).filter(x => x.kind === 'all')
  } catch (e) { /* 快照失败不影响列表 */ }
}

async function savePos() {
  const f = form.value
  if (!f) return
  await api.positionSave({ code: f.code, shares: Number(f.shares) || 0, cost: Number(f.cost) || 0 })
  form.value = null
  await load()
  loadSnapshots()
}

async function clearPos() {
  const f = form.value
  if (!f) return
  const confirmed = await showConfirm({
    title: '清空持仓确认',
    message: `确定清空【${f.name || f.code}】的持仓记录吗？`,
    confirmText: '确认清空',
    variant: 'danger',
  })
  if (!confirmed) return
  await api.positionDelete(f.code)
  form.value = null
  showToast(`已清空【${f.name || f.code}】的持仓`)
  await load()
}

async function clearOne(s) {
  const confirmed = await showConfirm({
    title: '清空持仓确认',
    message: `确定清空【${s.name}（${s.code}）】的持仓记录吗？`,
    confirmText: '确认清空',
    variant: 'danger',
  })
  if (!confirmed) return
  await api.positionDelete(s.code)
  showToast(`已清空【${s.name}】的持仓`)
  await load()
}

async function deleteSnapshot(r) {
  const confirmed = await showConfirm({
    title: '删除记录确认',
    message: `确定删除该收益记录（${r.ts} · ${kindLabel(r.kind)}）吗？`,
    confirmText: '确认删除',
    variant: 'danger',
  })
  if (!confirmed) return
  try {
    await api.positionSnapshotDelete(r.id)
    await loadSnapshots()
    showToast('记录已删除')
  } catch (e) {
    showToast('删除失败：' + e.message, 'error')
  }
}

async function clearSnapshots() {
  if (!snapshots.length) return
  const confirmed = await showConfirm({
    title: '清空收益记录确认',
    message: '确定清空全部收益记录吗？此操作不可恢复。',
    confirmText: '彻底清空',
    variant: 'danger',
  })
  if (!confirmed) return
  try {
    await api.positionSnapshotsClear()
    snapshots.value = []
    showToast('全部收益记录已清空')
  } catch (e) {
    showToast('清空失败：' + e.message, 'error')
  }
}

async function removeStock(s) {
  const code = typeof s === 'string' ? s : s.code
  const sName = typeof s === 'object' ? s.name : code
  const curGid = currentGroupId.value
  if (curGid !== null) {
    const curGroup = watchState.groups.find(g => g.id === curGid)
    const gName = curGroup ? curGroup.name : '当前分组'
    const confirmed = await showConfirm({
      title: '移出分组确认',
      message: `确定将【${sName || code}】移出「${gName}」分组吗？`,
      detail: '提示：该股票仍会保留在自选「全部」及其他所属分组中。',
      confirmText: '确认移出',
      variant: 'danger',
    })
    if (!confirmed) return
    await removeWatch(code, curGid)
  } else {
    const inGroups = stockGroupsMap.value[code] || []
    let detail = '提示：删除后将同时从所有所属分组及持仓中彻底移除。'
    if (inGroups.length > 0) {
      detail = `该股票当前归属于以下分组：【${inGroups.join('】、【')}】。\n删除后将同时从所有分组及持仓中彻底移除。`
    }
    const confirmed = await showConfirm({
      title: '删除自选确认',
      message: `确定从全部自选中删除【${sName || code}】吗？`,
      detail,
      confirmText: '彻底删除',
      variant: 'danger',
    })
    if (!confirmed) return
    await removeWatch(code, null)
  }
  await load()
}

async function load() {
  try {
    const codes = await loadWatchlist(watchState.currentGroupId)
    const pos = await api.positions().catch(() => ({ items: [] }))
    const posItems = pos.items || []
    // 聚合全量代码（所有分组代码 ∪ 当前视图代码 ∪ 持仓代码），确保所有分组涨跌幅均能实时计算
    const allGroupCodes = (watchState.groups || []).flatMap(g => g.codes || [])
    const allCodes = [...new Set([...watchState.allCodes, ...allGroupCodes, ...codes, ...posItems.map(p => p.code)])]
    if (!allCodes.length) { list.value = []; Object.keys(posMap).forEach(k => delete posMap[k]); return }
    const quotes = await api.batch(allCodes)
    list.value = quotes
    Object.keys(posMap).forEach(k => delete posMap[k])
    for (const it of posItems) posMap[it.code] = it
    error.value = ''
    if (!snapReady.value) {
      snapReady.value = true
      loadSnapshots()
    }
    // 异步拉取排雷标签（不阻塞行情）
    loadRiskTags(allCodes)
  } catch (e) {
    error.value = '自选股加载失败：' + e.message
  }
}

async function loadRiskTags(allCodes) {
  try {
    const stockOnly = allCodes.filter(c => !isEtf({ code: c }))
    if (!stockOnly.length) return
    // 增量模式：只查询当前前端内存中尚未分析过的个股（每天只拉一次，绝不重复拉取）
    const missingCodes = stockOnly.filter(c => !(c in riskMap.value))
    if (!missingCodes.length) return
    const res = await api.batchStockRisk(missingCodes.slice(0, 100))
    riskMap.value = { ...riskMap.value, ...(res || {}) }
  } catch (e) { /* ignore */ }
}

usePolling(load, 3000)
</script>

<style scoped>
.name-cell { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.card-title-sub { font-size: 12px; color: var(--text-dim); font-weight: 400; }

/* 自选分组导航条 */
.group-bar-container {
  position: relative;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 48px 10px 14px;
  min-height: 48px;
}
.group-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 10px;
  align-items: center;
}
.group-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 12px;
  border-radius: var(--radius-sm); font-size: 13px; font-weight: 500;
  color: var(--text-dim); background: var(--bg-hover); border: 1px solid transparent;
  cursor: pointer; white-space: nowrap; transition: all .15s ease;
}
.group-pill:hover { color: var(--text); background: var(--border); }
.group-pill.active {
  color: var(--accent); background: var(--accent-bg); border-color: var(--accent);
  font-weight: 600;
}
.group-pill-icon { font-size: 14px; line-height: 1; }
.group-pill-name { font-weight: 500; }
.group-pill-pct {
  font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums;
  padding: 1px 5px; border-radius: 3px; line-height: 1.2;
}
.group-pill-pct.up { color: var(--up); background: var(--up-bg); }
.group-pill-pct.down { color: var(--down); background: var(--down-bg); }
.group-pill-pct.flat { color: var(--text-dim); }

.group-pill[draggable="true"] { cursor: grab; }
.group-pill:active { cursor: grabbing; }
.group-pill.pill-dragging { opacity: 0.35; transform: scale(0.95); }
.group-pill.pill-drag-over { border-color: var(--accent); background: var(--accent-bg); transform: scale(1.05); }

/* 分组卡片右下角纯图标设置按钮 */
.group-settings-btn {
  position: absolute;
  right: 12px;
  bottom: 10px;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text-dim);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  transition: all .15s ease;
}
.group-settings-btn:hover {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent);
  transform: scale(1.08);
}
.group-settings-btn:active {
  transform: scale(0.95);
}

.empty-title { font-size: 14px; font-weight: 500; color: var(--text); }
.empty-desc { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
.empty-actions { display: flex; gap: 10px; justify-content: center; }

/* 排雷微胶囊 */
.risk-pill {
  font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: var(--radius-sm);
  cursor: pointer; transition: transform .12s; white-space: nowrap; user-select: none;
}
.risk-pill:hover { transform: scale(1.06); filter: brightness(1.1); }
.risk-pill.pill-high { background: var(--up-bg); color: var(--up); border: 1px solid var(--up); }
.risk-pill.pill-medium { background: var(--yellow-bg); color: var(--yellow); border: 1px solid var(--yellow); }
.risk-pill.pill-low, .risk-pill.pill-safe { background: var(--down-bg); color: var(--down); }

/* 持仓标记（自选表） */
.hold-tag {
  margin-left: 2px; padding: 0 4px; border-radius: var(--radius-sm);
  font-size: 10px; line-height: 14px; font-weight: 600;
  background: var(--accent-bg); color: var(--accent);
}

/* 同花顺风格持仓表 */
.hold-table th, .hold-table td { text-align: right; white-space: nowrap; }
.hold-table th:nth-child(1), .hold-table td:nth-child(1) { text-align: left; }
.hold-table td { font-variant-numeric: tabular-nums; }
.hold-table td.stock-name { font-weight: 600; }

/* 名称按盈亏着色：盈利红 / 亏损绿 */
.name-cell.up { color: var(--up); }
.name-cell.down { color: var(--down); }

/* 名称下方当前市值（仅金额，加粗） */
.name-mv { font-size: 12px; font-weight: 600; color: var(--text-dim); margin-top: 2px; }

/* 仓位迷你进度条 */
.pos-ratio { display: inline-flex; align-items: center; gap: 6px; min-width: 76px; }
.pos-ratio span { font-size: 12px; color: var(--text); min-width: 36px; text-align: right; font-variant-numeric: tabular-nums; }
.pos-ratio-track {
  height: 5px; border-radius: 3px; flex: 1; min-width: 34px; max-width: 60px;
  background: var(--accent-bg); overflow: hidden;
}
.pos-ratio-bar {
  height: 100%; border-radius: 3px; min-width: 2px;
  background: linear-gradient(90deg, var(--accent), rgba(76, 154, 255, .55));
}
.pos-ratio-bar.over { background: linear-gradient(90deg, var(--yellow), rgba(227, 179, 65, .55)); }

/* 截图按钮与卡片顶栏操作区 */
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title-left {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.card-title-text {
  font-weight: 600;
}
.hold-filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 14px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text-dim);
  transition: all .15s ease;
  user-select: none;
}
.hold-filter-chip:hover {
  background: var(--border);
  color: var(--text);
}
.hold-filter-chip.active {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent);
  font-weight: 600;
}
.hold-filter-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-dim);
  transition: background .15s ease;
}
.hold-filter-chip.active .hold-filter-dot {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
}
.card-title-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quick-add-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}

.btn-quick-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
  transition: all .15s ease;
}
.btn-quick-add:hover {
  background: var(--accent-bg);
  border-color: var(--accent);
  color: var(--accent);
  transform: scale(1.08);
}
.plus-icon {
  font-size: 16px;
  line-height: 1;
  font-weight: 600;
  margin-top: -1px;
}

.quick-add-box {
  display: inline-flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--accent);
  border-radius: var(--radius-sm);
  padding: 0 6px 0 8px;
  height: 28px;
  box-shadow: 0 0 0 2px var(--accent-bg);
  position: relative;
  animation: popIn .15s ease-out;
}
@keyframes popIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
.quick-add-icon {
  font-size: 11px;
  color: var(--text-dim);
  margin-right: 4px;
}
.quick-add-input {
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 12px;
  outline: none;
  width: 210px;
}
.quick-add-input::placeholder {
  color: var(--text-dim);
  font-size: 11px;
}
.quick-add-close {
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 11px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 2px;
  line-height: 1;
  margin-left: 2px;
}
.quick-add-close:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.quick-suggest-pop {
  position: absolute;
  top: 32px;
  right: 0;
  width: 280px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 24px rgba(0, 0, 0, .45);
  z-index: 100;
  max-height: 240px;
  overflow-y: auto;
}
.suggest-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background .1s;
}
.suggest-item:last-child {
  border-bottom: none;
}
.suggest-item:hover, .suggest-item.active {
  background: var(--accent-bg);
  color: var(--accent);
}
.suggest-code {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  min-width: 52px;
}
.suggest-name {
  flex: 1;
  margin: 0 6px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.suggest-item:hover .suggest-name, .suggest-item.active .suggest-name {
  color: var(--accent);
}
.suggest-type {
  font-size: 11px;
  color: var(--text-dim);
  margin-right: 4px;
}
.suggest-tag {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 2px;
  background: var(--bg-hover);
  color: var(--text-dim);
}

/* 截图按钮 */
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; color: var(--text-dim);
  padding: 2px 6px; border-radius: 4px; opacity: .7;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }

/* 数量 / 成本 ± 调整 */
.modal-qty { display: flex; gap: 6px; align-items: center; }
.modal-qty .ui-input { flex: 1; min-width: 0; }

/* 弹窗底部按钮组 */
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.td-actions { display: inline-flex; align-items: center; gap: 8px; }
</style>