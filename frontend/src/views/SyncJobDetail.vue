<!-- src/views/SyncJobDetail.vue -->
<template>
  <div class="p-6 space-y-6 max-w-4xl mx-auto">

    <!-- Back -->
    <button
        @click="router.back()"
        class="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
    >
      ← Back to jobs
    </button>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-16">
      <svg class="animate-spin h-8 w-8 text-indigo-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10"
                stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
    </div>

    <template v-else-if="job">

      <!-- Job header card -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h1 class="text-xl font-bold text-gray-900">
              Sync Job #{{ job.id }}
            </h1>
            <p class="text-sm text-gray-500 mt-0.5">
              {{ job.site_project_name }} — {{ job.site_name }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <StatusBadge :status="job.status" size="lg" />
            <button
                v-if="job.is_cancellable"
                @click="handleCancel"
                class="px-3 py-1.5 text-sm font-medium text-red-600 border border-red-300
                     rounded-lg hover:bg-red-50 transition-colors"
            >
              Cancel
            </button>
            <button
                v-if="job.status === 'failed'"
                @click="handleRetry"
                class="px-3 py-1.5 text-sm font-medium text-indigo-600 border border-indigo-300
                     rounded-lg hover:bg-indigo-50 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>

        <!-- Meta grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2 border-t border-gray-100">
          <MetaField label="Sync type"    :value="job.sync_type" />
          <MetaField label="Date range"   :value="job.date_range" />
          <MetaField label="Registry"     :value="job.registry_name" />
          <MetaField label="Triggered by" :value="job.triggered_by_name" />
          <MetaField label="Created"      :value="formatDate(job.created_at)" />
          <MetaField label="Started"      :value="formatDate(job.started_at)" />
          <MetaField label="Completed"    :value="formatDate(job.completed_at)" />
          <MetaField label="Duration"
                     :value="job.duration_secs != null ? job.duration_secs.toFixed(3) + 's' : '—'" />
        </div>

        <!-- Record counters -->
        <div class="grid grid-cols-3 gap-4 pt-2 border-t border-gray-100">
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">{{ job.records_pulled }}</div>
            <div class="text-xs text-gray-500 mt-0.5">Records pulled</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-green-600">{{ job.records_pushed }}</div>
            <div class="text-xs text-gray-500 mt-0.5">Records pushed</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-amber-500">{{ job.records_skipped }}</div>
            <div class="text-xs text-gray-500 mt-0.5">Records skipped</div>
          </div>
        </div>

        <!-- Error message -->
        <div v-if="job.error_message"
             class="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          <span class="font-medium">Error:</span> {{ job.error_message }}
        </div>
      </div>

      <!-- Log viewer -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 border-b border-gray-200 bg-gray-50">
          <h2 class="text-sm font-semibold text-gray-700">
            Logs
            <span class="ml-1 text-gray-400 font-normal">({{ logs.length }})</span>
          </h2>
          <div class="flex items-center gap-3">
            <!-- Level filter -->
            <select
                v-model="logLevel"
                class="text-xs border border-gray-300 rounded px-2 py-1 bg-white
                     focus:outline-none focus:ring-1 focus:ring-indigo-400"
            >
              <option value="">All levels</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
            <!-- Auto-scroll toggle -->
            <label class="flex items-center gap-1 text-xs text-gray-500 cursor-pointer">
              <input type="checkbox" v-model="autoScroll" class="rounded" />
              Auto-scroll
            </label>
          </div>
        </div>

        <div
            ref="logContainer"
            class="bg-gray-950 text-gray-100 font-mono text-xs p-4
                 overflow-y-auto max-h-[420px] space-y-1"
        >
          <div
              v-for="log in filteredLogs"
              :key="log.id"
              class="flex gap-3 leading-relaxed"
          >
            <span class="text-gray-500 shrink-0 tabular-nums">
              {{ formatTime(log.timestamp) }}
            </span>
            <span :class="levelClass(log.level)" class="shrink-0 w-16 text-center
                  text-[10px] font-bold uppercase tracking-wide py-0.5 rounded">
              {{ log.level }}
            </span>
            <span class="flex-1 break-words">{{ log.message }}</span>
          </div>

          <!-- Detail JSON block -->
          <template v-for="log in filteredLogs" :key="'d-' + log.id">
            <div
                v-if="log.detail"
                class="ml-[7.5rem] mb-1 p-2 bg-gray-800 rounded text-gray-400
                     text-[11px] whitespace-pre overflow-x-auto"
            >{{ JSON.stringify(log.detail, null, 2) }}</div>
          </template>

          <div v-if="filteredLogs.length === 0" class="text-gray-500 py-4 text-center">
            No log entries.
          </div>
        </div>
      </div>

    </template>

    <!-- Not found -->
    <div v-else class="text-center py-16 text-gray-400">
      Job not found.
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSyncStore } from '@/stores/sync'
import { syncApi }      from '@/api/sync'
import StatusBadge from '@/components/sync/StatusBadge.vue'
import MetaField   from '@/components/sync/MetaField.vue'

const route     = useRoute()
const router    = useRouter()
const syncStore = useSyncStore()

const jobId      = computed(() => Number(route.params.id))
const job        = computed(() => syncStore.currentJob)
const loading    = ref(true)
const logs       = ref([])
const logLevel   = ref('')
const autoScroll = ref(true)
const logContainer = ref(null)

let pollTimer = null

// ── Filtered logs ─────────────────────────────────────────────────────────────
const filteredLogs = computed(() =>
    logLevel.value
        ? logs.value.filter(l => l.level === logLevel.value)
        : logs.value
)

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadJob()
  loading.value = false
  startPolling()
})

onUnmounted(() => clearInterval(pollTimer))

async function loadJob() {
  await syncStore.fetchJob(jobId.value)
  await loadLogs()
}

async function loadLogs() {
  try {
    const { data } = await syncApi.getJobLogs(jobId.value)
    logs.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch (err) {
    console.error('[SyncJobDetail] loadLogs:', err)
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    const s = job.value?.status
    if (s === 'pending' || s === 'running') {
      await syncStore.fetchJob(jobId.value)
      await loadLogs()
    }
  }, 4000)
}

// Auto-scroll when logs update
watch(logs, async () => {
  if (!autoScroll.value) return
  await nextTick()
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
})

// ── Actions ───────────────────────────────────────────────────────────────────
async function handleCancel() {
  if (!confirm('Cancel this job?')) return
  await syncStore.cancelJob(jobId.value)
}

async function handleRetry() {
  const newJob = await syncStore.retryJob(jobId.value)
  if (newJob) router.replace({ name: 'sync-job-detail', params: { id: newJob.id } })
}

// ── Formatters ────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-GB', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function levelClass(level) {
  return {
    INFO:    'bg-blue-900  text-blue-300',
    WARNING: 'bg-amber-900 text-amber-300',
    ERROR:   'bg-red-900   text-red-300',
  }[level] ?? 'bg-gray-800 text-gray-400'
}
</script>
