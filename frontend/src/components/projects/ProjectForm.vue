<template>
  <form class="project-form" @submit.prevent="handleSubmit">
    <div class="form-body">
      <!-- Name -->
      <div class="field">
        <label class="field-label" for="pf-name">Project Name *</label>
        <input
            id="pf-name"
            v-model.trim="form.name"
            type="text"
            class="field-input"
            :class="{ 'field-error': errors.name }"
            placeholder="e.g. KNH Maternal Admission Records"
            required
        />
        <span v-if="errors.name" class="error-msg">{{ errors.name }}</span>
      </div>

      <!-- Site -->
      <div class="field">
        <label class="field-label" for="pf-site">Site *</label>
        <select
            id="pf-site"
            v-model="form.site"
            class="field-input"
            :class="{ 'field-error': errors.site }"
            required
        >
          <option value="" disabled>Select a site…</option>
          <option v-for="site in sites" :key="site.id" :value="site.id">
            {{ site.name }}
            <template v-if="site.code">({{ site.code }})</template>
          </option>
        </select>
        <span v-if="errors.site" class="error-msg">{{ errors.site }}</span>
      </div>

      <!-- Status -->
      <div class="field">
        <label class="field-label" for="pf-status">Status</label>
        <select id="pf-status" v-model="form.status" class="field-input">
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      <!-- REDCap URL -->
      <div class="field">
        <label class="field-label" for="pf-url">REDCap API URL</label>
        <input
            id="pf-url"
            v-model.trim="form.redcap_url"
            type="url"
            class="field-input"
            placeholder="https://redcap.example.org/api/"
        />
      </div>

      <!-- Record ID prefix -->
      <div class="field">
        <label class="field-label" for="pf-prefix">
          Record ID Prefix
          <span class="field-hint">(defaults to site code if blank)</span>
        </label>
        <input
            id="pf-prefix"
            v-model.trim="form.record_id_prefix"
            type="text"
            class="field-input"
            placeholder="Leave blank to use site code"
        />
      </div>

      <!-- Description -->
      <div class="field field-full">
        <label class="field-label" for="pf-desc">Description</label>
        <textarea
            id="pf-desc"
            v-model.trim="form.description"
            class="field-input"
            rows="3"
            placeholder="Optional project description"
        />
      </div>
    </div>

    <div class="form-footer">
      <button type="button" class="btn btn-ghost" @click="$emit('cancel')">
        Cancel
      </button>
      <button type="submit" class="btn btn-primary" :disabled="loading">
        {{ loading ? 'Saving…' : (initial ? 'Save Changes' : 'Create Project') }}
      </button>
    </div>
  </form>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  initial: { type: Object, default: null },
  sites:   { type: Array,  default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['submit', 'cancel'])

// ── Form state ─────────────────────────────────────────────────────────────
const form = reactive({
  name:             '',
  site:             '',
  status:           'active',
  redcap_url:       '',
  record_id_prefix: '',
  description:      '',
  sync_forms:       [],
  sync_fields:      [],
})

const errors = reactive({})

// ── Pre-fill when editing ──────────────────────────────────────────────────
watch(
    () => props.initial,
    project => {
      if (!project) {
        Object.assign(form, {
          name: '', site: '', status: 'active',
          redcap_url: '', record_id_prefix: '',
          description: '', sync_forms: [], sync_fields: [],
        })
      } else {
        form.name             = project.name             ?? ''
        form.site             = project.site             ?? ''
        form.status           = project.status           ?? 'active'
        form.redcap_url       = project.redcap_url       ?? ''
        form.record_id_prefix = project.record_id_prefix ?? ''
        form.description      = project.description      ?? ''
        form.sync_forms       = project.sync_forms       ?? []
        form.sync_fields      = project.sync_fields      ?? []
      }
    },
    { immediate: true }
)

// ── Validation ─────────────────────────────────────────────────────────────
function validate() {
  Object.keys(errors).forEach(k => delete errors[k])

  if (!form.name)
    errors.name = 'Project name is required.'
  if (!form.site)
    errors.site = 'Please select a site.'

  return Object.keys(errors).length === 0
}

// ── Submit ─────────────────────────────────────────────────────────────────
function handleSubmit() {
  if (!validate()) return

  // Per Postman: send empty string for record_id_prefix to let backend
  // default it to site_code
  const payload = {
    name:             form.name,
    site:             form.site,
    status:           form.status,
    redcap_url:       form.redcap_url || '',
    record_id_prefix: form.record_id_prefix || '',
    description:      form.description || '',
    sync_forms:       form.sync_forms,
    sync_fields:      form.sync_fields,
  }

  emit('submit', payload)
}
</script>

<style scoped>
.project-form { display: flex; flex-direction: column; }

.form-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem 1.5rem;
  padding: 1.5rem;
}

.field       { display: flex; flex-direction: column; gap: 0.375rem; }
.field-full  { grid-column: 1 / -1; }

.field-label {
  font-size: 0.8rem; font-weight: 600;
  color: #374151; letter-spacing: 0.01em;
}
.field-hint  { font-weight: 400; color: #9ca3af; }

.field-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  background: #fff;
  transition: border-color 0.15s, box-shadow 0.15s;
  width: 100%; box-sizing: border-box;
}
.field-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}
.field-input.field-error { border-color: #dc2626; }

textarea.field-input { resize: vertical; min-height: 80px; }

.error-msg { font-size: 0.75rem; color: #dc2626; }

.form-footer {
  display: flex; justify-content: flex-end; gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid #e5e7eb;
}

/* Shared button styles */
.btn {
  display: inline-flex; align-items: center; gap: 0.375rem;
  padding: 0.5rem 1.25rem; border-radius: 0.5rem;
  font-size: 0.875rem; font-weight: 500;
  border: none; cursor: pointer;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-ghost   { background: transparent; color: #374151; border: 1px solid #d1d5db; }
.btn-ghost:hover { background: #f9fafb; }
</style>
