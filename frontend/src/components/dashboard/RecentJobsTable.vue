<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const props = defineProps({
  jobs:    { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
})

const router = useRouter()

const skeletonRows = Array.from({ length: 5 })

function formatDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso))
}

function formatDuration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function goToJob(id) {
  router.push({ name: 'sync-job-detail', params: { id } })
}
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
      <h2 class="text-sm font-semibold text-slate-700">Recent Sync Jobs</h2>
      <router-link
          :to="{ name: 'sync-jobs' }"
          class="text-xs text-blue-600 hover:underline"
      >
        View all →
      </router-link>
    </div>

    <table class="w-full text-sm">
      <thead class="bg-slate-50 text-xs uppercase text-slate-400">
      <tr>
        <th class="px-5 py-3 text-left font-medium">Job ID</th>
        <th class="px-5 py-3 text-left font-medium">Site Project</th>
        <th class="px-5 py-3 text-left font-medium">Status</th>
        <th class="px-5 py-3 text-left font-medium">Started</th>
        <th class="px-5 py-3 text-left font-medium">Duration</th>
      </tr>
      </thead>

      <tbody class="divide-y divide-slate-100">
      <!-- loading skeleton -->
      <template v-if="loading">
        <tr v-for="i in skeletonRows" :key="i">
          <td colspan="5" class="px-5 py-3">
            <div class="h-4 w-full animate-pulse rounded bg-slate-100" />
          </td>
        </tr>
      </template>

      <!-- empty state -->
      <template v-else-if="jobs.length === 0">
        <tr>
          <td colspan="5" class="px-5 py-10 text-center text-slate-400">
            No sync jobs found
          </td>
        </tr>
      </template>

      <!-- data rows -->
      <template v-else>
        <tr
            v-for="job in jobs"
            :key="job.id"
            class="cursor-pointer hover:bg-slate-50 transition-colors"
            @click="goToJob(job.id)"
        >
          <td class="px-5 py-3 font-mono text-xs text-slate-500">
            #{{ job.id }}
          </td>
          <td class="px-5 py-3 text-slate-700">
            {{ job.site_project_name ?? job.site_project ?? '—' }}
          </td>
          <td class="px-5 py-3">
            <StatusBadge :status="job.status" />
          </td>
          <td class="px-5 py-3 text-slate-500">
            {{ formatDate(job.started_at ?? job.created_at) }}
          </td>
          <td class="px-5 py-3 text-slate-500">
            {{ formatDuration(job.duration_secs) }}
          </td>
        </tr>
      </template>
      </tbody>
    </table>
  </div>
</template>
