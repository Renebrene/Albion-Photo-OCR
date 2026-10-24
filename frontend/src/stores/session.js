import { defineStore } from 'pinia'
import { setCssVar } from 'quasar'

import {
  clearImageCache,
  fetchMe,
  fetchUsers,
  login as loginApi,
  logout as logoutApi,
  setToken,
} from '../api/client'

export const useSessionStore = defineStore('session', {
  state: () => ({
    user: null,
    users: [],
    // Пока сервер не ответил, считаем, что вход нужен. Открытый режим — это
    // явный ответ сервера (`auth_enabled: false`), а не наше умолчание:
    // иначе сбой /auth/me (сеть, 5xx) открывал бы техраздел и запуск прогона
    // любому, кто открыл страницу.
    authEnabled: true,
    // Заполняется, когда спросить сервер не удалось: экран входа показывает
    // причину и кнопку «Повторить».
    authError: null,
  }),

  actions: {
    async load() {
      this.authError = null

      try {
        const data = await fetchMe()
        this.user = data.user
        this.authEnabled = data.auth_enabled !== false
      } catch (err) {
        this.user = null
        this.authEnabled = true
        this.authError = 'Нет связи с сервером — проверьте подключение и повторите'
      }

      this.applyColor()
      return !this.authError
    },

    async loadUsers(activeOnly = true) {
      try {
        const data = await fetchUsers(activeOnly)
        this.users = data.items || []
      } catch {
        this.users = []
      }
    },

    async login(name, password) {
      const data = await loginApi(name, password)
      setToken(data.token)
      // Permissions changed: drop any cached media from the previous session.
      clearImageCache()
      this.user = data.user
      this.applyColor()
      return data.user
    },

    async logout() {
      try {
        await logoutApi()
      } catch {
        // ignore
      }
      setToken(null)
      clearImageCache()
      this.user = null
      this.applyColor()
    },

    applyColor() {
      // Manager colour themes the app (legacy behaviour).
      setCssVar('primary', this.user?.color || '#1976d2')
    },
  },
})
