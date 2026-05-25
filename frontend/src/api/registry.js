// src/api/registry.js
import api from './axios.js'

export const registryApi = {

    /** GET /api/registry/ */
    list(params = {}) {
        return api.get('/api/registry/', { params })
    },

    /** POST /api/registry/ */
    create(data) {
        return api.post('/api/registry/', data)
    },

    /** GET /api/registry/:id/ */
    get(id) {
        return api.get(`/api/registry/${id}/`)
    },

    /** PATCH /api/registry/:id/ */
    update(id, data) {
        return api.patch(`/api/registry/${id}/`, data)
    },

    /** DELETE /api/registry/:id/  →  409 if linked projects exist */
    destroy(id) {
        return api.delete(`/api/registry/${id}/`)
    },

    /** POST /api/registry/:id/validate-token/ */
    validateToken(id) {
        return api.post(`/api/registry/${id}/validate-token/`)
    },
}
