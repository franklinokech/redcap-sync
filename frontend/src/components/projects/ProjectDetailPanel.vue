<template>
  <div class="detail-panel">
    <!-- ── Tabs ──────────────────────────────────────────────────────────── -->
    <div class="tabs">
      <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- ── Overview ──────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'overview'" class="tab-content">
      <dl class="info-grid">
        <div class="info-row">
          <dt>Status</dt>
          <dd>
            <span class="status-badge" :class="`status-${project.status}`">
              {{ project.status }}
            </span>
          </dd>
        </div>
        <div class="info-row">
          <dt>Site</dt>
          <dd>{{ project.site_name || '—' }}
            <span v-if="project.site_code" class="muted">({{ project.site_code }})</span>
          </dd>
        </div>
        <div class="info-row">
          <dt>REDCap URL</dt>
          <dd>
            <a v-if="project.redcap_url" :href="project.redcap_url" target="_blank" rel="noopener">
              {{ project.redcap_url }}
            </a>
            <span v-else class="muted">—</span>
          </dd>
        </div>
        <div class="info-row">
          <dt>REDCap Project ID</dt>
          <dd>{{ project.project_id ?? '—' }}</dd>
        </div>
        <div class="info-row">
          <dt>Record ID Prefix</dt>
          <dd>{{ project.record_id_prefix || project.site_code || '—' }}</dd>
        </div>
        <div class="info-row">
          <dt>Description</dt>
          <dd>{{ project.description || '—' }}</dd>
        </div>
        <div class="info-row">
          <dt>Created</dt>
          <dd>{{ formatDate(project.created_at) }}</dd>
        </div>
        <div class="info-row">
          <dt>Updated</dt>
          <dd>{{ formatDate(project.updated_at) }}</dd>
        </div>
      </dl>
    </div>

    <!-- ── Token ─────────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'token'" class="tab-content">
      <!-- Current token status -->
      <div class="token-status" :class="project.has_token ? 'token-ok' : 'token-missing'">
        <span>{{ project.has_token ? '🔑 Token configured' : '⚠️  No token set' }}</span>
        <code v-if="project.token_preview" class="token-preview">
          {{ project.token_preview }}
        </code>
      </div>

      <!-- Validate existing token -->
      <div v-if="project.has_token" class="section">
        <button
            class="btn btn-outline"
            :disabled="validating"
            @click="handleValidateToken"
        >
          {{ validating ? 'Validating…' : 'Validate Token' }}
        </button>
        <p v-if="validateResult" class="validate-result" :class="validateResult.ok ? 'ok' : 'fail'">
          {{ validateResult.message }}
        </p>
      </div>

      <!-- Add / rotate token -->
      <div class="section">
        <h4>{{ project.has_token ? 'Rotate Token' : 'Add Token' }}</h4>
        <form @submit.prevent="handleAddToken">
          <div class="field">
            <label class="field-label">REDCap API Token *</label>
            <input
                v-model.trim="tokenForm.token"
                type="text"
                class="field-input font-mono"
                placeholder="32-character hex token"
                maxlength="32"
                required
            />
          </div>
          <div class="field">
            <label class="field-label">Label</label>
            <input
                v-model.trim="tokenForm.label"
                type="text"
                class="field-input"
                placeholder="e.g. Primary token"
            />
          </div>
          <button
              type="submit"
              class="btn btn-primary mt-1"
              :disabled="tokenLoading"
          >
            {{ tokenLoading ? 'Saving…' : 'Save Token' }}
          </button>
        </form>
      </div>

      <p v-if="tokenError" class="error-msg">{{ tokenError }}</p>
    </div>

    <!-- ── Registry ───────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'registry'" class="tab-content">
      <!-- Current link -->
      <div
          class="token-status"
          :class="project.central_registry ? 'token-ok' : 'token-missing'"
      >
        <span>
          {{
            project.central_registry
                ? `🔗 Linked to: ${project.central_registry_name}`
                : '○  No registry linked'
          }}
        </span>
        <span v-if="project.central_registry_url" class="muted small">
          {{ project.central_registry_url }}
        </span>
      </div>

      <!-- Link form -->
      <div class="section">
        <h4>{{ project.central_registry ? 'Change Registry' : 'Link Registry' }}</h4>
        <form @submit.prevent="handleLinkRegistry">
          <div class="field">
            <label class="field-label">Central Registry *</label>
            <select
                v-model="registryForm.central_registry"
                class="field-input"
                required
            >
              <option value="" disabled>Select a registry…</option>
              <option
                  v-for="reg in registries"
                  :key="reg.id"
                  :value="reg.id"
              >
                {{ reg.name }}
              </option>
            </select>
          </div>
          <button
              type="submit"
              class="btn btn-primary mt-1"
              :disabled="registryLoading"
          >
            {{ registryLoading ? 'Linking…' : 'Link Registry' }}
          </button>
        </form>
        <p v-if="registryError" class="error-msg">{{ registryError }}</p>
      </div>
    </div>

    <!-- ── Sync config ────────────────────────────────────────────────────── -->
    <div v-if="activeTab === 'sync'" class="tab-content">
      <dl class="info-grid">
        <div class="info-row">
          <dt>Sync Forms</dt>
          <dd>
            <template v-if="project.sync_forms?.length">
              <code v-for="f in project.sync_forms" :key="f" class="tag">{{ f }}</code>
            </template>
            <span v-else class="muted">All forms</span>
          </dd>
        </div>
        <div class="info-row">
          <dt>Sync Fields</dt>
          <dd>
            <template v-if="project.sync_fields?.length">
              <code v-for="f in project.sync_fields" :key="f" class="tag">{{ f }}</code>
            </template>
            <span v-else class="muted">All fields</span>
          </dd>
        </div>
        <div class="info-row">
          <dt>Central Project ID</dt>
          <dd>{{ project.central_project_id ?? '—' }}</dd>
        </div>
      </dl>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useProjectsStore } from '@/stores/projects'

