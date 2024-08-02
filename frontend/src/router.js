import { createRouter, createWebHistory } from 'vue-router'
import DatafieldListView from './pages/DatafieldListView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/pages/Home.vue'),
  },
  {
    path: '/datafields',
    name: 'DatafieldList',
    component: DatafieldListView,
  },
]

let router = createRouter({
  history: createWebHistory('/frontend'),
  routes,
})

export default router
