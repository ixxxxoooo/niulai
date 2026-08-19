<template>
  <div v-if="open" class="modal-mask" @click.self="close">
    <div class="modal-card group-manage-card">
      <div class="modal-hd">
        <div class="modal-hd-title">
          <span class="hd-main">自选分组管理</span>
          <span class="hd-sub">按住左侧手柄拖拽排序，支持新建、重命名或删除</span>
        </div>
        <button class="modal-close-btn" @click="close" title="关闭">✕</button>
      </div>

      <div class="modal-bd">
        <!-- 新建分组栏 -->
        <div class="new-group-box mb16">
          <UiInput
            v-model="newGroupName"
            placeholder="输入新分组名称（例如：算力芯片、消费电子、光伏储能）…"
            class="new-group-input"
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
                <th style="width:50px;text-align:center">排序</th>
                <th>分组名称</th>
                <th style="width:90px;text-align:center">股票数量</th>
                <th style="width:150px;text-align:right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(g, idx) in groups"
                :key="g.id"
                draggable="true"
                :class="{ 'row-dragging': dragIndex === idx, 'row-drag-over': dragOverIndex === idx }"
                @dragstart="onDragStart(idx, $event)"
                @dragover.prevent="onDragOver(idx, $event)"
                @dragenter.prevent="dragOverIndex = idx"
                @dragleave="onDragLeave(idx, $event)"
                @drop="onDrop(idx, $event)"
                @dragend="onDragEnd"
              >
                <td class="order-cell">
                  <span class="drag-handle" title="按住拖拽调整顺序">⋮⋮</span>
                </td>
                <td class="name-col">
                  <div v-if="editingId === g.id" class="edit-row">
                    <UiInput v-model="editName" size="sm" class="edit-input" @keydown.enter="saveRename(g)" />
                    <UiButton size="sm" variant="primary" @click="saveRename(g)">保存</UiButton>
                    <UiButton size="sm" variant="ghost" @click="editingId = null">取消</UiButton>
                  </div>
                  <div v-else class="name-display">
                    <span class="g-icon">{{ groupIcon(g.name) }}</span>
                    <span class="g-name">{{ g.name }}</span>
                  </div>
                </td>
                <td style="text-align:center">
                  <span class="count-pill">{{ g.count || 0 }} 只</span>
                </td>
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
                      :disabled="busy"
                      @click="doDeleteGroup(g)"
                    >删除</UiButton>
                  </div>
                </td>
              </tr>
              <tr v-if="!groups.length">
                <td colspan="4" class="empty-cell">暂无自定义分组，可输入名称创建或导入热门预设。</td>
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
              title="一键补全光通信、PCB、先进封装、存储芯片等 8 大热门赛道及核心龙头股票"
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
import { showConfirm } from '../composables/useConfirm.js'
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

function groupIcon(name) {
  if (/光通信|CPO/i.test(name)) return '📡'
  if (/PCB|覆铜/i.test(name)) return '🖨️'
  if (/封装|Chiplet|HBM/i.test(name)) return '🧩'
  if (/存储|内存/i.test(name)) return '💾'
  if (/半导体|芯片|设备|自主可控/i.test(name)) return '🛡️'
  if (/AI硬件|算力|服务器/i.test(name)) return '🖥️'
  if (/AI软件|大模型|软件/i.test(name)) return '🌐'
  if (/消费电子|苹果|华为/i.test(name)) return '📱'
  if (/锂电|固态电池|电池/i.test(name)) return '🔋'
  if (/电网|特高压|电力设备/i.test(name)) return '⚡'
  if (/光伏|储能|太阳能/i.test(name)) return '☀️'
  if (/券商|证券|互联网金融/i.test(name)) return '📈'
  if (/商业航天|卫星/i.test(name)) return '🛰️'
  if (/军工|航发|航空|船舶/i.test(name)) return '✈️'
  if (/贵金属|小金属|黄金|稀土|有色/i.test(name)) return '🥇'
  if (/化工|化纤|制冷剂/i.test(name)) return '🛢️'
  if (/创新药|医药|CXO|生物/i.test(name)) return '🧪'
  if (/白酒|酒|食品/i.test(name)) return '🍶'
  if (/银行/i.test(name)) return '🏦'
  if (/能源|石油|煤炭|油气/i.test(name)) return '⛽'
  if (/机器人|具身/i.test(name)) return '🤖'
  if (/低空|eVTOL|飞行/i.test(name)) return '🚁'
  return '📁'
}

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
  const confirmed = await showConfirm({
    title: '删除分组确认',
    message: `确定删除分组「${g.name}」吗？`,
    detail: '提示：该分组下的股票仍会保留在自选「全部」及其他所属分组中。',
    confirmText: '确认删除',
    variant: 'danger',
  })
  if (!confirmed) return
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

