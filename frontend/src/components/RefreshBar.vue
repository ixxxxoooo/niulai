<template>
  <div class="refresh-bar">
    <span class="dot" :class="{ active: refreshing }"></span>
    <span>自动刷新 {{ intervalText }}</span>
    <span v-if="countdown != null" class="countdown">{{ countdown }}s 后刷新</span>
    <span>· 上次 {{ lastUpdated || '--:--:--' }}</span>
    <span v-if="refreshing" style="color: var(--accent)">刷新中…</span>
    <span class="spacer"></span>
    <button class="btn-mini" @click="refresh">立即刷新</button>
  </div>
</template>

<script setup>
defineProps({
  intervalText: { type: String, default: '5 秒' },
  countdown: { type: Number, default: null },
  lastUpdated: { type: String, default: '' },
  refreshing: { type: Boolean, default: false },
})
defineEmits(['refresh'])
</script>
