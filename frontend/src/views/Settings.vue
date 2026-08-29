<template>
  <div>
    <div class="page-title">设置</div>

    <div class="settings-nav">
      <div class="sn-item" :class="{ active: settingsTab === 'general' }" @click="settingsTab = 'general'">通用</div>
      <div class="sn-item" :class="{ active: settingsTab === 'data' }" @click="settingsTab = 'data'">数据</div>
      <div class="sn-item" :class="{ active: settingsTab === 'ai' }" @click="settingsTab = 'ai'">AI 与通知</div>
      <div class="sn-item" :class="{ active: settingsTab === 'logs' }" @click="settingsTab = 'logs'">日志</div>
    </div>

    <!-- ── 通用：主题 / 刷新 / 图表 / 过滤 / 关于 ── -->
    <div v-if="settingsTab === 'general'" class="settings-grid">
    <div class="card">
      <div class="card-title">外观与过滤</div>
      <div class="setting-row">
        <span class="setting-label">颜色主题</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: themeMode === 'dark' }" @click="setTheme('dark')">深色</div>
          <div class="tab" :class="{ active: themeMode === 'light' }" @click="setTheme('light')">浅色</div>
          <div class="tab" :class="{ active: themeMode === 'system' }" @click="setTheme('system')">跟随系统</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">导航布局</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: navMode === 'top' }" @click="setNavMode('top')">顶部导航</div>
          <div class="tab" :class="{ active: navMode === 'side' }" @click="setNavMode('side')">左侧导航</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">过滤标的</span>
        <div class="setting-control" style="flex-wrap:wrap">
          <span class="filter-opt" :class="{ on: hideKcb }">
            <UiCheckbox :checked="hideKcb" @change="toggleHide('hideKcb')"> 科创板</UiCheckbox></span>
          <span class="filter-opt" :class="{ on: hideCyb }">
            <UiCheckbox :checked="hideCyb" @change="toggleHide('hideCyb')"> 创业板</UiCheckbox></span>
          <span class="filter-opt" :class="{ on: hideSt }">
            <UiCheckbox :checked="hideSt" @change="toggleHide('hideSt')"> ST</UiCheckbox></span>
          <span class="filter-opt" :class="{ on: hideBse }">
            <UiCheckbox :checked="hideBse" @change="toggleHide('hideBse')"> 北交所</UiCheckbox></span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">数据刷新</div>
      <div class="setting-row">
        <span class="setting-label">交易时段刷新间隔</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: refreshInterval === 3 }" @click="setRefresh(3)">3秒</div>
          <div class="tab" :class="{ active: refreshInterval === 5 }" @click="setRefresh(5)">5秒</div>
          <div class="tab" :class="{ active: refreshInterval === 10 }" @click="setRefresh(10)">10秒</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">非交易时段刷新间隔</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: offInterval === 30000 }" @click="setOffInterval(30000)">30秒</div>
          <div class="tab" :class="{ active: offInterval === 300000 }" @click="setOffInterval(300000)">5分钟</div>
          <div class="tab" :class="{ active: offInterval === 600000 }" @click="setOffInterval(600000)">10分钟</div>
          <div class="tab" :class="{ active: offInterval === 1200000 }" @click="setOffInterval(1200000)">20分钟</div>
          <div class="tab" :class="{ active: offInterval === 1800000 }" @click="setOffInterval(1800000)">30分钟</div>
          <div class="tab" :class="{ active: offInterval === 3600000 }" @click="setOffInterval(3600000)">1小时</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">图表显示</div>
      <div class="setting-row">
        <span class="setting-label">板块资金 TOP N</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: chartTopN === 15 }" @click="setChartTopN(15)">15</div>
          <div class="tab" :class="{ active: chartTopN === 20 }" @click="setChartTopN(20)">20</div>
          <div class="tab" :class="{ active: chartTopN === 30 }" @click="setChartTopN(30)">30</div>
          <div class="tab" :class="{ active: chartTopN === 50 }" @click="setChartTopN(50)">50</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">分时坐标</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: trendYScale === 'normal' }" @click="setTrendYScale('normal')">自适应</div>
          <div class="tab" :class="{ active: trendYScale === 'fill' }" @click="setTrendYScale('fill')">满占</div>
          <div class="tab" :class="{ active: trendYScale === 'limit' }" @click="setTrendYScale('limit')">涨停板</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">K线坐标</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: klineYScale === 'auto' }" @click="setKlineYScale('auto')">自适应</div>
          <div class="tab" :class="{ active: klineYScale === 'fixed' }" @click="setKlineYScale('fixed')">固定对称</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">关于</div>
      <div class="setting-row">
        <span class="setting-label">版本</span>
        <span class="setting-value">v1.1.0</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">数据来源</span>
        <span class="setting-value">东方财富 / 腾讯 / 同花顺 / TickFlow 免费（K线兜底）</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">声明</span>
        <span class="setting-value">仅供个人学习，不构成投资建议</span>
      </div>
    </div>
    </div>

    <!-- ── 数据：备份 / 同步 / 游资榜单 ── -->
    <div v-if="settingsTab === 'data'">
    <div class="card">
      <div class="card-title">数据备份（JSON · 用于 iCloud 多设备同步）</div>
      <div class="setting-row">
        <span class="setting-label">备份内容</span>
        <span class="setting-value">自选 · 持仓 · 监控 · 设置 · 流水 · 游资 · 选股记录 · AI历史</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">导出自选股（旧格式）</span>
        <UiButton variant="subtle" @click="exportWatch">导出代码列表</UiButton>
      </div>
      <div class="setting-row">
        <span class="setting-label">完整导出</span>
        <UiButton variant="subtle" @click="exportBackup" :disabled="backupBusy">{{ backupBusy ? '导出中…' : '导出全部数据 JSON' }}</UiButton>
      </div>
      <div class="setting-row">
        <span class="setting-label">完整导入</span>
        <UiInput type="file" accept=".json" @change="importBackupFile" :disabled="backupBusy" style="font-size: 12px;" />
      </div>
      <div class="setting-row">
        <span class="setting-label">导入说明</span>
        <span class="setting-value">完整导入会<strong>覆盖</strong>本机对应的自选/持仓/监控/设置等数据，建议先导出一份备份。</span>
      </div>
    </div>

    <div class="card mt16">
      <div class="card-title">数据同步（写入本地标签，详情页直接用）</div>
      <div class="setting-row">
        <span class="setting-label">本地股票数</span>
        <span class="setting-value">{{ stockMeta.count ?? '-' }} 只 · 更新于 {{ stockMeta.updated_at || '-' }}</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">概念标签上次同步</span>
        <span class="setting-value">{{ stockMeta.lastConceptSyncAt || '-' }}</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">自动同步间隔</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: autoSyncHours === 0 }" @click="setAutoSync(0)">关闭</div>
          <div class="tab" :class="{ active: autoSyncHours === 6 }" @click="setAutoSync(6)">6小时</div>
          <div class="tab" :class="{ active: autoSyncHours === 12 }" @click="setAutoSync(12)">12小时</div>
          <div class="tab" :class="{ active: autoSyncHours === 24 }" @click="setAutoSync(24)">24小时</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">同步全 A + ETF 名称/行业</span>
        <UiButton variant="subtle" :disabled="!!syncing" @click="resync('stocks')">{{ syncing === 'stocks' ? '同步中…' : '立即同步' }}</UiButton>
      </div>
      <div class="setting-row">
        <span class="setting-label">同步概念标签（按板块成分，较慢）</span>
        <UiButton variant="subtle" :disabled="!!syncing" @click="resync('concepts')">{{ syncing === 'concepts' ? '同步中…' : '同步概念' }}</UiButton>
      </div>
      <div class="setting-row">
        <span class="setting-label">全部同步</span>
        <UiButton variant="subtle" :disabled="!!syncing" @click="resync('all')">{{ syncing === 'all' ? '同步中…' : '名称+行业+概念' }}</UiButton>
      </div>
      <div class="setting-row" v-if="syncing || syncMsg">
        <span class="setting-label">同步进度</span>
        <div class="progress-wrap">
          <div class="progress"><i :style="{ width: syncPct + '%' }"></i></div>
          <div class="progress-msg">{{ syncMsg || '准备中…' }} · {{ syncPct }}%</div>
        </div>
      </div>
    </div>
    </div>

    <!-- ── 日志 ── -->
    <div v-if="settingsTab === 'logs'">
    <div class="card">
      <div class="card-title">
        <span>运行日志（便于定位慢接口）</span>
        <div class="tabs mini-tabs">
          <div class="tab" :class="{ active: logTab === 'api' }" @click="logTab = 'api'; loadLogs()">接口耗时</div>
          <div class="tab" :class="{ active: logTab === 'ds' }" @click="logTab = 'ds'; loadLogs()">数据源</div>
          <div class="tab" :class="{ active: logTab === 'act' }" @click="logTab = 'act'; loadLogs()">页面操作</div>
        </div>
      </div>
      <div class="table-wrap" style="max-height: 360px; overflow-y: auto;">
        <table class="data-table" v-if="logTab === 'api'">
          <thead><tr><th>时间</th><th>接口</th><th>状态</th><th>耗时</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in apiLogs" :key="i">
              <td>{{ r.ts }}</td>
              <td>{{ r.method }} {{ r.path }}{{ r.query ? '?' + r.query : '' }}</td>
              <td>{{ r.status }}</td>
              <td :class="r.duration_ms > 1000 ? 'up' : r.duration_ms > 400 ? 'flat' : ''">{{ Number(r.duration_ms).toFixed(0) }}ms</td>
            </tr>
            <tr v-if="!apiLogs.length"><td colspan="4" class="empty">暂无记录</td></tr>
          </tbody>
        </table>
        <table class="data-table" v-else-if="logTab === 'ds'">
          <thead><tr><th>时间</th><th>源</th><th>节点</th><th>路径</th><th>结果</th><th>耗时</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in dsLogs" :key="i">
              <td>{{ r.ts }}</td>
              <td>{{ r.source }}</td>
              <td>{{ r.host }}</td>
              <td>{{ r.path }}</td>
              <td :class="r.ok ? 'up' : 'down'">{{ r.ok ? 'OK' : '失败' }}</td>
              <td>{{ Number(r.duration_ms).toFixed(0) }}ms</td>
            </tr>
            <tr v-if="!dsLogs.length"><td colspan="6" class="empty">暂无记录</td></tr>
          </tbody>
        </table>
        <table class="data-table" v-else>
          <thead><tr><th>时间</th><th>操作</th><th>目标</th><th>详情</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in actLogs" :key="i">
              <td>{{ r.ts }}</td>
              <td>{{ r.action }}</td>
              <td>{{ r.target }}</td>
              <td>{{ r.detail }}</td>
            </tr>
            <tr v-if="!actLogs.length"><td colspan="4" class="empty">暂无记录</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    </div>

    <!-- ── AI 与通知：AI 分析 / 飞书 / 异动监控 ── -->
    <div v-if="settingsTab === 'ai'">
    <div class="card">
      <div class="card-title">AI 分析（个股分时/K线智能解读）</div>
      <div class="setting-row">
        <span class="setting-label">启用 AI 分析</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: aiEnabled }" @click="setAi('aiEnabled', true)">开启</div>
          <div class="tab" :class="{ active: !aiEnabled }" @click="setAi('aiEnabled', false)">关闭</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">API Base URL</span>
        <UiInput v-model="aiBaseUrl" placeholder="https://api.deepseek.com" style="width:360px;max-width:60vw" @change="setAi('aiBaseUrl', aiBaseUrl)" />
      </div>
      <div class="setting-row">
        <span class="setting-label">API Key</span>
        <UiInput type="password" v-model="aiApiKey" placeholder="sk-..." style="width:360px;max-width:60vw" @change="setAi('aiApiKey', aiApiKey)" />
      </div>
      <div class="setting-row">
        <span class="setting-label">模型</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: aiModel === 'deepseek-chat' }" @click="setAi('aiModel', 'deepseek-chat')">DeepSeek Chat</div>
          <div class="tab" :class="{ active: aiModel === 'deepseek-reasoner' }" @click="setAi('aiModel', 'deepseek-reasoner')">DeepSeek R1</div>
          <div class="tab" :class="{ active: aiModel === 'deepseek-v4-flash' }" @click="setAi('aiModel', 'deepseek-v4-flash')">V4 Flash</div>
          <div class="tab" :class="{ active: aiModel === 'gpt-4o' }" @click="setAi('aiModel', 'gpt-4o')">GPT-4o</div>
          <div class="tab" :class="{ active: showCustomModel || !['deepseek-chat','deepseek-reasoner','deepseek-v4-flash','gpt-4o'].includes(aiModel) }" @click="showCustomModel = true">自定义</div>
        </div>
      </div>
      <div class="setting-row" v-if="showCustomModel || !['deepseek-chat','deepseek-reasoner','deepseek-v4-flash','gpt-4o'].includes(aiModel)">
        <span class="setting-label">自定义模型名</span>
        <UiInput v-model="customModelName" placeholder="model-name" style="width:360px;max-width:60vw" @change="setAi('aiModel', customModelName)" />
      </div>
      <div class="setting-row">
        <span class="setting-label" style="font-size:12px; color:var(--text-dim)">说明：推理类模型（R1 / V4 Flash）会先「思考」再输出，耗时更长；盘中分析建议优先用 DeepSeek Chat。API Key 保存在本机后端，分析经 `/api/ai/chat` 代理。</span>
      </div>
    </div>

    <div class="card mt16">
      <div class="card-title">东财数据源</div>
      <div class="setting-row">
        <span class="setting-label">东财 Cookie（ct / ut）</span>
        <UiInput type="text" v-model="eastmoneyCookie" placeholder="可粘贴完整 Cookie，自动识别 ct / ut" style="width:440px;max-width:70vw" @change="setAi('eastmoneyCookie', eastmoneyCookie)" />
      </div>
      <div class="setting-row">
        <span class="setting-label" style="font-size:12px; color:var(--text-dim)">说明：东财数据中心对资金流历史等接口有风控，需携带浏览器 Cookie 中的 ct 与 ut 才能返回完整数据。支持直接粘贴浏览器复制的完整 Cookie（含 ct=...; ut=...），系统会自动提取 ct / ut 两项。获取方式：浏览器打开 data.eastmoney.com 个股资金流向页 → F12 → Network → 任意请求的 Cookie 中复制整串填入。过期后需更新。</span>
      </div>
    </div>

    <div class="card mt16">
      <div class="card-title">飞书通知</div>
      <div class="setting-row">
        <span class="setting-label">启用飞书推送</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: feishuEnabled }" @click="setFeishu('feishu_enabled', '1')">开启</div>
          <div class="tab" :class="{ active: !feishuEnabled }" @click="setFeishu('feishu_enabled', '0')">关闭</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">Webhook URL</span>
        <UiInput v-model="feishuWebhook" placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/..." style="width:360px;max-width:60vw" @change="setFeishu('feishu_webhook', feishuWebhook)" />
      </div>
      <div class="setting-row">
        <span class="setting-label">如何配置</span>
        <div class="setting-control">
          <a class="source-link" href="https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot" target="_blank" rel="noopener">官方文档：群聊添加自定义机器人 <UiIcon name="external" :size="12" /></a>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">测试推送</span>
        <UiButton variant="subtle" :disabled="feishuTesting" @click="testFeishu">{{ feishuTesting ? '发送中…' : '发送测试卡片' }}</UiButton>
        <span v-if="feishuTestMsg" style="margin-left:12px;font-size:12px;" :style="{ color: feishuTestOk ? 'var(--up, #22c55e)' : 'var(--down, #ef4444)' }">{{ feishuTestMsg }}</span>
      </div>
      <div class="setting-row">
        <span class="setting-label" style="font-size:12px;color:var(--text-dim)">配置步骤：飞书群 → 设置 → 群机器人 → 添加自定义机器人（Webhook 机器人），复制 Webhook 地址填入上方。触发监控告警和盘后选股时，将自动推送飞书卡片消息。</span>
      </div>
    </div>

    <div class="card mt16">
      <div class="card-title">持仓异动监控</div>
      <div class="setting-row">
        <span class="setting-label">启用异动监控</span>
        <div class="setting-control">
          <div class="tab" :class="{ active: changesMonitorEnabled }" @click="setChangesMon('changes_monitor_enabled', '1')">开启</div>
          <div class="tab" :class="{ active: !changesMonitorEnabled }" @click="setChangesMon('changes_monitor_enabled', '0')">关闭</div>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label">监控异动类型</span>
        <div class="setting-control" style="flex-wrap:wrap">
          <span class="filter-opt" :class="{ on: watchTypes.includes(t.code) }" v-for="t in changeTypeOptions" :key="t.code">
            <UiCheckbox :checked="watchTypes.includes(t.code)" @change="toggleChangeType(t.code)"> {{ t.label }}</UiCheckbox></span>
        </div>
      </div>
      <div class="setting-row">
        <span class="setting-label" style="font-size:12px;color:var(--text-dim)">
          开启后，系统每 8 秒检查一次持仓股异动。命中时弹出桌面通知，飞书同步推送。
        </span>
      </div>
    </div>
    </div>

    <div v-if="settingsTab === 'general'" class="card mt16">
      <div class="card-title">关于</div>
      <div class="setting-row">
        <span class="setting-label">版本</span>
        <span class="setting-value">v1.1.0</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">数据来源</span>
        <span class="setting-value">东方财富 / 腾讯 / 同花顺 / TickFlow 免费（K线兜底）</span>
      </div>
      <div class="setting-row">
        <span class="setting-label">声明</span>
        <span class="setting-value">仅供个人学习，不构成投资建议</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// @author ygw
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api.js'
import { settingsState, saveSetting, loadSettings, applyThemeMode } from '../composables/useSettings.js'
import { watchState, clearWatch, importWatch } from '../composables/useWatchlist.js'
import { usePageTab } from '../composables/usePageTab.js'
import { showConfirm } from '../composables/useConfirm.js'
import { showToast } from '../composables/useToast.js'

