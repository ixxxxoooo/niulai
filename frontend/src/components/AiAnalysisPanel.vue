<template>
  <Teleport to="body">
    <div v-if="open" class="ai-modal-mask" @click.self="close">
      <div class="ai-modal" ref="modalEl">
        <div class="ai-modal-head">
          <span class="ai-modal-title">AI 智能分析 · {{ name || code }}</span>
          <UiSelect
            v-if="history.length"
            v-model="currentId"
            class="ai-hist-select"
            title="历史记录（最多 5 条，倒序）"
            @change="onSelectHistory"
          >
            <option v-for="h in history" :key="h.id" :value="h.id">
              {{ fmtHistTime(h.created_at) }}{{ h.id === latestId ? ' · 最新' : '' }}
            </option>
          </UiSelect>
          <UiButton variant="primary" :disabled="loading" @click="runAnalysis">
            {{ loading ? '分析中…' : (hasContent ? '重新生成' : '开始分析') }}
          </UiButton>
          <span v-if="elapsed" class="ai-elapsed">{{ elapsed }}s</span>
          <button class="btn-shot" @click="screenshot" title="截图复制到剪贴板"><UiIcon name="screenshot" :size="14" /></button>
          <button class="modal-close" @click="close" title="关闭"><UiIcon name="close" :size="16" /></button>
        </div>

        <div class="ai-modal-body" ref="modalBodyRef">
          <div v-if="!hasConfig" class="ai-tip">
            请先在「设置」中开启 AI 分析并配置 API Key。
            <a href="#/settings" class="link">前往设置 <UiIcon name="arrowRight" :size="12" /></a>
          </div>

          <template v-else>
            <div class="ai-presets">
              <span class="ai-presets-label">快捷分析：</span>
              <button
                v-for="p in PRESET_PROMPTS"
                :key="p.id"
                class="ai-preset-pill"
                :class="{ active: selectedPreset === p.id }"
                :disabled="loading"
                @click="runPreset(p.id)"
              >
                {{ p.label }}
              </button>
            </div>

            <div v-if="error" class="ai-error">
              <div>{{ error }}</div>
              <div v-if="debugInfo" class="ai-debug">{{ debugInfo }}</div>
            </div>

            <!-- 思考过程（生成中动态高亮展开并实时滚动最新，完成后自动收起） -->
            <div
              v-if="thinkingMd || currentReasoning || (loading && !streamText)"
              class="ai-think"
              :class="{ 'is-thinking': loading && !streamText, 'is-open': thinkOpen }"
            >
              <button type="button" class="ai-think-toggle" @click="toggleThink">
                <div class="ai-think-status-wrap">
                  <!-- 思考中动态脉冲徽标 -->
                  <span v-if="loading && !streamText" class="think-pulse-badge">
                    <span class="pulse-ring"></span>
                    <span class="pulse-dot"></span>
                  </span>
                  <span v-else class="ai-think-icon" :class="{ open: thinkOpen }">
                    <UiIcon name="chevronRight" :size="12" />
                  </span>

                  <!-- 状态文字 -->
                  <span v-if="loading && !streamText" class="think-active-title">
                    🧠 正在深度思考中…
                    <span class="think-live-timer" v-if="thinkLiveSeconds > 0">（已思考 {{ thinkLiveSeconds }}s）</span>
                  </span>
                  <span v-else class="think-done-title">
                    💡 已深度思考
                    <span v-if="thinkSeconds" class="think-time-tag">用时约 {{ thinkSeconds }}s</span>
                  </span>
                </div>

                <span class="ai-think-hint">{{ thinkOpen ? '收起思考' : '展开思考过程' }}</span>
              </button>

              <div v-show="thinkOpen" class="ai-think-body">
                <!-- 刚发起请求、模型思考内容还未吐出时的过渡态 -->
                <div v-if="loading && !thinkingMd && !currentReasoning" class="think-waiting-shimmer">
                  <div class="ai-spinner-sm"></div>
                  <span>正在构建股票盘口、分时均线与量价结构多维度上下文…</span>
                </div>
                <!-- 实时流式思考 Markdown 内容 + 打字光标 -->
                <div v-else class="ai-think-text md" ref="thinkTextRef">
                  <div v-html="renderMd(thinkingMd || currentReasoning)"></div>
                  <span v-if="loading && !streamText" class="think-typing-cursor">▌</span>
                </div>
              </div>
            </div>

            <div v-if="loading && !streamText && !thinkingMd" class="ai-loading">
              <div class="ai-spinner"></div>
              <span>正在获取数据并调用 AI 引擎…</span>
            </div>

            <div v-if="streamText && !showResult" class="ai-stream md" ref="streamElRef" v-html="renderMd(streamText)"></div>

            <div v-if="showResult" class="ai-result">
              <div class="ai-section" v-for="sec in resultSections" :key="sec.key">
                <div class="ai-section-title">{{ sec.title }}</div>
                <div class="ai-text md" v-html="renderMd(sec.text)"></div>
              </div>
              <div class="ai-disclaimer">
                <UiIcon name="warning" :size="12" /> AI 分析仅供参考，不构成投资建议。市场有风险，投资需谨慎。
              </div>
            </div>

            <div v-else-if="!loading && !error && !hasContent && !thinkingMd" class="ai-empty">
              <template v-if="history.length">
                最近一次分析记录已展示（{{ fmtHistTime(latestTime) }}）。点击「重新生成」可获取最新判断。
              </template>
              <template v-else>
                暂无历史记录。点击「开始分析」，AI 将综合分时、K线、资金流、技术指标等数据给出走势判断。
              </template>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * 个股 AI 分析弹窗（含深度思考过程流式展示、自动跟随最新与剪贴板截图）
 * @author ygw
 */
