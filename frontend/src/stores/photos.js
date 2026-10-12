import { defineStore } from 'pinia'

import { fetchPhotos } from '../api/client'

export const usePhotosStore = defineStore('photos', {
  state: () => ({
    items: [],
    nextCursor: null,
    loading: false,
    error: null,
    query: '',
    address: '',
    client: '',
  }),

  getters: {
    hasMore: (state) => state.nextCursor !== null,
  },

  actions: {
    async loadPage() {
      this.loading = true
      this.error = null

      try {
        const page = await fetchPhotos({
          limit: 50,
          cursor: this.nextCursor,
          q: this.query || null,
          address: this.address || null,
          client: this.client || null,
        })

        this.items.push(...page.items)
        this.nextCursor = page.next_cursor
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },

    async refresh() {
      this.items = []
      this.nextCursor = null
      await this.loadPage()
    },

    async applyFilters({ q = '', address = '', client = '' } = {}) {
      this.query = q
      this.address = address
      this.client = client
      await this.refresh()
    },
  },
})
