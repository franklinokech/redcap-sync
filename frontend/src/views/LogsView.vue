<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Logs</h1>
        <p class="page-sub">Full history of all sync jobs</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-row">
      <select class="form-select filter-select" v-model="filters.status" @change="applyFilters">
        <option value="">All statuses</option>
        <option value="success">Success</option>
        <option value="failed">Failed</option>
        <option value="running">Running</option>
        <option value="pending">Pending</option>
        <option value="cancelled">Cancelled</option>
      </select>
      <select class="form-select filter-select" v-model="filters.site" @change="applyFilters">
        <option value="">All sites</option>
        <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <select class="form-select filter-select" v-model="filters.project" @change="applyFilters">
        <option value="">All projects</option>
        <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <button class="btn btn-secondary btn-sm" @click="clearFilters">Clear</button>
      <button class="btn btn-secondary btn-sm" @click="loadJobs">⟳ Refresh</button>
    </div>

    <!-- Jobs table -->
    <div class="card">
      <div v-if="loading" class="empty-state">
        <div class="empty-state-text">Loading…</div>
      </div>

      <div v-else-if="!jobs.length" class="empty-state">
        <div class="empty-state-icon">≡</div>
        <div class="empty-state-title">No jobs found</div>
        <div class="empty-state-text">Try adjusting the filters</div>
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Project</th>
            <th>Site</th>
            <th>Type</th>
            <th>Date range</th>
            <th>Status</th>
            <th>Pulled</th>
            <th>Pushed</th>
            <th>Duration</th>
            <th>Triggered by</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="job in jobs"
            :key="job.id"
            @click="openDrawer(job)"
            :class="{ 'row-active': selectedJob?.id === job.id }"
          >
            <td class="font-mono text-dim">{{ job.id }}</td>
            <td>{{ job.site_project_name }}</td>
            <td class="text-muted">{{ job.site_code }}</td>
            <td>
              <span class="badge" :class="job.sync_type === 'full' ? 'badge-pending' : 'badge-warning'">
                {{ job.sync_type }}
              </span>
            </td>
            <td class="text-dim" style="font-size:11px">{{ job.date_range }}</td>
            <td><StatusBadge :status="job.status" /></td>
            <td class="font-mono text-dim">{{ job.records_pulled || '—' }}</td>
            <td class="font-mono">
              <span v-if="job.records_pushed" class="text-teal">{{ job.records_pushed }}</span>
              <span v-else class="text-dim">—</span>
            </td>
            <td class="font-mono text-dim">
              {{ job.duration_secs ? job.duration_secs.toFixed(2) + 's' : '—' }}
            </td>
            <td class="text-dim">{{ job.triggered_by_name || 'system' }}</td>
            <td class="text-dim" style="font-size:11px">{{ formatDt(job.started_at || job.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Log drawer -->
    <Transition name="drawer">
      <div v-if="selectedJob" class="drawer-overlay" @click.self="closeDrawer">
        <div class="drawer">
          <div class="drawer-header">
            <div>
              <div class="drawer-title">Job #{{ selectedJob.id }} — {{ selectedJob.site_project_name }}</div>
              <div class="drawer-sub">{{ selectedJob.registry_name }}</div>
            </div>
            <div class="drawer-header-right">
              <StatusBadge :status="selectedJob.status" />
              <button class="btn-icon" @click="closeDrawer">✕</button>
            </div>
          </div>

          <div class="drawer-meta">
            <div class="meta-item">
              <span class="meta-label">Pulled</span>
              <span class="meta-value">{{ selectedJob.records_pulled }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Pushed</span>
              <span class="meta-value text-teal">{{ selectedJob.records_pushed }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Duration</span>
              <span class="meta-value font-mono">{{ selectedJob.duration_secs?.toFixed(2) ?? '—' }}s</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Type</span>
              <span class="meta-value">{{ selectedJob.date_range }}</span>
            </div>
          </div>

          <div v-if="selectedJob.error_message" class="error-box" style="margin-bottom:16px">
            {{ selectedJob.error_message }}
          </div>

          <div class="log-list">
            <div v-if="logsLoading" class="empty-state">
              <div class="empty-state-text">Loading logs…</div>
            </div>
            <div v-else-if="!logs.length" class="empty-state">
              <div class="empty-state-text">No logs for this job</div>
            </div>
            <div v-else>
              <div
                v-for="log in logs"
                :key="log.id"
                class="log-entry"
                :class="`log-${log.level.toLowerCase()}`"
              >
                <div class="log-top">
                  <span class="log-level">{{ log.level }}</span>
                  <span class="log-time font-mono">{{ formatDt(log.timestamp) }}</span>
                </div>
                <div class="log-msg">{{ log.message }}</div>
                <pre v-if="log.detail" class="log-detail">{{ JSON.stringify(log.detail, null, 2) }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSyncStore } from '@/stores/sync'
import { syncApi } from '@/api'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { format } from 'date-fns'

const store       = useSyncStore()
const loading     = ref(false)
const logsLoading = ref(false)
const jobs        = ref([])
const logs        = ref([])
const selectedJob = ref(null)
const sites       = computed(() => store.sites)
const projects    = computed(() => store.projects)

const filters = ref({ status: '', site: '', project: '' })

function formatDt(dt) {
  if (!dt) return '—'
  try { return format(new Date(dt), 'dd MMM HH:mm:ss') }
  catch { return dt }
}

async function loadJobs() {
  loading.value = true
  const params = {}
  if (filters.value.status)  params.status  = filters.value.status
  if (filters.value.site)    params.site     = filters.value.site
  if (filters.value.project) params.project  = filters.value.project
  const data = await store.fetchJobs(params)
  jobs.value = store.jobs
  loading.value = false
}

function applyFilters() { loadJobs() }

function clearFilters() {
  filters.value = { status: '', site: '', project: '' }
  loadJobs()
}

async function openDrawer(job) {
  selectedJob.value = job
  logsLoading.value = true
  logs.value = []
  try {
    const { data } = await syncApi.logs(job.id)
    logs.value = data.results || data
  } finally {
    logsLoading.value = false
  }
}

function closeDrawer() {
  selectedJob.value = null
  logs.value = []
}

onMounted(async () => {
  await Promise.all([store.fetchSites(), store.fetchProjects()])
  await loadJobs()
})
</script>

<style scoped>
.page { padding: 28px; max-width: 1200px; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.02em; }
.page-sub   { font-size: 12px; color: var(--c-text-3); margin-top: 3px; }

.filters-row {
  display: flex; gap: 8px; margin-bottom: 14px; align-items: center; flex-wrap: wrap;
}
.filter-select { width: auto; min-width: 140px; }

.row-active td { background: var(--c-teal-glow) !important; }

.error-box {
  background: var(--c-danger-bg); border: 1px solid rgba(248,113,113,0.2);
  border-radius: var(--r-md); padding: 9px 12px; color: var(--c-danger); font-size: 12px;
}

/* Drawer */
.drawer-overlay {
  position: fixed; inset: 0; z-index: 100;
  background: rgba(0,0,0,0.6);
  display: flex; justify-content: flex-end;
}
.drawer {
  width: 480px; height: 100%;
  background: var(--c-bg-2);
  border-left: 1px solid var(--c-border);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.drawer-header {
  padding: 20px; border-bottom: 1px solid var(--c-border);
  display: flex; justify-content: space-between; align-items: flex-start;
}
.drawer-title { font-size: 15px; font-weight: 600; }
.drawer-sub   { font-size: 11px; color: var(--c-text-3); margin-top: 3px; }
.drawer-header-right { display: flex; align-items: center; gap: 8px; }
.btn-icon { background: none; border: none; cursor: pointer; color: var(--c-text-3); font-size: 14px; padding: 4px 6px; border-radius: 4px; }
.btn-icon:hover { color: var(--c-text); background: var(--c-bg-3); }

.drawer-meta {
  display: grid; grid-template-columns: repeat(4, 1fr);
  padding: 14px 20px; border-bottom: 1px solid var(--c-border); gap: 8px;
}
.meta-item { display: flex; flex-direction: column; gap: 2px; }
.meta-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-text-3); }
.meta-value { font-size: 15px; font-weight: 600; color: var(--c-text); }

.log-list { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 8px; }

.log-entry {
  padding: 10px 12px; border-radius: var(--r-md);
  border-left: 3px solid var(--c-border);
  background: var(--c-bg-3);
}
.log-info    { border-left-color: var(--c-info); }
.log-error   { border-left-color: var(--c-danger); background: var(--c-danger-bg); }
.log-warning { border-left-color: var(--c-warning); background: var(--c-warning-bg); }
.log-debug   { border-left-color: var(--c-border-2); }

.log-top { display: flex; justify-content: space-between; margin-bottom: 4px; }
.log-level { font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--c-text-3); }
.log-time  { font-size: 10px; color: var(--c-text-3); }
.log-msg   { font-size: 12px; color: var(--c-text-2); }
.log-detail {
  margin-top: 8px; padding: 8px; border-radius: var(--r-sm);
  background: var(--c-bg); font-size: 10px; font-family: var(--font-mono);
  color: var(--c-text-3); overflow-x: auto; max-height: 160px;
}

/* Drawer transition */
.drawer-enter-active, .drawer-leave-active { transition: transform 0.25s ease; }
.drawer-enter-from, .drawer-leave-to { transform: translateX(100%); }
</style>