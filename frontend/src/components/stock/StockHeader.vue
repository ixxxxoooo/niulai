<template>
  <div class="stock-head">
    <BackButton :label="backLabel" :to="backTo" :fallback="backTo || '/'" />
    <button v-if="nav.hasList" class="btn-nav-idx" :disabled="!nav.canPrev" @click="$emit('sibling', -1)" title="上一只">◀</button>
    <BoardBadges :row="badgeRow" />
    <span class="name">{{ displayName }}</span>
    <button v-if="nav.hasList" class="btn-nav-idx" :disabled="!nav.canNext" @click="$emit('sibling', 1)" title="下一只">▶</button>
    <span class="industry-tag" v-if="industry" :title="`查看行业板块：${industry}`" @click="gotoIndustry">{{ industry }}</span>
    <span class="code">{{ code }}</span>
    <span v-if="nav.hasList" class="nav-pos">{{ nav.index + 1 }}/{{ nav.total }}</span>
    <button class="btn-watch" :class="{ on: isWatched }" @click="$emit('toggle-watch')">
      <template v-if="isWatched">已自选</template>
      <template v-else><span class="plus">+</span>自选</template>
    </button>
    <button class="btn-bell" @click="$emit('add-alert')" title="设置监控/提醒">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
    </button>
    <button class="source-link link-ai" @click="$emit('open-ai')" title="AI 智能分析">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/></svg>
      AI分析
    </button>
    <a class="source-link" :href="eastmoneyUrl" target="_blank" rel="noopener">东财↗</a>
    <a class="source-link" :href="baiduUrl" target="_blank" rel="noopener">百度↗</a>
    <a class="source-link link-wencai" :href="iwencaiUrl" target="_blank" rel="noopener">问财↗</a>
  </div>
</template>

<script setup>
/**
 * 个股页顶栏：返回/切换/自选/监控/外链
 * @author ygw
 */
import BackButton from '../BackButton.vue'
import BoardBadges from '../BoardBadges.vue'
import { api } from '../../api.js'
import { navigate } from '../../router.js'

const props = defineProps({
  backLabel: { type: String, default: '返回' },
  backTo: { type: String, default: '' },
  nav: { type: Object, default: () => ({ hasList: false, canPrev: false, canNext: false, index: 0, total: 0 }) },
  badgeRow: { type: Object, default: () => ({}) },
  displayName: { type: String, default: '' },
  industry: { type: String, default: '' },
  code: { type: String, default: '' },
  isWatched: { type: Boolean, default: false },
  eastmoneyUrl: { type: String, default: '#' },
  baiduUrl: { type: String, default: '#' },
  iwencaiUrl: { type: String, default: '#' },
  quoteTime: { type: String, default: '' },
  dataSource: { type: String, default: '' },
  sourceTip: { type: String, default: '' },
})
defineEmits(['sibling', 'toggle-watch', 'add-alert', 'open-ai'])

async function gotoIndustry() {
  const name = props.industry
  if (!name) return
  try {
    const res = await api.sectorConceptCode(name, 'industry')
    if (res && res.code) navigate(`/sector/${res.code}`)
  } catch (e) { /* 无映射时忽略 */ }
}
</script>

<style scoped>
.btn-nav-idx {
  border: 1px solid var(--border); background: var(--bg); color: var(--text);
  width: 28px; height: 28px; border-radius: 6px; cursor: pointer; font-size: 12px;
  display: inline-flex; align-items: center; justify-content: center; padding: 0;
}
.btn-nav-idx:hover:not(:disabled) { background: var(--accent-bg); color: var(--accent); border-color: var(--accent); }
.btn-nav-idx:disabled { opacity: 0.35; cursor: not-allowed; }
.nav-pos { font-size: 12px; color: var(--text-dim); margin-right: 4px; }
.btn-bell {
  border: none; background: transparent; color: var(--text-dim);
  height: 26px; padding: 0 8px; border-radius: 6px; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.btn-bell:hover { color: var(--accent); background: var(--accent-bg); }
.link-ai {
  background: #d7f2ff; color: #0284c7; font-weight: 600;
  border: 1px solid #7dd3fc;
  display: inline-flex; align-items: center; gap: 4px;
}
.link-ai:hover { color: #fff; background: #0ea5e9; border-color: #0ea5e9; }
.src-tag {
  display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 3px;
  background: var(--kv-bg); color: var(--text-dim); border: 1px solid var(--border);
}
.link-wencai {
  background: #fff3cd; color: #1a56a8; font-weight: 600;
  border: 1px solid #bfdbfe;
}
.link-wencai:hover {
  color: #fff; background: #1a56a8; border-color: #1a56a8;
}
</style>
