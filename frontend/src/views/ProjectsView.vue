<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1 class="page-title">Projects</h1>
        <p class="page-sub">Manage sites, projects and API tokens</p>
      </div>
      <button class="btn btn-primary btn-sm" @click="openAddSite">+ Add site</button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="empty-state">
      <div class="empty-state-text">Loading…</div>
    </div>

    <!-- Sites + Projects -->
    <div v-else class="sites-list">
      <div v-if="!sites.length" class="empty-state">
        <div class="empty-state-icon">⊞</div>
        <div class="empty-state-title">No sites yet</div>
        <div class="empty-state-text">Add a site to get started</div>
      </div>

      <div v-for="site in sites" :key="site.id" class="site-block">
        <!-- Site header -->
        <div class="site-header">
          <div class="site-info">
            <div class="site-name">{{ site.name }}</div>
            <div class="site-meta">
              <span class="badge badge-pending font-mono">{{ site.code }}</span>
              <span v-if="site.location" class="text-dim">{{ site.location }}</span>
              <span class="text-dim">{{ site.project_count }} project{{ site.project_count !== 1 ? 's' : '' }}</span>
            </div>
          </div>
          <div class="site-actions">
            <button class="btn btn-secondary btn-sm" @click="openAddProject(site)">+ Project</button>
          </div>
        </div>

        <!-- Projects table -->
        <div v-if="projectsBySite(site.id).length" class="projects-table">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>REDCap URL</th>
                <th>Token</th>
                <th>Forms</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="proj in projectsBySite(site.id)" :key="proj.id">
                <td>
                  <div class="proj-name">{{ proj.name }}</div>
                  <div v-if="proj.record_id_prefix" class="text-dim font-mono" style="font-size:10px">
                    prefix: {{ proj.record_id_prefix }}
                  </div>
                </td>
                <td class="font-mono text-dim" style="font-size:11px">{{ proj.redcap_url }}</td>
                <td>
                  <div v-if="proj.has_token" class="token-ok">
                    <span class="text-success">✓</span>
                    <span class="font-mono text-dim" style="font-size:11px">{{ proj.token?.token_preview }}</span>
                    <button class="btn-link text-danger" @click="openRotateToken(proj)">rotate</button>
                  </div>
                  <div v-else class="token-missing">
                    <span class="text-warning">⚠</span>
                    <button class="btn-link text-teal" @click="openAddToken(proj)">Add token</button>
                  </div>
                </td>
                <td class="text-dim" style="font-size:11px">{{ proj.sync_forms || 'All' }}</td>
                <td>
                  <span class="badge" :class="`badge-${proj.status === 'active' ? 'success' : 'warning'}`">
                    {{ proj.status }}
                  </span>
                </td>
                <td>
                  <div class="row-actions">
                    <button
                      v-if="proj.has_token"
                      class="btn btn-secondary btn-sm"
                      @click="validateToken(proj)"
                      :disabled="validating === proj.id"
                    >
                      {{ validating === proj.id ? '…' : 'Validate' }}
                    </button>
                    <button class="btn btn-secondary btn-sm" @click="openEditProject(proj)">Edit</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="no-projects">
          No projects yet — click <strong>+ Project</strong> to add one
        </div>
      </div>
    </div>

    <!-- Registry section -->
    <div class="card registry-section">
      <div class="card-header">
        <h2 class="section-title">Central Registry</h2>
        <button class="btn btn-secondary btn-sm" @click="openRegistryModal">
          {{ registry ? 'Edit' : '+ Configure' }}
        </button>
      </div>
      <div v-if="registry" class="registry-detail">
        <div class="reg-row">
          <span class="meta-label">Name</span>
          <span>{{ registry.name }}</span>
        </div>
        <div class="reg-row">
          <span class="meta-label">URL</span>
          <span class="font-mono text-dim" style="font-size:12px">{{ registry.redcap_url }}</span>
        </div>
        <div class="reg-row">
          <span class="meta-label">Token</span>
          <span class="font-mono text-dim" style="font-size:12px">{{ registry.token_preview }}</span>
        </div>
        <div class="reg-row">
          <span class="meta-label">Project ID</span>
          <span class="font-mono">{{ registry.project_id || '—' }}</span>
        </div>
      </div>
      <div v-else class="empty-state">
        <div class="empty-state-icon">⬡</div>
        <div class="empty-state-title">No registry configured</div>
        <div class="empty-state-text">Configure the central registry to enable syncing</div>
      </div>
    </div>

    <!-- ── Modals ── -->

    <!-- Add/Edit Site -->
    <Modal v-if="siteModal.open" :title="siteModal.editing ? 'Edit site' : 'Add site'" @close="siteModal.open = false">
      <div class="form-group">
        <label class="form-label">Name <span class="text-danger">*</span></label>
        <input class="form-input" v-model="siteModal.form.name" placeholder="Nairobi County Hospital" />
      </div>
      <div class="form-group">
        <label class="form-label">Code <span class="text-danger">*</span></label>
        <input class="form-input" v-model="siteModal.form.code" placeholder="NBI-01" style="font-family:var(--font-mono)" />
      </div>
      <div class="form-group">
        <label class="form-label">Location</label>
        <input class="form-input" v-model="siteModal.form.location" placeholder="Nairobi, Kenya" />
      </div>
      <div class="form-group">
        <label class="form-label">Description</label>
        <input class="form-input" v-model="siteModal.form.description" />
      </div>
      <div v-if="modalError" class="modal-error">{{ modalError }}</div>
      <template #footer>
        <button class="btn btn-secondary" @click="siteModal.open = false">Cancel</button>
        <button class="btn btn-primary" @click="saveSite" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save site' }}
        </button>
      </template>
    </Modal>

    <!-- Add/Edit Project -->
    <Modal v-if="projectModal.open" :title="projectModal.editing ? 'Edit project' : 'Add project'" @close="projectModal.open = false">
      <div class="form-group">
        <label class="form-label">Site</label>
        <select class="form-select" v-model="projectModal.form.site">
          <option v-for="s in sites" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Name <span class="text-danger">*</span></label>
        <input class="form-input" v-model="projectModal.form.name" placeholder="Enrollment Form" />
      </div>
      <div class="form-group">
        <label class="form-label">REDCap API URL <span class="text-danger">*</span></label>
        <input class="form-input" v-model="projectModal.form.redcap_url" placeholder="https://redcap.site.ac.ke/api/" />
      </div>
      <div class="form-group">
        <label class="form-label">Record ID prefix</label>
        <input class="form-input" v-model="projectModal.form.record_id_prefix" placeholder="NBI-" style="font-family:var(--font-mono)" />
        <div class="form-hint">Added to record IDs to avoid collisions in the registry</div>
      </div>
      <div class="form-group">
        <label class="form-label">Sync forms (comma-separated, blank = all)</label>
        <input class="form-input" v-model="projectModal.form.sync_forms" placeholder="enrollment,follow_up" />
      </div>
      <div class="form-group">
        <label class="form-label">Status</label>
        <select class="form-select" v-model="projectModal.form.status">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="testing">Testing</option>
        </select>
      </div>
      <div v-if="modalError" class="modal-error">{{ modalError }}</div>
      <template #footer>
        <button class="btn btn-secondary" @click="projectModal.open = false">Cancel</button>
        <button class="btn btn-primary" @click="saveProject" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save project' }}
        </button>
      </template>
    </Modal>

    <!-- Add/Rotate Token -->
    <Modal v-if="tokenModal.open" :title="tokenModal.rotating ? 'Rotate token' : 'Add token'" @close="tokenModal.open = false">
      <p class="text-muted" style="font-size:12px; margin-bottom:16px">
        Project: <strong>{{ tokenModal.project?.name }}</strong>
      </p>
      <div class="form-group">
        <label class="form-label">REDCap API token <span class="text-danger">*</span></label>
        <input
          class="form-input"
          v-model="tokenModal.token"
          type="password"
          placeholder="32-character token"
          maxlength="32"
          style="font-family:var(--font-mono)"
        />
        <div class="form-hint">{{ tokenModal.token.length }}/32 characters</div>
      </div>
      <div class="form-group">
        <label class="form-label">Label (optional)</label>
        <input class="form-input" v-model="tokenModal.label" placeholder="Production token — Apr 2025" />
      </div>
      <div v-if="modalError" class="modal-error">{{ modalError }}</div>
      <div v-if="validateResult" class="validate-result" :class="validateResult.success?.[0] ? 'ok' : 'fail'">
        <div v-if="validateResult.success?.[0]">
          ✓ Connected to <strong>{{ validateResult.info?.[0]?.project_title }}</strong>
          (ID: {{ validateResult.info?.[0]?.project_id }})
        </div>
        <div v-else>✗ {{ validateResult.message?.[0] || 'Validation failed' }}</div>
      </div>
      <template #footer>
        <button class="btn btn-secondary" @click="tokenModal.open = false">Cancel</button>
        <button class="btn btn-primary" @click="saveToken" :disabled="saving || tokenModal.token.length !== 32">
          {{ saving ? 'Saving…' : 'Save token' }}
        </button>
      </template>
    </Modal>

    <!-- Registry modal -->
    <Modal v-if="registryModal.open" title="Configure registry" @close="registryModal.open = false">
      <div class="form-group">
        <label class="form-label">Name <span class="text-danger">*</span></label>
        <input class="form-input" v-model="registryModal.form.name" placeholder="National Registry" />
      </div>
      <div class="form-group">
        <label class="form-label">REDCap API URL <span class="text-danger">*</span></label>
        <input class="form-input" v-model="registryModal.form.redcap_url" placeholder="https://redcap.central.ac.ke/api/" />
      </div>
      <div class="form-group">
        <label class="form-label">API Token <span class="text-danger">*</span></label>
        <input
          class="form-input"
          v-model="registryModal.form.token"
          type="password"
          placeholder="32-character token"
          style="font-family:var(--font-mono)"
        />
      </div>
      <div class="form-group">
        <label style="display:flex; align-items:center; gap:8px; cursor:pointer">
          <input type="checkbox" v-model="registryModal.form.overwrite_with_blanks" />
          <span class="form-label" style="margin:0">Overwrite with blanks</span>
        </label>
        <div class="form-hint">Allow blank values from source to overwrite existing registry data</div>
      </div>
      <div v-if="modalError" class="modal-error">{{ modalError }}</div>
      <template #footer>
        <button class="btn btn-secondary" @click="registryModal.open = false">Cancel</button>
        <button class="btn btn-primary" @click="saveRegistry" :disabled="saving">
          {{ saving ? 'Saving…' : 'Save registry' }}
        </button>
      </template>
    </Modal>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useSyncStore } from '@/stores/sync'
