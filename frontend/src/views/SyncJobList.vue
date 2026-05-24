<!-- src/views/SyncJobList.vue -->
<template>
  <div class="p-6 space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Sync Jobs</h1>
        <p class="text-sm text-gray-500 mt-1">{{ total }} jobs total</p>
      </div>
      <button
          @click="showTriggerModal = true"
          class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white
               text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1
                   0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        Trigger Sync
      </button>
    </div>

    <!-- Stats bar -->
    <div v-if="stats" class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
      <StatCard label="Total Jobs"     :value="stats.total_jobs" />
      <StatCard label="Successful"     :value="stats.successful_jobs" variant="success" />
      <StatCard label="Failed"         :value="stats.failed_jobs"     variant="danger" />
      <StatCard label="Pending"        :value="stats.pending_jobs"    variant="warning" />
      <StatCard label="Records Pushed" :value="stats.total_records_pushed" />
      <StatCard label="Avg Duration"   :value="avgDuration" />
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3">
      <select
          v-model="filters.status"
          @change="applyFilters"
          class="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white
               focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="">All statuses</option>
        <option value="pending">Pending</option>
        <option value="running">Running</option>
        <option value="success">Success</option>
        <option value="failed">Failed</option>
        <option value="cancelled">Cancelled</option>
      </select>

      <select
          v-model="filters.sync_type"
          @change="applyFilters"
          class="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white
               focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        <option value="">All types</option>
        <option value="full">Full</option>
        <option value="partial">Partial</option>
      </select>

      <button
          v-if="filters.status || filters.sync_type"
          @click="clearFilters"
          class="text-sm text-gray-500 hover:text-gray-700 px-3 py-2"
      >
        Clear filters
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <svg class="animate-spin h-8 w-8 text-indigo-500"
           fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10"
                stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
    </div>

    <!-- Table -->
    <div v-else class="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <table class="min-w-full divide-y divide-gray-200 text-sm">
        <thead class="bg-gray-50">
        <tr>
          <th class="px-4 py-3 text-left font-medium text-gray-500">ID</th>
          <th class="px-4 py-3 text-left font-medium text-gray-500">Project</th>
          <th class="px-4 py-3 text-left font-medium text-gray-500">Type</th>
          <th class="px-4 py-3 text-left font-medium text-gray-500">Status</th>
          <th class="px-4 py-3 text-right font-medium text-gray-500">Pulled</th>
          <th class="px-4 py-3 text-right font-medium text-gray-500">Pushed</th>
          <th class="px-4 py-3 text-right font-medium text-gray-500">Duration</th>
          <th class="px-4 py-3 text-left font-medium text-gray-500">Triggered</th>
          <th class="px-4 py-3 text-left font-medium text-gray-500">By</th>
          <th class="px-4 py-3"></th>
        </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
        <tr
            v-for="job in jobs"
            :key="job.id"
            @click="goToDetail(job.id)"
            class="hover:bg-gray-50 cursor-pointer transition-colors"
        >
          <td class="px-4 py-3 text-gray-400 font-mono">#{{ job.id }}</td>
          <td class="px-4 py-3">
            <div class="font-medium text-gray-900 truncate max-w-[180px]">
              {{ job.site_project_name }}
            </div>
            <div class="text-xs text-gray-400">{{ job.site_name }}</div>
          </td>
          <td class="px-4 py-3">
              <span :class="syncTypeBadge(job.sync_type)">
                {{ job.sync_type }}
              </span>
          </td>
          <td class="px-4 py-3">
            <StatusBadge :status="job.status" />
          </td>
          <td class="px-4 py-3 text-right text-gray-700">{{ job.records_pulled }}</td>
          <td class="px-4 py-3 text-right text-gray-700">{{ job.records_pushed }}</td>
          <td class="px-4 py-3 text-right text-gray-500 font-mono text-xs">
            {{ job.duration_secs != null ? job.duration_secs.toFixed(2) + 's' : '—' }}
          </td>
          <td class="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
            {{ formatDate(job.created_at) }}
          </td>
          <td class="px-4 py-3 text-gray-500 text-xs">{{ job.triggered_by_name }}</td>
          <td class="px-4 py-3 text-right" @click.stop>
            <button
                v-if="job.is_cancellable"
                @click="handleCancel(job.id)"
                class="text-xs text-red-500 hover:text-red-700 font-medium"
            >
              Cancel
            </button>
            <button
                v-else-if="job.status === 'failed'"
                @click="handleRetry(job.id)"
                class="text-xs text-indigo-500 hover:text-indigo-700 font-medium"
            >
              Retry
            </button>
          </td>
        </tr>

        <tr v-if="jobs.length === 0">
          <td colspan="10" class="px-4 py-12 text-center text-gray-400">
            No sync jobs found.
          </td>
        </tr>
        </tbody>
      </table>
    </div>

  </div>

  <!-- Trigger modal -->
  <TriggerSyncModal
      v-if="showTriggerModal"
      @close="showTriggerModal = false"
      @triggered="onTriggered"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSyncStore } from '@/stores/sync'
import StatusBadge     from '@/components/sync/StatusBadge.vue'
import StatCard        from '@/components/sync/StatCard.vue'
import TriggerSyncModal from '@/components/sync/TriggerSyncModal.vue'

const router    = useRouter()
const syncStore = useSyncStore()

const { jobs, total, loading, stats } = syncStore

const showTriggerModal = ref(false)
const filters = ref({ status: '', sync_type: '' })

// ── Computed ─────────────────────────────────────────────────────────────────
const avgDuration = computed(() => {
  if (!stats?.avg_duration_secs) return '—'
  return stats.avg_duration_secs.toFixed(2) + 's'
})

// ── Lifecycle ─────────────────────────────────────────────────────────────────
let pollTimer = null

onMounted(async () => {
  await Promise.all([syncStore.fetchJobs(), syncStore.fetchStats()])
  startPolling()
})

onUnmounted(() => clearInterval(pollTimer))

function startPolling() {
  // Refresh every 8s while any job is pending/running
  pollTimer = setInterval(async () => {
    if (syncStore.runningJobs.length > 0) {
      await syncStore.fetchJobs(activeFilters())
    }
  }, 8000)
}

// ── Filters ───────────────────────────────────────────────────────────────────
function activeFilters() {
  const f = {}
  if (filters.value.status)    f.status    = filters.value.status
  if (filters.value.sync_type) f.sync_type = filters.value.sync_type
  return f
}

async function applyFilters() {
  await syncStore.fetchJobs(activeFilters())
}

async function clearFilters() {
  filters.value = { status: '', sync_type: '' }
  await syncStore.fetchJobs()
}

// ── Actions ───────────────────────────────────────────────────────────────────
function goToDetail(id) {
  router.push({ name: 'sync-job-detail', params: { id } })
}

async function handleCancel(id) {
  if (!confirm('Cancel this sync job?')) return
  await syncStore.cancelJob(id)
}

async function handleRetry(id) {
  await syncStore.retryJob(id)
}

async function onTriggered(job) {
  showTriggerModal.value = false
  await syncStore.fetchStats()
  router.push({ name: 'sync-job-detail', params: { id: job.id } })
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

function syncTypeBadge(type) {
  return type === 'full'
      ? 'inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700'
      : 'inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-700'
}
</script>
