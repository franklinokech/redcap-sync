// src/stores/registry.js
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { registryApi } from '@/api/registry'

export const useRegistryStore = defineStore('registry', () => {
    const registries       = ref([])
    const loading          = ref(false)
    const error            = ref(null)

    // key: registry id → { status: 'idle'|'checking'|'valid'|'invalid', message, meta }
    const validationState  = ref({})

    // ── CRUD ────────────────────────────────────────────────────────────────

    async function fetchAll() {
        loading.value = true
        error.value   = null
        try {
            const { data } = await registryApi.list()
            registries.value = data
        } catch (err) {
            error.value = err.response?.data?.detail ?? 'Failed to load registries.'
        } finally {
            loading.value = false
        }
    }

    async function create(payload) {
        const { data } = await registryApi.create(payload)
        registries.value.unshift(data)
        return data
    }

    async function update(id, payload) {
        const { data } = await registryApi.update(id, payload)
        const idx = registries.value.findIndex(r => r.id === id)
        if (idx !== -1) registries.value[idx] = data
        return data
    }

    async function remove(id) {
        await registryApi.delete(id)
        registries.value = registries.value.filter(r => r.id !== id)
        // clean up validation state too
        delete validationState.value[id]
    }

    // ── Token Validation ─────────────────────────────────────────────────────

    async function validateToken(id) {
        // Set checking state
        validationState.value = {
            ...validationState.value,
            [id]: { status: 'checking', message: null, meta: null },
        }

        try {
            const { data } = await registryApi.validateToken(id)

            if (data.success) {
                // Optimistically update project_id in the list if it changed
                const idx = registries.value.findIndex(r => r.id === id)
                if (idx !== -1 && data.project_id != null) {
                    registries.value[idx] = {
                        ...registries.value[idx],
                        project_id: data.project_id,
                    }
                }

                validationState.value = {
                    ...validationState.value,
                    [id]: {
                        status:  'valid',
                        message: null,
                        meta: {
                            project_id:     data.project_id,
                            project_title:  data.project_title,
                            redcap_version: data.redcap_version,
                        },
                    },
                }
            } else {
                validationState.value = {
                    ...validationState.value,
                    [id]: {
                        status:  'invalid',
                        message: data.message ?? 'Token validation failed.',
                        meta:    null,
                    },
                }
            }
        } catch (err) {
            const message =
                err.response?.data?.message ??
                err.response?.data?.detail ??
                'Could not reach validation service.'

            validationState.value = {
                ...validationState.value,
                [id]: { status: 'invalid', message, meta: null },
            }
        }
    }

    function clearValidation(id) {
        const next = { ...validationState.value }
        delete next[id]
        validationState.value = next
    }

    return {
        registries,
        loading,
        error,
        validationState,
        fetchAll,
        create,
        update,
        remove,
        validateToken,
        clearValidation,
    }
})
