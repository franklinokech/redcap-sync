// src/stores/sync.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { syncApi, sitesApi, projectsApi, registryApi } from '@/api'

export const useSyncStore = defineStore('sync', () => {
  const stats    = ref(null)
  const jobs     = ref([])
  const sites    = ref([])
  const projects = ref([])
  const registry = ref(null)
  const loading  = ref(false)

  async function fetchStats() {
    const { data } = await syncApi.stats()
    stats.value = data
  }

  async function fetchJobs(params = {}) {
    const { data } = await syncApi.jobs(params)
    jobs.value = data.results || data
    return data
  }

  async function fetchSites() {
    const { data } = await sitesApi.list()
    sites.value = data.results || data
  }

  async function fetchProjects(params = {}) {
    const { data } = await projectsApi.list(params)
    projects.value = data.results || data
    return data
  }

  async function fetchActiveRegistry() {
    try {
      const { data } = await registryApi.active()
      registry.value = data
    } catch {
      registry.value = null
    }
  }

  async function triggerSync(payload) {
    const { data } = await syncApi.trigger(payload)
    return data
  }

  async function previewSync(payload) {
    const { data } = await syncApi.preview(payload)
    return data
  }

  async function pollJob(id) {
    const { data } = await syncApi.job(id)
    const idx = jobs.value.findIndex(j => j.id === id)
    if (idx >= 0) jobs.value[idx] = data
    return data
  }

  return {
    stats, jobs, sites, projects, registry, loading,
    fetchStats, fetchJobs, fetchSites, fetchProjects,
    fetchActiveRegistry, triggerSync, previewSync, pollJob,
  }
})