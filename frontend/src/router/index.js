// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import GroupDetailsView from '../views/GroupDetailsView.vue'
import AllDomainsView from '../views/AllDomainsView.vue' // <-- 1. 导入新页面

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/group/:id',
      name: 'group-details',
      component: GroupDetailsView,
      props: true
    },
    { // <-- 2. 添加这个新路由
      path: '/all-domains',
      name: 'all-domains',
      component: AllDomainsView
    }
  ]
})

export default router