const themeMode = ref('dark')
const navMode = ref('top')
const settingsTab = usePageTab('settings', 'general')
const refreshInterval = ref(5)
const offInterval = ref(30000)
const chartTopN = ref(20)
const trendYScale = ref('normal')
const klineYScale = ref('auto')
const hideKcb = ref(false)
const hideCyb = ref(false)
const hideSt = ref(false)
const hideBse = ref(false)
const autoSyncHours = ref(0)
const aiEnabled = ref(false)
const aiApiKey = ref('')
const aiModel = ref('deepseek-chat')
const aiBaseUrl = ref('https://api.deepseek.com')
const eastmoneyCookie = ref('')
const showCustomModel = ref(false)
const customModelName = ref('')
const watchCount = ref(0)
const stockMeta = ref({})
const syncing = ref('')
const syncPct = ref(0)
const syncMsg = ref('')
let syncTimer = null
const logTab = ref('api')
const apiLogs = ref([])
const dsLogs = ref([])
const actLogs = ref([])
const backupBusy = ref(false)

// 飞书通知
const feishuEnabled = ref(false)
const feishuWebhook = ref('')
const feishuTesting = ref(false)
const feishuTestMsg = ref('')
const feishuTestOk = ref(false)

// 持仓异动监控
const changesMonitorEnabled = ref(true)
const watchTypes = ref([])
const changeTypeOptions = [
  { code: '8201', label: '大笔买入' },
  { code: '8202', label: '大笔卖出' },
  { code: '8193', label: '有大买盘' },
  { code: '8204', label: '有大卖盘' },
  { code: '8203', label: '竞价上涨' },
  { code: '8211', label: '高开5日线' },
  { code: '8212', label: '低开5日线' },
  { code: '4', label: '急速拉升' },
  { code: '64', label: '急速跳水' },
  { code: '8208', label: '封涨停板' },
  { code: '8210', label: '打开涨停' },
]
const DEFAULT_WATCH_TYPES = '8201,8202,8193,8204,4,64,8208,8210'

