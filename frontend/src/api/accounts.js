import api from './axios.js'

// GET /api/accounts/users/  → array of users (admin only)
export const listUsers = () =>
    api.get('/api/accounts/users/')

// GET /api/accounts/me/
export const getMe = () =>
    api.get('/api/accounts/me/')

// PATCH /api/accounts/me/
export const updateMe = (data) =>
    api.patch('/api/accounts/me/', data)
