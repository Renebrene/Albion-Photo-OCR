import { createRouter, createWebHistory } from 'vue-router'

import PhotosGrid from '../pages/PhotosGrid.vue'
import Technical from '../pages/Technical.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'photos',
      component: PhotosGrid,
    },
    {
      path: '/technical',
      name: 'technical',
      component: Technical,
    },
    // Backwards-compatible aliases for the earlier separate pages.
    { path: '/processing', redirect: '/technical' },
    { path: '/settings', redirect: '/technical' },
  ],
})
