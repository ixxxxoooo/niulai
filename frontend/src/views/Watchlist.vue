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
            v-for="g in watchState.groups"
            :key="g.id"
            class="group-pill"
            :class="{ active: currentGroupId === g.id }"
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
        <div class="group-bar-actions">
          <UiButton size="sm" variant="subtle" @click="showGroupManage = true">
            ⚙ 分组管理
          </UiButton>
        </div>
      </div>

      <div class="card mt12" v-if="watchStocks.length" ref="stockCard">
        <div class="card-title">
          <span>{{ currentGroupName }} · 个股（{{ watchStocks.length }}）</span>
          <button class="btn-screenshot" @click="captureElement(stockCard, `${currentGroupName}个股.png`)" title="截图">
            <UiIcon name="screenshot" :size="14" />
          </button>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>名称</th><th>代码</th>
                <th class="sortable" :class="{ sorted: tsWS.sortKey === 'price' }" @click="tsWS.toggleSort('price')">现价</th>
                <th class="sortable" :class="{ sorted: tsWS.sortKey === 'change_pct' }" @click="tsWS.toggleSort('change_pct')">涨跌幅</th>
                <th class="sortable" :class="{ sorted: tsWS.sortKey === 'zhangsu' }" @click="tsWS.toggleSort('zhangsu')">涨速</th>
                <th class="sortable" :class="{ sorted: tsWS.sortKey === 'amount' }" @click="tsWS.toggleSort('amount')">成交额</th>
                <th class="sortable" :class="{ sorted: tsWS.sortKey === 'main_inflow' }" @click="tsWS.toggleSort('main_inflow')">主力净流入</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in tsWS.sorted" :key="s.code" @click="openFromList(s, tsWS.sorted, '返回自选')">
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
      </div>

      <div class="card mt12" v-if="watchEtfs.length" ref="etfCard">
        <div class="card-title">
          <span>{{ currentGroupName }} · ETF（{{ watchEtfs.length }}）</span>
          <button class="btn-screenshot" @click="captureElement(etfCard, `${currentGroupName}ETF.png`)" title="截图">
            <UiIcon name="screenshot" :size="14" />
          </button>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>名称</th><th>代码</th>
                <th class="sortable" :class="{ sorted: tsWE.sortKey === 'price' }" @click="tsWE.toggleSort('price')">现价</th>
                <th class="sortable" :class="{ sorted: tsWE.sortKey === 'change_pct' }" @click="tsWE.toggleSort('change_pct')">涨跌幅</th>
                <th class="sortable" :class="{ sorted: tsWE.sortKey === 'zhangsu' }" @click="tsWE.toggleSort('zhangsu')">涨速</th>
                <th class="sortable" :class="{ sorted: tsWE.sortKey === 'amount' }" @click="tsWE.toggleSort('amount')">成交额</th>
                <th class="sortable" :class="{ sorted: tsWE.sortKey === 'main_inflow' }" @click="tsWE.toggleSort('main_inflow')">主力净流入</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in tsWE.sorted" :key="s.code" @click="openFromList(s, tsWE.sorted, '返回自选')">
                <td class="stock-name">
                  <MiniTrend :code="s.code" :name="s.name">
                    <span class="name-cell"><BoardBadges :row="s" />{{ s.name }}<span v-if="s.shares" class="hold-tag">持仓</span></span>
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
      </div>

      <div class="card mt12" v-if="!watchRows.length">
        <div class="empty">
          <div class="empty-title">当前分组「{{ currentGroupName }}」暂无自选股</div>
          <div class="empty-desc">可点击「分组管理」导入热门预设，或在其他页面搜索添加。</div>
          <div class="empty-actions mt12">
            <UiButton size="sm" variant="primary" @click="showGroupManage = true">管理分组 / 导入预设</UiButton>
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
import { ref, computed, reactive } from 'vue'
import { api } from '../api.js'
import { fmtAmount, fmtPrice, fmtPct, pctClass } from '../utils.js'
import { usePolling } from '../composables/usePolling.js'
import { useTableSort } from '../composables/useTableSort.js'
import { usePageTab } from '../composables/usePageTab.js'
import { loadWatchlist, removeWatch, watchState, setCurrentGroup } from '../composables/useWatchlist.js'
import { applyListFilter } from '../composables/useListFilter.js'
import { openStock } from '../composables/useStockMeta.js'
import { captureElement } from '../composables/useScreenshot.js'
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
  if (/光通信|CPO/i.test(name)) return '📡'
  if (/PCB|覆铜/i.test(name)) return '🖨️'
  if (/封装|Chiplet|HBM/i.test(name)) return '🧩'
  if (/存储|内存/i.test(name)) return '💾'
  if (/机器人|具身/i.test(name)) return '🤖'
  if (/低空|eVTOL|飞行/i.test(name)) return '🚁'
  if (/半导体|芯片|设备/i.test(name)) return '🛡️'
  if (/AI|硬件|服务器|算力/i.test(name)) return '⚡'
  if (/消费电子|苹果|华为/i.test(name)) return '📱'
  if (/固态电池|电池|锂电/i.test(name)) return '🔋'
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