import { sitesApi, projectsApi, registryApi } from '@/api'
import Modal from '@/components/ui/Modal.vue'

const store    = useSyncStore()
const loading  = ref(false)
const saving   = ref(false)
const validating = ref(null)
const modalError = ref('')
const validateResult = ref(null)

const sites    = computed(() => store.sites)
const projects = computed(() => store.projects)
const registry = computed(() => store.registry)

function projectsBySite(siteId) {
  return projects.value.filter(p => p.site === siteId)
}

// ── Site modal ────────────────────────────────────────────────────────────────
const siteModal = ref({
  open: false, editing: false,
  form: { name: '', code: '', location: '', description: '' },
  id: null,
})

function openAddSite() {
  siteModal.value = { open: true, editing: false, id: null,
    form: { name: '', code: '', location: '', description: '' } }
  modalError.value = ''
}

async function saveSite() {
  saving.value = true; modalError.value = ''
  try {
    if (siteModal.value.editing) {
      await sitesApi.update(siteModal.value.id, siteModal.value.form)
    } else {
      await sitesApi.create(siteModal.value.form)
    }
    siteModal.value.open = false
    await store.fetchSites()
  } catch (e) {
    modalError.value = e.response?.data?.detail || JSON.stringify(e.response?.data) || 'Save failed.'
  } finally { saving.value = false }
}

