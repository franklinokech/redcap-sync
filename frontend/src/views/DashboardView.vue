<!-- src/views/DashboardView.vue -->
<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useSyncStore }  from '@/stores/sync.js'
import { useAuthStore }  from '@/stores/auth.js'
import StatsRow          from '@/components/dashboard/StatsRow.vue'
import RecentJobsTable   from '@/components/dashboard/RecentJobsTable.vue'
import ServiceHealth     from '@/components/dashboard/ServiceHealth.vue'

const sync = useSyncStore()
const auth = useAuthStore()

let timer = null

onMounted(async () => {
  await sync.refresh()
  timer = setInterval(sync.refresh, 30_000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="space-y-6">

    <!-- Page header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-slate-800">Dashboard</h1>
        <p class="mt-0.5 text-sm text-slate-500">
          Welcome back,
          {{ auth.user?.first_name || auth.user?.username || 'there' }}
        </p>
      </div>

      <button
          class="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white
               px-3 py-2 text-sm text-slate-600 shadow-sm hover:bg-slate-50
               transition-colors disabled:opacity-50"
          :disabled="sync.loadingStats || sync.loadingJobs"
          @click="sync.refresh()"
      >
        <span
            class="text-base"
            :class="{ 'animate-spin': sync.loadingStats || sync.loadingJobs }"
        >
          🔄
        </span>
        Refresh
      </button>
    </div>

    <!-- Error banner -->
    <div
        v-if="sync.hasError"
        class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
    >
      {{ sync.error }}
    </div>

    <!-- ✅ Use apiStats (from /api/sync/stats/) not statusCounts (local array) -->
    <StatsRow
        :counts="sync.apiStats"
        :loading="sync.loadingStats"
    />

    <!-- Main content grid -->
    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div class="lg:col-span-2">
        <RecentJobsTable
            :jobs="sync.recentJobs"
            :loading="sync.loadingJobs"
        />
      </div>
      <div>
        <ServiceHealth />
      </div>
    </div>

  </div>
</template>
