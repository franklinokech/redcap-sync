<script setup>
defineProps({
  label:   { type: String,           required: true },
  value:   { type: [Number, String], default: 0 },
  icon:    { type: String,           default: null },
  color:   { type: String,           default: 'slate' }, // slate | green | yellow | red | blue
  loading: { type: Boolean,          default: false },
})
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm flex items-start gap-4">
    <!-- Icon blob -->
    <div
        v-if="icon"
        :class="[
        'flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-xl',
        color === 'green'  && 'bg-green-100 text-green-600',
        color === 'yellow' && 'bg-yellow-100 text-yellow-600',
        color === 'red'    && 'bg-red-100 text-red-600',
        color === 'blue'   && 'bg-blue-100 text-blue-600',
        color === 'slate'  && 'bg-slate-100 text-slate-600',
      ]"
    >
      <span>{{ icon }}</span>
    </div>

    <div class="flex-1 min-w-0">
      <p class="text-sm text-slate-500 truncate">{{ label }}</p>
      <!-- Loading skeleton -->
      <div
          v-if="loading"
          class="mt-1 h-7 w-16 animate-pulse rounded bg-slate-200"
      />
      <p v-else class="mt-0.5 text-2xl font-semibold text-slate-800">
        {{ value ?? 0 }}
      </p>
    </div>
  </div>
</template>
