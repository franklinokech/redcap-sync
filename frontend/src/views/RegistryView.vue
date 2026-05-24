<template>
  <div class="p-6 max-w-7xl mx-auto">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">Central Registry</h1>
        <p class="mt-1 text-sm text-slate-500">
          Manage REDCap central registry projects that site projects sync to.
        </p>
      </div>
      <button
          @click="openCreate"
          class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white
               text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M12 4v16m8-8H4"/>
        </svg>
        Add Registry
      </button>
    </div>

    <!-- Error Banner -->
    <div v-if="fetchError"
         class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
      {{ fetchError }}
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20 text-slate-400">
      <svg class="animate-spin w-6 h-6 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10"
                stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"/>
      </svg>
      Loading registries…
    </div>

    <!-- Empty State -->
    <div v-else-if="!loading && registries.length === 0"
         class="text-center py-20 bg-white rounded-xl border border-slate-200">
      <svg class="mx-auto w-12 h-12 text-slate-300 mb-4" fill="none"
           stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M4 7h16M4 12h16M4 17h7"/>
      </svg>
      <p class="text-slate-500 font-medium">No registry projects yet</p>
      <p class="text-slate-400 text-sm mt-1">Add your first central REDCap registry to get started.</p>
      <button @click="openCreate"
              class="mt-4 px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg
                     hover:bg-indigo-700 transition-colors">
        Add Registry
      </button>
    </div>

    <!-- Table -->
    <div v-else class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
        <tr>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Name
          </th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            REDCap URL
          </th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Project ID
          </th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Token
          </th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Token Status
          </th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Linked Sites
          </th>
          <th class="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Created By
          </th>
          <th class="px-5 py-3"></th>
        </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
        <tr v-for="reg in registries" :key="reg.id"
            class="hover:bg-slate-50 transition-colors">

          <!-- Name + description -->
          <td class="px-5 py-4">
            <p class="font-medium text-slate-800">{{ reg.name }}</p>
            <p v-if="reg.description" class="text-xs text-slate-400 mt-0.5 max-w-xs truncate">
              {{ reg.description }}
            </p>
          </td>

          <!-- URL -->
          <td class="px-5 py-4 text-slate-500 font-mono text-xs">
            {{ reg.redcap_url }}
          </td>

          <!-- Project ID -->
          <td class="px-5 py-4 font-mono text-slate-500 text-xs">
            {{ reg.project_id ?? '—' }}
          </td>

          <!-- Token -->
          <td class="px-5 py-4">
              <span v-if="reg.has_token"
                    class="inline-flex items-center gap-1.5 px-2 py-1 bg-emerald-50
                           text-emerald-700 text-xs rounded-md font-mono">
                <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd"
                        d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2
                           2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z"
                        clip-rule="evenodd"/>
                </svg>
                {{ reg.token_preview }}
              </span>
            <span v-else class="text-slate-300 text-xs">No token</span>
          </td>

          <!-- Token Status -->
          <td class="px-5 py-4">
            <div class="flex items-center gap-2">

              <!-- idle: no token -->
              <span v-if="!reg.has_token" class="text-slate-300 text-xs">—</span>

              <!-- idle: has token, never tested -->
              <template v-else-if="!validationState[reg.id] || validationState[reg.id].status === 'idle'">
                <button
                    @click="runValidation(reg.id)"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium
                           text-slate-600 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700
                           rounded-md transition-colors border border-slate-200 hover:border-indigo-200"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M13 10V3L4 14h7v7l9-11h-7z"/>
                  </svg>
                  Test
                </button>
              </template>

              <!-- checking -->
              <template v-else-if="validationState[reg.id].status === 'checking'">
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs
                               text-slate-500 bg-slate-50 rounded-md border border-slate-200">
                    <svg class="animate-spin w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10"
                              stroke="currentColor" stroke-width="4"/>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    Checking…
                  </span>
              </template>

              <!-- valid -->
              <template v-else-if="validationState[reg.id].status === 'valid'">
                <div class="flex items-center gap-1.5">
                    <span class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium
                                 text-emerald-700 bg-emerald-50 rounded-md border border-emerald-200">
                      <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd"
                              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0
                                 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414
                                 1.414l2 2a1 1 0 001.414 0l4-4z"
                              clip-rule="evenodd"/>
                      </svg>
                      Valid
                    </span>
                  <!-- project title tooltip -->
                  <span
                      v-if="validationState[reg.id].meta?.project_title"
                      class="text-xs text-slate-400 max-w-[120px] truncate"
                      :title="`${validationState[reg.id].meta.project_title} · REDCap v${validationState[reg.id].meta.redcap_version}`"
                  >
                      {{ validationState[reg.id].meta.project_title }}
                    </span>
                  <!-- re-test -->
                  <button
                      @click="runValidation(reg.id)"
                      class="p-1 text-slate-300 hover:text-indigo-500 transition-colors rounded"
                      title="Re-test connection"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0
                                 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357
                                 2H15"/>
                    </svg>
                  </button>
                </div>
              </template>

              <!-- invalid -->
              <template v-else-if="validationState[reg.id].status === 'invalid'">
                <div class="flex items-center gap-1.5">
                    <span
                        class="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium
                             text-red-700 bg-red-50 rounded-md border border-red-200 cursor-help"
                        :title="validationState[reg.id].message"
                    >
                      <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd"
                              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0
                                 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414
                                 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414
                                 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                              clip-rule="evenodd"/>
                      </svg>
                      Invalid
                    </span>
                  <!-- retry -->
                  <button
                      @click="runValidation(reg.id)"
                      class="p-1 text-slate-300 hover:text-indigo-500 transition-colors rounded"
                      title="Retry"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0
                                 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357
                                 2H15"/>
                    </svg>
                  </button>
                </div>
              </template>

            </div>
          </td>

          <!-- Linked sites count -->
          <td class="px-5 py-4">
              <span class="inline-flex items-center justify-center w-7 h-7 rounded-full
                           bg-indigo-50 text-indigo-700 text-xs font-semibold">
                {{ reg.linked_projects_count }}
              </span>
          </td>

          <!-- Created by -->
          <td class="px-5 py-4 text-slate-400 text-xs">
            {{ reg.created_by ?? '—' }}
          </td>

          <!-- Actions -->
          <td class="px-5 py-4">
            <div class="flex items-center gap-2 justify-end">
              <button
                  @click.stop="openEdit(reg)"
                  class="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50
                         rounded-md transition-colors"
                  title="Edit"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5
                             m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
              </button>
              <button
                  @click.stop="confirmDelete(reg)"
                  class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50
                         rounded-md transition-colors"
                  title="Delete"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858
                             L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </button>
            </div>
          </td>

        </tr>
        </tbody>
      </table>
    </div>

    <!-- ── CREATE / EDIT MODAL ─────────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showForm"
             class="fixed inset-0 z-50 flex items-center justify-center p-4"
             @click.self="closeForm">

          <!-- Backdrop -->
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"/>

          <!-- Panel -->
          <div class="relative z-10 w-full max-w-lg bg-white rounded-2xl shadow-2xl
                      overflow-hidden">

            <!-- Modal Header -->
            <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 class="text-base font-semibold text-slate-800">
                {{ editing ? 'Edit Registry' : 'Add Registry' }}
              </h2>
              <button @click="closeForm"
                      class="p-1 text-slate-400 hover:text-slate-600 rounded-md transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <!-- Form -->
            <form @submit.prevent="submitForm" class="px-6 py-5 space-y-4">

              <!-- Form Error -->
              <div v-if="formError"
                   class="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {{ formError }}
              </div>

              <!-- Name -->
              <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">
                  Name <span class="text-red-500">*</span>
                </label>
                <input
                    v-model="form.name"
                    type="text"
                    required
                    placeholder="e.g. KNH Central Registry"
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>

              <!-- Description -->
              <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">
                  Description
                </label>
                <textarea
                    v-model="form.description"
                    rows="2"
                    placeholder="Optional description"
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                         resize-none"
                />
              </div>

              <!-- REDCap URL -->
              <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">
                  REDCap URL <span class="text-red-500">*</span>
                </label>
                <input
                    v-model="form.redcap_url"
                    type="url"
                    required
                    placeholder="https://redcap.example.org/api/"
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                         font-mono"
                />
              </div>

              <!-- Token -->
              <div>
                <label class="block text-xs font-medium text-slate-600 mb-1">
                  API Token
                  <span v-if="!editing" class="text-red-500">*</span>
                  <span v-else class="text-slate-400 font-normal">(leave blank to keep existing)</span>
                </label>
                <div class="relative">
                  <input
                      v-model="form.token"
                      :type="showToken ? 'text' : 'password'"
                      :required="!editing"
                      minlength="32"
                      maxlength="32"
                      placeholder="32-character hex token"
                      class="w-full px-3 py-2 pr-10 text-sm border border-slate-200 rounded-lg
                           focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                           font-mono"
                  />
                  <button
                      type="button"
                      @click="showToken = !showToken"
                      class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400
                           hover:text-slate-600 transition-colors p-1"
                  >
                    <svg v-if="!showToken" class="w-4 h-4" fill="none"
                         stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943
                               9.542 7-1.274 4.057-5.064 7-9.542 7-4.477
                               0-8.268-2.943-9.542-7z"/>
                    </svg>
                    <svg v-else class="w-4 h-4" fill="none"
                         stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478
                               0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3
                               3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29
                               m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0
                               0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0
                               01-4.132 5.411m0 0L21 21"/>
                    </svg>
                  </button>
                </div>
                <p v-if="form.token && form.token.length !== 32"
                   class="mt-1 text-xs text-amber-600">
                  {{ form.token.length }}/32 characters
                </p>
              </div>

              <!-- Overwrite with blanks -->
              <div class="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <input
                    id="overwrite_with_blanks"
                    v-model="form.overwrite_with_blanks"
                    type="checkbox"
                    class="w-4 h-4 text-indigo-600 border-slate-300 rounded
                         focus:ring-indigo-500 cursor-pointer"
                />
                <label for="overwrite_with_blanks" class="text-sm text-slate-700 cursor-pointer">
                  Overwrite with blanks
                  <span class="block text-xs text-slate-400 font-normal">
                    Allow blank values in the registry to overwrite non-blank site values
                  </span>
                </label>
              </div>

              <!-- Footer buttons -->
              <div class="flex items-center justify-end gap-3 pt-2 border-t border-slate-100">
                <button
                    type="button"
                    @click="closeForm"
                    class="px-4 py-2 text-sm text-slate-600 hover:text-slate-800
                         hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                    type="submit"
                    :disabled="submitting"
                    class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white
                         text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg v-if="submitting" class="animate-spin w-4 h-4"
                       fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10"
                            stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  {{ submitting ? 'Saving…' : (editing ? 'Save Changes' : 'Add Registry') }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- ── DELETE CONFIRM MODAL ───────────────────────────────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="deleteTarget"
             class="fixed inset-0 z-50 flex items-center justify-center p-4"
             @click.self="deleteTarget = null">
          <div class="absolute inset-0 bg-black/40 backdrop-blur-sm"/>
          <div class="relative z-10 w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6">
            <div class="flex items-start gap-4">
              <div class="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full
                          flex items-center justify-center">
                <svg class="w-5 h-5 text-red-600" fill="none"
                     stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667
                           1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464
                           0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
              </div>
              <div class="flex-1">
                <h3 class="text-base font-semibold text-slate-800">Delete Registry</h3>
                <p class="mt-1 text-sm text-slate-500">
                  Are you sure you want to delete
                  <span class="font-medium text-slate-700">{{ deleteTarget?.name }}</span>?
                  This action cannot be undone.
                </p>
              </div>
            </div>
            <div class="flex justify-end gap-3 mt-5">
              <button
                  @click="deleteTarget = null"
                  class="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100
                       rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                  @click="executeDelete"
                  :disabled="submitting"
                  class="px-4 py-2 text-sm font-medium text-white bg-red-600
                       hover:bg-red-700 rounded-lg transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ submitting ? 'Deleting…' : 'Delete' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { registryApi } from '@/api/registry.js'

// ── State ────────────────────────────────────────────────────────────────────
const registries   = ref([])
const loading      = ref(false)
const fetchError   = ref(null)
const submitting   = ref(false)
const formError    = ref(null)

// key: registry id → { status: 'idle'|'checking'|'valid'|'invalid', message, meta }
const validationState = ref({})

// Modal state
const showForm     = ref(false)
const editing      = ref(null)
const deleteTarget = ref(null)
const showToken    = ref(false)

const emptyForm = () => ({
  name:                  '',
  description:           '',
  redcap_url:            '',
  token:                 '',
  overwrite_with_blanks: false,
})
const form = ref(emptyForm())

// ── Fetch ────────────────────────────────────────────────────────────────────
async function fetchRegistries() {
  loading.value    = true
  fetchError.value = null
  try {
    const { data } = await registryApi.list()
    registries.value = Array.isArray(data) ? data : (data.results ?? [])
  } catch (err) {
    fetchError.value = err?.response?.data?.detail ?? 'Failed to load registries.'
  } finally {
    loading.value = false
  }
}

// ── Token Validation ─────────────────────────────────────────────────────────
async function runValidation(id) {
  // mark as checking
  validationState.value = {
    ...validationState.value,
    [id]: { status: 'checking', message: null, meta: null },
  }

  try {
    const { data } = await registryApi.validateToken(id)

    if (data.success) {
      // optimistically update project_id in the list if backend refreshed it
      if (data.project_id != null) {
        const idx = registries.value.findIndex(r => r.id === id)
        if (idx !== -1) {
          registries.value[idx] = { ...registries.value[idx], project_id: data.project_id }
        }
      }

      validationState.value = {
        ...validationState.value,
        [id]: {
          status: 'valid',
          message: null,
          meta: {
            project_id:     data.project_id,
            project_title:  data.project_title,
            redcap_version: data.redcap_version,
          },
        },
      }
    } else {
      validationState.value = {
        ...validationState.value,
        [id]: {
          status:  'invalid',
          message: data.message ?? 'Token validation failed.',
          meta:    null,
        },
      }
    }
  } catch (err) {
    const message =
        err?.response?.data?.message ??
        err?.response?.data?.detail ??
        'Could not reach validation service.'

    validationState.value = {
      ...validationState.value,
      [id]: { status: 'invalid', message, meta: null },
    }
  }
}

// ── Create ───────────────────────────────────────────────────────────────────
function openCreate() {
  editing.value   = null
  form.value      = emptyForm()
  showToken.value = false
  formError.value = null
  showForm.value  = true
}

// ── Edit ─────────────────────────────────────────────────────────────────────
function openEdit(reg) {
  editing.value = reg
  form.value = {
    name:                  reg.name,
    description:           reg.description ?? '',
    redcap_url:            reg.redcap_url,
    token:                 '',
    overwrite_with_blanks: reg.overwrite_with_blanks ?? false,
  }
  showToken.value = false
  formError.value = null
  showForm.value  = true
}

function closeForm() {
  showForm.value  = false
  editing.value   = null
  formError.value = null
}

// ── Submit ───────────────────────────────────────────────────────────────────
async function submitForm() {
  submitting.value = true
  formError.value  = null

  const payload = {
    name:                  form.value.name,
    description:           form.value.description,
    redcap_url:            form.value.redcap_url,
    overwrite_with_blanks: form.value.overwrite_with_blanks,
  }
  if (form.value.token) {
    payload.token = form.value.token
  }

  try {
    if (editing.value) {
      const { data } = await registryApi.update(editing.value.id, payload)
      const idx = registries.value.findIndex(r => r.id === editing.value.id)
      if (idx !== -1) registries.value[idx] = data
      // reset validation for this registry since token may have changed
      if (payload.token) {
        validationState.value = {
          ...validationState.value,
          [editing.value.id]: { status: 'idle', message: null, meta: null },
        }
      }
    } else {
      const { data } = await registryApi.create(payload)
      registries.value.unshift(data)
    }
    closeForm()
  } catch (err) {
    const d = err?.response?.data
    if (d && typeof d === 'object') {
      formError.value = Object.entries(d)
          .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
          .join(' | ')
    } else {
      formError.value = 'An unexpected error occurred.'
    }
  } finally {
    submitting.value = false
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
function confirmDelete(reg) {
  deleteTarget.value = reg
}

async function executeDelete() {
  if (!deleteTarget.value) return
  submitting.value = true
  try {
    await registryApi.destroy(deleteTarget.value.id)
    registries.value = registries.value.filter(r => r.id !== deleteTarget.value.id)
    // clean up validation state
    const next = { ...validationState.value }
    delete next[deleteTarget.value.id]
    validationState.value = next
    deleteTarget.value = null
  } catch (err) {
    fetchError.value = err?.response?.data?.detail ?? 'Failed to delete registry.'
    deleteTarget.value = null
  } finally {
    submitting.value = false
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────
onMounted(fetchRegistries)
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .relative,
.modal-leave-active .relative {
  transition: transform 0.15s ease;
}
.modal-enter-from .relative,
.modal-leave-to .relative {
  transform: scale(0.95);
}
</style>
