<template>
  <span
    v-if="info"
    class="bdg-role"
    :class="info.role === '中军' ? 'bdg-army' : 'bdg-core'"
    :data-tooltip="`【${info.sector} · ${info.role === '中军' ? '容量中军' : '核心灵魂'}】&#10;定位：${info.title}`"
  >
    {{ info.role }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { getStockRole } from '../constants/stockLeaders.js'

const props = defineProps({
  code: { type: [String, Number], default: '' },
})

const info = computed(() => getStockRole(props.code))
</script>

<style scoped>
.bdg-role {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  line-height: 1.2;
  padding: 1px 4px;
  border-radius: 3px;
  vertical-align: middle;
  margin-left: 4px;
  cursor: help;
  user-select: none;
  white-space: nowrap;
  letter-spacing: 0.5px;
  transition: all 0.15s ease;
}

/* 核心：活力金橙色 */
.bdg-core {
  background: rgba(255, 159, 10, 0.16);
  color: #ff9f0a;
  border: 1px solid rgba(255, 159, 10, 0.45);
}
.bdg-core:hover {
  background: rgba(255, 159, 10, 0.3);
  border-color: #ff9f0a;
  box-shadow: 0 0 4px rgba(255, 159, 10, 0.4);
}

/* 中军：沉稳科技紫蓝色 */
.bdg-army {
  background: rgba(167, 139, 250, 0.16);
  color: #a78bfa;
  border: 1px solid rgba(167, 139, 250, 0.45);
}
.bdg-army:hover {
  background: rgba(167, 139, 250, 0.3);
  border-color: #a78bfa;
  box-shadow: 0 0 4px rgba(167, 139, 250, 0.4);
}
</style>
