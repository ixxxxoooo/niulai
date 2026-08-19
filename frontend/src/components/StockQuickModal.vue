<template>
  <Teleport to="body">
    <div v-if="open" class="modal-mask stock-modal-mask" @click.self="close">
      <div class="modal-card stock-fullview-card">
        <!-- 弹窗顶部栏 -->
        <div class="modal-card-topbar">
          <div class="topbar-left">
            <span class="stock-quick-title">⚡ 个股详情速览</span>
            <span class="stock-quick-code" v-if="code">{{ code }}</span>
          </div>
          <div class="topbar-right">
            <button class="topbar-btn accent" @click="goToFullscreen" title="在新页面全屏打开">
              <UiIcon name="external" :size="13" />
              <span>全屏主页</span>
            </button>
            <button class="topbar-btn close-btn" @click="close" title="关闭 (Esc)">✕</button>
          </div>
        </div>

        <!-- 嵌入完整 Stock.vue 页面 -->
        <div class="modal-stock-scroll-body">
          <StockView :code="code" :key="code" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { navigate } from '../router.js'
import { openStock } from '../composables/useStockMeta.js'
import UiIcon from './ui/UiIcon.vue'
import StockView from '../views/Stock.vue'

const props = defineProps({
  code: { type: String, default: '' },
  name: { type: String, default: '' },
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['update:open'])

function close() {
  emit('update:open', false)
}

function goToFullscreen() {
  close()
  openStock({ code: props.code, name: props.name }, {
    origin: '/screener',
    originLabel: '返回选股',
  })
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.open) {
    close()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.stock-modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.78);
  backdrop-filter: blur(6px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.stock-fullview-card {
  width: 95vw;
  max-width: 1280px;
  height: 90vh;
  max-height: 92vh;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.75);
  display: flex;
  flex-direction: column;
  padding: 0 !important;
  overflow: hidden;
  animation: modalScaleIn .16s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modalScaleIn {
  from { opacity: 0; transform: scale(0.96) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-card-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-quick-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.stock-quick-code {
  font-size: 13px;
  color: var(--accent);
  background: var(--accent-bg);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--border);
  background: var(--kv-bg);
  color: var(--text-dim);
  font-size: 12px;
  cursor: pointer;
  transition: all .15s;
}

.topbar-btn:hover {
  border-color: var(--accent);
  color: var(--text);
}

.topbar-btn.accent {
  background: var(--accent-bg);
  color: var(--accent);
  border-color: rgba(76, 154, 255, 0.4);
  font-weight: 600;
}

.topbar-btn.accent:hover {
  background: var(--accent);
  color: #ffffff;
}

.topbar-btn.close-btn {
  width: 26px;
  height: 26px;
  padding: 0;
  border-radius: 50%;
  justify-content: center;
  font-size: 13px;
}

.topbar-btn.close-btn:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.modal-stock-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px 30px;
  background: var(--bg);
}
</style>
