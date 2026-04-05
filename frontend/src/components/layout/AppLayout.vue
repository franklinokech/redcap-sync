<template>
  <div class="app-shell">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">⬡</span>
        <span class="brand-name">REDCap<span class="brand-accent">Sync</span></span>
      </div>

      <nav class="sidebar-nav">
        <RouterLink to="/"         class="nav-item" exact-active-class="active">
          <span class="nav-icon">◈</span> Dashboard
        </RouterLink>
        <RouterLink to="/sync"     class="nav-item" active-class="active">
          <span class="nav-icon">⟳</span> Sync
        </RouterLink>
        <RouterLink to="/projects" class="nav-item" active-class="active">
          <span class="nav-icon">⊞</span> Projects
        </RouterLink>
        <RouterLink to="/logs"     class="nav-item" active-class="active">
          <span class="nav-icon">≡</span> Logs
        </RouterLink>
      </nav>

      <div class="sidebar-footer">
        <div class="user-chip">
          <div class="user-avatar">{{ initials }}</div>
          <div class="user-info">
            <div class="user-name">{{ auth.user?.username }}</div>
            <div class="user-role">{{ auth.user?.role }}</div>
          </div>
        </div>
        <button class="btn-logout" @click="handleLogout" title="Logout">⏻</button>
      </div>
    </aside>

    <!-- Main -->
    <main class="main-content">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" :key="$route.path" />
        </Transition>
      </RouterView>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth   = useAuthStore()
const router = useRouter()

const initials = computed(() => {
  const u = auth.user?.username || '?'
  return u.slice(0, 2).toUpperCase()
})

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: var(--c-bg-2);
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  padding: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--c-border);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.02em;
}
.brand-icon { color: var(--c-teal); font-size: 20px; }
.brand-name { color: var(--c-text); }
.brand-accent { color: var(--c-teal); }

.sidebar-nav {
  flex: 1;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--r-md);
  color: var(--c-text-2);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
  text-decoration: none;
}
.nav-item:hover { background: var(--c-bg-3); color: var(--c-text); }
.nav-item.active {
  background: var(--c-teal-glow);
  color: var(--c-teal);
  border: 1px solid rgba(45,212,191,0.2);
}
.nav-icon { font-size: 14px; width: 18px; text-align: center; }

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--c-border);
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-chip {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.user-avatar {
  width: 30px; height: 30px;
  background: var(--c-teal-glow);
  border: 1px solid rgba(45,212,191,0.3);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: var(--c-teal);
  flex-shrink: 0;
}
.user-info { min-width: 0; }
.user-name { font-size: 12px; font-weight: 500; color: var(--c-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-role { font-size: 10px; color: var(--c-text-3); text-transform: capitalize; }

.btn-logout {
  background: none; border: none; cursor: pointer;
  color: var(--c-text-3); font-size: 14px; padding: 4px;
  border-radius: 6px; transition: color 0.15s;
  flex-shrink: 0;
}
.btn-logout:hover { color: var(--c-danger); }

/* ── Main ── */
.main-content {
  flex: 1;
  overflow-y: auto;
  background: var(--c-bg);
}

/* Page transition */
.page-enter-active, .page-leave-active { transition: opacity 0.15s, transform 0.15s; }
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-to   { opacity: 0; transform: translateY(-4px); }
</style>