<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Sync</h1>
        <p class="page-sub">Trigger a data sync from a site project to the registry</p>
      </div>
    </div>

    <div class="sync-layout">
      <!-- Left: Sync form -->
      <div class="sync-form-col">

        <!-- Registry status -->
        <div class="card registry-card" :class="registry ? 'registry-ok' : 'registry-missing'">
          <div class="registry-row">
            <span class="registry-icon">{{ registry ? '✓' : '!' }}</span>
            <div>
              <div class="registry-name">{{ registry?.name || 'No active registry configured' }}</div>
              <div class="registry-url text-dim font-mono">{{ registry?.redcap_url || 'Go to Projects to configure one' }}</div>
            </div>
          </div>
        </div>

        <div class="card">
          <h2 class="section-title" style="margin-bottom:20px">Configure sync</h2>

          <!-- Site filter -->
          <div class="form-group">
            <label class="form-label">Site</label>
            <select class="form-select" v-model="selectedSite" @change="onSiteChange">
              <option value="">All sites</option>
              <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.name }} ({{ s.code }})</option>
            </select>
          </div>

          <!-- Project -->
          <div class="form-group" style="margin-top:14px">
            <label class="form-label">Project <span class="text-danger">*</span></label>
            <select class="form-select" v-model="form.site_project" @change="onProjectChange">
              <option value="">Select a project…</option>
              <option v-for="p in filteredProjects" :key="p.id" :value="p.id">
                {{ p.name }}
                <template v-if="!p.has_token"> ⚠ no token</template>
              </option>
            </select>
            <div v-if="selectedProject && !selectedProject.has_token" class="form-error">
              This project has no API token configured. Add one in Projects first.
            </div>
          </div>

          <!-- Sync type toggle -->
          <div class="form-group" style="margin-top:14px">
            <label class="form-label">Sync type</label>
            <div class="toggle-group">
              <button
                class="toggle-btn"
                :class="{ active: form.sync_type === 'full' }"
                @click="form.sync_type = 'full'"
                type="button"
              >Full sync</button>
              <button
                class="toggle-btn"
                :class="{ active: form.sync_type === 'partial' }"
                @click="form.sync_type = 'partial'"
                type="button"
              >Date range</button>
            </div>
          </div>

          <!-- Date range (shown only for partial) -->
          <Transition name="slide">
            <div v-if="form.sync_type === 'partial'" class="date-range-row" style="margin-top:14px">
              <div class="form-group">
                <label class="form-label">From</label>
                <input class="form-input" type="date" v-model="form.date_from" />
              </div>
              <div class="form-group">
                <label class="form-label">To</label>
                <input class="form-input" type="date" v-model="form.date_to" />
              </div>
            </div>
          </Transition>

          <!-- Error -->
          <div v-if="error" class="error-box" style="margin-top:14px">{{ error }}</div>

          <!-- Actions -->
          <div class="action-row" style="margin-top:20px">
            <button
              class="btn btn-secondary"
              @click="handlePreview"
              :disabled="!canSubmit || previewing"
            >
              {{ previewing ? 'Previewing…' : '⊙ Preview' }}
            </button>
            <button
              class="btn btn-primary"
              @click="handleSync"
              :disabled="!canSubmit || syncing || !registry"
            >
              {{ syncing ? 'Queuing…' : '⟳ Trigger sync' }}
            </button>
          </div>
        </div>

        <!-- Preview result -->
        <Transition name="slide">
          <div v-if="previewResult" class="card preview-card">
            <div class="preview-header">
              <h3 class="section-title">Preview</h3>
              <button class="btn-icon" @click="previewResult = null">✕</button>
            </div>
            <div class="preview-meta">
              <span class="badge badge-pending">{{ previewResult.records_count?.[0] ?? previewResult.records_count }} records</span>
              <span class="text-dim font-mono" style="font-size:11px">{{ (previewResult.columns || []).length }} columns</span>
            </div>
            <div class="preview-columns">
              <span v-for="col in (previewResult.columns || [])" :key="col" class="col-chip">{{ col }}</span>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Right: Active jobs -->
      <div class="jobs-col">
        <div class="card">
          <div class="card-header">
            <h2 class="section-title">Recent jobs</h2>
            <button class="btn btn-secondary btn-sm" @click="refreshJobs">⟳</button>
          </div>

          <div v-if="!recentJobs.length" class="empty-state">
            <div class="empty-state-icon">⟳</div>
            <div class="empty-state-text">No jobs yet</div>
          </div>

          <div v-else class="jobs-list">
            <div
              v-for="job in recentJobs"
              :key="job.id"
              class="job-row"
              :class="{ 'job-running': job.status === 'running' }"
            >
              <div class="job-top">
                <span class="job-name">{{ job.site_project_name }}</span>
                <StatusBadge :status="job.status" />
              </div>
              <div class="job-meta">
                <span class="font-mono text-dim">#{{ job.id }}</span>
                <span class="text-dim">{{ job.sync_type }}</span>
                <span v-if="job.records_pushed" class="text-teal">{{ job.records_pushed }} pushed</span>
                <span v-if="job.duration_secs" class="text-dim font-mono">{{ job.duration_secs.toFixed(1) }}s</span>
              </div>
              <div v-if="job.error_message" class="job-error">{{ job.error_message }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSyncStore } from '@/stores/sync'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const store = useSyncStore()

const form = ref({
  site_project: '',
  sync_type:    'full',
  date_from:    '',
  date_to:      '',
})

