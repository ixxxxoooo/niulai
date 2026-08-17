<template>
  <div class="ui-select" :class="{ full }">
    <select
      :value="modelValue"
      :disabled="disabled"
      @change="onChange"
    >
      <slot />
    </select>
    <span class="ui-select-caret">
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6" /></svg>
    </span>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  disabled: { type: Boolean, default: false },
  full: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])
function onChange(e) {
  emit('update:modelValue', e.target.value)
  emit('change', e)
}
</script>

<style scoped>
.ui-select { position: relative; display: inline-flex; align-items: center; }
.ui-select select {
  height: 32px; width: 100%; padding: 0 30px 0 12px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text);
  font-size: 13px; outline: none; cursor: pointer; font-family: inherit;
  appearance: none; -webkit-appearance: none; transition: border-color 0.15s;
}
.ui-select select:focus { border-color: var(--accent); }
.ui-select select:disabled { opacity: 0.5; cursor: not-allowed; }
.ui-select-caret {
  position: absolute; right: 10px; display: inline-flex;
  color: var(--text-dim); pointer-events: none;
}
.ui-select.full select { width: 100%; }
</style>
