<template>
  <div v-if="open" class="modal-mask" @click.self="close">
    <div class="modal-card group-manage-card">
      <div class="modal-hd">
        <span>自选分组管理</span>
        <UiButton size="sm" variant="ghost" @click="close">关闭</UiButton>
      </div>

      <div class="modal-bd">
        <!-- 新建分组栏 -->
        <div class="new-group-box mb16">
          <UiInput
            v-model="newGroupName"
            placeholder="输入新分组名称（如：算力芯片、消费电子）…"
            @keydown.enter="doCreateGroup"
          />
          <UiButton variant="primary" :disabled="!newGroupName.trim() || busy" @click="doCreateGroup">
            + 添加分组
          </UiButton>
        </div>

        <div class="error-banner mb12" v-if="error">{{ error }}</div>
        <div class="success-banner mb12" v-if="successMsg">{{ successMsg }}</div>

        <!-- 分组列表 -->
        <div class="group-table-wrap">
          <table class="group-table">
            <thead>
              <tr>
                <th style="width:40px">排序</th>
                <th>分组名称</th>
                <th style="width:80px;text-align:center">股票数</th>
                <th style="width:140px;text-align:right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(g, idx) in groups" :key="g.id">
                <td class="order-cell">
                  <div class="order-btns">
                    <button
                      class="btn-order"
                      :disabled="idx === 0 || busy"
                      @click="moveOrder(idx, -1)"
                      title="上移"
                    >▲</button>
                    <button
                      class="btn-order"
                      :disabled="idx === groups.length - 1 || busy"
                      @click="moveOrder(idx, 1)"
                      title="下移"
                    >▼</button>
                  </div>
                </td>
                <td class="name-col">
                  <div v-if="editingId === g.id" class="edit-row">
                    <UiInput v-model="editName" size="sm" @keydown.enter="saveRename(g)" />
                    <UiButton size="sm" variant="ghost" @click="saveRename(g)">保存</UiButton>
                    <UiButton size="sm" variant="ghost" @click="editingId = null">取消</UiButton>
                  </div>
                  <div v-else class="name-display">
                    <span class="g-name">{{ g.name }}</span>
                    <span v-if="g.id === 1" class="default-badge">默认</span>
                  </div>
                </td>
                <td style="text-align:center;font-variant-numeric:tabular-nums">{{ g.count || 0 }}</td>
                <td style="text-align:right">
                  <div class="td-actions">
                    <UiButton
                      size="sm"
                      variant="ghost"
                      v-if="editingId !== g.id"
                      @click="startRename(g)"
                    >重命名</UiButton>
                    <UiButton
                      size="sm"
                      variant="danger"
                      v-if="g.id !== 1"
                      :disabled="busy"
                      @click="doDeleteGroup(g)"
                    >删除</UiButton>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 底部快捷预设与提示 -->
        <div class="modal-footer-box mt16">
          <div class="footer-left">
            <UiButton
              size="sm"
              variant="subtle"
              :disabled="busy"
              @click="doInitPresets"
              title="一键补全光通信、PCB、先进封装、存储芯片等热门赛道及核心龙头股票"
            >
              ⚡ 导入/补全热门预设分组
            </UiButton>
          </div>
          <div class="footer-right">
            <UiButton variant="primary" @click="close">完成</UiButton>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * 自选分组管理弹窗
 * @author ygw
 */
import { ref, computed, watch } from 'vue'
import {
  watchState,
  loadGroups,
  createGroup,
  renameGroup,
  deleteGroup,
  reorderGroups,
  initPresetGroups,
} from '../composables/useWatchlist.js'
import UiButton from './ui/UiButton.vue'
import UiInput from './ui/UiInput.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'changed'])

const newGroupName = ref('')
const editingId = ref(null)
const editName = ref('')
const busy = ref(false)
const error = ref('')
const successMsg = ref('')

const groups = computed(() => watchState.groups)

watch(() => props.open, (v) => {
  if (v) {
    error.value = ''
    successMsg.value = ''
    editingId.value = null
    newGroupName.value = ''
    loadGroups()
  }
})

