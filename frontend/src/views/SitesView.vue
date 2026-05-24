<!-- src/views/SitesView.vue -->
<template>
  <div class="p-6 space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Sites</h1>
        <p class="text-sm text-gray-500 mt-1">
          Manage physical collection sites and their members
        </p>
      </div>
      <button @click="openCreate" class="btn-primary flex items-center gap-2">
        <PlusIcon class="w-4 h-4" />
        Add Site
      </button>
    </div>

    <!-- Stats strip -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <StatCard
          label="Total Sites"
          :value="store.total"
          color="blue"
      />
      <StatCard
          label="Active"
          :value="store.activeSites.length"
          color="green"
      />
      <StatCard
          label="Inactive"
          :value="store.inactiveSites.length"
          color="gray"
      />
      <StatCard
          label="Total Projects"
          :value="store.sites.reduce((s, x) => s + (x.project_count ?? 0), 0)"
          color="purple"
      />
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-3">
      <input
          v-model="search"
          type="text"
          placeholder="Search sites..."
          class="input w-64"
          @input="debouncedFetch"
      />
      <select v-model="filterStatus" class="input w-36" @change="doFetch">
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
      </select>
      <button @click="doFetch" class="btn-secondary flex items-center gap-1">
        <ArrowPathIcon class="w-4 h-4" />
        Refresh
      </button>
    </div>

    <!-- Table -->
    <div class="card overflow-hidden">

      <div v-if="store.loading" class="flex justify-center py-16">
        <Spinner />
      </div>

      <div v-else-if="store.error" class="p-6">
        <AlertBanner :message="store.error" variant="error" />
      </div>

      <div v-else-if="!store.sites.length" class="py-20 text-center text-gray-400">
        <BuildingOffice2Icon class="w-12 h-12 mx-auto mb-3 opacity-40" />
        <p class="text-sm">No sites yet. Create one to get started.</p>
      </div>

      <table v-else class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
        <tr>
          <th class="th">Name</th>
          <th class="th">Code</th>
          <th class="th">Location</th>
          <th class="th">Status</th>
          <th class="th text-center">Projects</th>
          <th class="th text-center">Members</th>
          <th class="th text-center">Created</th>
          <th class="th text-right">Actions</th>
        </tr>
        </thead>
        <tbody class="divide-y divide-gray-100 bg-white">
        <tr
            v-for="site in store.sites"
            :key="site.id"
            class="hover:bg-gray-50 transition-colors"
        >
          <td class="td font-medium text-gray-900">{{ site.name }}</td>
          <td class="td">
              <span class="font-mono bg-gray-100 px-2 py-0.5 rounded text-xs">
                {{ site.code }}
              </span>
          </td>
          <td class="td text-gray-500">{{ site.location || '—' }}</td>
          <td class="td">
            <StatusBadge :status="site.status" />
          </td>
          <td class="td text-center">
              <span class="text-sm font-semibold text-blue-600">
                {{ site.project_count ?? 0 }}
              </span>
          </td>
          <td class="td text-center">
            <button
                class="text-sm font-semibold text-purple-600 hover:underline"
                @click="openMembers(site)"
            >
              {{ site.member_count ?? 0 }}
            </button>
          </td>
          <td class="td text-gray-400 text-xs">
            {{ formatDate(site.created_at) }}
          </td>
          <td class="td text-right">
            <div class="flex justify-end gap-2">
              <button
                  @click="openEdit(site)"
                  class="icon-btn text-blue-600"
                  title="Edit"
              >
                <PencilIcon class="w-4 h-4" />
              </button>
              <button
                  @click="confirmDelete(site)"
                  class="icon-btn text-red-500"
                  title="Delete"
              >
                <TrashIcon class="w-4 h-4" />
              </button>
            </div>
          </td>
        </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div
          v-if="store.total > pageSize"
          class="px-4 py-3 border-t border-gray-200 flex items-center justify-between text-sm text-gray-600"
      >
        <span>Showing {{ store.sites.length }} of {{ store.total }}</span>
        <div class="flex gap-2">
          <button
              :disabled="page === 1"
              @click="changePage(page - 1)"
              class="btn-secondary py-1 px-3 disabled:opacity-40"
          >
            Prev
          </button>
          <button
              :disabled="store.sites.length < pageSize"
              @click="changePage(page + 1)"
              class="btn-secondary py-1 px-3 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Create / Edit Modal -->
    <Modal
        v-if="showForm"
        :title="editTarget ? 'Edit Site' : 'Add Site'"
        @close="closeForm"
    >
      <SiteForm
          :site="editTarget"
          :saving="saving"
          @submit="handleSubmit"
          @cancel="closeForm"
      />
    </Modal>

    <!-- Members Modal -->
    <Modal
        v-if="showMembers"
        :title="`Members — ${membersTarget?.name}`"
        @close="closeMembers"
    >
      <SiteMembersPanel
          :site="membersTarget"
          :members="store.members"
          :loading="membersLoading"
          @add="handleAddMember"
          @remove="handleRemoveMember"
      />
    </Modal>

    <!-- Delete Confirm Modal -->
    <ConfirmModal
        v-if="showDeleteConfirm"
        title="Delete Site"
        :message="`Permanently delete '${deleteTarget?.name}'? This cannot be undone.`"
        confirm-label="Delete"
        confirm-class="btn-danger"
        :loading="deleting"
        @confirm="doDelete"
        @cancel="showDeleteConfirm = false"
    />

    <!-- Toast -->
    <Toast ref="toast" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useSitesStore } from '@/stores/sites.js'
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ArrowPathIcon,
  BuildingOffice2Icon,
} from '@heroicons/vue/24/outline'

