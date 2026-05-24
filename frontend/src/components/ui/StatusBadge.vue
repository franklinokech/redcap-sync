<script setup>
defineProps({
  status: { type: String, required: true },
})

const map = {
  pending:   { label: 'Pending',   cls: 'bg-slate-100 text-slate-600' },
  running:   { label: 'Running',   cls: 'bg-blue-100  text-blue-700'  },
  completed: { label: 'Completed', cls: 'bg-green-100 text-green-700' },
  failed:    { label: 'Failed',    cls: 'bg-red-100   text-red-700'   },
  cancelled: { label: 'Cancelled', cls: 'bg-yellow-100 text-yellow-700' },
}
</script>

<template>
  <span
      :class="[
      'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
      map[status]?.cls ?? 'bg-slate-100 text-slate-600',
    ]"
  >
    {{ map[status]?.label ?? status }}
  </span>
</template>
