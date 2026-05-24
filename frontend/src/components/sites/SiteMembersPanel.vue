<!-- src/components/sites/SiteMembersPanel.vue -->
<template>
  <div class="space-y-4">

    <!-- Add member -->
    <div class="flex gap-2">
      <input
          v-model.number="newUserId"
          type="number"
          min="1"
          placeholder="User ID"
          class="input w-32"
          @keydown.enter.prevent="add"
      />
      <button @click="add" :disabled="!newUserId" class="btn-primary">Add Member</button>
    </div>

    <!-- List -->
    <div v-if="loading" class="flex justify-center py-6">
      <Spinner />
    </div>

    <div v-else-if="!members.length" class="text-center py-8 text-gray-400 text-sm">
      No members yet.
    </div>

    <ul v-else class="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
      <li
          v-for="m in members"
          :key="m.id"
          class="flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50"
      >
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-semibold uppercase">
            {{ initials(m) }}
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900">
              {{ m.full_name || m.username }}
            </p>
            <p class="text-xs text-gray-400">{{ m.email }} · {{ m.role }}</p>
          </div>
        </div>
        <button
            @click="emit('remove', m.id)"
            class="icon-btn text-red-500"
            title="Remove member"
        >
          <TrashIcon class="w-4 h-4" />
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { TrashIcon } from '@heroicons/vue/24/outline'
import Spinner from '../ui/Spinner.vue'

const props = defineProps({
  site:    { type: Object,  required: true },
  members: { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['add', 'remove'])

const newUserId = ref('')

function add() {
  if (!newUserId.value) return
  emit('add', newUserId.value)
  newUserId.value = ''
}

function initials(m) {
  if (m.full_name) return m.full_name.split(' ').map(w => w[0]).join('').slice(0, 2)
  return (m.username ?? '?')[0].toUpperCase()
}
</script>
