import { createRouter, createWebHistory } from 'vue-router'

import { useSessionStore } from '../stores/session'

// Route-level chunks: the photo grid is the landing page, while the technical
// section and the video editor are loaded only when the user opens them.
const PhotosGrid = () => import('../pages/PhotosGrid.vue')
const VideosGrid = () => import('../pages/VideosGrid.vue')
const Technical = () => import('../pages/Technical.vue')
const Help = () => import('../pages/Help.vue')

// The technical section is administrator-only. Менеджер works through the gear
// dialog (display settings + client normalization) and still runs the base
// update; A Гость (read-only) never sees it, not even by typing the address.
const TECH_ROLES = ['Администратор']

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

  if (!session.authEnabled) return true

  return TECH_ROLES.includes(session.user?.role) ? true : { path: '/' }
})

export default router
