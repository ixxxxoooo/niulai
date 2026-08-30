<template>
  <div class="tool-nav-bar mb16">
    <div class="tabs tool-tabs">
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
  </div>
</template>

<script setup>
/**
 * 工具模块统一顶部导航 Tab（条件选股 / 盯盘监控 / 事件日历）
 * @author ygw
 */
import { navigate } from '../router.js'

defineProps({
  currentTab: { type: String, required: true }, // 'screener' | 'alerts' | 'calendar'
})

function go(path) {
  navigate(path)
}
</script>

<style scoped>
.tool-nav-bar {
  display: flex;
  align-items: center;
}
.tool-tabs {
  margin-bottom: 0;
}
</style>
