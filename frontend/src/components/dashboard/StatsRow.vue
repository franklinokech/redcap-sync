<!-- src/components/dashboard/StatsRow.vue -->
<script setup>
import StatCard from '@/components/ui/StatCard.vue'

defineProps({
  /**
   * Expects the normalised apiStats object from useSyncStore:
   * { total, pending, running, completed, failed, cancelled, ... }
   */
  counts: {
    type: Object,
    default: () => ({
      total: 0, pending: 0, running: 0,
      completed: 0, failed: 0, cancelled: 0,
    }),
  },
  loading: { type: Boolean, default: false },
})
</script>

<template>
  <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
    <StatCard
        label="Total Jobs"
        :value="counts.total"
        icon="📋"
        color="slate"
        :loading="loading"
    />
    <StatCard
        label="Running"
        :value="counts.running"
        icon="⚙️"
        color="blue"
        :loading="loading"
    />
    <StatCard
        label="Completed"
        :value="counts.completed"
        icon="✅"
        color="green"
        :loading="loading"
    />
    <StatCard
        label="Failed"
        :value="counts.failed"
        icon="❌"
        color="red"
        :loading="loading"
    />
    <StatCard
        label="Pending"
        :value="counts.pending"
        icon="⏳"
        color="yellow"
        :loading="loading"
    />
  </div>
</template>