// ── Project modal ─────────────────────────────────────────────────────────────
const projectModal = ref({
  open: false, editing: false, id: null,
  form: { site: '', name: '', redcap_url: '', record_id_prefix: '', sync_forms: '', status: 'active' },
})

function openAddProject(site) {
  projectModal.value = {
    open: true, editing: false, id: null,
    form: { site: site.id, name: '', redcap_url: '', record_id_prefix: '', sync_forms: '', status: 'active' },
  }
  modalError.value = ''
}

function openEditProject(proj) {
  projectModal.value = {
    open: true, editing: true, id: proj.id,
    form: { site: proj.site, name: proj.name, redcap_url: proj.redcap_url,
            record_id_prefix: proj.record_id_prefix, sync_forms: proj.sync_forms, status: proj.status },
  }
  modalError.value = ''
}

async function saveProject() {
  saving.value = true; modalError.value = ''
  try {
    if (projectModal.value.editing) {
      await projectsApi.update(projectModal.value.id, projectModal.value.form)
    } else {
      await projectsApi.create(projectModal.value.form)
    }
    projectModal.value.open = false
    await store.fetchProjects()
    await store.fetchSites()
  } catch (e) {
    modalError.value = e.response?.data?.detail || JSON.stringify(e.response?.data) || 'Save failed.'
  } finally { saving.value = false }
}

// ── Token modal ───────────────────────────────────────────────────────────────
const tokenModal = ref({ open: false, rotating: false, project: null, token: '', label: '' })

function openAddToken(proj) {
  tokenModal.value = { open: true, rotating: false, project: proj, token: '', label: '' }
  modalError.value = ''; validateResult.value = null
}

function openRotateToken(proj) {
  tokenModal.value = { open: true, rotating: true, project: proj, token: '', label: '' }
  modalError.value = ''; validateResult.value = null
}

