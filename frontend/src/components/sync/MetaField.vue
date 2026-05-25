<template>
  <div>
    <dt class="text-xs text-gray-400 uppercase tracking-wide">{{ label }}</dt>
    <dd class="text-sm font-medium text-gray-800 mt-0.5 capitalize">{{ value || '—' }}</dd>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null },
})
</script>
