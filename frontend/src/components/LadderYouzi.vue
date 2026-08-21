<template>
  <span
    v-if="items.length"
    class="yz-host"
    @mouseenter="onEnter"
    @mouseleave="onLeave"
    @click.stop
  >
    <span class="yz-tag" :class="{ lhasa: hasLhasa }">游</span>
    <Teleport to="body">
      <div
        v-if="visible"
        class="yz-pop"
        :style="pos"
        @mouseenter="onEnter"
        @mouseleave="onLeave"
        @click.stop
      >
        <div class="yz-hd">游资</div>
        <div class="yz-body">
          <span
            v-for="y in items"
            :key="y"
            class="youzi-badge"
            :class="{ lhasa: y.includes('拉萨') }"
            :title="`查看 ${y} 买入动向`"
            @click.stop="goSeat(y)"
          >{{ y }}</span>
        </div>
      </div>
    </Teleport>
  </span>
</template>

<script setup>
// 连板梯队游资徽章：卡片上仅显示「游」小徽章，悬浮弹出具体游资徽章列表
// @author ygw
import { ref, computed, onUnmounted } from 'vue'
import { navigate } from '../router.js'

const props = defineProps({
  youzi: { type: Array, default: () => [] },
})

const items = computed(() => (props.youzi || []).filter(Boolean))
const hasLhasa = computed(() => items.value.some(y => y.includes('拉萨')))

const visible = ref(false)
const pos = ref({ left: '0px', top: '0px' })
let timer = null

function place(e) {
  const w = 260
  const h = 90
  const x = Math.min((e?.clientX || 0) + 14, window.innerWidth - w - 14)
  const y = Math.min((e?.clientY || 0) + 14, window.innerHeight - h - 14)
  pos.value = { left: x + 'px', top: y + 'px' }
}

function onEnter(e) {
  if (!items.value.length) return
  place(e)
  clearTimeout(timer)
  visible.value = true
}

function onLeave() {
  clearTimeout(timer)
  timer = setTimeout(() => { visible.value = false }, 160)
}

function goSeat(nickname) {
  navigate('/seats?nick=' + encodeURIComponent(nickname))
}

onUnmounted(() => {
  clearTimeout(timer)
})
</script>

<style scoped>
.yz-host { display: inline-flex; align-items: center; }
.yz-tag {
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; line-height: 1;
  min-width: 16px; height: 16px; padding: 0 4px; border-radius: var(--radius-sm);
  background: var(--yellow-bg); color: var(--yellow); border: 1px solid var(--yellow);
  cursor: pointer; user-select: none; transition: transform .12s;
}
.yz-tag:hover { transform: scale(1.12); }
.yz-tag.lhasa { background: var(--up); color: #fff; border-color: var(--up); }
.yz-pop {
  position: fixed; z-index: 400;
  width: 260px; background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  padding: 8px; pointer-events: auto;
}
.yz-hd { font-size: 12px; font-weight: 600; color: var(--text-dim); padding: 0 2px 6px; }
.yz-body { display: flex; flex-wrap: wrap; gap: 4px; }
</style>