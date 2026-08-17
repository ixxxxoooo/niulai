<template>
  <Teleport to="body">
    <div v-if="visible" class="global-tip" :style="{ left: x + 'px', top: y + 'px' }">{{ text }}</div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const visible = ref(false)
const text = ref('')
const x = ref(0)
const y = ref(0)

function position(e) {
  const pad = 14
  x.value = e.clientX + pad
  y.value = e.clientY + pad
  requestAnimationFrame(() => {
    const tip = document.querySelector('.global-tip')
    if (tip) {
      const r = tip.getBoundingClientRect()
      if (r.right > window.innerWidth) x.value = e.clientX - r.width - pad
      if (r.bottom > window.innerHeight) y.value = e.clientY - r.height - pad
      if (x.value < 0) x.value = 4
      if (y.value < 0) y.value = 4
    }
  })
}

function onMove(e) { position(e) }

function onMouseOver(e) {
  const el = e.target && e.target.closest ? e.target.closest('[data-tip]') : null
  if (el && el.dataset.tip) {
    text.value = el.dataset.tip
    visible.value = true
    position(e)
    document.addEventListener('mousemove', onMove)
  }
}

function onMouseOut(e) {
  const el = e.target && e.target.closest ? e.target.closest('[data-tip]') : null
  const to = e.relatedTarget
  if (!el || !(to && el.contains(to))) {
    visible.value = false
    document.removeEventListener('mousemove', onMove)
  }
}

onMounted(() => {
  document.addEventListener('mouseover', onMouseOver)
  document.addEventListener('mouseout', onMouseOut)
})
onUnmounted(() => {
  document.removeEventListener('mouseover', onMouseOver)
  document.removeEventListener('mouseout', onMouseOut)
  document.removeEventListener('mousemove', onMove)
})
</script>

<style scoped>
.global-tip {
  position: fixed; z-index: 9999; max-width: 340px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 12px; font-size: 12px; line-height: 1.65;
  color: var(--text); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  pointer-events: none;
}
body.light .global-tip { box-shadow: 0 8px 24px rgba(27, 31, 35, 0.12); }
</style>
