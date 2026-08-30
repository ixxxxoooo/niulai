<template>
  <div class="tabs">
    <button
      class="tab"
      :class="{ active: currentTab === 'screener' }"
      @click="go('/screener')"
    >
      🎯 条件选股
    </button>
    <button
      class="tab"
      :class="{ active: currentTab === 'alerts' }"
      @click="go('/alerts')"
    >
      🔔 盯盘监控
    </button>
    <button
      class="tab"
      :class="{ active: currentTab === 'calendar' }"
      @click="go('/calendar')"
    >
      📅 事件日历
    </button>
  </div>
</template>

<script setup>
/**
 * 工具模块统一顶部导航 Tab（条件选股 / 盯盘监控 / 事件日历）
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
