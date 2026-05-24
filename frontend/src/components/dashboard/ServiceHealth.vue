<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api/axios.js'

const services = ref([
  { name: 'Django API',   key: 'django',  status: 'checking' },
  { name: 'R Sync Service', key: 'r',     status: 'checking' },
  { name: 'Redis / Celery', key: 'redis', status: 'checking' },
])

async function checkHealth() {
  try {
    await api.get('/api/health/')
    setStatus('django', 'up')
  } catch {
    setStatus('django', 'down')
  }

  try {
    const { data } = await api.get('/api/sync/stats/')
    // if stats returned, celery/redis is likely reachable
    setStatus('redis', data ? 'up' : 'degraded')
  } catch {
    setStatus('redis', 'down')
  }

  // R service — backend exposes a proxy health check
  try {
    await api.get('/api/sync/r-health/')
    setStatus('r', 'up')
  } catch (err) {
    setStatus('r', err.response?.status === 503 ? 'down' : 'degraded')
  }
}

function setStatus(key, status) {
  const svc = services.value.find((s) => s.key === key)
  if (svc) svc.status = status
}

const dotClass = {
  up:       'bg-green-400',
  down:     'bg-red-400',
  degraded: 'bg-yellow-400',
  checking: 'bg-slate-300 animate-pulse',
}

const labelClass = {
  up:       'text-green-700',
  down:     'text-red-700',
  degraded: 'text-yellow-700',
  checking: 'text-slate-400',
}

onMounted(checkHealth)
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white shadow-sm p-5">
    <h2 class="text-sm font-semibold text-slate-700 mb-4">Service Health</h2>
    <ul class="space-y-3">
      <li
          v-for="svc in services"
          :key="svc.key"
          class="flex items-center justify-between"
      >
        <span class="text-sm text-slate-600">{{ svc.name }}</span>
        <span class="flex items-center gap-1.5">
          <span
              :class="['h-2.5 w-2.5 rounded-full', dotClass[svc.status]]"
          />
          <span :class="['text-xs font-medium capitalize', labelClass[svc.status]]">
            {{ svc.status }}
          </span>
        </span>
      </li>
    </ul>

    <button
        class="mt-4 w-full rounded-lg border border-slate-200 py-1.5 text-xs text-slate-500 hover:bg-slate-50 transition-colors"
        @click="checkHealth"
    >
      Refresh
    </button>
  </div>
</template>
