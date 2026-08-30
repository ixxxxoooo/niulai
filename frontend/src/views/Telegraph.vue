<template>
  <div class="telegraph-view">
    <!-- 顶部控制台卡片 -->
    <div class="card telegraph-header-card" ref="headerCard">
      <div class="th-top-row">
        <div class="th-title-group">
          <h1 class="page-title">7×24 实时财经电报</h1>
          <span class="th-subtitle">财联社首发 · 智能关联标的 · 毫秒级快讯</span>
        </div>

        <div class="th-controls-group">
          <!-- 实时时间与独立倒计时 -->
          <div class="th-live-status">
            <span class="live-pulse"></span>
            <span class="live-text">电报持续更新中</span>
            <span
              class="th-polling-badge"
              @click="refreshAll"
              :title="'点击立即刷新（当前 ' + intervalSec + ' 秒轮询）'"
            >
              <span class="ri-dot" :class="{ active: loading || isRefreshing }"></span>
              {{ countdown }}s
            </span>
            <!-- 5s / 10s 独立倒计时切换 -->
            <div class="th-interval-switcher" title="选择电报刷新频率">
              <button
                class="interval-btn"
                :class="{ active: intervalSec === 5 }"
                @click="setIntervalSec(5)"
              >5s</button>
              <button
                class="interval-btn"
                :class="{ active: intervalSec === 10 }"
                @click="setIntervalSec(10)"
              >10s</button>
            </div>
          </div>

          <!-- 桌面通知开关 -->
          <label class="toggle-control" title="有新电报时发送系统桌面通知">
            <input type="checkbox" v-model="notifyEnabled" @change="toggleNotification" />
            <span class="toggle-slider"></span>
            <span class="toggle-label">桌面通知</span>
          </label>

          <!-- 声音提醒开关 -->
          <label class="toggle-control" title="有重要加红电报时播放提示音">
            <input type="checkbox" v-model="audioEnabled" />
            <span class="toggle-slider"></span>
            <span class="toggle-label">声音提醒</span>
          </label>

          <!-- 截图按钮 -->
          <button class="btn-screenshot-custom" @click="captureElement(headerCard, '财经电报.png')" title="截图保存">
            <UiIcon name="screenshot" :size="15" />
          </button>
        </div>
      </div>

      <!-- 分类 Tab 栏与搜索 -->
      <div class="th-nav-row">
        <div class="th-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="th-tab-btn"
            :class="{ active: currentTab === tab.key, 'tab-red': tab.key === 'red' }"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="th-search-box">
          <UiIcon name="search" :size="14" class="search-icon" />
          <input
            type="text"
            v-model="searchQuery"
            placeholder="搜索电报关键词 / 股票代码..."
            class="th-search-input"
          />
          <button v-if="searchQuery" class="search-clear-btn" @click="searchQuery = ''">×</button>
        </div>
      </div>
    </div>

    <!-- 电报流主体卡片 -->
    <div class="card mt16 telegraph-feed-card">
      <!-- 首次加载态 -->
      <div v-if="loading && !items.length" class="empty feed-loading">
        <UiIcon name="refresh" :size="16" class="rotating" /> 正在连接 7×24 实时电报流…
      </div>

      <!-- 无数据 -->
      <div v-else-if="!filteredItems.length" class="empty feed-empty">
        暂无相关财经电报
      </div>

      <!-- 电报时间轴列表 -->
      <div v-else class="feed-timeline">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="feed-item"
          :class="{ 'item-red': item.is_red }"
        >
          <!-- 左侧时间与标识 -->
          <div class="item-time-col">
            <span class="item-time" :class="{ 'time-red': item.is_red }">{{ item.time || '-' }}</span>
            <span class="item-red-pill" v-if="item.is_red">重要</span>
            <div class="item-timeline-dot" :class="{ 'dot-red': item.is_red }"></div>
          </div>

          <!-- 右侧正文内容 -->
          <div class="item-content-col">
            <!-- 标题（若有） -->
            <div class="item-title" v-if="item.title" :class="{ 'title-red': item.is_red }">
              【{{ item.title }}】
            </div>

            <!-- 正文（含智能折叠） -->
            <div class="item-body">
              <span class="item-text">{{ getDisplayText(item) }}</span>
              <button
                v-if="isExpandable(item)"
                class="btn-expand-text"
                @click="toggleExpand(item.id)"
              >
                {{ expandedSet.has(item.id) ? '收起 ▴' : '展开全文 ▾' }}
              </button>
            </div>

            <!-- 关联板块 / 主题标签 -->
            <div class="item-tags-row" v-if="(item.subjects && item.subjects.length) || (item.stocks && item.stocks.length)">
              <!-- 关联股票 -->
              <a
                v-for="stk in (item.stocks || [])"
                :key="stk.code"
                class="stock-chip"
                @click.stop="openStock({ code: stk.code, name: stk.name }, { origin: '/telegraph', originLabel: '返回电报' })"
              >
                <span class="stk-name">{{ stk.name }}</span>
                <span class="stk-code">{{ stk.code }}</span>
                <span class="stk-pct" :class="pctClass(stk.change_pct)" v-if="stk.change_pct != null">
                  {{ fmtPct(stk.change_pct) }}
                </span>
              </a>

              <!-- 关联主题 -->
              <span v-for="sub in (item.subjects || [])" :key="sub" class="subject-tag">
                # {{ sub }}
              </span>
            </div>

            <!-- 底部来源与外链 -->
            <div class="item-footer">
              <span class="item-source-badge">{{ item.source || '财联社' }}</span>
              <span class="item-full-time">{{ item.full_time }}</span>
              <a
                v-if="item.share_url"
                :href="item.share_url"
                target="_blank"
                rel="noopener"
                class="item-link"
                title="查看原文"
              >
                原文 <UiIcon name="external" :size="11" />
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载更多历史电报 -->
      <div class="feed-footer" v-if="items.length >= 20">
        <button
          class="btn-load-more"
          :disabled="loadingMore"
          @click="loadMore"
        >
          <template v-if="loadingMore">
            <UiIcon name="refresh" :size="13" class="rotating" /> 正在加载历史电报…
          </template>
          <template v-else>
            点击加载更多历史电报 ▾
          </template>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 7x24 实时财经电报视图（财联社主源 + 东方财富快讯备源）
 * @author ygw
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { api } from '../api.js'
import { fmtPct, pctClass } from '../utils.js'
import { usePageTab } from '../composables/usePageTab.js'
import { openStock } from '../composables/useStockMeta.js'
import { captureElement } from '../composables/useScreenshot.js'
import { showToast } from '../composables/useToast.js'
import { requestTelegraphNotifyPermission, playTelegraphBeep, sendTelegraphNotification } from '../composables/useTelegraphNotify.js'
import UiIcon from '../components/ui/UiIcon.vue'