function setTheme(mode) {
  themeMode.value = mode
  applyThemeMode(mode)
  saveSetting('theme', mode)
}

function setNavMode(mode) {
  navMode.value = mode
  saveSetting('navMode', mode)
}

function setRefresh(sec) {
  refreshInterval.value = sec
  saveSetting('refreshInterval', sec)
}

function setOffInterval(ms) {
  offInterval.value = ms
  saveSetting('offMarketInterval', ms)
}

function setChartTopN(n) {
  chartTopN.value = n
  saveSetting('chartTopN', n)
}

function setTrendYScale(mode) {
  trendYScale.value = mode
  saveSetting('trendYScale', mode)
}

function setKlineYScale(mode) {
  klineYScale.value = mode
  saveSetting('klineYScale', mode)
}

function toggleHide(key) {
  const map = { hideKcb, hideCyb, hideSt, hideBse }
  const r = map[key]
  r.value = !r.value
  saveSetting(key, r.value)
}

function setAutoSync(h) {
  autoSyncHours.value = h
  saveSetting('autoSyncHours', h)
}

function setAi(key, value) {
  if (key === 'aiEnabled') { aiEnabled.value = value; saveSetting('aiEnabled', value) }
  else if (key === 'aiApiKey') { aiApiKey.value = value; saveSetting('aiApiKey', value) }
  else if (key === 'aiModel') { aiModel.value = value; saveSetting('aiModel', value) }
  else if (key === 'aiBaseUrl') { aiBaseUrl.value = value; saveSetting('aiBaseUrl', value) }
  else if (key === 'eastmoneyCookie') { eastmoneyCookie.value = value; saveSetting('eastmoneyCookie', value) }
}

