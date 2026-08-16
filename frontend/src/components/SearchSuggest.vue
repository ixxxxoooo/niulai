<template>
  <div class="suggest-wrap">
    <div class="search-box">
      <input
        ref="inputEl"
        v-model="kw"
        :placeholder="placeholder"
        @input="onInput"
        @focus="onFocus"
        @blur="onBlur"
        @keydown.enter.prevent="onEnter"
        @keydown.esc="show = false"
        @keydown.up.prevent="move(-1)"
        @keydown.down.prevent="move(1)"
      />
    </div>
    <div v-if="show" class="suggest-dropdown">
      <template v-if="kw.trim()">
        <div
          v-for="(s, i) in suggestions"
          :key="s.code"
          class="suggest-item"
          :class="{ active: i === activeIndex }"
          @mousedown.prevent="select(s)"
        >
          <span class="s-name">{{ s.name }}</span>
          <span class="s-code">{{ s.code }}</span>
          <span class="s-type">{{ s.type }}</span>
          <span
            class="s-watch"
            :class="{ watched: isWatched(s.code) }"
            @mousedown.stop.prevent
            @click.stop="toggleWatch(s)"
          >{{ isWatched(s.code) ? '已自选' : '+ 自选' }}</span>
        </div>
        <div v-if="!suggestions.length" class="suggest-empty">未找到匹配结果</div>
      </template>
      <template v-else>
        <div v-if="history.length" class="suggest-history">
          <div class="suggest-hist-head">
            <span>搜索历史</span>
            <span class="suggest-clear" @mousedown.stop.prevent @click.stop="clearHistory">清空</span>
          </div>
          <div
            v-for="(s, i) in history"
            :key="s.code"
            class="suggest-item"
            :class="{ active: i === activeIndex }"
            @mousedown.prevent="select(s)"
          >
            <span class="s-name">{{ s.name || '代码' }}</span>
            <span class="s-code">{{ s.code }}</span>
            <span class="s-type">{{ s.type }}</span>
            <span
              class="s-watch"
              :class="{ watched: isWatched(s.code) }"
              @mousedown.stop.prevent
              @click.stop="toggleWatch(s)"
            >{{ isWatched(s.code) ? '已自选' : '+ 自选' }}</span>
          </div>
        </div>
        <div v-else class="suggest-empty">暂无搜索历史</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { api } from '../api.js'
import { isWatched, toggleWatch as tw } from '../composables/useWatchlist.js'
import { logAction } from '../composables/useActionLog.js'

const props = defineProps({
  placeholder: { type: String, default: '代码 / 名称 / 拼音（首字母或全拼）' },
  autofocus: { type: Boolean, default: false },
})
const emit = defineEmits(['select', 'toggle'])

const kw = ref('')
const suggestions = ref([])
const show = ref(false)
const activeIndex = ref(0)
const inputEl = ref(null)
let debounceTimer = null

watch(() => props.autofocus, async (v) => {
  if (v) {
    await nextTick()
    inputEl.value && inputEl.value.focus()
  }
}, { immediate: true })

// ---------------- 搜索历史（localStorage） ----------------
const HISTORY_KEY = 'search_history'
const MAX_HISTORY = 10

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch (e) { return [] }
}
function saveHistory() {
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value)) } catch (e) { /* ignore */ }
}
const history = ref(loadHistory())

function addHistory(s) {
  if (!s || !s.code) return
  history.value = history.value.filter(h => h.code !== s.code)
  history.value.unshift({ code: s.code, name: s.name || '', type: s.type || '' })
  if (history.value.length > MAX_HISTORY) history.value = history.value.slice(0, MAX_HISTORY)
  saveHistory()
}

function clearHistory() {
  history.value = []
  saveHistory()
}

/** 当前展示列表：有输入显示搜索结果，无输入显示历史 */
const currentList = computed(() => kw.value.trim() ? suggestions.value : history.value)

async function toggleWatch(s) {
  if (!s || !s.code) return
  await tw(s.code)
  emit('toggle', s)
}

async function doSearch() {
  const q = kw.value.trim()
  if (!q) {
    suggestions.value = []
    show.value = history.value.length > 0
    activeIndex.value = 0
    return
  }
  try {
    const list = await api.search(q, 10)
    suggestions.value = list
    activeIndex.value = 0
    show.value = true
    logAction('search', q, `hits=${list.length}`)
  } catch (e) { /* 搜索失败静默 */ }
}

function onInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(doSearch, 200)
}

function onFocus() {
  if (kw.value.trim()) doSearch()
  else if (history.value.length) { show.value = true; activeIndex.value = 0 }
}

function onBlur() {
  setTimeout(() => { show.value = false }, 200)
}

function move(d) {
  if (!show.value || !currentList.value.length) return
  activeIndex.value = (activeIndex.value + d + currentList.value.length) % currentList.value.length
}

function onEnter() {
  const s = currentList.value[activeIndex.value] || currentList.value[0]
  if (s) { select(s); return }
  const k = kw.value.trim()
  if (/^\d{6}$/.test(k)) {
    addHistory({ code: k, name: '', type: '' })
    emit('select', { code: k, name: '', market: null })
  }
}

function select(s) {
  addHistory(s)
  emit('select', s)
  kw.value = ''
  suggestions.value = []
  show.value = false
}
</script>

<style scoped>
.suggest-wrap { position: relative; }

.search-box {
  display: flex; align-items: center;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 0 10px; height: 32px; width: 240px;
}
.search-box input {
  background: transparent; border: none; outline: none; color: var(--text);
  width: 100%; font-size: 13px;
}
.search-box input::placeholder { color: var(--text-dim); }

.suggest-dropdown {
  position: absolute; top: 38px; left: 0; z-index: 300;
  min-width: 320px; width: max-content;
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  max-height: 360px; overflow-y: auto;
}
body.light .suggest-dropdown { box-shadow: 0 8px 24px rgba(31, 36, 43, 0.15); }

.suggest-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 14px; cursor: pointer; font-size: 13px;
  transition: background 0.1s;
}
.suggest-item:hover, .suggest-item.active { background: var(--bg-hover); }
.s-name { font-weight: 600; color: var(--text); }
.s-code { color: var(--text-dim); font-size: 12px; font-variant-numeric: tabular-nums; }
.s-type { color: var(--text-dim); font-size: 11px; }
.s-watch {
  margin-left: auto; font-size: 12px; cursor: pointer; font-weight: 700;
  color: var(--accent); background: var(--accent-bg); border: 1px solid var(--accent);
  border-radius: 6px; padding: 2px 8px; white-space: nowrap;
}
.s-watch:hover { opacity: 0.85; }
.s-watch.watched { color: var(--text-dim); background: var(--kv-bg); border-color: var(--border); font-weight: 600; }
.suggest-empty { padding: 14px; color: var(--text-dim); text-align: center; font-size: 12px; }
.suggest-history { max-height: 360px; overflow-y: auto; }
.suggest-hist-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 14px 4px; font-size: 12px; color: var(--text-dim);
  border-bottom: 1px solid var(--border);
}
.suggest-clear { cursor: pointer; font-weight: 700; color: var(--text-dim); }
.suggest-clear:hover { color: var(--accent); }
</style>
