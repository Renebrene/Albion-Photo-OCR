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
  removeCollectionMembers,
} from '../api/client'

// Номера поколений запросов панелей. Медленный ответ старого режима не должен
// перезаписывать свежий список (например, пустой список клиентов в режиме
// приоритета адресов после возврата к объединению).
let facetsRequest = 0
let clientsRequest = 0
let addressesRequest = 0
// Подборки адресов и клиентов применяются независимо: поздний ответ одной
// не должен перебивать более новый клик по другой.
let addressCollectionRequest = 0
let clientCollectionRequest = 0
// Collections/searches can be reloaded independently (create/delete/save);
// a slower loadFacets must not restore the pre-change list.
let collectionsRequest = 0
let searchesRequest = 0

// Размер страницы грида. API принимает до 100 строк; 50 — компромисс по
// времени до первой картинки (аудит 28.10.2026): первая страница — это 50
// карточек с превью вместо 100 (плитки ленивые, но разметка и запросы превью
// создаются сразу), а прокрутка догружает следующие страницы тем же курсором.
const PAGE_SIZE = 50
// Сколько страниц обходит фоновое обновление строк за один проход.
const SYNC_MAX_PAGES = 25

// Размер страницы правой панели (клиенты и бренды). Замер на корпусе: страница
// любого размера считается одинаково (~0.7 с, стоимость — проход по корпусу),
// поэтому выгоднее брать крупнее: 700 записей — это четыре запроса вместо
// восьми, а прокрутка подгружает их по мере надобности.
const CLIENTS_PAGE_SIZE = 200

// Задержка перед отдельным запросом счётчика: даёт странице показаться и
// схлопывает быстрый перебор кнопок в один счёт (аудит 28.10.2026).
const TOTAL_DELAY_MS = 400
let totalTimer = null

/**
 * Параметры /v1/photos для текущих фильтров.
 *
 * Один и тот же набор нужен странице, фоновому syncLoaded() и проверке
 * «сколько фото сейчас в выборке» — поэтому он собирается здесь.
 */