import { ref, computed, nextTick, onUnmounted } from 'vue'
import { marked } from 'marked'
import { api } from '../api.js'
import { settingsState } from '../composables/useSettings.js'
import { captureElement } from '../composables/useScreenshot.js'
import UiIcon from './ui/UiIcon.vue'
import UiButton from './ui/UiButton.vue'
import UiSelect from './ui/UiSelect.vue'

const props = defineProps({
  code: { type: String, required: true },
  name: { type: String, default: '' },
})

marked.setOptions({ breaks: true, gfm: true })

// ── 弹窗与历史状态 ──
const open = ref(false)
const modalEl = ref(null)
const modalBodyRef = ref(null)
const thinkTextRef = ref(null)
const streamElRef = ref(null)
const history = ref([])
const currentId = ref(null)
const currentReasoning = ref('')
const currentContent = ref('')
const currentResult = ref({})
const latestId = ref(null)
const latestTime = ref('')

// ── 生成状态 ──
const loading = ref(false)
const error = ref('')
const debugInfo = ref('')
const streamText = ref('')
const thinkingMd = ref('')
const thinkOpen = ref(false)
const thinkSeconds = ref(0)
const thinkLiveSeconds = ref(0)
const elapsed = ref(0)
const freshContent = ref('')
let liveTimerId = null
let scrollRafId = null

const hasConfig = computed(() => {
  return settingsState.aiEnabled && settingsState.aiApiKey && settingsState.aiApiKey.length > 5
})

const hasContent = computed(() => !!(currentContent.value || currentReasoning.value || freshContent.value))

const showResult = computed(() => {
  if (loading.value) return false
  return !!Object.keys(currentResult.value).filter(k => currentResult.value[k]).length
})

const PRESET_PROMPTS = [
  { id: 'all', label: '⚡ 全面技术分析', focus: '' },
  { id: 'flow', label: '📊 量价与主力资金', focus: '【重点聚焦】请结合近10日主力资金进出、分时均价线与量比，重点研判主力控盘动向与量价背离风险。' },
  { id: 'trend', label: '📈 买卖点与关键位', focus: '【重点聚焦】请结合日K均线多空排列、MACD/KDJ/RSI与压力支撑位，重点给出明确买入区间、止损价与目标位。' },
  { id: 'chip', label: '🎯 题材情绪与连板', focus: '【重点聚焦】请结合概念题材风口热度、连板情绪周期与筹码博弈，重点评估短线资金接力意愿与持续性。' },
]

