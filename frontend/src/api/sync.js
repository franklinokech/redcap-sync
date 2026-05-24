// src/api/sync.js
import api from './axios'

export const syncApi = {
  // Jobs
  listJobs:  (params = {})    => api.get('/api/sync/jobs/', { params }),
  getJob:    (id)              => api.get(`/api/sync/jobs/${id}/`),
  getJobLogs:(id, params = {}) => api.get(`/api/sync/jobs/${id}/logs/`, { params }),
  cancelJob: (id)              => api.post(`/api/sync/jobs/${id}/cancel/`),
  retryJob:  (id)              => api.post(`/api/sync/jobs/${id}/retry/`),

  // Trigger
  triggerSync: (projectId, payload) => api.post(`/api/sync/trigger/${projectId}/`, payload),

  // Preview
  previewSync: (projectId)     => api.post(`/api/sync/preview/${projectId}/`),

  // Stats
  getStats: ()                 => api.get('/api/sync/stats/'),
}
