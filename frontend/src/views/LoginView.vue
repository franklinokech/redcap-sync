<template>
  <div class="login-page">
    <div class="login-card fade-in">
      <div class="login-header">
        <div class="login-logo">⬡</div>
        <h1 class="login-title">REDCap<span>Sync</span></h1>
        <p class="login-sub">Multi-site registry synchronisation</p>
      </div>

      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label">Username</label>
          <input
            v-model="form.username"
            class="form-input"
            type="text"
            placeholder="your username"
            autocomplete="username"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">Password</label>
          <input
            v-model="form.password"
            class="form-input"
            type="password"
            placeholder="••••••••"
            autocomplete="current-password"
            required
          />
        </div>

        <div v-if="error" class="login-error">
          {{ error }}
        </div>

        <button type="submit" class="btn btn-primary btn-lg login-btn" :disabled="loading">
          <span v-if="loading">Signing in…</span>
          <span v-else>Sign in →</span>
        </button>
      </form>
    </div>

    <!-- Background grid decoration -->
    <div class="login-bg-grid" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth    = useAuthStore()
const router  = useRouter()
const loading = ref(false)
const error   = ref('')

const form = ref({ username: '', password: '' })

async function handleLogin() {
  loading.value = true
  error.value   = ''
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Invalid username or password.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--c-bg);
  position: relative;
  overflow: hidden;
}

.login-bg-grid {
  position: absolute; inset: 0; pointer-events: none;
  background-image:
    linear-gradient(var(--c-border) 1px, transparent 1px),
    linear-gradient(90deg, var(--c-border) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.3;
  mask-image: radial-gradient(ellipse 60% 60% at 50% 50%, black, transparent);
}

.login-card {
  position: relative; z-index: 1;
  width: 100%; max-width: 380px;
  background: var(--c-bg-2);
  border: 1px solid var(--c-border);
  border-radius: 16px;
  padding: 36px;
  box-shadow: var(--shadow-lg);
}

.login-header { text-align: center; margin-bottom: 28px; }

.login-logo {
  font-size: 36px; color: var(--c-teal);
  display: block; margin-bottom: 12px;
}

.login-title {
  font-size: 22px; font-weight: 600;
  letter-spacing: -0.03em; color: var(--c-text);
  margin-bottom: 6px;
}
.login-title span { color: var(--c-teal); }

.login-sub {
  font-size: 12px; color: var(--c-text-3);
  letter-spacing: 0.02em;
}

.login-form { display: flex; flex-direction: column; gap: 16px; }

.login-error {
  background: var(--c-danger-bg);
  border: 1px solid rgba(248,113,113,0.2);
  border-radius: var(--r-md);
  padding: 10px 12px;
  color: var(--c-danger);
  font-size: 12px;
}

.login-btn { width: 100%; justify-content: center; margin-top: 4px; }
</style>