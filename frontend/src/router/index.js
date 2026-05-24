// src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/AppLayout.vue'),
    children: [
      { path: '',         redirect: { name: 'dashboard' } },
      { path: 'dashboard', name: 'dashboard',        component: () => import('@/views/DashboardView.vue') },
      { path: 'registry',  name: 'registry',         component: () => import('@/views/RegistryView.vue') },
      { path: 'sites',     name: 'sites',            component: () => import('@/views/SitesView.vue') },
      { path: 'projects',  name: 'projects',         component: () => import('@/views/ProjectsView.vue') },
      { path: 'sync',      name: 'sync-jobs',        component: () => import('@/views/SyncJobList.vue') },
      {
        path: 'sync/:id',
        name: 'sync-job-detail',
        component: () => import('@/views/SyncJobDetail.vue'),
        props: true,
      },
      { path: 'accounts',  name: 'accounts',         component: () => import('@/views/AccountsView.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: { name: 'dashboard' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

let sessionRestored = false

router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!sessionRestored) {
    sessionRestored = true
    await auth.loadUser()
  }

  const loggedIn = auth.isLoggedIn

  // Already logged in → don't show login page
  if (to.meta.public) {
    return loggedIn ? { name: 'dashboard' } : true
  }

  // Not logged in → redirect to login
  if (!loggedIn) {
    return { name: 'login' }
  }

  return true
})

export default router
