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
    path: '/l1-buffer',
    name: 'L1Buffer',
    component: () => import('@/views/L1BufferView.vue'),
    meta: { title: 'L1 缓冲', icon: 'mdi-lightning-bolt' }
  },
  {
    path: '/l2-memory',
    name: 'L2Memory',
    component: () => import('@/views/L2MemoryView.vue'),
    meta: { title: 'L2 记忆', icon: 'mdi-database-search' }
  },
  {
    path: '/l3-graph',
    name: 'L3Graph',
    component: () => import('@/views/L3GraphView.vue'),
    meta: { title: 'L3 图谱', icon: 'mdi-graph' }
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