async function saveToken() {
  saving.value = true; modalError.value = ''
  try {
    await projectsApi.setToken(tokenModal.value.project.id, {
      token: tokenModal.value.token,
      label: tokenModal.value.label,
    })
    tokenModal.value.open = false
    await store.fetchProjects()
  } catch (e) {
    modalError.value = e.response?.data?.detail || 'Failed to save token.'
  } finally { saving.value = false }
}

async function validateToken(proj) {
  validating.value = proj.id
  try {
    const { data } = await projectsApi.validateToken(proj.id)
    const ok = data.success?.[0] ?? data.success
    const title = data.info?.[0]?.project_title || data.info?.project_title
    alert(ok ? `✓ Connected to: ${title}` : `✗ ${data.message?.[0] || 'Validation failed'}`)
  } catch (e) {
    alert('Validation error: ' + (e.response?.data?.message || e.message))
  } finally { validating.value = null }
}

// ── Registry modal ────────────────────────────────────────────────────────────
const registryModal = ref({
  open: false,
  form: { name: '', redcap_url: '', token: '', is_active: true, overwrite_with_blanks: false },
})

function openRegistryModal() {
  const r = registry.value
  registryModal.value = {
    open: true,
    form: {
      name:                 r?.name        || '',
      redcap_url:           r?.redcap_url  || '',
      token:                '',
      is_active:            true,
      overwrite_with_blanks: r?.overwrite_with_blanks || false,
    },
  }
  modalError.value = ''
}

async function saveRegistry() {
  saving.value = true; modalError.value = ''
  try {
    const r = registry.value
    if (r) {
      const payload = { ...registryModal.value.form }
      if (!payload.token) delete payload.token
      await registryApi.update(r.id, payload)
    } else {
      await registryApi.create(registryModal.value.form)
    }
    registryModal.value.open = false
    await store.fetchActiveRegistry()
  } catch (e) {
    modalError.value = e.response?.data?.detail || JSON.stringify(e.response?.data) || 'Save failed.'
  } finally { saving.value = false }
}

onMounted(async () => {
  loading.value = true
  await Promise.all([
    store.fetchSites(),
    store.fetchProjects(),
    store.fetchActiveRegistry(),
  ])
  loading.value = false
})
</script>

<style scoped>
.page { padding: 28px; max-width: 1100px; }
.page-header {
  display: flex; justify-content: space-between;
  align-items: flex-start; margin-bottom: 24px;
}
.page-title { font-size: 20px; font-weight: 600; letter-spacing: -0.02em; }
.page-sub   { font-size: 12px; color: var(--c-text-3); margin-top: 3px; }

.sites-list { display: flex; flex-direction: column; gap: 16px; margin-bottom: 16px; }

.site-block {
  background: var(--c-bg-2); border: 1px solid var(--c-border);
  border-radius: var(--r-lg); overflow: hidden;
}
.site-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid var(--c-border);
  background: var(--c-bg-3);
}
.site-name { font-size: 14px; font-weight: 600; margin-bottom: 6px; }
.site-meta { display: flex; align-items: center; gap: 10px; font-size: 12px; }

.projects-table { padding: 0; }
.no-projects {
  padding: 16px 20px; font-size: 12px; color: var(--c-text-3);
}

.proj-name { font-size: 13px; font-weight: 500; color: var(--c-text); }

.token-ok, .token-missing {
  display: flex; align-items: center; gap: 6px; font-size: 12px;
}
.btn-link {
  background: none; border: none; cursor: pointer;
  font-size: 11px; font-family: var(--font); padding: 0;
  text-decoration: underline;
}

.row-actions { display: flex; gap: 6px; }

.registry-section { margin-top: 4px; }
.card-header {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 16px;
}
.section-title { font-size: 14px; font-weight: 600; }

.registry-detail { display: flex; flex-direction: column; gap: 10px; }
.reg-row { display: flex; gap: 16px; align-items: center; font-size: 13px; }
.meta-label {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--c-text-3); min-width: 80px;
}

.modal-error {
  background: var(--c-danger-bg); border: 1px solid rgba(248,113,113,0.2);
  border-radius: var(--r-md); padding: 9px 12px;
  color: var(--c-danger); font-size: 12px; margin-top: 12px;
}

.validate-result {
  margin-top: 10px; padding: 10px 12px;
  border-radius: var(--r-md); font-size: 12px;
}
.validate-result.ok   { background: var(--c-success-bg); color: var(--c-success); border: 1px solid rgba(52,211,153,0.2); }
.validate-result.fail { background: var(--c-danger-bg);  color: var(--c-danger);  border: 1px solid rgba(248,113,113,0.2); }
</style>