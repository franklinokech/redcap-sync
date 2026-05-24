<template>
  <div class="min-h-screen flex items-center justify-center bg-surface-muted">
    <div class="w-full max-w-sm">

      <div class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">

        <div class="mb-8 text-center">
          <span class="text-2xl font-bold text-brand-700">REDCap Sync</span>
          <p class="mt-1 text-sm text-gray-500">Sign in to your account</p>
        </div>

        <div
            v-if="error"
            class="mb-4 px-4 py-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm"
        >
          {{ error }}
        </div>

        <form @submit.prevent="submit" class="space-y-4" novalidate>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
                v-model="form.username"
                type="text"
                autocomplete="username"
                required
                :disabled="loading"
                class="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm
                     focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                     disabled:bg-gray-50 disabled:text-gray-400"
                placeholder="username"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
                v-model="form.password"
                type="password"
                autocomplete="current-password"
                required
                :disabled="loading"
                class="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm
                     focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                     disabled:bg-gray-50 disabled:text-gray-400"
                placeholder="••••••••"
            />
          </div>

          <button
              type="submit"
              :disabled="loading || !form.username || !form.password"
              class="w-full py-2 px-4 rounded-lg bg-brand-600 hover:bg-brand-700
                   text-white text-sm font-medium transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="flex items-center justify-center gap-2">
              <svg
                  class="animate-spin h-4 w-4 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
              >
                <circle
                    class="opacity-25"
                    cx="12" cy="12" r="10"
                    stroke="currentColor"
                    stroke-width="4"
                />
                <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
              Signing in…
            </span>
            <span v-else>Sign in</span>
          </button>

        </form>
      </div>

      <p class="mt-4 text-center text-xs text-gray-400">REDCap Sync Manager</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth   = useAuthStore()
const router = useRouter()

const form    = reactive({ username: '', password: '' })
const loading = ref(false)
const error   = ref('')

async function submit() {
  error.value   = ''
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push({ name: 'dashboard' })
  } catch (e) {
    // SimpleJWT returns { detail: "..." } on 401
    error.value =
        e.response?.data?.detail ??
        e.response?.data?.non_field_errors?.[0] ??
        'Login failed. Check your credentials.'
  } finally {
    loading.value = false
  }
}
</script>
