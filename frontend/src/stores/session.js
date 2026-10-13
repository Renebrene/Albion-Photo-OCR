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
    authEnabled: false,
  }),

  actions: {
    async load() {
      try {
        const data = await fetchMe()
        this.user = data.user
        this.authEnabled = data.auth_enabled
      } catch {
        this.user = null
      }
      this.applyColor()
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