function filterParams(state, { limit, cursor = null, count = true }) {
  return {
    limit,
    cursor,
    count,
    // Порядок задаёт сервер: клиент не пересортировывает страницы.
    sort: state.sortKey || 'photo_id',
    order: state.sortDirection || 'asc',
    q: state.query || null,
    group: state.group || null,
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
 * Параметры панели адресов: период, группа и активные подборки.
 *
 * Панель показывает тот же список адресов, что и грид, поэтому сужается той
 * же группой верхней панели, а при выбранной подборке — её составом (задание,
 * 28.10.2026): в списке остаются адреса подборки, а не весь корпус.
 */
function addressPanelParams(state) {
  return {
    dateFrom: state.dateFrom,
    dateTo: state.dateTo,
    dateMode: state.dateMode,
    group: state.group || null,
    collectionIds: [
      ...state.addressCollectionIds,
      ...state.clientCollectionIds,
    ],
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

/**
 * Union of several member lists, case-insensitive and order-preserving.
 *
 * Overlapping client/address collections must not duplicate filters or
 * counters; the first spelling wins.
 */
function unionValues(lists) {
  const result = []
  const seen = new Set()

  for (const list of lists) {
    for (const value of list || []) {
      const key = String(value).trim().toLowerCase()

      if (key && !seen.has(key)) {
        seen.add(key)
        result.push(value)
      }
    }
  }

  return result
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
    // Грид хотя бы раз что-то загрузил. Пустой список означает и «фильтр ничего
    // не нашёл», и «ещё не грузили» — по флагу эти случаи различимы.
    loadedOnce: false,
    nextCursor: null,
    // Size of the whole filtered set. The API returns it on the first page
    // only; later pages keep it unchanged.
    total: null,
    loading: false,
    error: null,
    // Ошибка панелей: показывается в панели, не в галерее.
    // Ошибка каждой панели отдельно: источник важен, потому что панель
    // показывает именно свою (см. getters ниже).
    facetsErrors: { addresses: '', clients: '', collections: '', searches: '' },
    // Когда строки последний раз сверялись с базой (для отладки и тестов).
    syncedAt: null,

    // Группа верхней панели (задание, п. 7): грид показывает только адреса
    // этой закладки. Пусто — без ограничения (для старых ссылок и тестов).
    group: null,

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
    // Несколько подборок одного вида можно держать активными одновременно;
    // скалярные id оставлены первым элементом для старых сохранённых поисков.
    addressCollectionIds: [],
    clientCollectionIds: [],
    addressCollectionId: null,
    clientCollectionId: null,
    // Состав активных подборок: id -> значения и общий union. По ним видно,
    // изменил ли пользователь выделение вручную (тогда подборки неактивны).
    addressCollectionMembers: {},
    clientCollectionMembers: {},
    addressCollectionValues: [],
    clientCollectionValues: [],
    // Номер изменения выбора: поздний ответ applyCollection не должен
    // вернуть выбор после сброса режима.
    selectionEpoch: 0,
    nlIds: [],
    // Ключ и направление сортировки: живут в сторе, потому что уходят в запрос.
    sortKey: 'date',
    sortDirection: 'desc',

    // side panels (mirroring the legacy UI)
    addresses: [],
    clients: [],
    // Правый список листается при прокрутке: без курсора панель была бы
    // ограничена первыми ста именами, а их в корпусе больше двухсот.
    clientsCursor: null,
    clientsLoadingMore: false,
    collections: [],
    savedSearches: [],
    facetsLoading: false,

    // selection
    selected: [],
  }),

  getters: {
    hasMore: (state) => state.nextCursor !== null,
    // Размер страницы панели клиентов: подсказка в интерфейсе берёт число
    // отсюда, чтобы снова не разойтись с фактическим лимитом (второй аудит, 2.5).
    clientsPageSize: () => CLIENTS_PAGE_SIZE,
    // Ошибки панелей — по источникам. Раньше одна строка показывалась в обеих
    // панелях: падение /v1/searches рисовало одинаковый текст и одинаковую
    // кнопку «Повторить» и над адресами, и над клиентами (второй аудит, п. 5).
    // Слева — адреса и сохранённые поиски, справа — клиенты и бренды;
    // справочник подборок один запрос на всех, поэтому его сбой видно в обеих.
    addressesPanelError: (state) =>
      state.facetsErrors.addresses
      || state.facetsErrors.searches
      || state.facetsErrors.collections,
    clientsPanelError: (state) =>
      state.facetsErrors.clients || state.facetsErrors.collections,
    selectedCount: (state) => state.selected.length,
    // Плитка спрашивает выделение на каждой отрисовке, а `includes` по массиву
    // это O(n) на плитку — при тысячах выбранных фото получается O(n·m).
    // Набор считается один раз на новое значение списка (обновления ниже
    // всегда заменяют массив, а не меняют его на месте).
    selectedSet: (state) => new Set(state.selected),
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
          filterParams(this, {
            limit: PAGE_SIZE,
            cursor: this.nextCursor,
            // Счётчик не ждём: страница с LIMIT по индексу даты приходит за
            // десятые доли секунды, а счёт по корпусу — секунды. Подпись
            // «За период N фото» дозаполняется отдельным запросом (refresh).
            count: false,
          }),
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
        this.loadedOnce = true

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
      this._scheduleTotal(this.generation)
    },

    /**
     * Досчитать размер выборки для подписи «За период N фото».
     *
     * Отдельным запросом и с небольшой задержкой: страница уже показана, а
     * счёт по корпусу идёт секунды — при быстром переборе кнопок незачем
     * запускать его на каждое нажатие. Результат применяется, только если
     * фильтр с тех пор не сменился.
     */
    _scheduleTotal(generation) {
      // `setTimeout`, а не `window.setTimeout`: стор гоняется и в node-тестах.
      if (totalTimer !== null) clearTimeout(totalTimer)

      totalTimer = setTimeout(() => {
        totalTimer = null

        this.countFiltered().then((value) => {
          if (value !== null && value !== undefined && generation === this.generation) {
            this.total = value
          }
        })
      }, TOTAL_DELAY_MS)
    },

    /**
     * Обновить уже загруженные строки, не сбрасывая прокрутку.
     *
     * Пока идёт пайплайн, адреса HYBRID и статусы QWEN меняются на месте:
     * перечитываем столько же строк с теми же фильтрами и подменяем
     * совпавшие по photo_id.
     */
    async syncLoaded() {
      const loaded = this.items.length

      if (!loaded || this.loading) return

      const generation = this.generation
      const byId = new Map()
      let cursor = null
      let pages = 0

      try {
        // Обходим столько строк, сколько уже загружено: раньше обновлялись
        // только первые 100, а при выборке больше 500 обновление молча
        // пропускалось — во время прогона адреса у остальных строк не менялись.
        // Ограничение по страницам держит фон в разумных рамках (25 страниц
        // по 100 = 2500 строк).
        while (byId.size < loaded && pages < SYNC_MAX_PAGES) {
          pages += 1

          const page = await fetchPhotos(
            filterParams(this, { limit: PAGE_SIZE, cursor }),
          )

          // Фильтр сменился, пока шёл запрос — не подменяем новые строки.
          if (generation !== this.generation) return

          for (const item of page.items || []) byId.set(item.photo_id, item)

          if (!page.next_cursor) break

          cursor = page.next_cursor
        }

        if (generation !== this.generation) return

        this.items = this.items.map((item) => byId.get(item.photo_id) || item)
        this.syncedAt = Date.now()
      } catch {
        // Фоновое обновление не должно ломать грид.
      }
    },

    /**
     * Update one loaded row in place (rescanned QWEN fields, address override).
     *
     * Keeps lazy-loaded pages and scroll position; facets are refreshed by the
     * caller when the client/brand/address counters changed.
     */
    updateLoadedPhoto(photo) {
      const index = this.items.findIndex(
        (item) => item.photo_id === photo.photo_id,
      )

      if (index !== -1) {
        this.items[index] = { ...this.items[index], ...photo }
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
      const request = ++facetsRequest
      const addressToken = ++addressesRequest
      const clientToken = ++clientsRequest
      const collectionToken = ++collectionsRequest
      const searchToken = ++searchesRequest
      this.facetsLoading = true

      // Панели грузятся независимо: падение одной (например, сохранённых
      // поисков) не должно ни рисовать баннер в галерее, ни скрывать «Ничего
      // не найдено», ни останавливать автодогрузку страниц. Ошибку показываем
      // в самой панели.
      const [addresses, clients, collections, searches] =
        await Promise.allSettled([
          fetchAddresses({
            ...addressPanelParams(this),
            // В приоритете по клиентам список адресов сужается ими.
            clients:
              this.combine === 'client' && this.selectedClients.length
                ? this.selectedClients
                : null,
          }),
          fetchClients({
            // База поиска клиентов и брендов — весь корпус: список не зависит
            // ни от выбранных адресов, ни от кнопки-подборки (владелец,
            // 28.10.2026). Сужение по адресам убрано и здесь, и в loadClients.
            limit: CLIENTS_PAGE_SIZE,
          }),
          fetchCollections(),
          fetchSavedSearches(),
        ])

      if (request === facetsRequest) {
        // Ошибку сохраняем по источникам: панель показывает только свою.
        const results = { addresses, clients, collections, searches }
        const errors = {}

        for (const [source, result] of Object.entries(results)) {
          errors[source] = result.status === 'rejected'
            ? result.reason?.message || 'не загрузилось'
            : ''
        }

        this.facetsErrors = errors

        if (addresses.status === 'fulfilled' && addressToken === addressesRequest) {
          this.addresses = addresses.value.items || []
        }

        if (clients.status === 'fulfilled' && clientToken === clientsRequest) {
          this.clients = clients.value.items || []
          this.clientsCursor = clients.value.next_cursor || null
        }

        if (
          collections.status === 'fulfilled' &&
          collectionToken === collectionsRequest
        ) {
          this.collections = collections.value.items || []
        }

        if (searches.status === 'fulfilled' && searchToken === searchesRequest) {
          this.savedSearches = searches.value.items || []
        }

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
      const request = ++addressesRequest

      try {
        const data = await fetchAddresses({
          ...addressPanelParams(this),
          clients:
            this.combine === 'client' && this.selectedClients.length
              ? this.selectedClients
              : null,
        })

        if (request === addressesRequest) this.addresses = data.items || []
      } catch {
        // Счётчики — вспомогательные: грид продолжает работать.
      }
    },

    /**
     * Пересчитать клиентов и брендов с учётом выбранных адресов.
     *
     * Нужен в режиме приоритета по адресам: панель показывает только тех
     * клиентов, которые встречаются на выбранных адресах. При снятии выбора
     * возвращается полный список. Возвращает первую страницу и её курсор.
     */
    async loadClients() {
      const request = ++clientsRequest

      try {
        // База поиска клиентов и брендов не зависит от списка адресов: ни от
        // выбранных адресов, ни от кнопки-подборки верхней панели. Раньше в
        // приоритете по адресам список сужался выбранными адресами, и при
        // переключении подборки (выбор адресов сбрасывается) он менялся на
        // глазах — владелец: поиск должен искать по всей базе (28.10.2026).
        const data = await fetchClients({
          limit: CLIENTS_PAGE_SIZE,
        })

        if (request === clientsRequest) {
          this.clients = data.items || []
          this.clientsCursor = data.next_cursor || null
        }
      } catch {
        // Вспомогательная панель: грид продолжает работать.
      }
    },

    /**
     * Следующая страница списка клиентов — вызывается прокруткой.
     *
     * Ответ мог прийти после смены фильтра (или после входа другого
     * пользователя): тогда список уже другой, и дописывать в него нельзя —
     * сверяем поколение запроса `clientsRequest`.
     */
    async loadMoreClients() {
      const cursor = this.clientsCursor

      if (!cursor || this.clientsLoadingMore) return

      const request = clientsRequest
      this.clientsLoadingMore = true

      try {
        // Продолжение того же полного списка (см. loadClients): сужения по
        // адресам здесь нет.
        const data = await fetchClients({
          limit: CLIENTS_PAGE_SIZE,
          cursor,
        })

        if (request !== clientsRequest) return

        // Страницы могут пересечься, если список успел измениться между
        // запросами: ключ — имя в нижнем регистре (имена в списке уникальны,
        // клиент и бренд с одним названием — одна строка).
        const known = new Set(this.clients.map((item) => String(item.name).toLowerCase()))

        for (const item of data.items || []) {
          const key = String(item.name).toLowerCase()

          if (!known.has(key)) {
            known.add(key)
            this.clients.push(item)
          }
        }

        this.clientsCursor = data.next_cursor || null
      } catch {
        // Панель остаётся с тем, что уже загружено; повтор — при прокрутке.
      } finally {
        this.clientsLoadingMore = false
      }
    },

    async loadCollections() {
      const request = ++collectionsRequest

      try {
        const data = await fetchCollections()

        if (request === collectionsRequest) {
          this.collections = data.items || []
        }
      } catch (err) {
        if (request === collectionsRequest) this.error = err.message
      }
    },

    /**
     * Сменить группу верхней панели (задание, п. 7).
     *
     * Грид перерисовывается под адреса закладки. Выбор адресов и клиентов
     * сбрасывается: он относился к прежней группе, а «пустой выбор» в новой
     * означал бы «все адреса группы».
     */
    async setGroup(group) {
      const value = group || null

      if (this.group === value) return

      this.group = value

      // На старте приложения грид ещё ни разу не грузился: достаточно запомнить
      // группу, первый запрос страницы уже уйдёт с ней. Признак — отдельный
      // флаг, а не пустой список: у группы может не быть ни одного фото, и тогда
      // «нет строк» означало не «ещё не грузили», а «здесь пусто». Из-за этого
      // после пустой группы кнопки переставали работать вовсе: подсветка
      // менялась, а грид не перезапрашивался (аудит 28.10.2026).
      if (!this.loadedOnce) return

      // Подборка живёт в своей группе (задание, п. 7е), поэтому смена группы
      // снимает и выбор, и подборки: иначе панель адресов осталась бы суженной
      // подборкой другой группы.
      this.resetSelectionFilters()
      this.nlIds = []
      await this.refresh()
      await Promise.allSettled([this.loadAddresses(), this.loadClients()])
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
      // Любое новое действие с фильтром отменяет ещё не применённую подборку.
      addressCollectionRequest += 1
      clientCollectionRequest += 1
      this.query = q
      this.selectedAddresses = addresses.map((value) =>
        normalizeAddressValue(this.addresses, value),
      )
      // Copy: a saved search passes its stored array, and tag toggling mutates
      // the selected list in place.
      this.selectedClients = [...clients]
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

      // Панели считаются параллельно: это независимые запросы, и раньше они
      // ждали друг друга — выдача уже пришла, а счётчики ещё нет.
      // Счётчики адресов идут за периодом грида; список клиентов — за текущим
      // режимом (в приоритете по адресам он сужается ими, иначе полный).
      await Promise.allSettled([this.loadAddresses(), this.loadClients()])
    },

    /**
     * Подборка = сохранённое состояние выбора.
     *
     * Адресная подборка отмечает свои адреса в левом списке, клиентская — свои
     * клиенты в правом; грид после этого показывает фото по этим фильтрам.
     * Повторный клик по активной подборке снимает выбор.
     */
    /**
     * Сбросить выделение адресов и клиентов вместе с подборками.
     *
     * Используется при смене режима ○ △ □: номер эпохи делает недействительным
     * поздний ответ applyCollection, который иначе вернул бы выбор.
     */
    resetSelectionFilters() {
      this.selectionEpoch += 1
      addressCollectionRequest += 1
      clientCollectionRequest += 1
      this.selectedAddresses = []
      this.selectedClients = []
      this.addressCollectionIds = []
      this.clientCollectionIds = []
      this.addressCollectionId = null
      this.clientCollectionId = null
      this.addressCollectionMembers = {}
      this.clientCollectionMembers = {}
      this.addressCollectionValues = []
      this.clientCollectionValues = []
      this.collectionId = null
    },

    /**
     * Отменить поздние ответы выбора, но сам выбор не трогать.
     *
     * Нужно при смене режима ○/△/□: режим меняет только то, как складываются
     * адреса и клиенты, а выбранное пользователем должно остаться (владелец:
     * в приоритете по клиентам множественный выбор клиентов сохраняется).
     */
    cancelPendingSelections() {
      this.selectionEpoch += 1
      addressCollectionRequest += 1
      clientCollectionRequest += 1
    },

    _syncCollectionId() {
      this.addressCollectionId = this.addressCollectionIds[0] ?? null
      this.clientCollectionId = this.clientCollectionIds[0] ?? null
      this.collectionId = this.addressCollectionId ?? this.clientCollectionId ?? null
    },

    /**
     * Снять активные подборки, если выделение изменили вручную.
     *
     * Пока набор совпадает с объединением состава подборок (например,
     * пользователь поменял только период), они остаются активными. Любое
     * ручное добавление/снятие адреса или клиента делает их неактуальными.
     */
    _dropStaleCollections() {
      if (
        this.addressCollectionIds.length
        && !sameValues(this.addressCollectionValues, this.selectedAddresses)
      ) {
        this.addressCollectionIds = []
        this.addressCollectionMembers = {}
        this.addressCollectionValues = []
      }

      if (
        this.clientCollectionIds.length
        && !sameValues(this.clientCollectionValues, this.selectedClients)
      ) {
        this.clientCollectionIds = []
        this.clientCollectionMembers = {}
        this.clientCollectionValues = []
      }

      this._syncCollectionId()
    },

    isCollectionActive(collection) {
      const ids = collection.scope === 'clients'
        ? this.clientCollectionIds
        : this.addressCollectionIds
      return ids.includes(collection.collection_id)
    },

    async applyCollection(collection) {
      const epoch = this.selectionEpoch
      const isClients = collection.scope === 'clients'
      const idsKey = isClients ? 'clientCollectionIds' : 'addressCollectionIds'
      const membersKey = isClients
        ? 'clientCollectionMembers'
        : 'addressCollectionMembers'
      const valuesKey = isClients
        ? 'clientCollectionValues'
        : 'addressCollectionValues'
      const selectedKey = isClients ? 'selectedClients' : 'selectedAddresses'
      const request = isClients
        ? ++clientCollectionRequest
        : ++addressCollectionRequest
      const currentRequest = () =>
        isClients ? clientCollectionRequest : addressCollectionRequest
      const ids = this[idsKey]

      if (ids.includes(collection.collection_id)) {
        // Снимаем только эту подборку; значения, общие с другими активными
        // подборками, остаются.
        ids.splice(ids.indexOf(collection.collection_id), 1)
        delete this[membersKey][collection.collection_id]
        const union = unionValues(Object.values(this[membersKey]))
        this[selectedKey] = union
        this[valuesKey] = union
        this._syncCollectionId()
        await this.refresh()
        await this.loadAddresses()
        await this.loadClients()
        return
      }

      const memberType = isClients ? 'client' : 'address'
      const data = await fetchCollectionMembers(
        collection.collection_id,
        memberType,
      )
      // Пока шёл запрос, режим сменили, выбор сбросили или нажали другую
      // подборку — поздний ответ не должен вернуть старый выбор.
      if (epoch !== this.selectionEpoch) return
      if (request !== currentRequest()) return

      const raw = data.items || []

      // Пустая подборка не должна активироваться: иначе чип есть, а фильтра
      // нет, и грид показывает всё.
      if (!raw.length) {
        throw new Error('Подборка пуста — нечего выбирать')
      }

      const values = isClients
        ? [...raw]
        : raw.map((value) => normalizeAddressValue(this.addresses, value))

      ids.push(collection.collection_id)
      this[membersKey][collection.collection_id] = values

      // Объединение всех активных подборок; пересечения не дублируются.
      const union = unionValues(Object.values(this[membersKey]))
      this[selectedKey] = union
      this[valuesKey] = union
      this._syncCollectionId()
      await this.refresh()
      // Обе панели пересчитываются под новый выбор и текущий режим.
      await this.loadAddresses()
      await this.loadClients()
    },

    /** Сохранить текущий выбор адресов (или клиентов) как подборку. */
    async saveSelectionAsCollection({ name, scope, collectionId = null }) {
      const epoch = this.selectionEpoch
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

      // Режим сменили во время сохранения — не активируем подборку.
      if (epoch !== this.selectionEpoch) return id

      const idsKey = isClients ? 'clientCollectionIds' : 'addressCollectionIds'
      const membersKey = isClients
        ? 'clientCollectionMembers'
        : 'addressCollectionMembers'
      const valuesKey = isClients
        ? 'clientCollectionValues'
        : 'addressCollectionValues'
      const selectedKey = isClients ? 'selectedClients' : 'selectedAddresses'

      if (!this[idsKey].includes(id)) this[idsKey].push(id)
      this[membersKey][id] = [...values]

      const union = unionValues(Object.values(this[membersKey]))
      this[selectedKey] = union
      this[valuesKey] = union
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
      const request = ++searchesRequest

      try {
        const data = await fetchSavedSearches()

        if (request === searchesRequest) {
          this.savedSearches = data.items || []
        }
      } catch (err) {
        if (request === searchesRequest) this.error = err.message
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
        // Режим ○/△/□ — часть набора: без него тот же поиск давал другую
        // выдачу (адреса и клиенты складываются иначе).
        combine: this.combine,
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
      return this.selectedSet.has(photoId)
    },

    toggleSelected(photoId) {
      // Новый массив, а не правка на месте: иначе `selectedSet` остаётся тем
      // же самым набором, и плитка не узнаёт об изменении.
      this.selected = this.selectedSet.has(photoId)
        ? this.selected.filter((id) => id !== photoId)
        : [...this.selected, photoId]
    },

    // selectAllCurrent() удалён: он выбирал только загруженные страницы (грид
    // листается по 100), ниоткуда не вызывался, а «выбрать всё по фильтру»
    // требует серверного шага — клиентский обход 57 тысяч фото это 570
    // запросов. Подробности — в docs/roadmap_ui_audit_20261024.md.

    clearSelection() {
      // Выделение фото — состояние страницы, а не профиля: при входе на
      // страницу (F5, «Обновить», возвращение из другого раздела) набор
      // пустой — решение владельца, 2026-10-24.
      //
      // Раньше рядом жила ветка сохранения в /v1/selection, но она была
      // недостижима (состояние грузилось с `persist: false` для всех, поэтому
      // `scheduleSelectionPersist` выходил на первой строке). Сохранение
      // признано ненужным, поэтому ветка удалена, а не починена (пункт 18
      // старого плана, пункт 5 второго аудита).
      this.selected = []
    },

    // ---- per-manager state ----

    // ---- collections ----

    async createCollection(payload) {
      const created = await createCollectionApi(payload)
      await this.loadCollections()
      return created
    },

    async deleteCollectionById(collectionId) {
      // Удаление отменяет и ещё не применённую подборку — в том числе ту,
      // чей ответ придёт, пока DELETE ещё выполняется.
      addressCollectionRequest += 1
      clientCollectionRequest += 1
      await deleteCollectionApi(collectionId)
      let cleared = false

      if (this.addressCollectionIds.includes(collectionId)) {
        this.addressCollectionIds.splice(
          this.addressCollectionIds.indexOf(collectionId), 1,
        )
        delete this.addressCollectionMembers[collectionId]
        const union = unionValues(
          Object.values(this.addressCollectionMembers),
        )
        this.addressCollectionValues = union
        this.selectedAddresses = union
        cleared = true
      }

      if (this.clientCollectionIds.includes(collectionId)) {
        this.clientCollectionIds.splice(
          this.clientCollectionIds.indexOf(collectionId), 1,
        )
        delete this.clientCollectionMembers[collectionId]
        const union = unionValues(
          Object.values(this.clientCollectionMembers),
        )
        this.clientCollectionValues = union
        this.selectedClients = union
        cleared = true
      }

      this._syncCollectionId()
      await this.loadCollections()

      // Активную подборку удалили — грид и счётчики должны вернуться к
      // состоянию без неё, а не показывать старую выдачу.
      if (cleared) {
        await this.refresh()
        await this.loadAddresses()
        await this.loadClients()
      }
    },
  },
})
