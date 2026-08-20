<template>
  <span
    v-if="leader"
    class="bdg-leader"
    :data-tooltip="`【${leader.sector} 核心龙头】&#10;定位：${leader.title}`"
  >
    龙头
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { getLeaderInfo } from '../constants/stockLeaders.js'

const props = defineProps({
  code: { type: [String, Number], default: '' },
})

const leader = computed(() => getLeaderInfo(props.code))
</script>

<style scoped>
.bdg-leader {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.2;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(255, 159, 10, 0.16);
  color: #ff9f0a;
  border: 1px solid rgba(255, 159, 10, 0.45);
  vertical-align: middle;
  margin-left: 4px;
  cursor: help;
  user-select: none;
  white-space: nowrap;
  letter-spacing: 0.5px;
  transition: all 0.15s ease;
}
.bdg-leader:hover {
  background: rgba(255, 159, 10, 0.3);
  border-color: #ff9f0a;
  box-shadow: 0 0 4px rgba(255, 159, 10, 0.4);
}
</style>
