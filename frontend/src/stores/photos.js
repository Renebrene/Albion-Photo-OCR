import { defineStore } from 'pinia'

import {
  addCollectionMembers,
  createCollection as createCollectionApi,
  createSavedSearch as createSavedSearchApi,
  deleteCollection as deleteCollectionApi,
  deleteSavedSearch as deleteSavedSearchApi,
  fetchAddresses,
  fetchClients,
  fetchCollections,
  fetchPhotos,
  fetchSavedSearches,
} from '../api/client'

export const usePhotosStore = defineStore('photos', {
  state: () => ({
    items: [],
    nextCursor: null,
    loading: false,
    error: null,

    // active filters (addresses/clients are multi-select arrays)
    query: '',
    selectedAddresses: [],
    selectedClients: [],
    dateFrom: null,
    dateTo: null,
    collectionId: null,
    nlIds: [],

    // side panels (mirroring the legacy UI)
    addresses: [],
    clients: [],
    collections: [],
    savedSearches: [],
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
          address: this.selectedAddresses.length
            ? this.selectedAddresses
            : null,
          client: this.selectedClients.length ? this.selectedClients : null,
          date_from: this.dateFrom || null,
          date_to: this.dateTo || null,
          collection_id: this.collectionId || null,
          ids: this.nlIds.length ? this.nlIds : null,
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
        const [addresses, clients, collections, searches] = await Promise.all([
          fetchAddresses(),
          fetchClients(),
          fetchCollections(),
          fetchSavedSearches(),
        ])
        this.addresses = addresses.items || []
        this.clients = clients.items || []
        this.collections = collections.items || []
        this.savedSearches = searches.items || []
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
      addresses = [],
      clients = [],
      dateFrom = null,
      dateTo = null,
      collectionId = null,
      ids = [],
    } = {}) {
      this.query = q
      this.selectedAddresses = addresses
      this.selectedClients = clients
      this.dateFrom = dateFrom
      this.dateTo = dateTo
      this.collectionId = collectionId
      this.nlIds = ids
      await this.refresh()
    },

    async selectCollection(collectionId) {
      await this.applyFilters({
        q: this.query,
        addresses: this.selectedAddresses,
        clients: this.selectedClients,
        dateFrom: this.dateFrom,
        dateTo: this.dateTo,
        collectionId,
        ids: this.nlIds,
      })
    },

    // ---- natural-language search ----

    async applyNlResults(ids) {
      await this.applyFilters({
        q: this.query,
        addresses: this.selectedAddresses,
        clients: this.selectedClients,
        dateFrom: this.dateFrom,
        dateTo: this.dateTo,
        collectionId: this.collectionId,
        ids,
      })
    },

    // ---- saved searches ----

    async loadSavedSearches() {
      try {
        this.savedSearches = (await fetchSavedSearches()).items || []
      } catch (err) {
        this.error = err.message
      }
    },

    async saveCurrentSearch(name) {
      const filters = {
        q: this.query,
        addresses: this.selectedAddresses,
        clients: this.selectedClients,
        date_from: this.dateFrom,
        date_to: this.dateTo,
        collection_id: this.collectionId,
      }
      const created = await createSavedSearchApi({ name, filters })
      await this.loadSavedSearches()
      return created
    },

    async deleteSavedSearchById(searchId) {
      await deleteSavedSearchApi(searchId)
      await this.loadSavedSearches()
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
