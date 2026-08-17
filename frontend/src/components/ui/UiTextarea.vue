<template>
  <textarea
    class="ui-textarea"
    :class="{ full }"
    :value="modelValue"
    :rows="rows"
    :placeholder="placeholder"
    :disabled="disabled"
    @input="onInput"
    @change="onChange"
  ></textarea>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, default: '' },
  rows: { type: [String, Number], default: 4 },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  full: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])
function onInput(e) {
  emit('update:modelValue', e.target.value)
}
function onChange(e) {
  emit('change', e)
}
</script>

<style scoped>
.ui-textarea {
  width: 100%; padding: 8px 12px; border-radius: 6px;
  border: 1px solid var(--border); background: var(--bg-card); color: var(--text);
  font-size: 13px; outline: none; font-family: inherit; resize: vertical;
  transition: border-color 0.15s; box-sizing: border-box;
}
.ui-textarea::placeholder { color: var(--text-dim); }
.ui-textarea:focus { border-color: var(--accent); }
.ui-textarea:disabled { opacity: 0.5; cursor: not-allowed; }
.ui-textarea.full { width: 100%; }
</style>