const selectedSite    = ref('')
const previewResult   = ref(null)
const syncing         = ref(false)
const previewing      = ref(false)
const error           = ref('')
const sites           = computed(() => store.sites)
const registry        = computed(() => store.registry)

const filteredProjects = computed(() => {
  if (!selectedSite.value) return store.projects
  return store.projects.filter(p => p.site === Number(selectedSite.value))
})

const selectedProject = computed(() =>
  store.projects.find(p => p.id === Number(form.value.site_project))
)

const canSubmit = computed(() => {
  if (!form.value.site_project) return false
  if (!selectedProject.value?.has_token) return false
  if (form.value.sync_type === 'partial' && (!form.value.date_from || !form.value.date_to)) return false
  return true
})

const recentJobs = computed(() => store.jobs.slice(0, 15))

function onSiteChange() { form.value.site_project = '' }
function onProjectChange() { previewResult.value = null; error.value = '' }

async function handlePreview() {
  previewing.value = true
  error.value = ''
  previewResult.value = null
  try {
    const payload = { site_project: form.value.site_project, sync_type: form.value.sync_type }
    if (form.value.sync_type === 'partial') {
      payload.date_from = form.value.date_from
      payload.date_to   = form.value.date_to
    }
    previewResult.value = await store.previewSync(payload)
  } catch (e) {
    error.value = e.response?.data?.detail || 'Preview failed.'
  } finally {
    previewing.value = false
  }
}

async function handleSync() {
  syncing.value = true
  error.value   = ''
  try {
    const payload = { site_project: form.value.site_project, sync_type: form.value.sync_type }
    if (form.value.sync_type === 'partial') {
      payload.date_from = form.value.date_from
      payload.date_to   = form.value.date_to
    }
    await store.triggerSync(payload)
    await refreshJobs()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Sync failed to queue.'
  } finally {
    syncing.value = false
  }
}

async function refreshJobs() {
  await store.fetchJobs()
}

let interval
onMounted(async () => {
  await Promise.all([
    store.fetchSites(),
    store.fetchProjects(),
    store.fetchActiveRegistry(),
    store.fetchJobs(),
  ])
  interval = setInterval(() => {
    const hasActive = store.jobs.some(j => ['pending','running'].includes(j.status))
    if (hasActive) refreshJobs()
  }, 4000)
})
onUnmounted(() => clearInterval(interval))
</script>

<style scoped>
.page { padding: 28px; max-width: 1100px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.02em; }
.page-sub   { font-size: 12px; color: var(--c-text-3); margin-top: 3px; }

.sync-layout {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 16px;
  align-items: start;
}

.registry-card { margin-bottom: 0; }
.registry-ok   { border-color: rgba(52,211,153,0.3); background: rgba(52,211,153,0.05); }
.registry-missing { border-color: rgba(251,191,36,0.3); background: rgba(251,191,36,0.05); }
.registry-row  { display: flex; align-items: flex-start; gap: 10px; }
.registry-icon { font-size: 14px; font-weight: 700; margin-top: 1px; }
.registry-ok .registry-icon { color: var(--c-success); }
.registry-missing .registry-icon { color: var(--c-warning); }
.registry-name { font-size: 13px; font-weight: 500; }
.registry-url  { font-size: 11px; margin-top: 2px; }

.sync-form-col { display: flex; flex-direction: column; gap: 12px; }

.section-title { font-size: 14px; font-weight: 600; }

.toggle-group { display: flex; gap: 4px; }
.toggle-btn {
  flex: 1; padding: 7px 12px;
  background: var(--c-bg-3); border: 1px solid var(--c-border);
  border-radius: var(--r-md); color: var(--c-text-2);
  font-size: 13px; font-weight: 500; cursor: pointer;
  transition: all 0.15s;
}
.toggle-btn.active {
  background: var(--c-teal-glow); border-color: rgba(45,212,191,0.4);
  color: var(--c-teal);
}

.date-range-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

.action-row { display: flex; gap: 8px; }

.error-box {
  background: var(--c-danger-bg);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: var(--r-md);
  padding: 9px 12px; color: var(--c-danger); font-size: 12px;
}

.preview-card { padding: 16px; }
.preview-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.btn-icon { background: none; border: none; cursor: pointer; color: var(--c-text-3); font-size: 13px; padding: 2px 6px; border-radius: 4px; }
.btn-icon:hover { color: var(--c-text); background: var(--c-bg-3); }
.preview-meta { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.preview-columns { display: flex; flex-wrap: wrap; gap: 4px; }
.col-chip {
  padding: 2px 8px; border-radius: 4px;
  background: var(--c-bg-3); border: 1px solid var(--c-border);
  font-size: 11px; font-family: var(--font-mono); color: var(--c-text-2);
}

.card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.jobs-list { display: flex; flex-direction: column; gap: 2px; }
.job-row {
  padding: 10px 12px; border-radius: var(--r-md);
  border: 1px solid transparent;
  transition: background 0.1s;
}
.job-row:hover { background: var(--c-bg-3); }
.job-running { border-color: rgba(96,165,250,0.2); background: rgba(96,165,250,0.04); }
.job-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.job-name { font-size: 13px; font-weight: 500; }
.job-meta { display: flex; gap: 10px; font-size: 11px; }
.job-error { font-size: 11px; color: var(--c-danger); margin-top: 4px; }

/* Transition */
.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-6px); }
</style>