<template>
  <div class="min-h-screen flex bg-surface-muted">
    <aside class="w-56 bg-white border-r border-gray-200 flex flex-col">
      <div class="h-14 flex items-center px-4 border-b border-gray-200">
        <span class="font-bold text-brand-700">REDCap Sync</span>
      </div>
      <nav class="flex-1 p-3 space-y-1">
        <RouterLink
          v-for="link in nav"
          :key="link.name"
          :to="{ name: link.name }"
          class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-600
                 hover:bg-brand-50 hover:text-brand-700 transition-colors"
          active-class="bg-brand-50 text-brand-700 font-medium"
        >
          {{ link.label }}
        </RouterLink>
      </nav>
    </aside>

    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="h-14 bg-white border-b border-gray-200 flex items-center justify-end px-6">
        <button
            @click="handleSignOut"
            class="text-sm text-gray-500 hover:text-gray-800 transition-colors"
        >
          Sign out
        </button>
      </header>

      <main class="flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import {RouterLink, RouterView, useRouter} from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const nav = [
  { name: 'dashboard',  label: 'Dashboard'  },
  { name: 'registry',   label: 'Registry'   },
  { name: 'sites',      label: 'Sites'      },
  { name: 'projects',   label: 'Projects'   },
  { name: 'sync-jobs',  label: 'Sync Jobs'  },
  { name: 'accounts',   label: 'Accounts'   },
]

async function handleSignOut() {
  await auth.signOut()
  router.push({ name: 'login' })
}

</script>
