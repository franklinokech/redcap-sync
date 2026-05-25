<!-- src/components/sites/SiteForm.vue -->
<template>
  <form @submit.prevent="emit('submit', form)" class="space-y-4">

    <div>
      <label class="label">Name <span class="text-red-500">*</span></label>
      <input v-model="form.name" type="text" class="input" placeholder="Kenyatta National Hospital" required />
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="label">Site Code <span class="text-red-500">*</span></label>
        <input v-model="form.code" type="text" class="input font-mono" placeholder="KNH" required />
        <p class="text-xs text-gray-400 mt-1">Used as the record_id prefix</p>
      </div>
      <div>
        <label class="label">Status</label>
        <select v-model="form.status" class="input">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>
    </div>

    <div>
      <label class="label">Location</label>
      <input v-model="form.location" type="text" class="input" placeholder="Nairobi, Kenya" />
    </div>

    <div>
      <label class="label">Description</label>
      <textarea v-model="form.description" rows="3" class="input resize-none" placeholder="Optional description…" />
    </div>

    <div class="flex justify-end gap-3 pt-2">
      <button type="button" @click="emit('cancel')" class="btn-secondary">Cancel</button>
      <button type="submit" :disabled="saving" class="btn-primary flex items-center gap-2">
        <Spinner v-if="saving" class="w-4 h-4" />
        {{ saving ? 'Saving…' : (site ? 'Update Site' : 'Create Site') }}
      </button>
    </div>

  </form>
</template>

<script setup>
import { reactive, watch } from 'vue'
import Spinner from '../ui/Spinner.vue'

const props = defineProps({
  site:   { type: Object,  default: null  },
  saving: { type: Boolean, default: false },
})
const emit = defineEmits(['submit', 'cancel'])

const form = reactive({
  name:        '',
  code:        '',
  location:    '',
  description: '',
  status:      'active',
})

watch(() => props.site, (s) => {
  if (s) Object.assign(form, {
    name:        s.name        ?? '',
    code:        s.code        ?? '',
    location:    s.location    ?? '',
    description: s.description ?? '',
    status:      s.status      ?? 'active',
  })
}, { immediate: true })
</script>
