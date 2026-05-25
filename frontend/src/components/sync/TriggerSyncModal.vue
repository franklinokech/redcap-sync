<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-md p-6 space-y-5">

      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-gray-900">Trigger Sync</h2>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
      </div>

      <form @submit.prevent="submit" class="space-y-4">

        <!-- Project -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Project</label>
          <select v-model="form.project_id" required
                  class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                   focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">Select a project…</option>
            <option v-for="p in projectsStore.projects" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
        </div>

        <!-- Sync type -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Sync type</label>
          <div class="flex gap-3">
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input type="radio" v-model="form.sync_type" value="full" />
              Full sync
            </label>
            <label class="flex items-center gap-2 text-sm cursor-pointer">
              <input type="radio" v-model="form.sync_type" value="partial" />
              Partial (date range)
            </label>
          </div>
        </div>

        <!-- Date range (partial only) -->
        <template v-if="form.sync_type === 'partial'">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">From</label>
              <input type="date" v-model="form.date_from" required
                     class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">To</label>
              <input type="date" v-model="form.date_to" required
                     class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>
          </div>
        </template>

        <!-- Error -->
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

        <!-- Actions -->
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" @click="$emit('close')"
                  class="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50">
            Cancel
          </button>
          <button type="submit" :disabled="submitting"
                  class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg
                   hover:bg-indigo-700 disabled:opacity-50 transition-colors">
            {{ submitting ? 'Triggering…' : 'Trigger Sync' }}
          </button>
        </div>

      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSyncStore }     from '@/stores/sync'
import { useProjectsStore } from '@/stores/projects'

const emit = defineEmits(['close', 'triggered'])

const syncStore     = useSyncStore()
const projectsStore = useProjectsStore()

const submitting = ref(false)
const error      = ref(null)

const form = ref({
  project_id: '',
  sync_type:  'full',
  date_from:  '',
  date_to:    '',
})

onMounted(async () => {
  if (!projectsStore.projects.length) await projectsStore.fetchProjects()
})

async function submit() {
  error.value = null
  submitting.value = true
  try {
    const payload = { sync_type: form.value.sync_type }
    if (form.value.sync_type === 'partial') {
      payload.date_from = form.value.date_from
      payload.date_to   = form.value.date_to
    }
    const job = await syncStore.triggerSync(form.value.project_id, payload)
    emit('triggered', job)
  } catch (err) {
    error.value = err.response?.data?.detail ?? err.message ?? 'Trigger failed'
  } finally {
    submitting.value = false
  }
}
</script>
