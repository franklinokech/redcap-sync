<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-sub">Overview of sync activity across all sites</p>
      </div>
      <button class="btn btn-secondary btn-sm" @click="refresh" :disabled="loading">
        ⟳ Refresh
      </button>
    </div>

    <!-- Stats row -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats?.total_jobs ?? '—' }}</div>
        <div class="stat-label">Total jobs</div>
      </div>
      <div class="stat-card stat-success">
        <div class="stat-value">{{ stats?.success ?? '—' }}</div>
        <div class="stat-label">Successful</div>
      </div>
      <div class="stat-card stat-danger">
        <div class="stat-value">{{ stats?.failed ?? '—' }}</div>
        <div class="stat-label">Failed</div>
      </div>
      <div class="stat-card stat-teal">
        <div class="stat-value">{{ stats?.total_records_pushed ?? '—' }}</div>
        <div class="stat-label">Records pushed</div>
      </div>
    </div>

    <!-- Running jobs alert -->
    <div v-if="runningJobs.length" class="running-banner">
      <span class="pulse" style="color:var(--c-info)">●</span>
      {{ runningJobs.length }} sync{{ runningJobs.length > 1 ? 's' : '' }} running now
      <span class="text-dim" style="font-size:11px; margin-left:8px">
        Auto-refreshing every 5s
      </span>
    </div>

    <!-- Recent jobs table -->
    <div class="card">
      <div class="card-header">
        <h2 class="section-title">Recent jobs</h2>
        <RouterLink to="/logs" class="text-teal" style="font-size:12px">View all →</RouterLink>
      </div>

      <div v-if="loading && !jobs.length" class="empty-state">
        <div class="empty-state-text">Loading…</div>
      </div>

      <div v-else-if="!jobs.length" class="empty-state">
        <div class="empty-state-icon">⟳</div>
        <div class="empty-state-title">No sync jobs yet</div>
        <div class="empty-state-text">Go to Sync to trigger your first sync</div>
      </div>

      <table v-else class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Project</th>
            <th>Site</th>
            <th>Type</th>
            <th>Status</th>
            <th>Records</th>
            <th>Duration</th>
            <th>When</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in jobs" :key="job.id" @click="$router.push('/logs')">
            <td class="font-mono text-dim">{{ job.id }}</td>
            <td>{{ job.site_project_name }}</td>
            <td class="text-muted">{{ job.site_code }}</td>
            <td>
              <span class="badge" :class="job.sync_type === 'full' ? 'badge-pending' : 'badge-warning'">
                {{ job.sync_type }}
              </span>
            </td>
            <td><StatusBadge :status="job.status" /></td>
            <td class="font-mono">
              <span v-if="job.status === 'success'">{{ job.records_pushed }}</span>
              <span v-else class="text-dim">—</span>
            </td>
            <td class="font-mono text-dim">
              <span v-if="job.duration_secs">{{ job.duration_secs.toFixed(1) }}s</span>
              <span v-else>—</span>
            </td>
            <td class="text-dim">{{ timeAgo(job.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useSyncStore } from '@/stores/sync'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { formatDistanceToNow } from 'date-fns'

const store   = useSyncStore()
const loading = ref(false)
const stats   = computed(() => store.stats)
const jobs    = computed(() => store.jobs.slice(0, 10))
const runningJobs = computed(() =>
  store.jobs.filter(j => j.status === 'running' || j.status === 'pending')
)

function timeAgo(dt) {
  try { return formatDistanceToNow(new Date(dt), { addSuffix: true }) }
  catch { return '—' }
}

async function refresh() {
  loading.value = true
  await Promise.all([store.fetchStats(), store.fetchJobs()])
  loading.value = false
}

let interval
onMounted(async () => {
  await refresh()
  interval = setInterval(() => {
    if (runningJobs.value.length) refresh()
  }, 5000)
})
onUnmounted(() => clearInterval(interval))
</script>

<style scoped>
.page { padding: 28px; max-width: 1100px; }

.page-header {
  display: flex; align-items: flex-start;
  justify-content: space-between; margin-bottom: 24px;
}
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.02em; }
.page-sub   { font-size: 12px; color: var(--c-text-3); margin-top: 3px; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--c-bg-2);
  border: 1px solid var(--c-border);
  border-radius: var(--r-lg);
  padding: 18px 20px;
}
.stat-value { font-size: 28px; font-weight: 600; letter-spacing: -0.03em; color: var(--c-text); }
.stat-label { font-size: 11px; color: var(--c-text-3); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }

.stat-success .stat-value { color: var(--c-success); }
.stat-danger  .stat-value { color: var(--c-danger); }
.stat-teal    .stat-value { color: var(--c-teal); }

.running-banner {
  display: flex; align-items: center; gap: 8px;
  background: var(--c-info-bg);
  border: 1px solid rgba(96,165,250,0.2);
  border-radius: var(--r-md);
  padding: 10px 14px;
  font-size: 13px; color: var(--c-info);
  margin-bottom: 16px;
}

.card-header {
  display: flex; align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.section-title { font-size: 14px; font-weight: 600; }
</style>