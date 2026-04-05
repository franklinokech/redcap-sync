<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal fade-in">
        <div class="modal-header">
          <h3 class="modal-title">{{ title }}</h3>
          <button class="btn-icon" @click="$emit('close')">✕</button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div v-if="$slots.footer" class="modal-footer">
          <slot name="footer" />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({ title: String })
defineEmits(['close'])
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.modal {
  background: var(--c-bg-2);
  border: 1px solid var(--c-border);
  border-radius: 14px;
  width: 100%; max-width: 480px;
  max-height: 90vh;
  display: flex; flex-direction: column;
  box-shadow: var(--shadow-lg);
}
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 18px 20px; border-bottom: 1px solid var(--c-border);
}
.modal-title { font-size: 15px; font-weight: 600; }
.btn-icon {
  background: none; border: none; cursor: pointer;
  color: var(--c-text-3); font-size: 14px;
  padding: 4px 6px; border-radius: 4px;
}
.btn-icon:hover { color: var(--c-text); background: var(--c-bg-3); }

.modal-body {
  padding: 20px;
  overflow-y: auto;
  display: flex; flex-direction: column; gap: 14px;
}
.modal-footer {
  padding: 14px 20px; border-top: 1px solid var(--c-border);
  display: flex; justify-content: flex-end; gap: 8px;
}
</style>