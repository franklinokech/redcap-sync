<!-- src/components/registry/TokenValidationBadge.vue -->
<template>
  <div class="token-validation">
    <!-- Idle: just the button -->
    <button
        v-if="state.status === 'idle'"
        class="btn btn-sm btn-outline-secondary"
        :disabled="disabled"
        @click="$emit('validate')"
    >
      <i class="bi bi-plug me-1"></i>Test
    </button>

    <!-- Checking -->
    <button
        v-else-if="state.status === 'checking'"
        class="btn btn-sm btn-outline-secondary"
        disabled
    >
      <span class="spinner-border spinner-border-sm me-1" role="status"></span>
      Checking…
    </button>

    <!-- Valid -->
    <div v-else-if="state.status === 'valid'" class="d-flex align-items-center gap-2">
      <span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1">
        <i class="bi bi-check-circle-fill me-1"></i>Valid
      </span>
      <span
          v-if="state.meta"
          class="text-muted small"
          :title="`REDCap v${state.meta.redcap_version}`"
      >
        {{ state.meta.project_title }}
      </span>
      <button
          class="btn btn-sm btn-link text-muted p-0"
          title="Re-test"
          @click="$emit('validate')"
      >
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>

    <!-- Invalid -->
    <div v-else-if="state.status === 'invalid'" class="d-flex align-items-center gap-2">
      <span
          class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1"
          :title="state.message"
      >
        <i class="bi bi-x-circle-fill me-1"></i>Invalid
      </span>
      <span class="text-danger small text-truncate" style="max-width: 200px;" :title="state.message">
        {{ state.message }}
      </span>
      <button
          class="btn btn-sm btn-link text-muted p-0"
          title="Retry"
          @click="$emit('validate')"
      >
        <i class="bi bi-arrow-clockwise"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  state: {
    type: Object,
    default: () => ({ status: 'idle', message: null, meta: null }),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['validate'])
</script>

<style scoped>
.token-validation {
  display: inline-flex;
  align-items: center;
  min-width: 120px;
}
</style>
