// src/stores/projects.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectsApi } from '@/api/projects'
import { sitesApi }    from '@/api/sites'
import { registryApi } from '@/api/registry'

export const useProjectsStore = defineStore('projects', () => {
    // ── State ───────────────────────────────────────────────────────────────────
    const projects   = ref([])
    const sites      = ref([])
    const registries = ref([])
    const total      = ref(0)
    const loading    = ref(false)
    const error      = ref(null)

    // ── Getters ─────────────────────────────────────────────────────────────────
    const projectById = computed(() =>
        id => projects.value.find(p => p.id === id) ?? null
    )

    const siteById = computed(() =>
        id => sites.value.find(s => s.id === id) ?? null
    )

    const registryById = computed(() =>
        id => registries.value.find(r => r.id === id) ?? null
    )

    // ── Helpers ─────────────────────────────────────────────────────────────────

    /**
     * Normalise a raw project object from the API into a flat, safe shape.
     * Maps every field the Postman collection documents.
     */
    function normalise(raw) {
        return {
            // Identity
            id:                    raw.id,
            name:                  raw.name                  ?? '',
            description:           raw.description           ?? '',
            status:                raw.status                ?? 'active',

            // Site
            site:                  raw.site                  ?? null,
            site_name:             raw.site_name             ?? '',
            site_code:             raw.site_code             ?? '',

            // REDCap connection
            redcap_url:            raw.redcap_url            ?? '',
            project_id:            raw.project_id            ?? null,
            has_token:             raw.has_token             ?? false,
            token:                 raw.token                 ?? null,
            token_preview:         raw.token_preview         ?? null,

            // Sync config
            record_id_prefix:      raw.record_id_prefix      ?? '',
            sync_forms:            raw.sync_forms            ?? [],
            sync_fields:           raw.sync_fields           ?? [],

            // Central registry
            central_registry:      raw.central_registry      ?? null,
            central_registry_name: raw.central_registry_name ?? null,
            central_registry_url:  raw.central_registry_url  ?? null,
            central_project_id:    raw.central_project_id    ?? null,

            // Timestamps
            created_at:            raw.created_at            ?? null,
            updated_at:            raw.updated_at            ?? null,
        }
    }

    function patchLocal(id, changes) {
        const idx = projects.value.findIndex(p => p.id === id)
        if (idx !== -1) {
            projects.value[idx] = { ...projects.value[idx], ...changes }
        }
    }

    // ── Actions ─────────────────────────────────────────────────────────────────

    async function fetchProjects(params = {}) {
        loading.value = true
        error.value   = null
        try {
            const { data } = await projectsApi.list(params)
            if (Array.isArray(data)) {
                projects.value = data.map(normalise)
                total.value    = data.length
            } else {
                projects.value = (data.results ?? []).map(normalise)
                total.value    = data.count ?? 0
            }
        } catch (err) {
            error.value = err.response?.data?.detail
                ?? err.response?.data
                ?? err.message
                ?? 'Failed to load projects'
            console.error('[ProjectsStore] fetchProjects error:', err)
        } finally {
            loading.value = false
        }
    }

    async function fetchSites() {
        try {
            const { data } = await sitesApi.list()
            sites.value = Array.isArray(data) ? data : (data.results ?? [])
        } catch (err) {
            console.error('[ProjectsStore] fetchSites error:', err)
        }
    }

    async function fetchRegistries() {
        try {
            const { data } = await registryApi.list()
            registries.value = Array.isArray(data) ? data : (data.results ?? [])
        } catch (err) {
            console.error('[ProjectsStore] fetchRegistries error:', err)
        }
    }

    async function addProject(payload) {
        const { data } = await projectsApi.create(payload)
        const project  = normalise(data)
        projects.value.unshift(project)
        total.value += 1
        return project
    }

    async function editProject(id, payload) {
        const { data } = await projectsApi.update(id, payload)
        const updated  = normalise(data)
        patchLocal(id, updated)
        return updated
    }

    async function removeProject(id) {
        await projectsApi.delete(id)
        projects.value = projects.value.filter(p => p.id !== id)
        total.value    = Math.max(0, total.value - 1)
    }

    async function setToken(projectId, token, label = 'Primary token') {
        const { data } = await projectsApi.addToken(projectId, { token, label })
        patchLocal(projectId, {
            has_token:     true,
            token_preview: data.token_preview ?? null,
        })
        return data
    }

    async function validateToken(projectId) {
        const { data } = await projectsApi.validateToken(projectId)
        patchLocal(projectId, {
            project_id: data.project_id ?? null,
        })
        return data
    }

    async function linkProjectRegistry(projectId, registryId) {
        const { data } = await projectsApi.linkRegistry(projectId, registryId)
        const updated  = normalise(data)
        patchLocal(projectId, updated)
        return updated
    }

    async function unlinkProjectRegistry(projectId) {
        const { data } = await projectsApi.unlinkRegistry(projectId)
        const updated  = normalise(data)
        patchLocal(projectId, updated)
        return updated
    }

    // ── Site actions (used by SitesView) ────────────────────────────────────────

    async function addSite(payload) {
        const { data } = await sitesApi.create(payload)
        sites.value.push(data)
        return data
    }

    async function editSite(id, payload) {
        const { data } = await sitesApi.update(id, payload)
        const idx = sites.value.findIndex(s => s.id === id)
        if (idx !== -1) sites.value[idx] = data
        return data
    }

    async function removeSite(id) {
        await sitesApi.destroy(id)
        sites.value = sites.value.filter(s => s.id !== id)
    }

    // ── Registry actions (used by RegistriesView) ────────────────────────────────

    async function addRegistry(payload) {
        const { data } = await registryApi.create(payload)
        registries.value.push(data)
        return data
    }

    async function editRegistry(id, payload) {
        const { data } = await registryApi.update(id, payload)
        const idx = registries.value.findIndex(r => r.id === id)
        if (idx !== -1) registries.value[idx] = data
        return data
    }

    async function removeRegistry(id) {
        await registryApi.destroy(id)
        registries.value = registries.value.filter(r => r.id !== id)
    }

    async function validateRegistryToken(id) {
        const { data } = await registryApi.validateToken(id)
        const idx = registries.value.findIndex(r => r.id === id)
        if (idx !== -1) registries.value[idx] = { ...registries.value[idx], ...data }
        return data
    }

    return {
        // State
        projects,
        sites,
        registries,
        total,
        loading,
        error,

        // Getters
        projectById,
        siteById,
        registryById,

        // Project actions
        fetchProjects,
        addProject,
        editProject,
        removeProject,
        setToken,
        validateToken,
        linkProjectRegistry,
        unlinkProjectRegistry,

        // Site actions
        fetchSites,
        addSite,
        editSite,
        removeSite,

        // Registry actions
        fetchRegistries,
        addRegistry,
        editRegistry,
        removeRegistry,
        validateRegistryToken,
    }
})