async function doCreateGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  busy.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await createGroup(name)
    newGroupName.value = ''
    successMsg.value = `分组「${name}」创建成功`
    emit('changed')
  } catch (e) {
    error.value = '创建分组失败：' + e.message
  } finally {
    busy.value = false
  }
}

function startRename(g) {
  editingId.value = g.id
  editName.value = g.name
}

async function saveRename(g) {
  const name = editName.value.trim()
  if (!name || name === g.name) {
    editingId.value = null
    return
  }
  busy.value = true
  error.value = ''
  try {
    await renameGroup(g.id, name)
    editingId.value = null
    emit('changed')
  } catch (e) {
    error.value = '重命名失败：' + e.message
  } finally {
    busy.value = false
  }
}

async function doDeleteGroup(g) {
  if (!confirm(`确定删除分组「${g.name}」吗？\n该分组下的股票不会被删除，仅移除该分组标签。`)) return
  busy.value = true
  error.value = ''
  try {
    await deleteGroup(g.id)
    successMsg.value = `分组「${g.name}」已删除`
    emit('changed')
  } catch (e) {
    error.value = '删除失败：' + e.message
  } finally {
    busy.value = false
  }
}

async function moveOrder(idx, delta) {
  const targetIdx = idx + delta
  if (targetIdx < 0 || targetIdx >= groups.value.length) return
  const list = [...groups.value]
  const item = list.splice(idx, 1)[0]
  list.splice(targetIdx, 0, item)
  busy.value = true
  error.value = ''
  try {
    await reorderGroups(list.map(g => g.id))
    emit('changed')
  } catch (e) {
    error.value = '排序更新失败：' + e.message
  } finally {
    busy.value = false
  }
}

async function doInitPresets() {
  if (!confirm('确定导入/补全 8 大热门产业链赛道（光通信、PCB、先进封装、存储芯片、人形机器人、低空经济、半导体等）及其核心龙头股票吗？')) return
  busy.value = true
  error.value = ''
  successMsg.value = ''
  try {
    await initPresetGroups()
    successMsg.value = '热门预设分组与核心标的已成功导入/补全！'
    emit('changed')
  } catch (e) {
    error.value = '导入失败：' + e.message
  } finally {
    busy.value = false
  }
}

function close() {
  emit('close')
}
</script>

<style scoped>
.group-manage-card { max-width: 620px; }
.new-group-box { display: flex; gap: 8px; align-items: center; }
.new-group-box .ui-input { flex: 1; }
.group-table-wrap {
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  max-height: 380px; overflow-y: auto;
}
.group-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.group-table th {
  background: var(--bg-hover); color: var(--text-dim); font-weight: 500;
  padding: 8px 12px; text-align: left; position: sticky; top: 0; z-index: 1;
}
.group-table td {
  padding: 8px 12px; border-top: 1px solid var(--border); vertical-align: middle;
}
.order-btns { display: flex; flex-direction: column; gap: 2px; }
.btn-order {
  border: none; background: transparent; cursor: pointer; color: var(--text-dim);
  font-size: 9px; line-height: 1; padding: 2px; border-radius: 2px;
}
.btn-order:hover:not(:disabled) { background: var(--bg-hover); color: var(--text); }
.btn-order:disabled { opacity: .25; cursor: not-allowed; }
.name-display { display: flex; align-items: center; gap: 6px; }
.g-name { font-weight: 500; color: var(--text); }
.default-badge {
  font-size: 10px; padding: 1px 5px; border-radius: 3px;
  background: var(--accent-bg); color: var(--accent); font-weight: 600;
}
.edit-row { display: flex; gap: 6px; align-items: center; }
.edit-row .ui-input { width: 140px; }
.td-actions { display: inline-flex; align-items: center; gap: 6px; }
.modal-footer-box {
  display: flex; justify-content: space-between; align-items: center;
}
.success-banner {
  background: var(--down-bg); color: var(--down); padding: 6px 12px;
  border-radius: var(--radius-sm); font-size: 12px; border: 1px solid var(--down);
}
.mb16 { margin-bottom: 16px; }
.mb12 { margin-bottom: 12px; }
.mt16 { margin-top: 16px; }
</style>
