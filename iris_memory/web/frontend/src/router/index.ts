import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '仪表盘', icon: 'mdi-view-dashboard' }
  },
  {
    path: '/memory',
    name: 'Memory',
    component: () => import('@/views/MemoryView.vue'),
    meta: { title: '记忆管理', icon: 'mdi-brain' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/ProfileView.vue'),
    meta: { title: '画像管理', icon: 'mdi-account-group' }
  },
  {
    path: '/stats',
    name: 'Stats',
    component: () => import('@/views/StatsView.vue'),
    meta: { title: '数据统计', icon: 'mdi-chart-bar' }
  }
]

const router = createRouter({
  history: createWebHistory('/iris'),
  routes
})

export default router
