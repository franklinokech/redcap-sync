<template>
  <div class="projects-view">
    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="page-header">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-subtitle">
          {{ store.total }} project{{ store.total !== 1 ? 's' : '' }} total
        </p>
      </div>
      <button class="btn btn-primary" @click="openCreate">
        <span class="btn-icon">+</span> New Project
      </button>
    </div>

    <!-- ── Error banner ───────────────────────────────────────────────────── -->
    <div v-if="store.error" class="alert alert-error">
      <strong>Error:</strong> {{ store.error }}
      <button class="alert-close" @click="store.error = null">✕</button>
    </div>

    <!-- ── Loading skeleton ───────────────────────────────────────────────── -->
    <div v-if="store.loading && store.projects.length === 0" class="skeleton-list">
      <div v-for="n in 4" :key="n" class="skeleton-card" />
    </div>

    <!-- ── Empty state ────────────────────────────────────────────────────── -->
    <div
        v-else-if="!store.loading && store.projects.length === 0"
        class="empty-state"
    >
      <div class="empty-icon">📋</div>
      <h3>No projects yet</h3>
      <p>Create your first project to start syncing REDCap data.</p>
      <button class="btn btn-primary" @click="openCreate">
        Create Project
      </button>
    </div>

    <!-- ── Project grid ───────────────────────────────────────────────────── -->
    <div v-else class="project-grid">
      <ProjectCard
          v-for="project in store.projects"
          :key="project.id"
          :project="project"
          @click="openDetail(project)"
          @edit="openEdit(project)"
          @delete="confirmDelete(project)"
      />
    </div>

    <!-- ── Create / Edit modal ────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showForm" class="modal-backdrop" @click.self="closeForm">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editTarget ? 'Edit Project' : 'New Project' }}</h2>
            <button class="modal-close" @click="closeForm">✕</button>
          </div>
          <ProjectForm
              :initial="editTarget"
              :sites="store.sites"
              :loading="formLoading"
              @submit="handleFormSubmit"
              @cancel="closeForm"
          />
        </div>
      </div>
    </Teleport>

    <!-- ── Detail panel ───────────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="detailProject" class="modal-backdrop" @click.self="closeDetail">
        <div class="modal modal-wide">
          <div class="modal-header">
            <h2>{{ detailProject.name }}</h2>
            <button class="modal-close" @click="closeDetail">✕</button>
          </div>
          <ProjectDetailPanel
              :project="detailProject"
              :registries="store.registries"
              @update="handleDetailUpdate"
              @close="closeDetail"
          />
        </div>
      </div>
    </Teleport>

    <!-- ── Delete confirmation ────────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="deleteTarget" class="modal-backdrop" @click.self="deleteTarget = null">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h2>Delete Project</h2>
          </div>
          <div class="modal-body">
            <p>
              Are you sure you want to delete
              <strong>{{ deleteTarget.name }}</strong>?
              This action cannot be undone.
            </p>
          </div>
          <div class="modal-footer">
            <button class="btn btn-ghost" @click="deleteTarget = null">
              Cancel
            </button>
            <button
                class="btn btn-danger"
                :disabled="deleteLoading"
                @click="handleDelete"
            >
              {{ deleteLoading ? 'Deleting…' : 'Delete' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useProjectsStore } from '@/stores/projects'
import ProjectCard        from '@/components/projects/ProjectCard.vue'
import ProjectForm        from '@/components/projects/ProjectForm.vue'
import ProjectDetailPanel from '@/components/projects/ProjectDetailPanel.vue'

const store = useProjectsStore()

// ── Modal state ────────────────────────────────────────────────────────────
const showForm     = ref(false)
const editTarget   = ref(null)
const formLoading  = ref(false)

const detailProject = ref(null)

const deleteTarget  = ref(null)
const deleteLoading = ref(false)

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    store.fetchProjects(),
    store.fetchSites(),
    store.fetchRegistries(),
  ])
})

// ── Form helpers ───────────────────────────────────────────────────────────
function openCreate() {
  editTarget.value = null
  showForm.value   = true
}

