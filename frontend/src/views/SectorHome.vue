<template>
  <div>
    <Sectors v-if="tab === 'list'" />
    <SectorMoves v-else-if="tab === 'flow'" />
    <SectorStrength v-else />
  </div>
</template>

<script setup>
/**
 * 板块一级页：内部子 Tab 切换「板块分析」「板块资金」「板块强度」
 * @author ygw
 */
import { ref, watch } from 'vue'
import Sectors from './Sectors.vue'
import SectorMoves from './SectorMoves.vue'
import SectorStrength from './SectorStrength.vue'

const props = defineProps({
  sector: { type: String, default: '' },
  flow: { type: Boolean, default: false },
  strength: { type: Boolean, default: false },
})

const tab = ref(props.strength ? 'strength' : props.flow ? 'flow' : 'list')
watch(() => [props.flow, props.strength], ([f, s]) => { tab.value = s ? 'strength' : f ? 'flow' : 'list' })
</script>