const headerCard = ref(null)
const items = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const isRefreshing = ref(false)
const searchQuery = ref('')
const expandedSet = ref(new Set())

// 独立轮询倒计时：默认 5 秒，支持 5s / 10s
const intervalSec = ref(parseInt(localStorage.getItem('niulai_telegraph_interval'), 10) || 5)
const countdown = ref(intervalSec.value)
let pollTimer = null

function setIntervalSec(sec) {
  intervalSec.value = sec
  countdown.value = sec
  try {
    localStorage.setItem('niulai_telegraph_interval', String(sec))
    showToast(`电报自动刷新频率已设为 ${sec} 秒`)
  } catch (e) { /* ignore */ }
}

const notifyEnabled = ref(localStorage.getItem('niulai_telegraph_notify') === '1')
const audioEnabled = ref(localStorage.getItem('niulai_telegraph_audio') === '1')

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'red', label: '加红' },
  { key: 'company', label: '公司' },
  { key: 'watch', label: '看盘' },
  { key: 'hk_us', label: '港美股' },
  { key: 'fund', label: '基金' },
]

const currentTab = usePageTab('telegraph_tab', 'all')

function switchTab(k) {
  currentTab.value = k
}

const filteredItems = computed(() => {
  let list = items.value || []
  if (currentTab.value === 'red') {
    list = list.filter(it => it.is_red)
  }
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(it => {
    return (
      (it.title && it.title.toLowerCase().includes(q)) ||
      (it.content && it.content.toLowerCase().includes(q)) ||
      (it.subjects && it.subjects.some(s => s.toLowerCase().includes(q))) ||
      (it.stocks && it.stocks.some(st => st.name.toLowerCase().includes(q) || st.code.includes(q)))
    )
  })
})

