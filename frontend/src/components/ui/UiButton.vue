<template>
  <button
    class="ui-btn"
    :class="[variant, size, { disabled }]"
    :type="type"
    :disabled="disabled || loading"
    @click="onClick"
  >
    <span v-if="loading" class="ui-btn-spinner"></span>
    <slot />
  </button>
</template>

<script setup>
const props = defineProps({
  variant: { type: String, default: 'default' }, // default | primary | ghost | danger | subtle
  size: { type: String, default: 'md' }, // sm | md
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['click'])
function onClick(e) {
  if (props.disabled || props.loading) return
  emit('click', e)
}
</script>

<style scoped>
.ui-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  border-radius: 6px; border: 1px solid transparent; cursor: pointer;
  font-size: 13px; font-weight: 600; line-height: 1; white-space: nowrap;
  user-select: none; transition: all 0.15s; font-family: inherit;
}
.ui-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.ui-btn:disabled, .ui-btn.disabled { opacity: 0.5; cursor: not-allowed; }

.ui-btn.md { height: 32px; padding: 0 14px; }
.ui-btn.sm { height: 26px; padding: 0 10px; font-size: 12px; }

/* default：描边按钮 */
.ui-btn.default {
  border-color: var(--border); background: var(--bg-card); color: var(--text);
}
.ui-btn.default:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }

/* primary：强调按钮 */
.ui-btn.primary {
  background: var(--accent); color: #fff;
}
.ui-btn.primary:hover:not(:disabled) { opacity: 0.88; }

/* ghost：无背景轻量按钮 */
.ui-btn.ghost {
  border-color: transparent; background: transparent; color: var(--text-dim);
}
.ui-btn.ghost:hover:not(:disabled) { color: var(--accent); background: var(--bg-hover); }

/* danger：危险操作 */
.ui-btn.danger {
  border-color: var(--border); background: transparent; color: var(--text-dim);
}
.ui-btn.danger:hover:not(:disabled) { color: var(--up); border-color: var(--up); }

/* subtle：弱化强调（同 primary 浅底） */
.ui-btn.subtle {
  border-color: var(--accent); background: var(--accent-bg); color: var(--accent);
}
.ui-btn.subtle:hover:not(:disabled) { opacity: 0.85; }

.ui-btn-spinner {
  width: 12px; height: 12px; border-radius: 50%;
  border: 2px solid currentColor; border-top-color: transparent;
  animation: ui-btn-spin 0.7s linear infinite;
}
@keyframes ui-btn-spin { to { transform: rotate(360deg); } }
</style>
