<template>
  <div class="bg-white rounded-lg border border-gray-200 px-4 py-3 shadow-sm">
    <div :class="['text-xl font-bold', variantClass]">{{ value }}</div>
    <div class="text-xs text-gray-500 mt-0.5">{{ label }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label:   { type: String, required: true },
  value:   { type: [String, Number], default: '—' },
  variant: { type: String, default: 'default' },
})

const variantClass = computed(() => ({
  default: 'text-gray-900',
  success: 'text-green-600',
  danger:  'text-red-600',
  warning: 'text-amber-600',
}[props.variant] ?? 'text-gray-900'))
</script>
