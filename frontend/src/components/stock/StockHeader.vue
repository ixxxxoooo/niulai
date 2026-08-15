<template>
  <div class="stock-head">
    <BackButton :label="backLabel" :to="backTo" :fallback="backTo || '/'" />
    <button v-if="nav.hasList" class="btn-nav-idx" :disabled="!nav.canPrev" @click="$emit('sibling', -1)" title="上一只">◀</button>
    <BoardBadges :row="badgeRow" />
    <span class="name">{{ displayName }}</span>
    <button v-if="nav.hasList" class="btn-nav-idx" :disabled="!nav.canNext" @click="$emit('sibling', 1)" title="下一只">▶</button>
    <span class="industry-tag" v-if="industry">{{ industry }}</span>
    <span class="code">{{ code }}</span>
    <span v-if="nav.hasList" class="nav-pos">{{ nav.index + 1 }}/{{ nav.total }}</span>
    <button class="btn-watch" :class="{ on: isWatched }" @click="$emit('toggle-watch')">
      <template v-if="isWatched">已自选</template>
      <template v-else><span class="plus">+</span>自选</template>
    </button>
    <button class="btn-ghost" @click="$emit('add-alert')">+ 监控</button>
    <a class="source-link" :href="eastmoneyUrl" target="_blank" rel="noopener">东财↗</a>
    <a class="source-link" :href="baiduUrl" target="_blank" rel="noopener">百度↗</a>
    <span v-if="dataSource" class="src-tag" :title="sourceTip">{{ dataSource }}</span>
    <span class="quote-time">行情时间：{{ quoteTime || '-' }}</span>
  </div>
</template>

<script setup>
/**
 * 个股页顶栏：返回/切换/自选/监控/外链
 * @author ygw
 */
import BackButton from '../BackButton.vue'
import BoardBadges from '../BoardBadges.vue'

defineProps({
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
  quoteTime: { type: String, default: '' },
  dataSource: { type: String, default: '' },
  sourceTip: { type: String, default: '' },
})
defineEmits(['sibling', 'toggle-watch', 'add-alert'])
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
.src-tag {
  display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 3px;
  background: var(--kv-bg); color: var(--text-dim); border: 1px solid var(--border);
}
</style>