const props = defineProps({
  project:    { type: Object, required: true },
  registries: { type: Array,  default: () => [] },
})

const emit = defineEmits(['update', 'close'])

const store = useProjectsStore()

// ── Tabs ───────────────────────────────────────────────────────────────────
const tabs = [
  { id: 'overview',  label: 'Overview' },
  { id: 'token',     label: 'Token' },
  { id: 'registry',  label: 'Registry' },
  { id: 'sync',      label: 'Sync Config' },
]
const activeTab = ref('overview')

// ── Token section ──────────────────────────────────────────────────────────
const tokenForm    = reactive({ token: '', label: 'Primary token' })
const tokenLoading = ref(false)
const tokenError   = ref(null)
const validating   = ref(false)
const validateResult = ref(null)

async function handleAddToken() {
  tokenError.value    = null
  tokenLoading.value  = true
  try {
    await store.setToken(props.project.id, tokenForm.token, tokenForm.label)
    const updated = store.projectById(props.project.id)
    if (updated) emit('update', updated)
    tokenForm.token = ''
    tokenForm.label = 'Primary token'
  } catch (err) {
    tokenError.value = err.response?.data?.token?.[0]
        ?? err.response?.data?.detail
        ?? 'Failed to save token.'
  } finally {
    tokenLoading.value = false
  }
}

async function handleValidateToken() {
  validating.value     = true
  validateResult.value = null
  try {
    const data = await store.validateToken(props.project.id)
    validateResult.value = {
      ok:      true,
      message: `✓ Valid — REDCap project: "${data.project_title}" (ID ${data.project_id})`,
    }
    const updated = store.projectById(props.project.id)
    if (updated) emit('update', updated)
  } catch (err) {
    validateResult.value = {
      ok:      false,
      message: err.response?.data?.error ?? 'Token validation failed.',
    }
  } finally {
    validating.value = false
  }
}

// ── Registry section ───────────────────────────────────────────────────────
const registryForm    = reactive({ central_registry: '' })
const registryLoading = ref(false)
const registryError   = ref(null)

