// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '',          name: 'Dashboard', component: () => import('@/views/DashboardView.vue') },
      { path: 'projects',  name: 'Projects',  component: () => import('@/views/ProjectsView.vue') },
      { path: 'sync',      name: 'Sync',      component: () => import('@/views/SyncView.vue') },
      { path: 'logs',      name: 'Logs',      component: () => import('@/views/LogsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) return '/login'
  if (to.meta.public && auth.isAuthenticated) return '/'
  if (auth.isAuthenticated && !auth.user) {
    try { await auth.fetchMe() } catch { auth.logout(); return '/login' }
  }
})

export default router