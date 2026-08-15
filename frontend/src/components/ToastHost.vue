<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-host">
      <div v-for="t in toastState.items" :key="t.id" class="toast" :class="t.type">
        <svg v-if="t.type === 'error'" class="toast-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="9" /><path d="M12 8v4.5M12 15.5v.01" />
        </svg>
        <svg v-else class="toast-icon" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 6 9 17l-5-5" />
        </svg>
        <span>{{ t.message }}</span>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { toastState } from '../composables/useToast.js'
</script>

<style scoped>
.toast-host {
  position: fixed; top: 62px; right: 16px;
  z-index: 10000;
  display: flex; flex-direction: column; align-items: flex-end; gap: 8px;
  pointer-events: none;
}
.toast {
  display: flex; align-items: center; gap: 8px;
  max-width: 320px;
  padding: 10px 14px;
  background: var(--bg-card); border: 1px solid var(--border);
  border-left: 3px solid var(--down);
  border-radius: 8px;
  font-size: 13px; color: var(--text);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.toast.error { border-left-color: var(--up); }
.toast-icon { flex-shrink: 0; color: var(--down); }
.toast.error .toast-icon { color: var(--up); }

.toast-enter-active, .toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(24px); }
</style>