function isExpandable(item) {
  const text = item.content || ''
  return text.length > 180
}

function getDisplayText(item) {
  const text = item.content || ''
  if (!isExpandable(item) || expandedSet.value.has(item.id)) {
    return text
  }
  return text.slice(0, 160) + '…'
}

function toggleExpand(id) {
  const set = new Set(expandedSet.value)
  if (set.has(id)) {
    set.delete(id)
  } else {
    set.add(id)
  }
  expandedSet.value = set
}

// 桌面通知开关切换
async function toggleNotification() {
  if (notifyEnabled.value) {
    const ok = await requestTelegraphNotifyPermission()
    if (ok) {
      localStorage.setItem('niulai_telegraph_notify', '1')
      showToast('已开启 7×24 实时电报全局后台桌面通知')
    } else {
      notifyEnabled.value = false
      localStorage.setItem('niulai_telegraph_notify', '0')
      showToast('未获得系统桌面通知权限')
    }
  } else {
    localStorage.setItem('niulai_telegraph_notify', '0')
    showToast('已关闭电报桌面通知')
  }
}

watch(audioEnabled, (v) => {
  try {
    localStorage.setItem('niulai_telegraph_audio', v ? '1' : '0')
    showToast(v ? '已开启加红电报全局后台声音提醒' : '已关闭声音提醒')
  } catch (e) { /* ignore */ }
})

let lastSeenId = null

async function loadData(isPolling = false) {
  if (!isPolling) loading.value = true
  else isRefreshing.value = true
  try {
    const cat = currentTab.value === 'red' ? 'red' : currentTab.value
    const res = await api.telegraph(cat, null, 30)
    const newItems = res?.items || []

    if (newItems.length) {
      lastSeenId = newItems[0].id
    }
    items.value = newItems
  } catch (e) {
    console.error('加载电报失败', e)
  } finally {
    loading.value = false
    isRefreshing.value = false
  }
}

async function loadMore() {
  if (!items.value.length || loadingMore.value) return
  const lastTime = items.value[items.value.length - 1]?.timestamp
  if (!lastTime) return
  loadingMore.value = true
  try {
    const cat = currentTab.value === 'red' ? 'red' : currentTab.value
    const res = await api.telegraph(cat, lastTime, 30)
    const moreItems = res?.items || []
    if (moreItems.length) {
      const map = new Map()
      items.value.forEach(it => map.set(it.id, it))
      moreItems.forEach(it => map.set(it.id, it))
      items.value = Array.from(map.values())
    }
  } catch (e) {
    console.error('加载更多历史电报失败', e)
  } finally {
    loadingMore.value = false
  }
}

function refreshAll() {
  countdown.value = intervalSec.value
  loadData(false)
}

watch(currentTab, () => {
  items.value = []
  lastSeenId = null
  countdown.value = intervalSec.value
  loadData(false)
})

function startTimer() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(() => {
    if (document.hidden) return
    if (countdown.value > 1) {
      countdown.value--
    } else {
      countdown.value = intervalSec.value
      loadData(true)
    }
  }, 1000)
}

function onVisibilityChange() {
  if (!document.hidden) {
    countdown.value = intervalSec.value
    loadData(true)
  }
}

onMounted(() => {
  loadData(false)
  startTimer()
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<style scoped>
.telegraph-view {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* 顶部控制台卡片 */
.telegraph-header-card {
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.th-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.th-title-group {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.page-title {
  font-size: 20px;
  font-weight: 800;
  margin: 0;
}
.th-subtitle {
  font-size: 12px;
  color: var(--text-dim);
}

.th-controls-group {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

/* 实时脉冲 */
.th-live-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-dim);
}
.live-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--up);
  box-shadow: 0 0 0 0 rgba(240, 68, 68, 0.7);
  animation: pulse-ring 1.8s infinite cubic-bezier(0.66, 0, 0, 1);
}
@keyframes pulse-ring {
  0% { box-shadow: 0 0 0 0 rgba(240, 68, 68, 0.7); }
  70% { box-shadow: 0 0 0 8px rgba(240, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(240, 68, 68, 0); }
}

.th-polling-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: var(--kv-bg);
  border: 1px solid var(--border);
  font-size: 11px;
  font-weight: 600;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  user-select: none;
  transition: all 0.15s;
}
.th-polling-badge:hover {
  border-color: var(--accent);
  color: var(--accent);
}

/* 5s / 10s 独立倒计时切换器 */
.th-interval-switcher {
  display: inline-flex;
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 1px;
  gap: 2px;
}
.interval-btn {
  background: none;
  border: none;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.15s;
}
.interval-btn:hover {
  color: var(--text);
}
.interval-btn.active {
  background: var(--accent);
  color: #fff;
}

/* 截图按钮（亮暗主题高对比） */
.btn-screenshot-custom {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--kv-bg);
  border: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-screenshot-custom:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-bg);
}

