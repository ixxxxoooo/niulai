<template>
  <div>
    <Sectors v-if="tab === 'list'" />
    <SectorMoves v-else />
  </div>
</template>

<script setup>
/**
 * 板块一级页：内部子 Tab 切换「板块分析」「板块资金」
 * @author ygw
 */
import { ref, watch } from 'vue'
import Sectors from './Sectors.vue'
import SectorMoves from './SectorMoves.vue'

const props = defineProps({
  sector: { type: String, default: '' },
  flow: { type: Boolean, default: false },
})

const tab = ref(props.flow ? 'flow' : 'list')
watch(() => props.flow, f => { tab.value = f ? 'flow' : 'list' })
</script>