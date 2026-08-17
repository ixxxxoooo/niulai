<template>
  <button type="button" class="btn-back" @click="onBack">
    <UiIcon name="chevronLeft" :size="14" />
    {{ label }}
  </button>
</template>

<script setup>
// @author ygw
import { navigate } from '../router.js'

const props = defineProps({
  label: { type: String, default: '返回' },
  fallback: { type: String, default: '/' },
  /** 有固定返回页时优先跳转（个股左右切换后仍回入口） */
  to: { type: String, default: '' },
})

function onBack() {
  if (props.to) {
    navigate(props.to)
    return
  }
  if (history.length > 1) history.back()
  else navigate(props.fallback)
}
</script>