const selectedPreset = ref('all')

function runPreset(id) {
  selectedPreset.value = id
  runAnalysis()
}

const SECTION_META = [
  { key: 'summary', title: '综合判断' },
  { key: 'trend', title: '趋势分析' },
  { key: 'buy_sell', title: '买卖点建议' },
  { key: 'support_resistance', title: '压力位 / 支撑位' },
  { key: 'risk', title: '风险提示' },
]

const resultSections = computed(() => {
  const r = currentResult.value || {}
  return SECTION_META.map(m => ({ ...m, text: r[m.key] || '' })).filter(s => s.text)
})

function fmtHistTime(t) {
  if (!t) return ''
  const m = String(t).match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/)
  if (m) return `${m[2]}-${m[3]} ${m[4]}:${m[5]}`
  return String(t).slice(5, 16)
}

function renderMd(text) {
  if (!text) return ''
  let html = ''
  try { html = marked.parse(text) } catch (e) { html = String(text).replace(/\n/g, '<br>') }
  html = String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<iframe[\s\S]*?<\/iframe>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
  return mdHighlight(html)
}

/**
 * 自动滚动追踪最新生成内容
 */
function autoScrollToLatest() {
  if (scrollRafId) return
  scrollRafId = requestAnimationFrame(() => {
    scrollRafId = null
    if (thinkOpen.value && thinkTextRef.value) {
      thinkTextRef.value.scrollTop = thinkTextRef.value.scrollHeight
    }
    if (modalBodyRef.value) {
      modalBodyRef.value.scrollTop = modalBodyRef.value.scrollHeight
    }
  })
}

function toggleThink() {
  thinkOpen.value = !thinkOpen.value
  if (thinkOpen.value) {
    nextTick(autoScrollToLatest)
  }
}

/**
 * 在 Markdown HTML 上做 AI 关键词着色
 */
function mdHighlight(html) {
  const tags = []
  let s = String(html).replace(/<[^>]+>/g, m => { tags.push(m); return `\u0000${tags.length - 1}\u0000` })
  s = s
    .replace(/([+-]?\d+\.?\d*%)/g, '<span class="ai-num">$1</span>')
    .replace(/(\d+\.?\d+)元/g, '<span class="ai-price">$1</span>元')
    .replace(/(看多|偏多|做多|买入|加仓|突破|金叉|放量上涨|强势|信心高)/g, '<span class="ai-bull">$1</span>')
    .replace(/(看空|偏空|做空|卖出|减仓|跌破|死叉|放量下跌|弱势)/g, '<span class="ai-bear">$1</span>')
    .replace(/(震荡|观望|等待|中性|持有)/g, '<span class="ai-neutral">$1</span>')
    .replace(/(止损|风险|警惕)/g, '<span class="ai-warn">$1</span>')
  s = s.replace(/\u0000(\d+)\u0000/g, (_m, i) => tags[+i] || '')
  return s
}

function applyRecord(rec) {
  if (!rec) return
  currentId.value = rec.id ?? null
  currentReasoning.value = rec.reasoning || ''
  currentContent.value = rec.content || ''
  currentResult.value = rec.result && Object.keys(rec.result).length ? rec.result : parseAiResult(rec.content || '')
  freshContent.value = ''
  // 历史记录展示时默认收起思考内容，突出正文分析
  thinkOpen.value = false
}

async function loadHistory(selectFirst = true) {
  try {
    const res = await api.aiHistory(props.code)
    history.value = res.items || []
    if (history.value.length) {
      latestId.value = history.value[0].id
      latestTime.value = history.value[0].created_at || ''
      if (selectFirst) applyRecord(history.value[0])
    } else {
      latestId.value = null
      latestTime.value = ''
    }
  } catch (e) {
    history.value = []
  }
}

function onSelectHistory() {
  const rec = history.value.find(h => h.id === currentId.value)
  if (rec) applyRecord(rec)
}