function openEdit(project) {
  editTarget.value = project
  showForm.value   = true
}

function closeForm() {
  showForm.value   = false
  editTarget.value = null
}

async function handleFormSubmit(payload) {
  formLoading.value = true
  try {
    if (editTarget.value) {
      await store.editProject(editTarget.value.id, payload)
    } else {
      await store.addProject(payload)
    }
    closeForm()
  } catch (err) {
    // Error surfaces in store.error — form stays open
    console.error('[ProjectsView] form submit error:', err)
  } finally {
    formLoading.value = false
  }
}

// ── Detail helpers ─────────────────────────────────────────────────────────
function openDetail(project) {
  detailProject.value = store.projectById(project.id) ?? project
}

function closeDetail() {
  detailProject.value = null
}

function handleDetailUpdate(updatedProject) {
  // Keep panel in sync after token / registry operations
  detailProject.value = updatedProject
}

// ── Delete helpers ─────────────────────────────────────────────────────────
function confirmDelete(project) {
  deleteTarget.value = project
}

async function handleDelete() {
  if (!deleteTarget.value) return
  deleteLoading.value = true
  try {
    await store.removeProject(deleteTarget.value.id)
    deleteTarget.value = null
    if (detailProject.value?.id === deleteTarget.value?.id) {
      detailProject.value = null
    }
  } catch (err) {
    console.error('[ProjectsView] delete error:', err)
  } finally {
    deleteLoading.value = false
  }
}
</script>

<style scoped>
.projects-view { padding: 1.5rem 2rem; max-width: 1400px; margin: 0 auto; }

/* Header */
.page-header {
  display: flex; align-items: flex-start;
  justify-content: space-between; margin-bottom: 1.5rem;
}
.page-title   { font-size: 1.75rem; font-weight: 700; margin: 0; }
.page-subtitle{ font-size: 0.875rem; color: #6b7280; margin: 0.25rem 0 0; }

/* Grid */
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

/* Skeleton */
.skeleton-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; }
.skeleton-card {
  height: 180px; border-radius: 0.75rem;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* Empty state */
.empty-state {
  text-align: center; padding: 4rem 2rem;
  color: #6b7280;
}
.empty-icon { font-size: 3rem; margin-bottom: 1rem; }
.empty-state h3 { font-size: 1.25rem; margin: 0 0 0.5rem; color: #374151; }
.empty-state p  { margin: 0 0 1.5rem; }

/* Alert */
.alert {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem; border-radius: 0.5rem;
  margin-bottom: 1rem; font-size: 0.875rem;
}
.alert-error  { background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b; }
.alert-close  { background: none; border: none; cursor: pointer; font-size: 1rem; }

/* Buttons */
.btn {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.5rem 1rem; border-radius: 0.5rem;
  font-size: 0.875rem; font-weight: 500;
  border: none; cursor: pointer; transition: opacity 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-danger  { background: #dc2626; color: #fff; }
.btn-danger:hover:not(:disabled) { background: #b91c1c; }
.btn-ghost   { background: transparent; color: #374151; border: 1px solid #d1d5db; }
.btn-ghost:hover { background: #f9fafb; }
.btn-icon    { font-size: 1.1rem; line-height: 1; }

/* Modal */
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 50; padding: 1rem;
}
.modal {
  background: #fff; border-radius: 0.75rem;
  width: 100%; max-width: 560px;
  max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.modal-wide { max-width: 860px; }
.modal-sm   { max-width: 400px; }
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.25rem 1.5rem; border-bottom: 1px solid #e5e7eb;
}
.modal-header h2 { margin: 0; font-size: 1.125rem; font-weight: 600; }
.modal-close {
  background: none; border: none; cursor: pointer;
  font-size: 1.25rem; color: #6b7280; line-height: 1;
}
.modal-close:hover { color: #111827; }
.modal-body   { padding: 1.5rem; }
.modal-footer {
  display: flex; justify-content: flex-end; gap: 0.75rem;
  padding: 1rem 1.5rem; border-top: 1px solid #e5e7eb;
}
</style>
