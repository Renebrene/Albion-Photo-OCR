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

/**
 * Параметры /v1/photos для текущих фильтров.
 *
 * Один и тот же набор нужен странице, фоновому syncLoaded() и проверке
 * «сколько фото сейчас в выборке» — поэтому он собирается здесь.
 */
function filterParams(state, { limit, cursor = null }) {
  return {
    limit,
    cursor,
    q: state.query || null,
    address: state.selectedAddresses.length ? state.selectedAddresses : null,
    client: state.selectedClients.length ? state.selectedClients : null,
    brand: state.brand || null,
    tag: state.tag || null,
    category: state.category || null,
    date_from: state.dateFrom || null,
    date_to: state.dateTo || null,
    date_mode: state.dateMode || 'upload',
    combine: state.combine || 'union',
    // Подборка на фото не влияет: она восстанавливает выбор адресов или
    // клиентов, а грид фильтруется уже по нему.
    ids: state.nlIds.length ? state.nlIds : null,
  }
}

/**
 * Привести значение адреса к идентификатору панели.
 *
 * Новые значения — `addr:<address_id>`; старые подборки и сохранённые поиски
 * хранят id слепка. Панель отдаёт список активных слепков адреса, поэтому
 * старый id можно развернуть в юридический адрес.
 */
/** Совпадают ли два набора значений (порядок не важен). */
function sameValues(left, right) {
  if (left.length !== right.length) return false

  const values = new Set(left)

  return right.every((value) => values.has(value))
}

function normalizeAddressValue(addresses, value) {
  const found = (addresses || []).find(
    (item) =>
      item.address === value || (item.fingerprints || []).includes(value),
  )

  return found ? found.address : value
}

