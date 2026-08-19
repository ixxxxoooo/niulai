<template>
  <label class="ui-checkbox" :class="{ on: isChecked }">
    <input
      type="checkbox"
      :checked="isChecked"
      :value="value"
      :disabled="disabled"
      @change="onChange"
    />
    <span class="ui-checkbox-box">
      <svg v-if="isChecked" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5" /></svg>
    </span>
    <span v-if="label" class="ui-checkbox-label">{{ label }}</span>
    <slot />
  </label>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [Array, Boolean], default: false },
  checked: { type: Boolean, default: null },
  value: { type: [String, Number], default: undefined },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

const isChecked = computed(() => {
  if (props.checked != null) return props.checked
  if (Array.isArray(props.modelValue)) return props.modelValue.includes(props.value)
  return !!props.modelValue
})

function onChange(e) {
  const el = e.target
  if (Array.isArray(props.modelValue)) {
    let next
    if (el.checked) {
      next = props.modelValue.includes(props.value) ? props.modelValue : [...props.modelValue, props.value]
    } else {
      next = props.modelValue.filter(v => v !== props.value)
    }
    emit('update:modelValue', next)
  } else if (props.modelValue !== undefined && typeof props.modelValue === 'boolean') {
    emit('update:modelValue', el.checked)
  }
  emit('change', e)
}
</script>

<style scoped>
.ui-checkbox {
  display: inline-flex; align-items: center; gap: 7px;
  cursor: pointer; user-select: none; font-size: 13px; color: var(--text);
}
.ui-checkbox input { position: absolute; opacity: 0; width: 0; height: 0; }
.ui-checkbox-box {
  width: 16px; height: 16px; border-radius: 4px; flex-shrink: 0;
  border: 1px solid var(--border); background: var(--bg-card);
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; transition: all 0.15s;
}
.ui-checkbox.on .ui-checkbox-box {
  background: var(--accent); border-color: var(--accent);
}
.ui-checkbox:hover .ui-checkbox-box { border-color: var(--accent); }
.ui-checkbox:has(input:disabled) { opacity: 0.5; cursor: not-allowed; }
</style>
