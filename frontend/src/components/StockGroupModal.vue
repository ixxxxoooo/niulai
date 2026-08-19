<template>
  <div v-if="open" class="modal-mask" @click.self="close">
    <div class="modal-card">
      <div class="modal-hd">
        <span>自选分组 · {{ name || code }}</span>
        <UiButton size="sm" variant="ghost" @click="close">关闭</UiButton>
      </div>
      <div class="modal-bd">
        <div class="tip-text mb12">勾选该股票所属的分组（可多选）：</div>
        
        <div class="group-checkbox-list">
          <label v-for="g in watchState.groups" :key="g.id" class="group-check-item">
            <UiCheckbox v-model="selectedGroupIds" :value="g.id" />
            <span class="group-name">{{ g.name }}</span>
            <span class="group-count">（{{ g.count || 0 }}只）</span>
          </label>
        </div>

        <div class="new-group-row mt12">
          <UiInput v-model="newGroupName" placeholder="新建分组名称…" @keydown.enter="quickCreateGroup" />
          <UiButton size="sm" variant="ghost" :disabled="!newGroupName.trim() || creating" @click="quickCreateGroup">
            {{ creating ? '创建中…' : '+ 创建' }}
          </UiButton>
        </div>

        <div class="error-banner mt8" v-if="error">{{ error }}</div>

        <div class="modal-actions mt16">
          <UiButton variant="ghost" @click="close">取消</UiButton>
          <UiButton variant="primary" :disabled="saving" @click="save">
            {{ saving ? '保存中…' : '保存设置' }}
          </UiButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 股票多分组分配弹窗
 * @author ygw
 */
import { ref, watch } from 'vue'
import { watchState, getStockGroups, setStockGroups, createGroup, loadGroups } from '../composables/useWatchlist.js'
import UiButton from './ui/UiButton.vue'
import UiInput from './ui/UiInput.vue'
import UiCheckbox from './ui/UiCheckbox.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  code: { type: String, default: '' },
  name: { type: String, default: '' },
})

const emit = defineEmits(['close', 'saved'])

const selectedGroupIds = ref([])
const newGroupName = ref('')
const saving = ref(false)
const creating = ref(false)
const error = ref('')

async function initData() {
  error.value = ''
  newGroupName.value = ''
  if (!props.code) return
  try {
    if (!watchState.groups.length) {
      await loadGroups()
    }
    const gids = await getStockGroups(props.code)
    selectedGroupIds.value = gids.length ? gids : [1]
  } catch (e) {
    error.value = '加载分组失败：' + e.message
  }
}

watch(() => props.open, (v) => {
  if (v) initData()
})

async function quickCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  creating.value = true
  error.value = ''
  try {
    const grp = await createGroup(name)
    if (grp && grp.id) {
      selectedGroupIds.value.push(grp.id)
    }
    newGroupName.value = ''
  } catch (e) {
    error.value = '创建分组失败：' + e.message
  } finally {
    creating.value = false
  }
}

async function save() {
  if (!props.code) return
  saving.value = true
  error.value = ''
  try {
    await setStockGroups(props.code, selectedGroupIds.value)
    emit('saved', { code: props.code, groupIds: selectedGroupIds.value })
    emit('close')
  } catch (e) {
    error.value = '保存失败：' + e.message
  } finally {
    saving.value = false
  }
}

function close() {
  emit('close')
}
</script>

<style scoped>
.tip-text { font-size: 13px; color: var(--text-dim); }
.group-checkbox-list {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px; max-height: 240px; overflow-y: auto; padding: 4px 2px;
}
.group-check-item {
  display: flex; align-items: center; gap: 6px; cursor: pointer;
  padding: 6px 8px; border-radius: var(--radius-sm); background: var(--bg-hover);
  transition: background .12s;
}
.group-check-item:hover { background: var(--border); }
.group-name { font-size: 13px; font-weight: 500; color: var(--text); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.group-count { font-size: 12px; color: var(--text-dim); }
.new-group-row { display: flex; gap: 8px; align-items: center; }
.new-group-row .ui-input { flex: 1; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; }
.mb12 { margin-bottom: 12px; }
.mt8 { margin-top: 8px; }
.mt12 { margin-top: 12px; }
.mt16 { margin-top: 16px; }
</style>
