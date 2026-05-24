<!-- src/components/ui/InfoRow.vue -->
<template>
  <div class="flex flex-col gap-0.5">
    <span class="text-xs text-gray-400 uppercase tracking-wide">{{ label }}</span>
    <a v-if="link && value !== '—'" :href="value" target="_blank"
       class="text-sm text-blue-600 hover:underline truncate">{{ value }}</a>
    <StatusBadge v-else-if="badge" :status="value" />
    <span v-else class="text-sm text-gray-800" :class="mono ? 'font-mono' : ''">{{ value }}</span>
  </div>
</template>

<script setup>
import StatusBadge from './StatusBadge.vue'
defineProps({
  label: String,
  value: { type: [String, Number], default: '—' },
  link:  { type: Boolean, default: false },
  badge: { type: Boolean, default: false },
  mono:  { type: Boolean, default: false },
})
</script>
