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
    // The two collection panels select independently. collectionId remains the
    // most recently picked one for saved searches/backwards compatibility.
    collectionId: null,
    addressCollectionId: null,
    clientCollectionId: null,
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

    /**
     * Обновить уже загруженные строки, не сбрасывая прокрутку.
     *
     * Пока идёт пайплайн, адреса HYBRID и статусы QWEN меняются на месте:
     * перечитываем столько же строк с теми же фильтрами и подменяем
     * совпавшие по photo_id.
     */
    async syncLoaded() {
      const count = this.items.length

      if (!count || this.loading || count > 500) return

      try {
        const page = await fetchPhotos({
          limit: count,
          cursor: null,
          q: this.query || null,
          address: this.selectedAddresses.length ? this.selectedAddresses : null,
          client: this.selectedClients.length ? this.selectedClients : null,
          date_from: this.dateFrom || null,
          date_to: this.dateTo || null,
          date_mode: this.dateMode || 'upload',
          ids: this.nlIds.length ? this.nlIds : null,
        })

        const byId = new Map(page.items.map((item) => [item.photo_id, item]))
        this.items = this.items.map((item) => byId.get(item.photo_id) || item)
      } catch {
        // Фоновое обновление не должно ломать грид.
      }
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
    _syncCollectionId() {
      this.collectionId = this.addressCollectionId ?? this.clientCollectionId ?? null
    },

    isCollectionActive(collection) {
      const collectionId = collection.scope === 'clients'
        ? this.clientCollectionId
        : this.addressCollectionId
      return collectionId === collection.collection_id
    },

    async applyCollection(collection) {
      const isClients = collection.scope === 'clients'
      const activeKey = isClients ? 'clientCollectionId' : 'addressCollectionId'

      if (this[activeKey] === collection.collection_id) {
        this[activeKey] = null

        if (isClients) this.selectedClients = []
        else this.selectedAddresses = []

        this._syncCollectionId()
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

      // The other scope keeps its own active collection and selected values.
      this[activeKey] = collection.collection_id
      this._syncCollectionId()
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
      this[isClients ? 'clientCollectionId' : 'addressCollectionId'] = id
      this._syncCollectionId()

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

    async loadSelectionState({ persist = true } = {}) {
      if (!persist) {
        // Гость: выбор не используется действиями и не сохраняется.
        this.selected = []
        this.selectionPersist = false
        return
      }

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
      if (this.addressCollectionId === collectionId) this.addressCollectionId = null
      if (this.clientCollectionId === collectionId) this.clientCollectionId = null
      this._syncCollectionId()
      await this.loadCollections()
    },
  },
})