export const usePhotosStore = defineStore('photos', {
  state: () => ({
    items: [],
    // Номер поколения фильтра: ответы старых запросов после смены фильтра
    // отбрасываются, иначе они дописывают чужие строки и курсор.
    generation: 0,
    nextCursor: null,
    // Size of the whole filtered set. The API returns it on the first page
    // only; later pages keep it unchanged.
    total: null,
    loading: false,
    error: null,

    // active filters (addresses/clients are multi-select arrays)
    query: '',
    selectedAddresses: [],
    selectedClients: [],
    // Structured values chosen from the search suggestions. They are exact
    // filters (brand/tag/category), unlike the substring `query`.
    brand: null,
    tag: null,
    category: null,
    dateFrom: null,
    dateTo: null,
    // Which date the range filter uses: upload date or EXIF capture date.
    dateMode: 'upload',
    // union — адреса и клиенты объединяются; address — адреса задают
    // вселенную, клиенты уточняют; client — наоборот.
    combine: 'union',
    // The two collection panels select independently. collectionId remains the
    // most recently picked one for saved searches/backwards compatibility.
    collectionId: null,
    addressCollectionId: null,
    clientCollectionId: null,
    // Состав активной подборки: по нему видно, изменил ли пользователь
    // выделение вручную (тогда подборка больше не активна).
    addressCollectionValues: [],
    clientCollectionValues: [],
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
    async loadPage(generation = this.generation) {
      this.loading = true
      this.error = null

      try {
        const page = await fetchPhotos(
          filterParams(this, { limit: PAGE_SIZE, cursor: this.nextCursor }),
        )

        // Пока запрос летел, фильтр сменился: строки и курсор уже не те.
        if (generation !== this.generation) return

        const seen = new Set(this.items.map((item) => item.photo_id))

        for (const item of page.items) {
          if (seen.has(item.photo_id)) continue
          seen.add(item.photo_id)
          this.items.push(item)
        }

        this.nextCursor = page.next_cursor

        // null on continuation pages: the set is unchanged while scrolling.
        if (page.total !== null && page.total !== undefined) {
          this.total = page.total
        }
      } catch (err) {
        if (generation === this.generation) this.error = err.message
      } finally {
        if (generation === this.generation) this.loading = false
      }
    },

    async refresh() {
      this.generation += 1
      this.items = []
      this.nextCursor = null
      this.total = null
      await this.loadPage(this.generation)
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

      const generation = this.generation

      try {
        // /v1/photos отдаёт не больше 100 строк за запрос: при длинной
        // прокрутке старый limit=count получал 422, который глушился catch.
        const page = await fetchPhotos(
          filterParams(this, { limit: Math.min(count, PAGE_SIZE) }),
        )

        // Фильтр сменился, пока шёл запрос — не подменяем новые строки.
        if (generation !== this.generation) return

        const byId = new Map(page.items.map((item) => [item.photo_id, item]))
        this.items = this.items.map((item) => byId.get(item.photo_id) || item)
      } catch {
        // Фоновое обновление не должно ломать грид.
      }
    },

    /**
     * Сколько фото сейчас в отфильтрованном наборе.
     *
     * Грид показывает только распознанные фото, поэтому во время HYBRID это
     * число растёт — по нему страница понимает, что пора перечитать грид.
     * null при ошибке: фоновая проверка не должна ничего ломать.
     */
    async countFiltered() {
      try {
        const page = await fetchPhotos(filterParams(this, { limit: 1 }))
        return page.total ?? null
      } catch {
        return null
      }
    },

    async loadFacets() {
      this.facetsLoading = true

      try {
        const [addresses, clients, collections, searches] = await Promise.all([
          fetchAddresses({
            dateFrom: this.dateFrom,
            dateTo: this.dateTo,
            dateMode: this.dateMode,
            // В приоритете по клиентам список адресов сужается ими.
            clients:
              this.combine === 'client' && this.selectedClients.length
                ? this.selectedClients
                : null,
          }),
          fetchClients({
            // В приоритете по адресам список клиентов сужается ими.
            addresses:
              this.combine === 'address' && this.selectedAddresses.length
                ? this.selectedAddresses
                : [],
          }),
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

    /**
     * Пересчитать счётчики адресов за выбранный период.
     *
     * Панель не должна перезагружать клиентов и подборки на каждую смену
     * фильтра — нужны только счётчики.
     */
    async loadAddresses() {
      try {
        const data = await fetchAddresses({
          dateFrom: this.dateFrom,
          dateTo: this.dateTo,
          dateMode: this.dateMode,
          clients:
            this.combine === 'client' && this.selectedClients.length
              ? this.selectedClients
              : null,
        })
        this.addresses = data.items || []
      } catch {
        // Счётчики — вспомогательные: грид продолжает работать.
      }
    },

    /**
     * Пересчитать клиентов с учётом выбранных адресов.
     *
     * Нужен в режиме приоритета по адресам: панель показывает только тех
     * клиентов, которые встречаются на выбранных адресах. При снятии выбора
     * возвращается полный список.
     */
    async loadClients() {
      try {
        const data = await fetchClients({
          addresses:
            this.combine === 'address' && this.selectedAddresses.length
              ? this.selectedAddresses
              : [],
        })
        this.clients = data.items || []
      } catch {
        // Вспомогательная панель: грид продолжает работать.
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
      brand = null,
      tag = null,
      category = null,
      dateFrom = null,
      dateTo = null,
      dateMode = 'upload',
      combine = 'union',
      collectionId = null,
      ids = [],
    } = {}) {
      this.query = q
      this.selectedAddresses = addresses.map((value) =>
        normalizeAddressValue(this.addresses, value),
      )
      this.selectedClients = clients
      this.brand = brand
      this.tag = tag
      this.category = category
      this.dateFrom = dateFrom
      this.dateTo = dateTo
      this.dateMode = dateMode
      this.combine = combine
      this.collectionId = collectionId
      this.nlIds = ids
      this._dropStaleCollections()
      await this.refresh()
      // Counters follow the same period as the grid.
      await this.loadAddresses()
      // В приоритете по адресам список клиентов сужается выбранными адресами.
      if (this.combine === 'address') await this.loadClients()
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

    /**
     * Снять активную подборку, если выделение изменили вручную.
     *
     * Пока набор совпадает с составом подборки (например, пользователь
     * поменял только период), подборка остаётся активной. Любое ручное
     * добавление/снятие адреса или клиента делает её неактуальной.
     */
    _dropStaleCollections() {
      if (
        this.addressCollectionId !== null
        && !sameValues(this.addressCollectionValues, this.selectedAddresses)
      ) {
        const previous = this.addressCollectionId
        this.addressCollectionId = null
        this.addressCollectionValues = []

        if (this.collectionId === previous) {
          this.collectionId = this.clientCollectionId ?? null
        }
      }

      if (
        this.clientCollectionId !== null
        && !sameValues(this.clientCollectionValues, this.selectedClients)
      ) {
        const previous = this.clientCollectionId
        this.clientCollectionId = null
        this.clientCollectionValues = []

        if (this.collectionId === previous) {
          this.collectionId = this.addressCollectionId ?? null
        }
      }
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

        if (isClients) {
          this.selectedClients = []
          this.clientCollectionValues = []
        } else {
          this.selectedAddresses = []
          this.addressCollectionValues = []
        }

        this._syncCollectionId()
        await this.refresh()
        // Сняли подборку — счётчики адресов возвращаются к полному списку.
        await this.loadAddresses()
        if (this.combine === 'address') await this.loadClients()
        return
      }

      const memberType = isClients ? 'client' : 'address'
      const data = await fetchCollectionMembers(
        collection.collection_id,
        memberType,
      )
      const values = data.items || []

      if (isClients) {
        this.selectedClients = values
        this.clientCollectionValues = [...values]
      } else {
        const normalized = values.map((value) =>
          normalizeAddressValue(this.addresses, value),
        )
        this.selectedAddresses = normalized
        this.addressCollectionValues = [...normalized]
      }

      // The other scope keeps its own active collection and selected values.
      this[activeKey] = collection.collection_id
      this._syncCollectionId()
      await this.refresh()
      // В приоритете по клиентам адресная панель пересчитывается сразу.
      await this.loadAddresses()
      if (this.combine === 'address') await this.loadClients()
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

      if (isClients) {
        this.clientCollectionId = id
        this.clientCollectionValues = [...values]
      } else {
        this.addressCollectionId = id
        this.addressCollectionValues = [...values]
      }

      this._syncCollectionId()

      return id
    },

    // ---- natural-language search ----

    async applyNlResults(ids) {
      // Сервер принимает не больше 200 ids за запрос, а ИИ-поиск отдаёт до
      // 500: лишние значения давали 422 и пустой грид.
      await this.applyFilters({
        q: this.query,
        addresses: this.selectedAddresses,
        clients: this.selectedClients,
        brand: this.brand,
        tag: this.tag,
        category: this.category,
        dateFrom: this.dateFrom,
        dateTo: this.dateTo,
        dateMode: this.dateMode,
        combine: this.combine,
        collectionId: this.collectionId,
        ids: Array.isArray(ids) ? ids.slice(0, 200) : ids,
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
        brand: this.brand,
        tag: this.tag,
        category: this.category,
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
      let cleared = false

      if (this.addressCollectionId === collectionId) {
        this.addressCollectionId = null
        this.addressCollectionValues = []
        this.selectedAddresses = []
        cleared = true
      }

      if (this.clientCollectionId === collectionId) {
        this.clientCollectionId = null
        this.clientCollectionValues = []
        this.selectedClients = []
        cleared = true
      }

      this._syncCollectionId()
      await this.loadCollections()

      // Активную подборку удалили — грид и счётчики должны вернуться к
      // состоянию без неё, а не показывать старую выдачу.
      if (cleared) {
        await this.refresh()
        await this.loadAddresses()
        if (this.combine === 'address') await this.loadClients()
      }
    },
  },
})
