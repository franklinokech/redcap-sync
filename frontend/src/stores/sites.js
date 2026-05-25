import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { sitesApi } from '@/api/sites.js'

export const useSitesStore = defineStore('sites', () => {

    // ── State ────────────────────────────────────────────────────────────────
    const sites       = ref([])
    const currentSite = ref(null)
    const members     = ref([])
    const loading     = ref(false)
    const error       = ref(null)
    const pagination  = ref({ count: 0, next: null, previous: null })

    // ── Getters ──────────────────────────────────────────────────────────────
    const total        = computed(() => pagination.value.count)
    const activeSites  = computed(() => sites.value.filter(s => s.status === 'active'))
    const inactiveSites = computed(() => sites.value.filter(s => s.status !== 'active'))

    // ── Sites CRUD ───────────────────────────────────────────────────────────
    async function fetchSites(params = {}) {
        loading.value = true
        error.value   = null
        try {
            const { data } = await sitesApi.list(params)
            if (Array.isArray(data)) {
                sites.value      = data
                pagination.value = { count: data.length, next: null, previous: null }
            } else {
                sites.value      = data.results ?? []
                pagination.value = {
                    count:    data.count    ?? 0,
                    next:     data.next     ?? null,
                    previous: data.previous ?? null,
                }
            }
        } catch (err) {
            error.value = err.response?.data?.detail
                ?? err.response?.data?.message
                ?? err.message
                ?? 'Failed to load sites'
        } finally {
            loading.value = false
        }
    }

    async function fetchSite(id) {
        loading.value = true
        error.value   = null
        try {
            const { data } = await sitesApi.get(id)
            currentSite.value = data
            return data
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    async function createSite(payload) {
        loading.value = true
        error.value   = null
        try {
            const { data } = await sitesApi.create(payload)
            sites.value.unshift(data)
            pagination.value.count++
            return data
        } catch (err) {
            error.value = err.response?.data ?? err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    async function updateSite(id, payload) {
        loading.value = true
        error.value   = null
        try {
            const { data } = await sitesApi.update(id, payload)
            const idx = sites.value.findIndex(s => s.id === id)
            if (idx !== -1) sites.value[idx] = data
            if (currentSite.value?.id === id) currentSite.value = data
            return data
        } catch (err) {
            error.value = err.response?.data ?? err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    async function deleteSite(id) {
        loading.value = true
        error.value   = null
        try {
            await sitesApi.destroy(id)
            sites.value = sites.value.filter(s => s.id !== id)
            pagination.value.count = Math.max(0, pagination.value.count - 1)
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    // ── Members ──────────────────────────────────────────────────────────────
    async function fetchMembers(siteId) {
        loading.value = true
        error.value   = null
        try {
            const { data } = await sitesApi.listMembers(siteId)
            members.value = Array.isArray(data) ? data : (data.results ?? [])
            return members.value
        } catch (err) {
            error.value = err.response?.data?.detail ?? err.message
            throw err
        } finally {
            loading.value = false
        }
    }

    async function addMember(siteId, userId) {
        const { data } = await sitesApi.addMember(siteId, userId)
        members.value.push(data)
        return data
    }

    async function removeMember(siteId, userId) {
        await sitesApi.removeMember(siteId, userId)
        members.value = members.value.filter(
            m => m.user?.id !== userId && m.id !== userId
        )
    }

    // ── Reset ────────────────────────────────────────────────────────────────
    function $reset() {
        sites.value       = []
        currentSite.value = null
        members.value     = []
        loading.value     = false
        error.value       = null
        pagination.value  = { count: 0, next: null, previous: null }
    }

    return {
        // state
        sites, currentSite, members, loading, error, pagination,
        // getters
        total, activeSites, inactiveSites,
        // actions
        fetchSites, fetchSite, createSite, updateSite, deleteSite,
        fetchMembers, addMember, removeMember, $reset,
    }
})
