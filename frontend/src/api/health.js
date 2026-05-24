import api from './axios.js'

// GET /api/health/  → { status: "ok" }  (no auth needed)
export const healthCheck = () =>
    api.get('/api/health/')
