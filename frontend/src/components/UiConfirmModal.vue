<template>
  <Teleport to="body">
    <div v-if="confirmState.open" class="modal-mask" @click.self="handleCancel">
      <div class="modal-card confirm-modal-card">
        <div class="confirm-hd">
          <div class="confirm-title">
            <span class="confirm-badge" :class="'badge-' + confirmState.variant">
              {{ confirmState.variant === 'danger' ? '⚠️' : (confirmState.variant === 'warning' ? '⚡' : 'ℹ️') }}
            </span>
            <span class="confirm-title-text">{{ confirmState.title }}</span>
          </div>
          <button class="confirm-close-btn" @click="handleCancel" title="关闭">✕</button>
        </div>

        <div class="confirm-bd">
          <div class="confirm-message">{{ confirmState.message }}</div>
          <div v-if="confirmState.detail" class="confirm-detail">{{ confirmState.detail }}</div>
        </div>

        <div class="confirm-ft">
          <button class="btn-dialog btn-cancel" @click="handleCancel">
            {{ confirmState.cancelText }}
          </button>
          <button class="btn-dialog" :class="'btn-' + confirmState.variant" @click="handleConfirm">
            {{ confirmState.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * 全局自绘确认弹窗组件（符合牛来暗色金融设计规范）
 * @author ygw
 */
import { confirmState, handleConfirm, handleCancel } from '../composables/useConfirm.js'
</script>

<style scoped>
.confirm-modal-card {
  width: 90%;
  max-width: 440px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: 0 16px 40px rgba(0, 0, 0, .45);
  padding: 0 !important;
  overflow: hidden;
  animation: modalPop .15s ease-out;
}
@keyframes modalPop {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
.confirm-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.confirm-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.confirm-badge {
  font-size: 14px;
  line-height: 1;
}
.confirm-title-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}
.confirm-close-btn {
  border: none;
  background: transparent;
  color: var(--text-dim);
  font-size: 14px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: all .12s;
}
.confirm-close-btn:hover {
  color: var(--text);
  background: var(--bg-hover);
}

.confirm-bd {
  padding: 20px 18px 16px;
}
.confirm-message {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  font-weight: 500;
  white-space: pre-line;
}
.confirm-detail {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-dim);
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin-top: 10px;
  white-space: pre-line;
}

.confirm-ft {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 18px 16px;
  background: var(--bg-card);
}
.btn-dialog {
  padding: 7px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all .15s ease;
}
.btn-dialog:active {
  transform: scale(0.97);
}
.btn-cancel {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-dim);
}
.btn-cancel:hover {
  background: var(--bg-hover);
  color: var(--text);
  border-color: var(--text-dim);
}
.btn-danger {
  background: var(--up);
  border: 1px solid var(--up);
  color: #fff;
}
.btn-danger:hover {
  filter: brightness(1.1);
  box-shadow: 0 4px 12px rgba(240, 68, 68, .3);
}
.btn-primary {
  background: var(--accent);
  border: 1px solid var(--accent);
  color: #fff;
}
.btn-primary:hover {
  filter: brightness(1.1);
  box-shadow: 0 4px 12px rgba(76, 154, 255, .3);
}
.btn-warning {
  background: var(--yellow);
  border: 1px solid var(--yellow);
  color: #000;
}
.btn-warning:hover {
  filter: brightness(1.1);
}
</style>
