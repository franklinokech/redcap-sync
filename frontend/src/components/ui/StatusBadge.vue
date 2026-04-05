<template>
  <span class="badge" :class="`badge-${status}`">
    <span v-if="status === 'running'" class="pulse">●</span>
    <span v-else>{{ dot }}</span>
    {{ status }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ status: String })
const dot = computed(() => ({
  success: '●', failed: '●', pending: '○',
  cancelled: '○', warning: '●',
}[props.status] || '○'))
</script>