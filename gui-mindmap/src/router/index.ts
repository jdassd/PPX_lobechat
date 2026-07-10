import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../pages/LoginPage.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../pages/RegisterPage.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('../pages/HomePage.vue'),
    meta: { auth: true },
  },
  {
    path: '/map/:id',
    name: 'map-editor',
    component: () => import('../pages/MapEditorPage.vue'),
    meta: { auth: true },
  },
  {
    path: '/teams',
    name: 'teams',
    component: () => import('../pages/TeamsPage.vue'),
    meta: { auth: true },
  },
  {
    path: '/teams/:id',
    name: 'team-detail',
    component: () => import('../pages/TeamDetailPage.vue'),
    meta: { auth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Wait for auth initialization
  if (auth.loading) {
    await auth.init()
  }

  if (to.meta.auth && !auth.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.meta.guest && auth.isAuthenticated) {
    next({ name: 'home' })
  } else {
    next()
  }
})

export default router
