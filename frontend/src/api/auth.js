import api from './axios.js'

// POST /api/auth/token/  → { access, refresh }
export const login = (username, password) =>
    api.post('/api/auth/token/', { username, password })

// POST /api/auth/token/refresh/  → { access }
export const refreshToken = (refresh) =>
    api.post('/api/auth/token/refresh/', { refresh })

// POST /api/auth/token/verify/  → 200 if valid
export const verifyToken = (token) =>
    api.post('/api/auth/token/verify/', { token })

// GET /api/accounts/me/  → { id, username, email, role, organisation }
export const getMe = () =>
    api.get('/api/accounts/me/')

// PATCH /api/accounts/me/
export const updateMe = (data) =>
    api.patch('/api/accounts/me/', data)
