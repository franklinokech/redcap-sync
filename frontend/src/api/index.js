// src/api/index.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 — redirect to login
api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/auth/token/refresh/', { refresh })
          localStorage.setItem('access_token', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return api(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login:   (credentials) => api.post('/auth/token/', credentials),
  refresh: (refresh)     => api.post('/auth/token/refresh/', { refresh }),
  me:      ()            => api.get('/accounts/me/'),
}

// ── Sites & Projects ──────────────────────────────────────────────────────────
export const sitesApi = {
  list:         ()         => api.get('/projects/sites/'),
  create:       (data)     => api.post('/projects/sites/', data),
  update:       (id, data) => api.patch(`/projects/sites/${id}/`, data),
  delete:       (id)       => api.delete(`/projects/sites/${id}/`),
  addMember:    (id, userId)    => api.post(`/projects/sites/${id}/members/`, { user_id: userId }),
  removeMember: (id, userId)    => api.delete(`/projects/sites/${id}/members/`, { data: { user_id: userId } }),
}

export const projectsApi = {
  list:          (params)   => api.get('/projects/', { params }),
  create:        (data)     => api.post('/projects/', data),
  update:        (id, data) => api.patch(`/projects/${id}/`, data),
  delete:        (id)       => api.delete(`/projects/${id}/`),
  getToken:      (id)       => api.get(`/projects/${id}/token/`),
  setToken:      (id, data) => api.post(`/projects/${id}/token/`, data),
  deleteToken:   (id)       => api.delete(`/projects/${id}/token/`),
  validateToken: (id)       => api.post(`/projects/${id}/validate-token/`),
}

// ── Registry ──────────────────────────────────────────────────────────────────
export const registryApi = {
  list:          ()         => api.get('/registry/'),
  active:        ()         => api.get('/registry/active/'),
  create:        (data)     => api.post('/registry/', data),
  update:        (id, data) => api.patch(`/registry/${id}/`, data),
  validateToken: (id)       => api.post(`/registry/${id}/validate-token/`),
}

// ── Sync ──────────────────────────────────────────────────────────────────────
export const syncApi = {
  trigger:  (data)   => api.post('/sync/trigger/', data),
  preview:  (data)   => api.post('/sync/preview/', data),
  jobs:     (params) => api.get('/sync/jobs/', { params }),
  job:      (id)     => api.get(`/sync/jobs/${id}/`),
  logs:     (id)     => api.get(`/sync/jobs/${id}/logs/`),
  cancel:   (id)     => api.post(`/sync/jobs/${id}/cancel/`),
  stats:    ()       => api.get('/sync/stats/'),
}

export default api