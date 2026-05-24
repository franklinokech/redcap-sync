import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  login as apiLogin,
  refreshToken as apiRefreshToken,
  getMe,
} from '@/api/auth.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token') || null)
  const refreshTokenVal = ref(localStorage.getItem('refresh_token') || null)

  // ── Computed ──────────────────────────────────────────────────────────────
  const isLoggedIn = computed(() => !!accessToken.value && !!user.value)
  const isAuthenticated = isLoggedIn        // router alias
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isManager = computed(() => user.value?.role === 'manager')

  // ── Helpers ───────────────────────────────────────────────────────────────
  function setTokens(access, refresh) {
    accessToken.value = access
    refreshTokenVal.value = refresh
    localStorage.setItem('access_token', access)
    if (refresh) localStorage.setItem('refresh_token', refresh)
  }

  function clearSession() {
    user.value = null
    accessToken.value = null
    refreshTokenVal.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // ── Actions ───────────────────────────────────────────────────────────────
  async function login(username, password) {
    const { data } = await apiLogin(username, password)
    setTokens(data.access, data.refresh)
    await loadUser()
  }

  // alias for components that call signIn
  const signIn = login

  async function loadUser() {
    if (!accessToken.value) return
    try {
      const { data } = await getMe()
      user.value = data
    } catch {
      clearSession()
    }
  }

  async function refresh() {
    if (!refreshTokenVal.value) throw new Error('No refresh token')
    const { data } = await apiRefreshToken(refreshTokenVal.value)
    accessToken.value = data.access
    localStorage.setItem('access_token', data.access)
    return data.access
  }

  async function signOut() {
    clearSession()
  }

  return {
    user,
    accessToken,
    isLoggedIn,
    isAuthenticated,
    isAdmin,
    isManager,
    login,
    signIn,
    loadUser,
    refresh,
    signOut,
  }
})