import StatCard         from '@/components/ui/StatCard.vue'
import StatusBadge      from '@/components/ui/StatusBadge.vue'
import Spinner          from '@/components/ui/Spinner.vue'
import AlertBanner      from '@/components/ui/AlertBanner.vue'
import Modal            from '@/components/ui/Modal.vue'
import ConfirmModal     from '@/components/ui/ConfirmModal.vue'
import Toast            from '@/components/ui/Toast.vue'
import SiteForm         from '@/components/sites/SiteForm.vue'
import SiteMembersPanel from '@/components/sites/SiteMembersPanel.vue'

// ── Store ────────────────────────────────────────────────────────────────────
const store = useSitesStore()

// ── Filters / pagination ─────────────────────────────────────────────────────
const search       = ref('')
const filterStatus = ref('')
const page         = ref(1)
const pageSize     = 20

let debounceTimer = null

function debouncedFetch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    page.value = 1
    doFetch()
  }, 350)
}

function doFetch() {
  const params = { page: page.value, page_size: pageSize }
  if (search.value)       params.search = search.value
  if (filterStatus.value) params.status = filterStatus.value
  store.fetchSites(params)
}

function changePage(n) {
  page.value = n
  doFetch()
}

onMounted(doFetch)

// ── Create / Edit ────────────────────────────────────────────────────────────
const showForm   = ref(false)
const editTarget = ref(null)
const saving     = ref(false)
const toast      = ref(null)

function openCreate() {
  editTarget.value = null
  showForm.value   = true
}

function openEdit(site) {
  editTarget.value = { ...site }
  showForm.value   = true
}

function closeForm() {
  showForm.value   = false
  editTarget.value = null
}

async function handleSubmit(payload) {
  saving.value = true
  try {
    if (editTarget.value) {
      await store.updateSite(editTarget.value.id, payload)
      toast.value?.show('Site updated successfully', 'success')
    } else {
      await store.createSite(payload)
      toast.value?.show('Site created successfully', 'success')
    }
    closeForm()
  } catch (e) {
    const msg = e.response?.data
        ? Object.values(e.response.data).flat().join(' ')
        : e.message
    toast.value?.show(msg, 'error')
  } finally {
    saving.value = false
  }
}

// ── Delete ───────────────────────────────────────────────────────────────────
const showDeleteConfirm = ref(false)
const deleteTarget      = ref(null)
const deleting          = ref(false)

function confirmDelete(site) {
  deleteTarget.value      = site
  showDeleteConfirm.value = true
}

async function doDelete() {
  deleting.value = true
  try {
    await store.deleteSite(deleteTarget.value.id)
    toast.value?.show('Site deleted', 'success')
    showDeleteConfirm.value = false
  } catch (e) {
    const detail = e.response?.data?.error
        ?? e.response?.data?.detail
        ?? e.message
    toast.value?.show(detail, 'error')
    showDeleteConfirm.value = false
  } finally {
    deleting.value = false
  }
}

// ── Members ──────────────────────────────────────────────────────────────────
const showMembers    = ref(false)
const membersTarget  = ref(null)
const membersLoading = ref(false)

async function openMembers(site) {
  membersTarget.value  = site
  showMembers.value    = true
  membersLoading.value = true
  try {
    await store.fetchMembers(site.id)
  } finally {
    membersLoading.value = false
  }
}

function closeMembers() {
  showMembers.value   = false
  membersTarget.value = null
}

async function handleAddMember(userId) {
  try {
    await store.addMember(membersTarget.value.id, userId)
    toast.value?.show('Member added', 'success')
  } catch (e) {
    toast.value?.show(e.response?.data?.error ?? e.message, 'error')
  }
}

async function handleRemoveMember(userId) {
  try {
    await store.removeMember(membersTarget.value.id, userId)
    toast.value?.show('Member removed', 'success')
  } catch (e) {
    toast.value?.show(e.response?.data?.error ?? e.message, 'error')
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day:   '2-digit',
    month: 'short',
    year:  'numeric',
  })
}
</script>
