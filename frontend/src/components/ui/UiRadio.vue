<template>
  <label class="ui-radio" :class="{ on: checked }">
    <input
      type="radio"
      :checked="checked"
      :value="value"
      :disabled="disabled"
      @change="onChange"
    />
    <span class="ui-radio-dot"></span>
    <span v-if="label" class="ui-radio-label">{{ label }}</span>
    <slot />
  </label>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: '' },
  checked: { type: Boolean, default: null },
  value: { type: [String, Number], default: undefined },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])
function onChange(e) {
  emit('update:modelValue', e.target.value)
  emit('change', e)
}
</script>

<style scoped>
.ui-radio {
  display: inline-flex; align-items: center; gap: 7px;
  cursor: pointer; user-select: none; font-size: 13px; color: var(--text);
}
.ui-radio input { position: absolute; opacity: 0; width: 0; height: 0; }
.ui-radio-dot {
  width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0;
  border: 1px solid var(--border); background: var(--bg-card);
  display: inline-flex; align-items: center; justify-content: center;
  transition: all 0.15s;
}
.ui-radio-dot::after {
  content: ''; width: 8px; height: 8px; border-radius: 50%;
  background: transparent; transition: background 0.15s;
}
.ui-radio.on .ui-radio-dot { border-color: var(--accent); }
.ui-radio.on .ui-radio-dot::after { background: var(--accent); }
.ui-radio:hover .ui-radio-dot { border-color: var(--accent); }
.ui-radio:has(input:disabled) { opacity: 0.5; cursor: not-allowed; }
</style>
