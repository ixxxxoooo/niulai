<template>
  <div class="market-nav-bar mb16">
    <div class="tabs market-tabs">
      <button
        class="tab"
        :class="{ active: currentTab === 'overview' }"
        @click="go('/')"
      >
        🇨🇳 盘面总览
      </button>
      <button
        class="tab"
        :class="{ active: currentTab === 'global' }"
        @click="go('/global')"
      >
        🌐 全球外盘
      </button>
      <button
        class="tab"
        :class="{ active: currentTab === 'heatmap' }"
        @click="go('/heatmap')"
      >
        🗺️ 大盘云图
      </button>
    </div>
  </div>
</template>

<script setup>
/**
 * 大盘模块统一顶部导航 Tab（总览 / 全球 / 云图）
 * @author ygw
 */
import { navigate } from '../router.js'

defineProps({
  currentTab: { type: String, required: true }, // 'overview' | 'global' | 'heatmap'
})

function go(path) {
  navigate(path)
}
</script>

<style scoped>
.market-nav-bar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}
.market-tabs {
  margin-bottom: 0;
}
</style>