/* 开关控件 */
.toggle-control {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  cursor: pointer;
  user-select: none;
}
.toggle-control input { display: none; }
.toggle-slider {
  width: 28px;
  height: 16px;
  background: var(--border);
  border-radius: 99px;
  position: relative;
  transition: background 0.2s;
}
.toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}
.toggle-control input:checked + .toggle-slider {
  background: var(--accent);
}
.toggle-control input:checked + .toggle-slider::after {
  transform: translateX(12px);
}
.toggle-label {
  color: var(--text);
  font-weight: 500;
}

/* 导航栏与搜索 */
.th-nav-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
  gap: 12px;
}

.th-tabs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}
.th-tab-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: var(--kv-bg);
  color: var(--text-dim);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.15s;
}
.th-tab-btn:hover {
  background: var(--bg-hover);
  color: var(--text);
}
.th-tab-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}
.th-tab-btn.tab-red.active {
  background: var(--up);
  border-color: var(--up);
}

.th-search-box {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 240px;
}
.search-icon {
  position: absolute;
  left: 10px;
  color: var(--text);
  opacity: 0.6;
}
.th-search-input {
  width: 100%;
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  padding: 6px 28px 6px 30px;
  color: var(--text);
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}
.th-search-input:focus {
  border-color: var(--accent);
}
.search-clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 14px;
  cursor: pointer;
}

/* 电报流主体卡片 */
.telegraph-feed-card {
  padding: 16px 20px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.feed-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
}

.feed-item {
  display: flex;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid var(--border);
  position: relative;
  transition: background 0.15s;
}
.feed-item:last-child {
  border-bottom: none;
}
.feed-item:hover {
  background: var(--bg-hover);
  margin: 0 -10px;
  padding: 14px 10px;
  border-radius: 6px;
}

/* 时间列 */
.item-time-col {
  flex: 0 0 76px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  position: relative;
}
.item-time {
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text-dim);
}
.item-time.time-red {
  color: var(--up);
  font-weight: 800;
}
.item-red-pill {
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: var(--up);
  padding: 0 5px;
  border-radius: 3px;
  line-height: 16px;
}

/* 内容列 */
.item-content-col {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
}
.item-title.title-red {
  color: var(--up);
}

.item-body {
  font-size: 13px;
  color: var(--text);
  line-height: 1.6;
  word-break: break-word;
}
.item-text {
  white-space: pre-wrap;
}

.btn-expand-text {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 0 4px;
  margin-left: 4px;
}
.btn-expand-text:hover {
  text-decoration: underline;
}

/* 标签行 */
.item-tags-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.stock-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: var(--kv-bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.stock-chip:hover {
  border-color: var(--accent);
  background: var(--accent-bg);
}
.stk-name { font-weight: 600; color: var(--text); }
.stk-code { font-size: 11px; color: var(--text-dim); font-variant-numeric: tabular-nums; }
.stk-pct { font-weight: 700; font-variant-numeric: tabular-nums; font-size: 11px; }

.subject-tag {
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 2px 6px;
  border-radius: 3px;
}

/* 底部来源 */
.item-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 4px;
}
.item-source-badge {
  background: var(--kv-bg);
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid var(--border);
  font-weight: 500;
  color: var(--text);
}
.item-full-time {
  font-variant-numeric: tabular-nums;
}
.item-link {
  color: var(--text-dim);
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
.item-link:hover {
  color: var(--accent);
}

/* 加载更多 */
.feed-footer {
  display: flex;
  justify-content: center;
  padding: 16px 0 6px;
}
.btn-load-more {
  background: var(--kv-bg);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  padding: 8px 24px;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all 0.15s;
}
.btn-load-more:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-bg);
}
</style>
