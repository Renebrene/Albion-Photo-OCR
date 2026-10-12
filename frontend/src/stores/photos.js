import { defineStore } from 'pinia'

import {
  addCollectionMembers,
  createCollection as createCollectionApi,
  deleteCollection as deleteCollectionApi,
  fetchAddresses,
  fetchClients,
  fetchCollections,
  fetchPhotos,
} from '../api/client'

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
    collectionId: null,

    // side panels (mirroring the legacy UI)
    addresses: [],
    clients: [],
    collections: [],
    facetsLoading: false,

    // selection
    selected: [],
  }),

  getters: {
    hasMore: (state) => state.nextCursor !== null,
    selectedCount: (state) => state.selected.length,
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
          collection_id: this.collectionId || null,
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
        const [addresses, clients, collections] = await Promise.all([
          fetchAddresses(),
          fetchClients(),
          fetchCollections(),
        ])
        this.addresses = addresses.items || []
        this.clients = clients.items || []
        this.collections = collections.items || []
      } catch (err) {
        this.error = err.message
      } finally {
        this.facetsLoading = false
      }
    },

    async loadCollections() {
      try {
        const data = await fetchCollections()
        this.collections = data.items || []
      } catch (err) {
        this.error = err.message
      }
    },

    async applyFilters({
      q = '',
      address = '',
      client = '',
      dateFrom = null,
      dateTo = null,
      collectionId = null,
    } = {}) {
      this.query = q
      this.address = address
      this.client = client
      this.dateFrom = dateFrom
      this.dateTo = dateTo
      this.collectionId = collectionId
      await this.refresh()
    },

    async selectCollection(collectionId) {
      await this.applyFilters({
        q: this.query,
        address: this.address,
        client: this.client,
        dateFrom: this.dateFrom,
        dateTo: this.dateTo,
        collectionId,
      })
    },

    // ---- selection ----

    isSelected(photoId) {
      return this.selected.includes(photoId)
    },

    toggleSelected(photoId) {
      const index = this.selected.indexOf(photoId)
      if (index === -1) this.selected.push(photoId)
      else this.selected.splice(index, 1)
    },

    selectAllCurrent() {
      this.selected = this.items.map((item) => item.photo_id)
    },

    clearSelection() {
      this.selected = []
    },

    // ---- collections ----

    async createCollection(payload) {
      const created = await createCollectionApi(payload)
      await this.loadCollections()
      return created
    },

    async deleteCollectionById(collectionId) {
      await deleteCollectionApi(collectionId)
      if (this.collectionId === collectionId) this.collectionId = null
      await this.loadCollections()
    },

    async addSelectedToCollection(collectionId) {
      const values = [...this.selected]
      if (!values.length) return 0

      const result = await addCollectionMembers(collectionId, {
        member_type: 'photo',
        values,
      })
      await this.loadCollections()
      return result.added
    },
  },
})
