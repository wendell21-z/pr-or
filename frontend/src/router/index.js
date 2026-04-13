import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    component: () => import('@/components/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '工作台' }
      },
      {
        path: '/master-data',
        name: 'MasterData',
        component: () => import('@/views/MasterDataView.vue'),
        meta: { title: '基础数据' }
      },
      {
        path: '/inventory',
        name: 'Inventory',
        component: () => import('@/views/InventoryView.vue'),
        meta: { title: '库存需求' }
      },
      {
        path: '/solve',
        name: 'Solve',
        component: () => import('@/views/SolveView.vue'),
        meta: { title: '排产求解' }
      },
      {
        path: '/solution',
        name: 'Solution',
        component: () => import('@/views/SolutionView.vue'),
        meta: { title: '方案管理' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
