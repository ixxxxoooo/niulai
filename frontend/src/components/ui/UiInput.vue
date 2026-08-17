<template>
  <input
    ref="inputEl"
    class="ui-input"
    :class="{ full }"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :min="min"
    :max="max"
    :step="step"
    :accept="accept"
    @input="onInput"
    @change="onChange"
    @focus="$emit('focus', $event)"
    @blur="$emit('blur', $event)"
  />
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' }, // text | number | password | date | file
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  full: { type: Boolean, default: false },
  min: { type: [String, Number], default: undefined },
  max: { type: [String, Number], default: undefined },
  step: { type: [String, Number], default: undefined },
  accept: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur'])

const inputEl = ref(null)
defineExpose({ focus: () => inputEl.value && inputEl.value.focus() })

function onInput(e) {
  let v = e.target.value
  if (props.type === 'number') {
    if (v === '') v = ''
    else if (!isNaN(Number(v))) v = Number(v)
  }
  emit('update:modelValue', v)
}
function onChange(e) {
  emit('change', e)
}
</script>

<style scoped>
.ui-input {
  height: 32px; padding: 0 12px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text);
  font-size: 13px; outline: none; font-family: inherit;
  transition: border-color 0.15s;
}
.ui-input::placeholder { color: var(--text-dim); }
.ui-input:focus { border-color: var(--accent); }
.ui-input:disabled { opacity: 0.5; cursor: not-allowed; }
.ui-input[type="date"] { -webkit-appearance: none; appearance: none; }
.ui-input.full { width: 100%; box-sizing: border-box; }
.ui-input[type="file"] { height: auto; padding: 6px 12px; font-size: 12px; }
</style>
