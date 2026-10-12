import { createRouter, createWebHistory } from 'vue-router'

import PhotosGrid from '../pages/PhotosGrid.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'photos',
      component: PhotosGrid,
    },
  ],
})
