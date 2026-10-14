import { defineStore } from 'pinia'

import {
  addCollectionMembers,
  createCollection as createCollectionApi,
  createSavedSearch as createSavedSearchApi,
  deleteCollection as deleteCollectionApi,
  deleteSavedSearch as deleteSavedSearchApi,
  fetchAddresses,
  fetchClients,
  fetchCollectionMembers,
  fetchCollections,
  fetchPhotos,
  fetchSavedSearches,
  fetchSelection,
  removeCollectionMembers,
  saveSelection,
} from '../api/client'

// Debounce timer for persisting the per-manager selection (module-scoped so
// it never lands in the reactive store state).
let persistTimer = null

// The API caps one page at 100 rows; the grid loads page by page as the user
// scrolls, so a bigger page means fewer round trips without holding everything
// in memory at once.
const PAGE_SIZE = 100

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
    // Which date the range filter uses: upload date or EXIF capture date.
    dateMode: 'upload',
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
    // true once a per-manager state has been loaded (auth present)
    selectionPersist: false,
  }),

  getters: {
    hasMore: (state) => state.nextCursor !== null,
    selectedCount: (state) => state.selected.length,
    // Подборки одного вида: 'addresses' — в левой панели, 'clients' — в правой.
    collectionsFor: (state) => (scope) =>
      state.collections.filter((item) => item.scope === scope),
  },

  actions: {
    async loadPage() {
      this.loading = true
      this.error = null

      try {
        const page = await fetchPhotos({
          limit: PAGE_SIZE,
          cursor: this.nextCursor,
          q: this.query || null,
          address: this.selectedAddresses.length
            ? this.selectedAddresses
            : null,
          client: this.selectedClients.length ? this.selectedClients : null,
          date_from: this.dateFrom || null,
          date_to: this.dateTo || null,
          date_mode: this.dateMode || 'upload',
          // Подборка на фото не влияет: она восстанавливает выбор адресов или
          // клиентов, а грид фильтруется уже по нему.
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
      dateMode = 'upload',
      collectionId = null,
      ids = [],
    } = {}) {
      this.query = q
      this.selectedAddresses = addresses
      this.selectedClients = clients
      this.dateFrom = dateFrom
      this.dateTo = dateTo
      this.dateMode = dateMode
      this.collectionId = collectionId
      this.nlIds = ids
      await this.refresh()
    },

    /**
     * Подборка = сохранённое состояние выбора.
     *
     * Адресная подборка отмечает свои адреса в левом списке, клиентская — свои
     * клиенты в правом; грид после этого показывает фото по этим фильтрам.
     * Повторный клик по активной подборке снимает выбор.
     */
    async applyCollection(collection) {
      const isClients = collection.scope === 'clients'

      if (this.collectionId === collection.collection_id) {
        this.collectionId = null

        if (isClients) this.selectedClients = []
        else this.selectedAddresses = []

        await this.refresh()
        return
      }

      const memberType = isClients ? 'client' : 'address'
      const data = await fetchCollectionMembers(
        collection.collection_id,
        memberType,
      )
      const values = data.items || []

      if (isClients) this.selectedClients = values
      else this.selectedAddresses = values

      this.collectionId = collection.collection_id
      await this.refresh()
    },

    /** Сохранить текущий выбор адресов (или клиентов) как подборку. */
    async saveSelectionAsCollection({ name, scope, collectionId = null }) {
      const isClients = scope === 'clients'
      const values = isClients
        ? [...this.selectedClients]
        : [...this.selectedAddresses]

      if (!values.length) return null

      const memberType = isClients ? 'client' : 'address'

      let id = collectionId

      if (!id) {
        const created = await createCollectionApi({ name, kind: 'Моя', scope })
        id = created.collection_id
      }

      // Подборка хранит ровно текущий выбор: прежний состав заменяем.
      const current = await fetchCollectionMembers(id, memberType)

      if ((current.items || []).length) {
        await removeCollectionMembers(id, {
          member_type: memberType,
          values: current.items,
        })
      }

      await addCollectionMembers(id, { member_type: memberType, values })

      await this.loadCollections()
      this.collectionId = id

      return id
    },

    // ---- natural-language search ----

    async applyNlResults(ids) {
      await this.applyFilters({
        q: this.query,
        addresses: this.selectedAddresses,
        clients: this.selectedClients,
        dateFrom: this.dateFrom,
        dateTo: this.dateTo,
        dateMode: this.dateMode,
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
        date_mode: this.dateMode,
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
      this.scheduleSelectionPersist()
    },

    selectAllCurrent() {
      this.selected = this.items.map((item) => item.photo_id)
      this.scheduleSelectionPersist()
    },

    clearSelection() {
      this.selected = []
      this.scheduleSelectionPersist()
    },

    // ---- per-manager state ----

    async loadSelectionState() {
      try {
        const data = await fetchSelection()
        this.selected = (data.state && data.state.selected) || []
        this.selectionPersist = true
      } catch {
        // Not authenticated (401) or endpoint unavailable: stay local-only.
        this.selectionPersist = false
      }
    },

    scheduleSelectionPersist() {
      if (!this.selectionPersist) return
      clearTimeout(persistTimer)
      persistTimer = setTimeout(() => {
        saveSelection({ selected: [...this.selected] }).catch(() => {})
      }, 800)
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
  },
})
