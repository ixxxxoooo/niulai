<template>
  <span class="bdg-wrap" v-if="items.length">
    <span v-for="b in items" :key="b.t" class="bdg" :class="'bdg-' + b.cls">{{ b.t }}</span>
  </span>
</template>

<script setup>
// 科创 / 创业 / ST / 北交 徽标
// @author ygw
import { computed } from 'vue'
import { boardBadges } from '../utils.js'

const props = defineProps({
  row: { type: Object, default: () => ({}) },
  code: { type: String, default: '' },
  name: { type: String, default: '' },
})

const items = computed(() => boardBadges(props.row?.code ? props.row : {
  code: props.code, name: props.name, board: props.row.board, is_st: props.row.is_st,
}))
</script>
