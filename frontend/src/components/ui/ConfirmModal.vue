<!-- src/components/ui/ConfirmModal.vue -->
<template>
  <Modal :title="title" @close="emit('cancel')">
    <div class="space-y-4">
      <p class="text-sm text-gray-600">{{ message }}</p>
      <div class="flex justify-end gap-3">
        <button @click="emit('cancel')" class="btn-secondary">Cancel</button>
        <button
            @click="emit('confirm')"
            :disabled="loading"
            :class="confirmClass || 'btn-danger'"
            class="flex items-center gap-2"
        >
          <Spinner v-if="loading" class="w-4 h-4" />
          {{ loading ? 'Processing…' : confirmLabel }}
        </button>
      </div>
    </div>
  </Modal>
</template>

<script setup>
import Modal   from './Modal.vue'
import Spinner from './Spinner.vue'
defineProps({
  title:        { type: String, default: 'Confirm' },
  message:      { type: String, default: 'Are you sure?' },
  confirmLabel: { type: String, default: 'Confirm' },
  confirmClass: { type: String, default: '' },
  loading:      { type: Boolean, default: false },
})
defineEmits(['confirm', 'cancel'])
</script>