// 计算某个分组内全部股票的平均涨跌幅
function getGroupAvgPct(g) {
  const codes = g?.codes || []
  if (!codes.length) return null
  let total = 0
  let count = 0
  for (const c of codes) {
    const q = quotesMap.value[c]
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

const filtered = computed(() => withPos(applyListFilter(list.value)))

/** 自选 tab：只展示真实自选（持仓股默认已在自选里，带「持仓」标记） */
const watchRows = computed(() => filtered.value.filter(s => watchState.codes.includes(s.code)))
const watchStocks = computed(() => watchRows.value.filter(s => !isEtf(s)))
const watchEtfs = computed(() => watchRows.value.filter(s => isEtf(s)))

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

const tsWS = useTableSort(watchStocks, 'watchlist_stocks')
const tsWE = useTableSort(watchEtfs, 'watchlist_etfs')
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
  if (!confirm(`确定清空 ${f.name} 的持仓？`)) return
  await api.positionDelete(f.code)
  form.value = null
  await load()
}

async function clearOne(s) {
  if (!confirm(`确定清空 ${s.name}（${s.code}）的持仓？`)) return
  await api.positionDelete(s.code)
  await load()
}

async function deleteSnapshot(r) {
  if (!confirm(`确定删除该收益记录（${r.ts} · ${kindLabel(r.kind)}）？`)) return
  try {
    await api.positionSnapshotDelete(r.id)
    await loadSnapshots()
  } catch (e) { alert('删除失败：' + e.message) }
}

async function clearSnapshots() {
  if (!snapshots.length) return
  if (!confirm('确定清空全部收益记录？此操作不可恢复。')) return
  try {
    await api.positionSnapshotsClear()
    snapshots.value = []
  } catch (e) { alert('清空失败：' + e.message) }
}

async function removeStock(s) {
  const code = typeof s === 'string' ? s : s.code
  const sName = typeof s === 'object' ? s.name : code
  const curGid = currentGroupId.value
  if (curGid !== null) {
    const curGroup = watchState.groups.find(g => g.id === curGid)
    const gName = curGroup ? curGroup.name : '当前分组'
    if (!confirm(`确定将【${sName || code}】移出「${gName}」分组吗？\n该股票仍会保留在自选「全部」及其他所属分组中。`)) return
    await removeWatch(code, curGid)
  } else {
    const inGroups = stockGroupsMap.value[code] || []
    let promptMsg = `确定从自选股中删除【${sName || code}】吗？`
    if (inGroups.length > 0) {
      promptMsg += `\n该股票当前归属于以下分组：【${inGroups.join('】、【')}】。\n删除后将同时从所有分组及持仓中彻底移除。`
    }
    if (!confirm(promptMsg)) return
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
    if (stockOnly.length) {
      const res = await api.batchStockRisk(stockOnly)
      riskMap.value = res || {}
    }
  } catch (e) { /* ignore */ }
}

usePolling(load, 3000)
</script>

<style scoped>
.name-cell { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.card-title-sub { font-size: 12px; color: var(--text-dim); font-weight: 400; }

/* 自选分组导航条 */
.group-bar-container {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 10px 14px;
}
.group-pills {
  display: flex; flex-wrap: wrap; gap: 8px 10px; align-items: center; flex: 1; min-width: 0;
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

.group-bar-actions { flex-shrink: 0; padding-top: 2px; }
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

/* 截图按钮 */
.btn-screenshot {
  border: none; background: transparent; cursor: pointer; color: var(--text-dim);
  padding: 2px 6px; border-radius: 4px; opacity: .7; margin-left: auto;
}
.btn-screenshot:hover { opacity: 1; background: var(--bg-hover); }

/* 数量 / 成本 ± 调整 */
.modal-qty { display: flex; gap: 6px; align-items: center; }
.modal-qty .ui-input { flex: 1; min-width: 0; }

/* 弹窗底部按钮组 */
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.td-actions { display: inline-flex; align-items: center; gap: 8px; }
</style>