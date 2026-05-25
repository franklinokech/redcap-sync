<template>
  <div class="project-card" @click="$emit('click')">
    <!-- Status badge -->
    <div class="card-header">
      <span class="status-badge" :class="`status-${project.status}`">
        {{ project.status }}
      </span>
      <div class="card-actions" @click.stop>
        <button class="action-btn" title="Edit" @click="$emit('edit')">✏️</button>
        <button class="action-btn" title="Delete" @click="$emit('delete')">🗑️</button>
      </div>
    </div>

    <!-- Name & site -->
    <h3 class="project-name">{{ project.name }}</h3>
    <p class="project-site">
      <span class="label">Site:</span>
      {{ project.site_name || '—' }}
      <span v-if="project.site_code" class="site-code">({{ project.site_code }})</span>
    </p>

    <!-- Description -->
    <p v-if="project.description" class="project-desc">
      {{ project.description }}
    </p>

    <!-- Footer indicators -->
    <div class="card-footer">
      <span class="indicator" :class="{ active: project.has_token }">
        {{ project.has_token ? '🔑 Token set' : '⚠️ No token' }}
      </span>
      <span class="indicator" :class="{ active: project.central_registry }">
        {{ project.central_registry ? '🔗 Registry linked' : '○ No registry' }}
      </span>
    </div>

    <!-- Token preview -->
    <div v-if="project.token_preview" class="token-preview">
      Token: <code>{{ project.token_preview }}</code>
    </div>
  </div>
</template>

<script setup>
defineProps({
  project: { type: Object, required: true },
})

defineEmits(['click', 'edit', 'delete'])
</script>

<style scoped>
.project-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.25rem;
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.project-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  border-color: #93c5fd;
}

.card-header {
  display: flex; align-items: center;
  justify-content: space-between; margin-bottom: 0.75rem;
}

.status-badge {
  font-size: 0.7rem; font-weight: 600;
  padding: 0.2rem 0.6rem; border-radius: 9999px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.status-active   { background: #dcfce7; color: #166534; }
.status-inactive { background: #f3f4f6; color: #6b7280; }
.status-pending  { background: #fef9c3; color: #854d0e; }

.card-actions { display: flex; gap: 0.25rem; }
.action-btn {
  background: none; border: none; cursor: pointer;
  padding: 0.25rem; border-radius: 0.375rem; font-size: 0.875rem;
  opacity: 0.5; transition: opacity 0.15s, background 0.15s;
}
.action-btn:hover { opacity: 1; background: #f3f4f6; }

.project-name {
  font-size: 1rem; font-weight: 600;
  margin: 0 0 0.375rem; color: #111827;
}
.project-site { font-size: 0.8rem; color: #6b7280; margin: 0 0 0.5rem; }
.label        { font-weight: 500; }
.site-code    { color: #9ca3af; }

.project-desc {
  font-size: 0.8rem; color: #6b7280;
  margin: 0 0 0.75rem;
  display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden;
}

.card-footer {
  display: flex; gap: 0.75rem; margin-top: 0.75rem;
  padding-top: 0.75rem; border-top: 1px solid #f3f4f6;
}
.indicator {
  font-size: 0.75rem; color: #9ca3af;
}
.indicator.active { color: #059669; }

.token-preview {
  margin-top: 0.5rem; font-size: 0.75rem; color: #6b7280;
}
.token-preview code {
  background: #f3f4f6; padding: 0.1rem 0.3rem;
  border-radius: 0.25rem; font-family: monospace;
}
</style>
