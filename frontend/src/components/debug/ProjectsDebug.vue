<!-- src/components/debug/ProjectsDebug.vue -->
<template>
  <div class="fixed bottom-4 right-4 z-50 w-96 max-h-[80vh] overflow-auto
              bg-gray-900 text-green-400 font-mono text-xs rounded-lg shadow-xl p-4">
    <div class="flex justify-between items-center mb-2">
      <span class="font-bold text-white">🔍 Projects Debug</span>
      <button @click="runDiag" class="text-yellow-400 hover:text-yellow-200">
        ▶ Run
      </button>
    </div>

    <div v-for="(line, i) in log" :key="i"
         :class="line.type === 'error' ? 'text-red-400' :
                 line.type === 'ok'    ? 'text-green-400' :
                 line.type === 'warn'  ? 'text-yellow-400' : 'text-gray-400'"
         class="leading-5 whitespace-pre-wrap break-all">
      {{ line.msg }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const log = ref([])

function push(msg, type = 'info') {
  log.value.push({ msg, type })
}

async function runDiag() {
  log.value = []
  push('── Starting diagnostics ──')

  // 1. Check what base URL axios is using
  const baseURL = axios.defaults.baseURL ?? '(none set)'
  push(`axios baseURL: ${baseURL}`)

  // Try to find the api instance
  try {
    const apiModule = await import('../../api/axios.js')
    const inst = apiModule.default
    push(`api instance baseURL: ${inst.defaults?.baseURL ?? '(none)'}`)
  } catch (e) {
    push(`Could not import api/axios: ${e.message}`, 'warn')
    // try alternate path
    try {
      const apiModule2 = await import('../../api/index.js')
      push(`api/index baseURL: ${apiModule2.default?.defaults?.baseURL ?? '?'}`)
    } catch {}
  }

  // 2. Raw fetch to common API locations
  const candidates = [
    '/api/projects/',
    'http://localhost:8001/api/projects/',
    'http://127.0.0.1:8001/api/projects/',
    '/api/projects/?page=1',
  ]

  for (const url of candidates) {
    push(`\nGET ${url}`)
    try {
      const token = localStorage.getItem('access_token') ||
          localStorage.getItem('token') ||
          sessionStorage.getItem('access_token') || ''
      const res = await fetch(url, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'Content-Type': 'application/json',
        },
      })
      push(`  → ${res.status} ${res.statusText}`, res.ok ? 'ok' : 'error')
      if (res.ok) {
        const data = await res.json()
        push(`  → type: ${Array.isArray(data) ? 'array' : 'object'}`)
        if (Array.isArray(data)) {
          push(`  → length: ${data.length}`)
          if (data[0]) push(`  → first keys: ${Object.keys(data[0]).join(', ')}`)
        } else {
          push(`  → keys: ${Object.keys(data).join(', ')}`)
          if ('count' in data) push(`  → count: ${data.count}`, 'ok')
          if ('results' in data) {
            push(`  → results.length: ${data.results.length}`, 'ok')
            if (data.results[0]) {
              push(`  → first project keys: ${Object.keys(data.results[0]).join(', ')}`)
              push(`  → first: ${JSON.stringify(data.results[0]).slice(0, 200)}`)
            }
          }
        }
      } else {
        const text = await res.text()
        push(`  → body: ${text.slice(0, 200)}`, 'error')
      }
    } catch (e) {
      push(`  → NETWORK ERROR: ${e.message}`, 'error')
    }
  }

  // 3. Check auth tokens in storage
  push('\n── Auth storage ──')
  const keys = ['access_token', 'token', 'auth_token', 'accessToken', 'jwt']
  for (const k of keys) {
    const v = localStorage.getItem(k) || sessionStorage.getItem(k)
    if (v) push(`  ${k}: ${v.slice(0, 20)}…`, 'ok')
  }
  push('  cookies: ' + (document.cookie.slice(0, 100) || '(empty)'))

  // 4. Check Pinia store
  push('\n── Pinia store ──')
  try {
    const { useProjectsStore } = await import('../../stores/projects.js')
    const store = useProjectsStore()
    push(`  projects.length: ${store.projects.length}`)
    push(`  total: ${store.total}`)
    push(`  loading: ${store.loading}`)
    push(`  error: ${store.error ?? '(null)'}`, store.error ? 'error' : 'ok')
  } catch (e) {
    push(`  store error: ${e.message}`, 'error')
  }

  push('\n── Done ──')
}

onMounted(runDiag)
</script>