async function onClearWatch() {
  const confirmed = await showConfirm({
    title: '清空自选确认',
    message: '确定要清空全部自选股吗？',
    detail: '警告：此操作将清空所有自选分组中的标的，操作后无法撤销。',
    confirmText: '确认清空',
    variant: 'danger',
  })
  if (!confirmed) return
  await clearWatch()
  watchCount.value = 0
  showToast('已清空全部自选股')
}

function exportWatch() {
  const data = JSON.stringify(watchState.codes, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'watchlist.json'
  a.click()
  URL.revokeObjectURL(url)
  showToast('自选股导出成功')
}

function importWatchFile(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async () => {
    try {
      const codes = JSON.parse(reader.result)
      if (Array.isArray(codes)) {
        const merged = await importWatch(codes.filter(c => /^\d{6}$/.test(c)))
        watchCount.value = merged.length
        showToast(`成功导入，当前共 ${merged.length} 只自选股`)
      }
    } catch (err) {
      showToast('导入失败：文件格式不正确', 'error')
    }
  }
  reader.readAsText(file)
}

async function exportBackup() {
  backupBusy.value = true
  try {
    const data = await api.backupExport()
    const json = JSON.stringify(data, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const d = new Date()
    const p = (n) => String(n).padStart(2, '0')
    a.download = `niulai-backup-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}.json`
    a.click()
    URL.revokeObjectURL(url)
    showToast('备份导出成功')
  } catch (e) {
    showToast('导出失败：' + e.message, 'error')
  } finally {
    backupBusy.value = false
  }
}

async function importBackupFile(e) {
  const file = e.target.files[0]
  if (!file) return
  const confirmed = await showConfirm({
    title: '导入备份确认',
    message: '完整导入将覆盖本机的自选/持仓/监控/设置等数据，确定继续吗？',
    confirmText: '确认覆盖导入',
    variant: 'danger',
  })
  if (!confirmed) {
    e.target.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = async () => {
    backupBusy.value = true
    try {
      const payload = JSON.parse(reader.result)
      const res = await api.backupImport(payload)
      const count = Object.values(res.imported || {}).reduce((a, b) => a + b, 0)
      await loadSettings()
      watchCount.value = (await api.watchlist().catch(() => ({ codes: [] }))).codes?.length || 0
      showToast(`导入成功：共恢复 ${count} 条数据`)
    } catch (err) {
      showToast('导入失败：文件格式不正确或数据版本不兼容', 'error')
    } finally {
      backupBusy.value = false
      e.target.value = ''
    }
  }
  reader.readAsText(file)
}

async function pollSync() {
  try {
    const st = await api.syncStatus()
    syncPct.value = st.percent || 0
    syncMsg.value = st.message || ''
    if (st.count != null) {
      stockMeta.value = {
        count: st.count,
        updated_at: st.updated_at,
        lastConceptSyncAt: st.lastConceptSyncAt || stockMeta.value.lastConceptSyncAt,
      }
    }
    if (!st.running) {
      clearInterval(syncTimer)
      syncTimer = null
      syncing.value = ''
      if (st.error) showToast('同步失败：' + st.error, 'error')
      else setTimeout(() => { if (!syncing.value) { syncMsg.value = ''; syncPct.value = 0 } }, 4000)
    }
  } catch (e) {
    clearInterval(syncTimer)
    syncTimer = null
    syncing.value = ''
  }
}

async function resync(scope = 'stocks') {
  if (syncing.value) return
  syncing.value = scope
  syncPct.value = 1
  syncMsg.value = '已提交任务…'
  try {
    await (scope === 'stocks' ? api.syncStocks() : api.syncTags(scope))
    if (syncTimer) clearInterval(syncTimer)
    syncTimer = setInterval(pollSync, 600)
    pollSync()
  } catch (e) {
    syncing.value = ''
    showToast('同步失败：' + e.message, 'error')
  }
}

function setFeishu(key, value) {
  if (key === 'feishu_enabled') feishuEnabled.value = value === '1'
  if (key === 'feishu_webhook') feishuWebhook.value = value
  saveSetting(key, value)
}

async function testFeishu() {
  feishuTesting.value = true
  feishuTestMsg.value = ''
  try {
    const res = await api.feishuTest()
    feishuTestOk.value = !!res.ok
    feishuTestMsg.value = res.message || (res.ok ? '成功' : '失败')
  } catch (e) {
    feishuTestOk.value = false
    feishuTestMsg.value = '请求失败：' + (e.message || e)
  } finally {
    feishuTesting.value = false
  }
}

function setChangesMon(key, value) {
  if (key === 'changes_monitor_enabled') {
    changesMonitorEnabled.value = value === '1'
    settingsState.changes_monitor_enabled = value
  }
  saveSetting(key, value)
}

function toggleChangeType(code) {
  const idx = watchTypes.value.indexOf(code)
  if (idx >= 0) {
    watchTypes.value.splice(idx, 1)
  } else {
    watchTypes.value.push(code)
  }
  const str = watchTypes.value.join(',')
  settingsState.changes_watch_types = str
  saveSetting('changes_watch_types', str)
}

async function loadLogs() {
  try {
    if (logTab.value === 'api') apiLogs.value = await api.logsApi(80)
    else if (logTab.value === 'ds') dsLogs.value = await api.logsDatasource(80)
    else actLogs.value = await api.logsActions(80)
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  await loadSettings()
  themeMode.value = ['light', 'dark', 'system'].includes(settingsState.theme) ? settingsState.theme : 'dark'
  navMode.value = settingsState.navMode === 'side' ? 'side' : 'top'
  refreshInterval.value = settingsState.refreshInterval
  offInterval.value = settingsState.offMarketInterval
  chartTopN.value = settingsState.chartTopN
  trendYScale.value = settingsState.trendYScale || 'normal'
  klineYScale.value = settingsState.klineYScale || 'auto'
  hideKcb.value = settingsState.hideKcb
  hideCyb.value = settingsState.hideCyb
  hideSt.value = settingsState.hideSt
  hideBse.value = settingsState.hideBse
  autoSyncHours.value = settingsState.autoSyncHours
  aiEnabled.value = settingsState.aiEnabled
  aiApiKey.value = settingsState.aiApiKey
  aiModel.value = settingsState.aiModel
  aiBaseUrl.value = settingsState.aiBaseUrl
  eastmoneyCookie.value = settingsState.eastmoneyCookie
  if (aiModel.value && !['deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-flash', 'gpt-4o'].includes(aiModel.value)) {
    showCustomModel.value = true
    customModelName.value = aiModel.value
  }
  watchCount.value = watchState.codes.length
  try { stockMeta.value = await api.metaStocks() } catch (e) { /* ignore */ }

  // 飞书通知
  feishuEnabled.value = settingsState.feishu_enabled === '1' || settingsState.feishu_enabled === true
  feishuWebhook.value = settingsState.feishu_webhook || ''

  // 异动监控持久化加载
  changesMonitorEnabled.value = (settingsState.changes_monitor_enabled || '1') === '1'
  const wt = settingsState.changes_watch_types !== undefined ? settingsState.changes_watch_types : DEFAULT_WATCH_TYPES
  watchTypes.value = wt ? wt.split(',').map(x => x.trim()).filter(Boolean) : []

  loadLogs()
})

onUnmounted(() => {
  if (syncTimer) {
    clearInterval(syncTimer)
    syncTimer = null
  }
})
</script>

<style scoped>
/* 分组导航：吸顶，便于在多个设置区之间切换 */
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

/* 通用组短卡片两列并排 */
.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; align-items: start; }
.settings-grid .card { padding: 12px 14px; }
.settings-grid .card-title { margin-bottom: 6px; }
@media (max-width: 1000px) { .settings-grid { grid-template-columns: 1fr; } }
.setting-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; border-bottom: 1px solid var(--border); gap: 10px;
}
.setting-row:last-child { border-bottom: none; }
.setting-label { font-size: 14px; color: var(--text); }
.setting-value { font-size: 13px; color: var(--text-dim); }
.setting-control { display: flex; gap: 4px; flex-wrap: wrap; }
.mini-tabs { margin-bottom: 0; }
.setting-input {
  padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--bg); color: var(--text); font-size: 13px; width: 320px; max-width: 50vw;
}
.setting-input:focus { outline: none; border-color: var(--accent); }
</style>
