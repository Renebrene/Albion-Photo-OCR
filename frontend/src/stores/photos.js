import { defineStore } from 'pinia'

import { fetchAddresses, fetchClients, fetchPhotos } from '../api/client'

export const usePhotosStore = defineStore('photos', {
  state: () => ({
    items: [],
    nextCursor: null,
    loading: false,
    error: null,

    // active filters
    query: '',
    address: '',
    client: '',
    dateFrom: null,
    dateTo: null,

    // side panels (mirroring the legacy UI)
    addresses: [],
    clients: [],
    facetsLoading: false,
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
          date_from: this.dateFrom || null,
          date_to: this.dateTo || null,
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

    async loadFacets() {
      this.facetsLoading = true

      try {
        const [addresses, clients] = await Promise.all([
          fetchAddresses(),
          fetchClients(),
        ])
        this.addresses = addresses.items || []
        this.clients = clients.items || []
      } catch (err) {
        this.error = err.message
      } finally {
        this.facetsLoading = false
      }
    },

    async applyFilters({
      q = '',
      address = '',
      client = '',
      dateFrom = null,
      dateTo = null,
    } = {}) {
      this.query = q
      this.address = address
      this.client = client
      this.dateFrom = dateFrom
      this.dateTo = dateTo
      await this.refresh()
    },

    resetFilters() {
      return this.applyFilters({})
    },
  },
})
