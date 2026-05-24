import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001',
  headers: { 'Content-Type': 'application/json' },
})

// ── Request: attach access token ─────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response: silent refresh on 401 ──────────────────────────────────────
let isRefreshing = false
let queue = []

function processQueue(error, token = null) {
  queue.forEach((p) => (error ? p.reject(error) : p.resolve(token)))
  queue = []
}

api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config

      // Skip refresh loop for the token endpoints themselves
      const isAuthEndpoint =
          original.url?.includes('/api/auth/token/') ||
          original.url?.includes('/api/auth/token/refresh/')

      if (error.response?.status === 401 && !original._retry && !isAuthEndpoint) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            queue.push({ resolve, reject })
          })
              .then((token) => {
                original.headers.Authorization = `Bearer ${token}`
                return api(original)
              })
              .catch(Promise.reject)
        }

        original._retry = true
        isRefreshing = true

        try {
          // Lazy import to avoid circular dependency
          const { useAuthStore } = await import('@/stores/auth.js')
          const authStore = useAuthStore()
          const newToken = await authStore.refresh()
          processQueue(null, newToken)
          original.headers.Authorization = `Bearer ${newToken}`
          return api(original)
        } catch (refreshError) {
          processQueue(refreshError, null)
          const { useAuthStore } = await import('@/stores/auth.js')
          useAuthStore().signOut()
          window.location.href = '/login'
          return Promise.reject(refreshError)
        } finally {
          isRefreshing = false
        }
      }

      return Promise.reject(error)
    }
)

export default api