async function openModal() {
  open.value = true
  error.value = ''
  loading.value = false
  streamText.value = ''
  thinkingMd.value = ''
  freshContent.value = ''
  await loadHistory(true)
  const last = history.value[0]
  if (!last || !isToday(last.created_at)) {
    runAnalysis()
  }
}

function isToday(ts) {
  if (!ts) return false
  const now = new Date()
  const ymd = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`
  return String(ts).slice(0, 10) === ymd
}

function close() {
  if (loading.value) return
  open.value = false
}

/**
 * 截图直接复制到剪贴板（不触发文件下载）
 */
async function screenshot() {
  if (!modalEl.value) return
  const name = (props.name || props.code || 'AI') + '_AI分析.png'
  await captureElement(modalEl.value, name, { forceDownload: false })
}

defineExpose({ open: openModal, close })

// ── AI 生成 ──
function buildPrompt(data) {
  const snap = data.snapshot || {}
  const kline = data.kline || {}
  const trend = data.trend || {}
  const flow = data.moneyflow || []
  const sr = data.support_resistance || {}
  const newsItems = data.news || []
  const pts = kline.points || []
  const ind = kline.indicators || {}

  const safe = (v, suffix = '') => (v != null && v !== '' && !isNaN(v)) ? v + suffix : '-'

  const kSummary = pts.slice(-15).map(p =>
    `${p.date} O${p.open} H${p.high} L${p.low} C${p.close} V${p.volume}`
  ).join('\n') || '暂无K线数据'

  const maSummary = ['ma5', 'ma10', 'ma20', 'ma60'].map(k => {
    const arr = ind[k] || []
    return arr.length ? `${k.toUpperCase()}=${arr[arr.length - 1]?.toFixed(2)}` : null
  }).filter(Boolean).join(' ') || '无'

  const macdArr = ind.macd || {}
  const macdSummary = macdArr.dif ? `DIF=${macdArr.dif?.slice(-1)[0]?.toFixed(3)} DEA=${macdArr.dea?.slice(-1)[0]?.toFixed(3)} HIST=${macdArr.hist?.slice(-1)[0]?.toFixed(3)}` : '无'
  const kdjSummary = ind.kdj ? `K=${ind.kdj.k?.slice(-1)[0]?.toFixed(1)} D=${ind.kdj.d?.slice(-1)[0]?.toFixed(1)} J=${ind.kdj.j?.slice(-1)[0]?.toFixed(1)}` : '无'
  const rsiVal = ind.rsi?.slice(-1)[0]
  const bollStr = ind.boll ? `上轨${ind.boll.upper?.slice(-1)[0]?.toFixed(2)} 中轨${ind.boll.mid?.slice(-1)[0]?.toFixed(2)} 下轨${ind.boll.lower?.slice(-1)[0]?.toFixed(2)}` : '无'

  const flowSummary = flow.length ? flow.map(f =>
    `${f.date?.slice(5)} 主力${f.main_inflow >= 0 ? '+' : ''}${(f.main_inflow / 1e4).toFixed(0)}万`
  ).join(' | ') : '暂无'

  const supportStr = (sr.support || []).map(s => `${s.label}=${s.price}`).join(', ') || '无'
  const resistStr = (sr.resistance || []).map(s => `${s.label}=${s.price}`).join(', ') || '无'

  const trendPts = (trend.points || [])
  let trendDetail = '非交易时段，无分时数据'
  if (trendPts.length > 0) {
    const first = trendPts[0], last = trendPts[trendPts.length - 1]
    const maxP = Math.max(...trendPts.map(p => p.price))
    const minP = Math.min(...trendPts.map(p => p.price))
    trendDetail = `分时${trendPts.length}点 开${first.price} 现${last.price} 均${last.avg?.toFixed(2) || '-'} 最高${maxP} 最低${minP}`
  }

  const newsSummary = newsItems.slice(0, 5).map(n => `- ${n.title}`).join('\n') || '暂无近期新闻'

  const presetObj = PRESET_PROMPTS.find(p => p.id === selectedPreset.value)
  const focusTxt = presetObj?.focus ? `\n\n${presetObj.focus}` : ''

  return `对「${props.name || props.code}(${props.code})」做系统化技术分析。${focusTxt}

## 盘面快照
现价${safe(snap.price)} 涨跌${safe(snap.change_pct, '%')} 今开${safe(snap.open)} 昨收${safe(snap.prev_close)} 最高${safe(snap.high)} 最低${safe(snap.low)}
成交额${safe(snap.amount)} 换手${safe(snap.turnover, '%')} 量比${safe(snap.volume_ratio)} 振幅${safe(snap.amplitude, '%')}
外盘${safe(snap.outer)} 内盘${safe(snap.inner)} 主力净流入${safe(snap.main_inflow)}
PE${safe(snap.pe)} PB${safe(snap.pb)} 流通市值${safe(snap.float_mv)}

## 分时走势
${trendDetail}

## 近15日K线(日期 开 高 低 收 量)
${kSummary}

## 技术指标(最新值)
均线: ${maSummary}
BOLL: ${bollStr}
MACD: ${macdSummary}
KDJ: ${kdjSummary}
RSI: ${rsiVal != null ? rsiVal.toFixed(1) : '无'}

## 今日资金流
${flowSummary}

## 关键价位
压力: ${resistStr}
支撑: ${supportStr}

## 近期新闻/事件
${newsSummary}

---
请严格按以下5个板块输出，每部分100-200字，重点数值用**加粗**：
**[综合判断]** 多空方向+置信度+核心逻辑（结合量价、指标、资金面综合判断）
**[趋势分析]** 均线形态+MACD/KDJ状态+量价配合+板块联动
**[买卖点建议]** 具体买入价区间+目标价位+止损价位（给出明确数值）
**[压力支撑]** 最重要的2-3个关键价位+技术含义
**[风险提示]** 2-3个核心风险因素`
}

function parseAiResult(text) {
  const sections = { summary: '', trend: '', buy_sell: '', support_resistance: '', risk: '' }
  const patterns = [
    { key: 'summary', re: /^\s*(?:#{1,3}\s*)?(?:\*{0,2})\[?\s*综合判断\s*\]?(?:\*{0,2})\s*[：:]?\s*/i },
    { key: 'trend', re: /^\s*(?:#{1,3}\s*)?(?:\*{0,2})\[?\s*趋势分析\s*\]?(?:\*{0,2})\s*[：:]?\s*/i },
    { key: 'buy_sell', re: /^\s*(?:#{1,3}\s*)?(?:\*{0,2})\[?\s*买卖点建议\s*\]?(?:\*{0,2})\s*[：:]?\s*/i },
    { key: 'support_resistance', re: /^\s*(?:#{1,3}\s*)?(?:\*{0,2})\[?\s*压力支撑\s*\]?(?:\*{0,2})\s*[：:]?\s*/i },
    { key: 'risk', re: /^\s*(?:#{1,3}\s*)?(?:\*{0,2})\[?\s*风险提示\s*\]?(?:\*{0,2})\s*[：:]?\s*/i },
  ]
  const lines = String(text || '').split('\n')
  let currentKey = 'summary'
  let sawHeader = false
  for (const line of lines) {
    let matched = false
    for (const p of patterns) {
      if (p.re.test(line)) {
        currentKey = p.key
        sawHeader = true
        const content = line.replace(p.re, '').trim()
        if (content) sections[currentKey] += content + '\n'
        matched = true
        break
      }
    }
    if (!matched) sections[currentKey] += line + '\n'
  }
  for (const k of Object.keys(sections)) sections[k] = sections[k].trim()
  if (!sawHeader && text) sections.summary = String(text).trim()
  return sections
}

function stopLiveTimer() {
  if (liveTimerId) {
    clearInterval(liveTimerId)
    liveTimerId = null
  }
}

async function runAnalysis() {
  if (!hasConfig.value) {
    error.value = '未配置 AI API Key，请前往设置页配置'
    return
  }
  loading.value = true
  error.value = ''
  debugInfo.value = ''
  streamText.value = ''
  thinkingMd.value = ''
  currentContent.value = ''
  currentResult.value = {}
  currentReasoning.value = ''
  // 开始生成时：默认展开思考过程，让用户清晰看到生成与推理动态
  thinkOpen.value = true
  thinkSeconds.value = 0
  thinkLiveSeconds.value = 0
  elapsed.value = 0
  freshContent.value = ''
  stopLiveTimer()

  const t0 = Date.now()
  let thinkStart = Date.now()

  // 启动实时秒数计时器
  liveTimerId = setInterval(() => {
    thinkLiveSeconds.value = Math.max(1, Math.round((Date.now() - thinkStart) / 1000))
  }, 250)

  try {
    let data = {}
    try {
      data = await api.analysisData(props.code) || {}
    } catch (e) {
      console.warn('[AI] 分析数据获取部分失败:', e.message)
    }

    if (!data.snapshot && !data.kline) {
      throw new Error('未获取到任何股票数据，请检查网络或稍后重试')
    }

    const prompt = buildPrompt(data)
    const resp = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: settingsState.aiModel || 'deepseek-chat',
        messages: [
          { role: 'system', content: '你是资深A股短线技术分析师，擅长量价分析、技术指标研判和资金面解读。请基于提供的数据给出明确的操作建议。输出全程中文，使用规范的 Markdown 排版（## 标题、**加粗**、- 列表、| 表格）。如果某项数据缺失，跳过相关分析即可，不要提及数据不足。' },
          { role: 'user', content: prompt },
        ],
        temperature: 0.3,
        max_tokens: 4000,
        stream: true,
      }),
    })

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}))
      throw new Error(errData.error?.message || `后端错误 ${resp.status}`)
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let fullText = ''
    let reasoningText = ''
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6).trim()
        if (!payload || payload === '[DONE]') continue
        try {
          const chunk = JSON.parse(payload)
          if (chunk.error?.message) throw new Error(chunk.error.message)
          const delta = chunk.choices?.[0]?.delta || {}
          const contentDelta = delta.content || ''
          const reasonDelta = delta.reasoning_content || ''
          
          if (reasonDelta) {
            reasoningText += reasonDelta
            thinkingMd.value = reasoningText
            autoScrollToLatest()
          }
          if (contentDelta) {
            // 正文开始输出：停止思考计时器，并自动收起思考内容
            if (thinkStart && !thinkSeconds.value) {
              thinkSeconds.value = Math.max(1, Math.round((Date.now() - thinkStart) / 1000))
              stopLiveTimer()
            }
            if (thinkOpen.value) {
              thinkOpen.value = false
            }
            fullText += contentDelta
            streamText.value = fullText
            autoScrollToLatest()
          }
        } catch (e) {
          if (e && e.message && !(e instanceof SyntaxError)) throw e
        }
      }
    }

    stopLiveTimer()
    if (thinkStart && !thinkSeconds.value) {
      thinkSeconds.value = Math.max(1, Math.round((Date.now() - thinkStart) / 1000))
    }
    thinkingMd.value = ''

    if (!fullText && reasoningText) fullText = reasoningText
    if (!fullText) {
      throw new Error('AI 未返回正文。若使用推理模型，请在设置中改用 DeepSeek Chat，或稍后重试')
    }

    const parsed = parseAiResult(fullText)
    streamText.value = ''
    freshContent.value = fullText
    currentReasoning.value = reasoningText
    currentContent.value = fullText
    currentResult.value = parsed
    
    // 生成完毕后：确保思考过程收起
    thinkOpen.value = false
    elapsed.value = ((Date.now() - t0) / 1000).toFixed(1)

    try {
      await api.aiSave({
        code: props.code,
        reasoning: reasoningText,
        content: fullText,
        result: parsed,
      })
      await loadHistory(false)
    } catch (e) {
      console.warn('[AI] 历史保存失败:', e.message)
    }
  } catch (e) {
    console.error('[AI] 分析失败:', e)
    error.value = e.message || '分析失败'
    debugInfo.value = `code=${props.code} model=${settingsState.aiModel}`
  } finally {
    stopLiveTimer()
    loading.value = false
  }
}

onUnmounted(() => {
  stopLiveTimer()
})
</script>

<style scoped>
.ai-modal-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center; z-index: 999;
}
.ai-modal {
  background: var(--bg); border: 1px solid var(--border); border-radius: 12px;
  width: 720px; max-width: 94vw; max-height: 88vh; display: flex; flex-direction: column;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}
.ai-modal-head {
  display: flex; align-items: center; gap: 10px; padding: 14px 18px;
  border-bottom: 1px solid var(--border); flex-wrap: wrap;
}
.ai-modal-title { font-size: 15px; font-weight: 600; color: var(--text); }
.ai-hist-select select {
  padding: 3px 8px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--bg); color: var(--text-dim); font-size: 12px; cursor: pointer;
  height: auto;
}
.ai-modal-body {
  padding: 16px 18px;
  overflow-y: auto;
  flex: 1;
  min-height: 120px;
  scroll-behavior: smooth;
}
.ai-presets {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 12px; background: var(--kv-bg); border-radius: 8px; margin-bottom: 14px;
}
.ai-presets-label { font-size: 12px; color: var(--text-dim); font-weight: 500; }
.ai-preset-pill {
  padding: 4px 10px; border-radius: 14px; border: 1px solid var(--border);
  background: var(--bg); color: var(--text); font-size: 12px; cursor: pointer;
  transition: all .15s;
}
.ai-preset-pill:hover:not(:disabled) {
  border-color: var(--accent); color: var(--accent); background: var(--bg-hover);
}
.ai-preset-pill.active {
  background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 500;
}
.ai-preset-pill:disabled { opacity: .5; cursor: not-allowed; }

.modal-close {
  border: none; background: transparent; cursor: pointer;
  font-size: 15px; color: var(--text-dim); padding: 4px 8px; border-radius: 6px;
}
.modal-close:hover { color: var(--text); background: var(--bg-hover); }
.btn-shot {
  margin-left: auto;
  border: none; background: transparent; cursor: pointer;
  padding: 4px 8px; border-radius: 6px; opacity: .75; color: var(--text);
  display: inline-flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.btn-shot:hover { opacity: 1; background: var(--bg-hover); color: var(--accent); }
.ai-elapsed { font-size: 12px; color: var(--text-dim); }
.ai-tip { font-size: 13px; color: var(--text-dim); padding: 16px 0; }
.ai-tip .link { color: var(--accent); text-decoration: underline; }
.ai-error { font-size: 13px; color: var(--up); padding: 12px; background: var(--up-bg); border-radius: var(--radius-md); margin-bottom: 10px; }
.ai-debug { font-size: 11px; color: var(--text-dim); margin-top: 6px; word-break: break-all; }
.ai-empty { font-size: 13px; color: var(--text-dim); padding: 20px 0; line-height: 1.7; }
.ai-loading { display: flex; align-items: center; gap: 10px; padding: 12px 0; color: var(--text-dim); font-size: 13px; }
.ai-spinner {
  width: 18px; height: 18px; border: 2px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .8s linear infinite;
}
.ai-spinner-sm {
  width: 14px; height: 14px; border: 2px solid var(--border); border-top-color: var(--accent);
  border-radius: 50%; animation: spin .8s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 思考过程容器 ── */
.ai-think {
  margin-bottom: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--kv-bg);
  overflow: hidden;
  transition: all .25s ease;
}

/* 正在思考中的特殊高亮动效 */
.ai-think.is-thinking {
  border-color: rgba(76, 154, 255, 0.45);
  background: linear-gradient(180deg, rgba(76, 154, 255, 0.06) 0%, var(--kv-bg) 100%);
  box-shadow: 0 0 16px rgba(76, 154, 255, 0.1);
}

.ai-think-toggle {
  width: 100%; display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border: none; background: transparent;
  color: var(--text-dim); font-size: 13px; cursor: pointer; text-align: left;
}
.ai-think-toggle:hover { color: var(--text); }

.ai-think-status-wrap {
  display: flex; align-items: center; gap: 8px;
}

/* 脉冲跳动点 */
.think-pulse-badge {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
}
.pulse-dot {
  width: 8px;
  height: 8px;
  background: var(--accent);
  border-radius: 50%;
}
.pulse-ring {
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0.4;
  animation: pulse-wave 1.5s ease-out infinite;
}
@keyframes pulse-wave {
  0% { transform: scale(0.6); opacity: 0.8; }
  100% { transform: scale(1.6); opacity: 0; }
}

.think-active-title {
  color: var(--accent);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.think-live-timer {
  font-size: 12px;
  color: var(--text-dim);
  font-weight: normal;
}
.think-done-title {
  color: var(--text);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.think-time-tag {
  font-size: 11px;
  color: var(--text-dim);
  background: var(--bg-hover);
  padding: 1px 6px;
  border-radius: 4px;
}

.ai-think-icon {
  display: inline-block; transition: transform .18s; font-size: 12px; color: var(--text-dim);
}
.ai-think-icon.open { transform: rotate(90deg); color: var(--accent); }
.ai-think-hint { font-size: 11px; opacity: .7; color: var(--text-dim); }

.ai-think-body {
  padding: 0 14px 14px;
  border-top: 1px dashed var(--border);
}

.think-waiting-shimmer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0 4px;
  font-size: 12px;
  color: var(--text-dim);
}

.ai-think-text {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-dim);
  max-height: 280px;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.think-typing-cursor {
  display: inline-block;
  color: var(--accent);
  font-weight: bold;
  animation: blink 0.8s infinite;
  margin-left: 2px;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.ai-stream { font-size: 13px; line-height: 1.7; color: var(--text); padding: 8px 0; }
.ai-section { margin-bottom: 16px; }
.ai-section-title { font-size: 13px; font-weight: 600; color: var(--accent); margin-bottom: 6px; }
.ai-text { font-size: 13px; line-height: 1.7; color: var(--text); }
.ai-disclaimer { font-size: 11px; color: var(--text-dim); padding: 10px; background: var(--kv-bg); border-radius: var(--radius-sm); margin-top: 12px; display: flex; align-items: center; gap: 5px; }

/* AI 关键词着色（作用在 v-html 渲染的 Markdown 内） */
.md :deep(.ai-num) { color: var(--accent); font-weight: 600; }
.md :deep(.ai-price) { color: var(--yellow); font-weight: 600; }
.md :deep(.ai-bull) { color: var(--up); font-weight: 600; }
.md :deep(.ai-bear) { color: var(--down); font-weight: 600; }
.md :deep(.ai-neutral) { color: var(--text-dim); font-weight: 600; }
.md :deep(.ai-warn) { color: var(--yellow); font-weight: 600; }

/* Markdown 通用样式 */
.md h1, .md h2, .md h3, .md h4 { margin: 10px 0 6px; line-height: 1.4; }
.md h2 { font-size: 14px; color: var(--accent); }
.md h3 { font-size: 13px; }
.md p { margin: 6px 0; }
.md ul, .md ol { margin: 6px 0; padding-left: 20px; }
.md li { margin: 2px 0; }
.md code { background: var(--bg-hover); padding: 1px 5px; border-radius: 4px; font-size: 12px; font-family: monospace; }
.md pre { background: var(--bg-hover); padding: 10px; border-radius: 8px; overflow-x: auto; font-size: 12px; }
.md pre code { background: transparent; padding: 0; }
.md blockquote { margin: 8px 0; padding: 4px 12px; border-left: 3px solid var(--accent); color: var(--text-dim); background: var(--bg-hover); border-radius: 4px; }
.md table { border-collapse: collapse; margin: 8px 0; font-size: 12px; width: 100%; }
.md th, .md td { border: 1px solid var(--border); padding: 5px 9px; text-align: left; }
.md th { background: var(--bg-hover); color: var(--text-dim); font-weight: 500; }
.md a { color: var(--accent); }
.md hr { border: none; border-top: 1px solid var(--border); margin: 10px 0; }
</style>
