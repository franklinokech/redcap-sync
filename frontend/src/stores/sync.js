// src/stores/sync.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { syncApi } from '@/api/sync'

export const useSyncStore = defineStore('sync', () => {

    // ── State ────────────────────────────────────────────────────────────────
    const jobs         = ref([])
    const currentJob   = ref(null)
    const stats        = ref(null)          // raw API response
    const total        = ref(0)
    const error        = ref(null)
    const triggering   = ref(false)
    const loadingJobs  = ref(false)
    const loadingStats = ref(false)

    // ── Getters ───────────────────────────────────────────────────────────────
    const jobById = computed(() =>
        (id) => jobs.value.find((j) => j.id === id) ?? null
    )

    const runningJobs = computed(() =>
        jobs.value.filter((j) => j.status === 'running' || j.status === 'pending')
    )

    /**
     * Counts derived from the LOCAL jobs array.
     * Used only for live job-list views — NOT for the dashboard header cards.
     */
    const statusCounts = computed(() => {
        const base = { pending: 0, running: 0, completed: 0, failed: 0, cancelled: 0 }
        for (const job of jobs.value) {
            if (job.status in base) base[job.status]++
        }
        return base
    })

    /**
     * ✅ NEW — Normalised counts from the /api/sync/stats/ endpoint.
     * Always safe to destructure: returns zeros before the first fetch.
     * Maps backend snake_case keys → consistent camelCase/friendly keys.
     */
    const apiStats = computed(() => {
        const s = stats.value
        if (!s) {
            return {
                total:          0,
                pending:        0,
                running:        0,
                completed:      0,   // ← backend: successful_jobs
                failed:         0,
                cancelled:      0,
                recordsPulled:  0,
                recordsPushed:  0,
                recordsSkipped: 0,
                avgDuration:    null,
                lastSyncAt:     null,
                lastSuccessAt:  null,
            }
        }
        return {
            total:          s.total_jobs          ?? 0,
            pending:        s.pending_jobs        ?? 0,
            running:        s.running_jobs        ?? 0,
            completed:      s.successful_jobs     ?? 0,   // ← THE KEY RENAME
            failed:         s.failed_jobs         ?? 0,
            cancelled:      s.cancelled_jobs      ?? 0,
            recordsPulled:  s.total_records_pulled  ?? 0,
            recordsPushed:  s.total_records_pushed  ?? 0,
            recordsSkipped: s.total_records_skipped ?? 0,
            avgDuration:    s.avg_duration_secs   ?? null,
            lastSyncAt:     s.last_sync_at        ?? null,
            lastSuccessAt:  s.last_success_at     ?? null,
        }
    })

    const totalJobs = computed(() => jobs.value.length)

    const recentJobs = computed(() =>
        [...jobs.value]
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .slice(0, 8)
    )

    const hasError = computed(() => !!error.value)

    // ── Helpers ───────────────────────────────────────────────────────────────
    function patchJob(id, changes) {
        const idx = jobs.value.findIndex((j) => j.id === id)
        if (idx !== -1) jobs.value[idx] = { ...jobs.value[idx], ...changes }
        if (currentJob.value?.id === id) {
            currentJob.value = { ...currentJob.value, ...changes }
        }
    }

    // ── Actions ───────────────────────────────────────────────────────────────
    async function fetchJobs(params = {}) {
        loadingJobs.value = true
        error.value       = null
        try {
            const { data } = await syncApi.listJobs(params)
            jobs.value  = data.results ?? data
            total.value = data.count   ?? jobs.value.length
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message ?? 'Failed to load jobs'
            console.error('[SyncStore] fetchJobs:', err)
        } finally {
            loadingJobs.value = false
        }
    }

    async function fetchJob(id) {
        loadingJobs.value = true
        error.value       = null
        try {
            const { data } = await syncApi.getJob(id)
            currentJob.value = data
            patchJob(id, data)
            return data
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message ?? 'Failed to load job'
            console.error('[SyncStore] fetchJob:', err)
        } finally {
            loadingJobs.value = false
        }
    }

    async function fetchStats() {
        loadingStats.value = true
        error.value        = null
        try {
            const { data } = await syncApi.getStats()
            stats.value = data          // store raw — apiStats computed normalises it
            return data
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message ?? 'Failed to load stats'
            console.error('[SyncStore] fetchStats:', err)
        } finally {
            loadingStats.value = false
        }
    }

    async function refresh() {
        error.value = null
        await Promise.all([fetchJobs(), fetchStats()])
    }

    async function triggerSync(projectId, payload = { sync_type: 'full' }) {
        triggering.value = true
        error.value      = null
        try {
            const { data } = await syncApi.triggerSync(projectId, payload)
            jobs.value.unshift(data)
            total.value += 1
            return data
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message ?? 'Sync trigger failed'
            throw err
        } finally {
            triggering.value = false
        }
    }

    async function cancelJob(id) {
        try {
            await syncApi.cancelJob(id)
            patchJob(id, { status: 'cancelled', is_cancellable: false })
        } catch (err) {
            console.error('[SyncStore] cancelJob:', err)
            throw err
        }
    }

    async function retryJob(id) {
        try {
            const { data } = await syncApi.retryJob(id)
            jobs.value.unshift(data)
            total.value += 1
            return data
        } catch (err) {
            console.error('[SyncStore] retryJob:', err)
            throw err
        }
    }

    async function previewSync(projectId) {
        try {
            const { data } = await syncApi.previewSync(projectId)
            return data
        } catch (err) {
            console.error('[SyncStore] previewSync:', err)
            throw err
        }
    }

    // ── Public API ────────────────────────────────────────────────────────────
    return {
        // State
        jobs, currentJob, stats, total,
        error, triggering, loadingJobs, loadingStats,

        // Getters
        jobById, runningJobs, statusCounts,
        apiStats,       // ✅ new normalised computed
        totalJobs, recentJobs, hasError,

        // Actions
        refresh, fetchJobs, fetchJob, fetchStats,
        triggerSync, cancelJob, retryJob, previewSync,
        patchJob,
    }
})