async function handleLinkRegistry() {
  registryError.value   = null
  registryLoading.value = true
  try {
    const updated = await store.linkProjectRegistry(
        props.project.id,
        registryForm.central_registry
    )
    emit('update', updated)
    registryForm.central_registry = ''
  } catch (err) {
    registryError.value = err.response?.data?.detail
        ?? err.response?.data?.error
        ?? 'Failed to link registry.'
  } finally {
    registryLoading.value = false
  }
}

// ── Utils ──────────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(new Date(iso))
}
</script>

<style scoped>
.detail-panel { display: flex; flex-direction: column; }

/* Tabs */
.tabs {
  display: flex; gap: 0; border-bottom: 1px solid #e5e7eb;
  padding: 0 1.5rem;
}
.tab-btn {
  background: none; border: none; cursor: pointer;
  padding: 0.75rem 1rem; font-size: 0.875rem; font-weight: 500;
  color: #6b7280; border-bottom: 2px solid transparent;
  margin-bottom: -1px; transition: color 0.15s, border-color 0.15s;
}
.tab-btn:hover  { color: #111827; }
.tab-btn.active { color: #2563eb; border-bottom-color: #2563eb; }

/* Content */
.tab-content { padding: 1.5rem; }

/* Info grid */
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem 1.5rem; margin: 0; }
.info-row  { display: flex; flex-direction: column; gap: 0.2rem; }
.info-row dt {
  font-size: 0.75rem; font-weight: 600;
  color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;
}
.info-row dd { margin: 0; font-size: 0.875rem; color: #111827; word-break: break-all; }

/* Status */
.status-badge {
  display: inline-block;
  font-size: 0.7rem; font-weight: 600;
  padding: 0.2rem 0.6rem; border-radius: 9999px;
  text-transform: uppercase;
}
.status-active   { background: #dcfce7; color: #166534; }
.status-inactive { background: #f3f4f6; color: #6b7280; }
.status-pending  { background: #fef9c3; color: #854d0e; }

/* Token status */
.token-status {
  display: flex; flex-direction: column; gap: 0.25rem;
  padding: 0.75rem 1rem; border-radius: 0.5rem;
  margin-bottom: 1.25rem; font-size: 0.875rem;
}
.token-ok      { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.token-missing { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
.token-preview { font-family: monospace; font-size: 0.8rem; }

/* Section */
.section { margin-top: 1.25rem; }
.section h4 { margin: 0 0 0.75rem; font-size: 0.9rem; font-weight: 600; }

/* Fields */
.field       { display: flex; flex-direction: column; gap: 0.375rem; margin-bottom: 0.75rem; }
.field-label { font-size: 0.8rem; font-weight: 600; color: #374151; }
.field-input {
  padding: 0.5rem 0.75rem; border: 1px solid #d1d5db;
  border-radius: 0.5rem; font-size: 0.875rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.field-input:focus {
  outline: none; border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}
.font-mono { font-family: monospace; letter-spacing: 0.05em; }

/* Validate result */
.validate-result { margin-top: 0.5rem; font-size: 0.8rem; }
.validate-result.ok   { color: #166534; }
.validate-result.fail { color: #dc2626; }

/* Tags */
.tag {
  display: inline-block; background: #f3f4f6;
  padding: 0.1rem 0.4rem; border-radius: 0.25rem;
  font-size: 0.75rem; margin: 0.125rem;
}

/* Misc */
.muted  { color: #9ca3af; }
.small  { font-size: 0.75rem; }
.mt-1   { margin-top: 0.25rem; }
.error-msg { font-size: 0.8rem; color: #dc2626; margin-top: 0.5rem; }
.ok   { color: #166534; }
.fail { color: #dc2626; }
a { color: #2563eb; }

/* Buttons */
.btn {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.5rem 1.25rem; border-radius: 0.5rem;
  font-size: 0.875rem; font-weight: 500;
  border: none; cursor: pointer;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-outline {
  background: transparent; color: #2563eb;
  border: 1px solid #2563eb;
}
.btn-outline:hover:not(:disabled) { background: #eff6ff; }
</style>