const dragIndex = ref(null)
const dragOverIndex = ref(null)

function onDragStart(idx, e) {
  dragIndex.value = idx
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(idx))
  }
}

function onDragOver(idx, e) {
  if (dragIndex.value === null || dragIndex.value === idx) return
  dragOverIndex.value = idx
}

function onDragLeave(idx, e) {
  if (dragOverIndex.value === idx) {
    dragOverIndex.value = null
  }
}

async function onDrop(idx, e) {
  if (dragIndex.value === null || dragIndex.value === idx) {
    onDragEnd()
    return
  }
  const list = [...groups.value]
  const [moved] = list.splice(dragIndex.value, 1)
  list.splice(idx, 0, moved)
  onDragEnd()

  busy.value = true
  error.value = ''
  try {
    await reorderGroups(list.map(g => g.id))
    emit('changed')
  } catch (err) {
    error.value = '拖拽排序保存失败：' + err.message
  } finally {
    busy.value = false
  }
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

async function doInitPresets() {
  const confirmed = await showConfirm({
    title: '导入热门预设确认',
    message: '确定导入/补全全部 22 大核心热门赛道及头部龙头股票吗？',
    detail: '包括：光通信、PCB、先进封装、存储芯片、半导体自主可控、AI软件、消费电子、锂电池、电网、光伏储能、券商、商业航天、国防军工、贵金属、化工、创新药、白酒、银行、能源、机器人、低空经济、ETF 等。',
    confirmText: '立即导入',
    variant: 'primary',
  })
  if (!confirmed) return
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
.group-manage-card {
  width: 92%;
  max-width: 760px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: 0 16px 40px rgba(0, 0, 0, .4);
  padding: 0 !important; /* 覆盖全局 modal-card 默认 padding，使顶栏与边框完美贴合 */
  overflow: hidden;
}
.modal-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.modal-hd-title { display: flex; align-items: baseline; gap: 10px; }
.hd-main { font-size: 16px; font-weight: 600; color: var(--text); }
.hd-sub { font-size: 12px; color: var(--text-dim); }

.modal-close-btn {
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 16px;
  line-height: 1;
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all .15s ease;
}
.modal-close-btn:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.modal-bd {
  padding: 18px 20px 20px;
}

.new-group-box { display: flex; gap: 10px; align-items: center; }
.new-group-box .ui-input { flex: 1; }

.group-table-wrap {
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  max-height: 420px; overflow-y: auto; background: var(--bg-card);
}
.group-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.group-table th {
  background: var(--bg-hover); color: var(--text-dim); font-weight: 600;
  padding: 10px 14px; text-align: left; position: sticky; top: 0; z-index: 1;
  border-bottom: 1px solid var(--border);
}
.group-table td {
  padding: 10px 14px; border-bottom: 1px solid var(--border); vertical-align: middle;
}
.group-table tbody tr:last-child td {
  border-bottom: none;
}
.group-table tbody tr {
  transition: background .15s ease, opacity .15s ease;
}
.group-table tbody tr.row-dragging {
  opacity: 0.35;
  background: var(--bg-hover);
}
.group-table tbody tr.row-drag-over {
  background: var(--accent-bg);
  border-top: 2px solid var(--accent);
}

.order-cell { text-align: center; }
.drag-handle {
  cursor: grab; color: var(--text-dim); font-size: 14px; font-weight: 600;
  user-select: none; padding: 4px 8px; border-radius: 4px;
  display: inline-block; transition: all .12s;
}
.drag-handle:hover { color: var(--text); background: var(--bg-hover); }
.drag-handle:active { cursor: grabbing; }

.name-display { display: flex; align-items: center; gap: 8px; }
.g-icon { font-size: 15px; line-height: 1; }
.g-name { font-weight: 600; color: var(--text); font-size: 14px; }
.count-pill {
  display: inline-block; font-size: 12px; padding: 2px 8px; border-radius: 10px;
  background: var(--bg-hover); color: var(--text-dim); font-variant-numeric: tabular-nums;
}

.edit-row { display: flex; gap: 8px; align-items: center; }
.edit-row .edit-input { width: 180px; }
.td-actions { display: inline-flex; align-items: center; gap: 8px; }

.empty-cell {
  text-align: center; padding: 32px 16px; color: var(--text-dim); font-size: 13px;
}

.modal-footer-box {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 14px; border-top: 1px solid var(--border);
}
.success-banner {
  background: var(--down-bg); color: var(--down); padding: 8px 14px;
  border-radius: var(--radius-sm); font-size: 13px; border: 1px solid var(--down);
}
.mb16 { margin-bottom: 16px; }
.mb12 { margin-bottom: 12px; }
.mt16 { margin-top: 16px; }
</style>
