<template>
  <div class="tabs">
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
</template>

<script setup>
/**
 * 大盘模块统一顶部导航 Tab（总览 / 全球 / 云图）
 * 严格遵循系统原生 .tabs 全局样式规范
 * @author ygw
 */
import { navigate } from '../router.js'

defineProps({
  currentTab: { type: String, required: true },
})

function go(path) {
  navigate(path)
}
</script>
