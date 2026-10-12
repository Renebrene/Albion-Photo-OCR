import { createRouter, createWebHistory } from 'vue-router'

import PhotosGrid from '../pages/PhotosGrid.vue'
import Processing from '../pages/Processing.vue'
import Settings from '../pages/Settings.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'photos',
      component: PhotosGrid,
    },
    {
      path: '/processing',
      name: 'processing',
      component: Processing,
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings,
    },
  ],
})
