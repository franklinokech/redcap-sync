// src/api/projects.js
import api from './axios.js'

export const projectsApi = {

    // ── Projects CRUD ───────────────────────────────────────────────────────
    list: (params = {}) =>
        api.get('/api/projects/', { params }),

    get: (id) =>
        api.get(`/api/projects/${id}/`),

    create: (data) =>
        api.post('/api/projects/', data),

    update: (id, data) =>
        api.patch(`/api/projects/${id}/`, data),

    delete: (id) =>
        api.delete(`/api/projects/${id}/`),

    // ── Tokens ──────────────────────────────────────────────────────────────
    listTokens: (projectId) =>
        api.get(`/api/projects/${projectId}/token/`),

    addToken: (projectId, payload) =>
        api.post(`/api/projects/${projectId}/token/`, payload),

    validateToken: (projectId) =>
        api.post(`/api/projects/${projectId}/validate-token/`),

    // ── Registry linking ─────────────────────────────────────────────────────
    linkRegistry: (projectId, registryId) =>
        api.post(`/api/projects/${projectId}/link-registry/`, {
            central_registry: registryId,
        }),

    unlinkRegistry: (projectId) =>
        api.patch(`/api/projects/${projectId}/`, {
            central_registry: null,
        }),

    // ── Sites ────────────────────────────────────────────────────────────────
    // GET  /api/projects/sites/
    listSites: (params = {}) =>
        api.get('/api/projects/sites/', { params }),

    // GET  /api/projects/sites/:id/
    getSite: (id) =>
        api.get(`/api/projects/sites/${id}/`),

    // POST /api/projects/sites/
    createSite: (data) =>
        api.post('/api/projects/sites/', data),

    // PATCH /api/projects/sites/:id/
    updateSite: (id, data) =>
        api.patch(`/api/projects/sites/${id}/`, data),

    // ── Site members ─────────────────────────────────────────────────────────
    // GET    /api/projects/sites/:id/members/
    listMembers: (siteId) =>
        api.get(`/api/projects/sites/${siteId}/members/`),

    // POST   /api/projects/sites/:id/members/   { user_id }
    addMember: (siteId, userId) =>
        api.post(`/api/projects/sites/${siteId}/members/`, { user_id: userId }),

    // DELETE /api/projects/sites/:id/members/   { user_id }
    removeMember: (siteId, userId) =>
        api.delete(`/api/projects/sites/${siteId}/members/`, {
            data: { user_id: userId },
        }),

    // ── Central registries ───────────────────────────────────────────────────
    // GET  /api/registry/
    listRegistries: (params = {}) =>
        api.get('/api/registry/', { params }),

    // GET  /api/registry/:id/
    getRegistry: (id) =>
        api.get(`/api/registry/${id}/`),

    // POST /api/registry/
    createRegistry: (data) =>
        api.post('/api/registry/', data),

    // PATCH /api/registry/:id/
    updateRegistry: (id, data) =>
        api.patch(`/api/registry/${id}/`, data),

    // DELETE /api/registry/:id/
    deleteRegistry: (id) =>
        api.delete(`/api/registry/${id}/`),

    // POST /api/registry/:id/validate-token/
    validateRegistryToken: (id) =>
        api.post(`/api/registry/${id}/validate-token/`),
}
