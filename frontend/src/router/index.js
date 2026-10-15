import { createRouter, createWebHistory } from 'vue-router'

import PhotosGrid from '../pages/PhotosGrid.vue'
import VideosGrid from '../pages/VideosGrid.vue'
import Technical from '../pages/Technical.vue'
import Help from '../pages/Help.vue'
import { useSessionStore } from '../stores/session'

// The technical section is for the staff: Администратор and Менеджер. A Гость
// (read-only) never sees it, not even by typing the address.
const TECH_ROLES = ['Администратор', 'Менеджер']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'photos',
      component: PhotosGrid,
    },
    {
      path: '/videos',
      name: 'videos',
      component: VideosGrid,
    },
    {
      path: '/technical',
      name: 'technical',
      component: Technical,
    },
    // Руководство пользователя: доступно всем ролям, включая Гостя.
    {
      path: '/help',
      name: 'help',
      component: Help,
    },
    // Backwards-compatible aliases for the earlier separate pages.
    { path: '/processing', redirect: '/technical' },
    { path: '/settings', redirect: '/technical' },
  ],
})

router.beforeEach((to) => {
  if (to.name !== 'technical') return true

  const session = useSessionStore()

  return TECH_ROLES.includes(session.user?.role) ? true : { path: '/' }
})

export default router
