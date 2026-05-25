<template>
  <div class="p-6 max-w-2xl space-y-6">

    <!-- Page header -->
    <div>
      <h1 class="text-xl font-semibold text-gray-800">Account</h1>
      <p class="text-sm text-gray-500 mt-1">Your profile and session.</p>
    </div>

    <!-- Profile card -->
    <div class="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Profile</h2>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Username</label>
          <p class="text-sm font-medium text-gray-800">{{ user?.username ?? '—' }}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Role</label>
          <span
              class="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
              :class="roleBadgeClass"
          >
            {{ user?.role ?? '—' }}
          </span>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Email</label>
          <p class="text-sm text-gray-800">{{ user?.email ?? '—' }}</p>
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Last login</label>
          <p class="text-sm text-gray-800">{{ lastLoginDisplay }}</p>
        </div>
      </div>
    </div>

    <!-- Session card -->
    <div class="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
      <h2 class="text-sm font-semibold text-gray-700 uppercase tracking-wide">Session</h2>
      <p class="text-xs text-gray-500">
        Signing out removes your tokens from this browser.
      </p>
      <button
          @click="handleSignOut"
          class="px-4 py-2 bg-red-600 text-white text-sm rounded-lg
               hover:bg-red-700 transition-colors"
      >
        Sign out
      </button>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth   = useAuthStore()
const router = useRouter()
const user   = computed(() => auth.user)

const roleBadgeClass = computed(() => ({
  'bg-purple-100 text-purple-700': user.value?.role === 'admin',
  'bg-blue-100 text-blue-700':     user.value?.role === 'manager',
  'bg-gray-100 text-gray-600':     !['admin', 'manager'].includes(user.value?.role),
}))

const lastLoginDisplay = computed(() => {
  if (!user.value?.last_login) return '—'
  return new Date(user.value.last_login).toLocaleString()
})

async function handleSignOut() {
  await auth.signOut()
  router.push({ name: 'login' })
}
</script>
