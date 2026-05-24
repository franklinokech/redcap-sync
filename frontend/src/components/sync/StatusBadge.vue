<template>
  <span :class="[baseClass, config.class, sizeClass]">
    <span v-if="config.dot" :class="['w-1.5 h-1.5 rounded-full mr-1.5', config.dot]" />
    {{ config.label }}
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  size:   { type: String, default: 'md' },   // 'sm' | 'md' | 'lg'
})

const baseClass = 'inline-flex items-center font-medium rounded-full'

const sizeClass = computed(() => ({
  sm: 'px-2 py-0.5 text-[10px]',
  md: 'px-2.5 py-0.5 text-xs',
  lg: 'px-3 py-1 text-sm',
}[props.size] ?? 'px-2.5 py-0.5 text-xs'))

const STATUS_MAP = {
  pending:   { label: 'Pending',   class: 'bg-yellow-100 text-yellow-700', dot: 'bg-yellow-500' },
  running:   { label: 'Running',   class: 'bg-blue-100   text-blue-700',   dot: 'bg-blue-500 animate-pulse' },
  success:   { label: 'Success',   class: 'bg-green-100  text-green-700',  dot: 'bg-green-500' },
  failed:    { label: 'Failed',    class: 'bg-red-100    text-red-700',    dot: 'bg-red-500' },
  cancelled: { label: 'Cancelled', class: 'bg-gray-100   text-gray-500',   dot: 'bg-gray-400' },
}

const config = computed(() =>
    STATUS_MAP[props.status] ?? { label: props.status, class: 'bg-gray-100 text-gray-600' }
)
</script>
