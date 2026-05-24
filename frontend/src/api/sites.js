import api from './axios.js'

export const sitesApi = {

    list(params = {}) {
        return api.get('/api/projects/sites/', { params })
    },

    get(id) {
        return api.get(`/api/projects/sites/${id}/`)
    },

    create(data) {
        return api.post('/api/projects/sites/', data)
    },

    update(id, data) {
        return api.patch(`/api/projects/sites/${id}/`, data)
    },

    destroy(id) {
        return api.delete(`/api/projects/sites/${id}/`)
    },

    listMembers(siteId) {
        return api.get(`/api/projects/sites/${siteId}/members/`)
    },

    addMember(siteId, userId) {
        return api.post(`/api/projects/sites/${siteId}/members/`, { user_id: userId })
    },

    removeMember(siteId, userId) {
        return api.delete(`/api/projects/sites/${siteId}/members/`, {
            data: { user_id: userId },
        })
    },
}
