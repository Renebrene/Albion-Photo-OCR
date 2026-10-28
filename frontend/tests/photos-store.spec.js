// Tests for the Pinia photos store, driven through the real API client with a
// stubbed global.fetch (store + client together, no module mocking).
// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePhotosStore } from '../src/stores/photos'

// client.js touches localStorage for the token.
if (!globalThis.localStorage) {
  const memory = new Map()
  globalThis.localStorage = {
    getItem: (key) => (memory.has(key) ? memory.get(key) : null),
    setItem: (key, value) => memory.set(key, String(value)),
    removeItem: (key) => memory.delete(key),
    clear: () => memory.clear(),
  }
}

const photo = (id) => ({ photo_id: id, filename: `${id}.jpg` })

let routes
let savedSearchBodies

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    for (const route of routes) {
      if (route.method === method && route.match(path)) {
        return route.respond(url, options)
      }
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })
}

beforeEach(() => {
  savedSearchBodies = []
  setActivePinia(createPinia())

  routes = [
    { method: 'GET', match: (p) => p === '/api/v1/addresses', respond: () => jsonResponse({ items: [] }) },
    { method: 'GET', match: (p) => p === '/api/v1/clients', respond: () => jsonResponse({ items: [] }) },
    { method: 'GET', match: (p) => p === '/api/v1/collections', respond: () => jsonResponse({ items: [] }) },
    { method: 'GET', match: (p) => p === '/api/v1/searches', respond: () => jsonResponse({ items: [] }) },
    {
      method: 'POST',
      match: (p) => p === '/api/v1/searches',
      respond: (_url, options) => {
        savedSearchBodies.push(JSON.parse(options.body))
        return jsonResponse({ search_id: 3, name: 'Поиск' })
      },
    },
    { method: 'GET', match: (p) => p === '/api/v1/photos', respond: (...args) => routes.photos(...args) },
    {
      method: 'POST',
      match: (p) => /^\/api\/v1\/collections\/\d+\/members$/.test(p),
      respond: () => jsonResponse({ collection_id: 7, added: 2 }),
    },
  ]
  routes.photos = () => jsonResponse({ items: [], next_cursor: null })

  installFetch()
})

afterEach(() => {
  delete global.fetch
})

function queryParam(url, name) {
  return new URL(String(url), 'http://localhost').searchParams.get(name)
}

function lastPhotosUrl() {
  const call = global.fetch.mock.calls
    .filter(([url]) => String(url).includes('/v1/photos?'))
    .at(-1)
  return String(call[0])
}

describe('photos store', () => {
  it('appends pages and tracks the cursor', async () => {
    routes.photos = () =>
      jsonResponse({ items: [photo('PH_a')], next_cursor: 'PH_a' })

    const store = usePhotosStore()
    await store.loadPage()

    expect(store.items).toHaveLength(1)
    expect(store.nextCursor).toBe('PH_a')
    expect(store.hasMore).toBe(true)
  })

  it('asks for a full page and keeps loading while the cursor lasts', async () => {
    const urls = []

    routes.photos = (url) => {
      urls.push(url)

      // Three pages of 100, 100 and 56: exactly how the grid walks 256 photos.
      const cursor = new URL(url, 'http://x').searchParams.get('cursor')
      const pages = {
        null: { items: Array.from({ length: 100 }, (_, i) => photo(`PH_${i}`)), next_cursor: 'c1' },
        c1: { items: Array.from({ length: 100 }, (_, i) => photo(`PH_b${i}`)), next_cursor: 'c2' },
        c2: { items: Array.from({ length: 56 }, (_, i) => photo(`PH_c${i}`)), next_cursor: null },
      }

      return jsonResponse(pages[cursor])
    }

    const store = usePhotosStore()

    await store.loadPage()
    expect(store.hasMore).toBe(true)
    await store.loadPage()
    await store.loadPage()

    expect(store.items).toHaveLength(256)
    expect(store.hasMore).toBe(false)

    // Одна страница — максимальный размер, который принимает API.
    expect(urls[0]).toContain('limit=100')
    // Никакого фильтра по дате по умолчанию: грид показывает все фото.
    expect(urls[0]).not.toContain('date_from')
  })

  it('passes multi-select filters as repeated params', async () => {
    const store = usePhotosStore()
    store.selectedAddresses = ['78_v33', '79_v33']
    store.selectedClients = ['Маркет']

    await store.refresh()

    const url = lastPhotosUrl()
    expect(url).toContain('address=78_v33&address=79_v33')
    expect(url).toContain('client=%D0%9C%D0%B0%D1%80%D0%BA%D0%B5%D1%82')
  })

  it('toggles and clears the selection', () => {
    const store = usePhotosStore()
    store.toggleSelected('PH_a')
    store.toggleSelected('PH_b')
    expect(store.selected).toEqual(['PH_a', 'PH_b'])

    store.toggleSelected('PH_a')
    expect(store.selected).toEqual(['PH_b'])

    store.clearSelection()
    expect(store.selected).toEqual([])
  })

  it('проверяет выделение по набору и обновляет его при каждом изменении', () => {
    const store = usePhotosStore()

    store.selected = Array.from({ length: 5000 }, (_, index) => `PH_${index}`)

    // Плитка спрашивает isSelected на каждой отрисовке: поиск по набору.
    expect(store.isSelected('PH_4999')).toBe(true)
    expect(store.isSelected('PH_none')).toBe(false)

    const before = store.selected
    store.toggleSelected('PH_0')

    expect(store.isSelected('PH_0')).toBe(false)
    // Набор пересобирается только при новом списке: правка на месте оставила
    // бы кэш getter'а устаревшим, и плитка не узнала бы об изменении.
    expect(store.selected).not.toBe(before)

    store.toggleSelected('PH_new')
    expect(store.isSelected('PH_new')).toBe(true)
    expect(store.selectedSet.has('PH_new')).toBe(true)
  })

  it('applyNlResults filters by the returned ids', async () => {
    const store = usePhotosStore()
    await store.applyNlResults(['PH_x', 'PH_y'])

    expect(store.nlIds).toEqual(['PH_x', 'PH_y'])
    expect(lastPhotosUrl()).toContain('ids=PH_x&ids=PH_y')
  })

  it('applyFilters resets the NL id filter', async () => {
    const store = usePhotosStore()
    store.nlIds = ['PH_x']

    await store.applyFilters({ q: 'hello', addresses: ['78_v33'] })

    expect(store.nlIds).toEqual([])
    expect(store.query).toBe('hello')
    expect(lastPhotosUrl()).not.toContain('ids=')
  })

  it('applyFilters refreshes the client panel in every mode', async () => {
    let clientCalls = 0

    routes = routes.map((route) =>
      route.match('/api/v1/clients')
        ? {
            ...route,
            respond: () => {
              clientCalls += 1
              return jsonResponse({
                items: [{ kind: 'client', name: 'AAA Моторс-Запад', count: 22 }],
                next_cursor: null,
              })
            },
          }
        : route,
    )

    const store = usePhotosStore()

    await store.applyFilters({
      clients: ['AAA Моторс-Запад'],
      combine: 'union',
    })

    expect(clientCalls).toBeGreaterThan(0)
    expect(store.clients).toEqual([
      { kind: 'client', name: 'AAA Моторс-Запад', count: 22 },
    ])
  })

  it('догружает следующие страницы клиентов и брендов по курсору', async () => {
    const asked = []

    routes = routes.map((route) =>
      route.match('/api/v1/clients')
        ? {
            ...route,
            respond: (url) => {
              asked.push(String(url))

              if (String(url).includes('cursor=page-2')) {
                return jsonResponse({
                  items: [
                    { kind: 'brand', name: 'СТС', count: 3 },
                    // Повтор первой страницы: сервер мог отдать границу дважды.
                    { kind: 'client', name: 'AAA Моторс-Запад', count: 22 },
                  ],
                  next_cursor: null,
                })
              }

              return jsonResponse({
                items: [{ kind: 'client', name: 'AAA Моторс-Запад', count: 22 }],
                next_cursor: 'page-2',
              })
            },
          }
        : route,
    )

    const store = usePhotosStore()
    await store.loadClients()

    expect(store.clientsCursor).toBe('page-2')
    expect(queryParam(asked[0], 'limit')).toBe('200')

    await store.loadMoreClients()

    // Дубликат не добавился, новая строка добавилась, курсор исчерпан.
    expect(store.clients.map((item) => `${item.kind}:${item.name}`)).toEqual([
      'client:AAA Моторс-Запад',
      'brand:СТС',
    ])
    expect(store.clientsCursor).toBe(null)
    expect(queryParam(asked[1], 'cursor')).toBe('page-2')

    // Курсора нет — новых запросов не делаем.
    const before = asked.length

    await store.loadMoreClients()

    expect(asked.length).toBe(before)
  })

  it('ignores a stale client list response', async () => {
    const pending = []

    routes = routes.map((route) =>
      route.match('/api/v1/clients')
        ? {
            ...route,
            respond: () =>
              new Promise((resolve) => pending.push(resolve)),
          }
        : route,
    )

    const store = usePhotosStore()
    const first = store.loadClients()
    const second = store.loadClients()

    pending[1](jsonResponse({ items: [{ kind: 'client', name: 'Новый', count: 1 }] }))
    await second
    pending[0](jsonResponse({ items: [] }))
    await first

    expect(store.clients).toEqual([{ kind: 'client', name: 'Новый', count: 1 }])
  })

  it('applyFilters copies clients so a saved search is not mutated', async () => {
    const store = usePhotosStore()
    const saved = { filters: { clients: ['Клиент А'], addresses: [] } }
    store.savedSearches = [saved]

    await store.applyFilters({ clients: saved.filters.clients })
    store.selectedClients.push('Клиент Б')

    expect(saved.filters.clients).toEqual(['Клиент А'])
  })

  it('keeps several collections of one scope active and unions them', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/7/members',
      respond: () => jsonResponse({ items: ['addr:1', 'addr:2'] }),
    })
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/8/members',
      respond: () => jsonResponse({ items: ['addr:2', 'addr:3'] }),
    })

    const store = usePhotosStore()

    await store.applyCollection({
      collection_id: 7, name: 'A', scope: 'addresses',
    })
    await store.applyCollection({
      collection_id: 8, name: 'B', scope: 'addresses',
    })

    // Пересечение addr:2 не дублируется.
    expect(store.selectedAddresses).toEqual(['addr:1', 'addr:2', 'addr:3'])
    expect(store.addressCollectionIds).toEqual([7, 8])
    expect(
      store.isCollectionActive({ collection_id: 7, scope: 'addresses' }),
    ).toBe(true)
    expect(
      store.isCollectionActive({ collection_id: 8, scope: 'addresses' }),
    ).toBe(true)

    // Снятие одной подборки оставляет значения второй.
    await store.applyCollection({
      collection_id: 8, name: 'B', scope: 'addresses',
    })

    expect(store.selectedAddresses).toEqual(['addr:1', 'addr:2'])
    expect(store.addressCollectionIds).toEqual([7])
  })

  it('late collection response does not overwrite a newer collection click', async () => {
    const pending = []

    routes.push({
      method: 'GET',
      match: (p) => /^\/api\/v1\/collections\/[78]\/members$/.test(p),
      respond: () => new Promise((resolve) => pending.push(resolve)),
    })

    const store = usePhotosStore()
    const first = store.applyCollection({
      collection_id: 7, name: 'A', scope: 'addresses',
    })
    const second = store.applyCollection({
      collection_id: 8, name: 'B', scope: 'addresses',
    })

    pending[1](jsonResponse({ items: ['addr:8'] }))
    await second
    pending[0](jsonResponse({ items: ['addr:7'] }))
    await first

    expect(store.selectedAddresses).toEqual(['addr:8'])
    expect(store.addressCollectionId).toBe(8)
  })

  it('manual filter change invalidates a pending collection response', async () => {
    const pending = []

    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/7/members',
      respond: () => new Promise((resolve) => pending.push(resolve)),
    })

    const store = usePhotosStore()
    const isPending = store.applyCollection({
      collection_id: 7, name: 'A', scope: 'addresses',
    })

    await store.applyFilters({ addresses: ['addr:9'] })

    pending[0](jsonResponse({ items: ['addr:7'] }))
    await isPending

    expect(store.selectedAddresses).toEqual(['addr:9'])
    expect(store.addressCollectionId).toBe(null)
  })

  it('a slow loadFacets does not restore an old collections list', async () => {
    const pending = []

    routes = routes.map((route) =>
      route.match('/api/v1/collections')
        ? {
            ...route,
            respond: () => new Promise((resolve) => pending.push(resolve)),
          }
        : route,
    )

    const store = usePhotosStore()
    const facets = store.loadFacets()
    const fresh = store.loadCollections()

    pending[1](jsonResponse({
      items: [{ collection_id: 2, name: 'Новая', scope: 'clients' }],
    }))
    await fresh
    pending[0](jsonResponse({
      items: [{ collection_id: 1, name: 'Старая', scope: 'clients' }],
    }))
    await facets

    expect(store.collections).toEqual([
      { collection_id: 2, name: 'Новая', scope: 'clients' },
    ])
  })

  it('collectionsFor keeps only the requested scope', () => {
    const store = usePhotosStore()
    store.collections = [
      { collection_id: 1, name: 'Центр', scope: 'addresses', members: 3 },
      { collection_id: 2, name: 'Маркет', scope: 'clients', members: 2 },
      { collection_id: 3, name: 'Старое', scope: 'photos', members: 9 },
    ]

    expect(store.collectionsFor('addresses').map((c) => c.collection_id)).toEqual([1])
    expect(store.collectionsFor('clients').map((c) => c.collection_id)).toEqual([2])
  })

  it('applyCollection restores an address selection and filters the grid', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/7/members',
      respond: () => jsonResponse({ items: ['78_v33', '79_v33'] }),
    })

    const store = usePhotosStore()
    const collection = { collection_id: 7, name: 'Центр', scope: 'addresses' }

    await store.applyCollection(collection)

    expect(store.selectedAddresses).toEqual(['78_v33', '79_v33'])
    expect(store.collectionId).toBe(7)

    const url = lastPhotosUrl()
    expect(url).toContain('address=78_v33&address=79_v33')
    // Подборка в /v1/photos не передаётся: грид строится по выбору адресов.
    expect(url).not.toContain('collection_id')

    const memberCall = global.fetch.mock.calls.find(([u]) =>
      String(u).includes('/collections/7/members'),
    )
    expect(String(memberCall[0])).toContain('member_type=address')

    // Повторный клик по активной подборке снимает выбор.
    await store.applyCollection(collection)
    expect(store.selectedAddresses).toEqual([])
    expect(store.collectionId).toBe(null)
  })

  it('applyCollection restores a client selection', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/5/members',
      respond: () => jsonResponse({ items: ['Маркет'] }),
    })

    const store = usePhotosStore()
    await store.applyCollection({
      collection_id: 5,
      name: 'Клиенты',
      scope: 'clients',
    })

    expect(store.selectedClients).toEqual(['Маркет'])
    expect(lastPhotosUrl()).toContain(
      'client=%D0%9C%D0%B0%D1%80%D0%BA%D0%B5%D1%82',
    )
  })

  it('keeps address and client collection selections active independently', async () => {
    routes.push(
      {
        method: 'GET',
        match: (p) => p === '/api/v1/collections/7/members',
        respond: () => jsonResponse({ items: ['78_v33'] }),
      },
      {
        method: 'GET',
        match: (p) => p === '/api/v1/collections/5/members',
        respond: () => jsonResponse({ items: ['Маркет'] }),
      },
    )

    const store = usePhotosStore()
    const addressCollection = { collection_id: 7, name: 'Центр', scope: 'addresses' }
    const clientCollection = { collection_id: 5, name: 'Клиенты', scope: 'clients' }

    await store.applyCollection(addressCollection)
    await store.applyCollection(clientCollection)

    expect(store.addressCollectionId).toBe(7)
    expect(store.clientCollectionId).toBe(5)
    expect(store.selectedAddresses).toEqual(['78_v33'])
    expect(store.selectedClients).toEqual(['Маркет'])
    expect(store.isCollectionActive(addressCollection)).toBe(true)
    expect(store.isCollectionActive(clientCollection)).toBe(true)

    // Turning off one panel's collection leaves the other one untouched.
    await store.applyCollection(addressCollection)
    expect(store.addressCollectionId).toBe(null)
    expect(store.clientCollectionId).toBe(5)
    expect(store.selectedAddresses).toEqual([])
    expect(store.selectedClients).toEqual(['Маркет'])
  })

  it('saveSelectionAsCollection stores the current address selection', async () => {
    const calls = []

    routes.push({
      method: 'POST',
      match: (p) => p === '/api/v1/collections',
      respond: (url, opts) => {
        calls.push({ url, body: JSON.parse(opts.body) })
        return jsonResponse(
          { collection_id: 12, name: 'Центр', scope: 'addresses', members: 0 },
          201,
        )
      },
    })
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/12/members',
      respond: () => jsonResponse({ items: [] }),
    })
    const store = usePhotosStore()
    store.selectedAddresses = ['78_v33', '79_v33']

    const id = await store.saveSelectionAsCollection({
      name: 'Центр',
      scope: 'addresses',
    })

    expect(id).toBe(12)
    expect(calls[0].body).toEqual({
      name: 'Центр',
      kind: 'Моя',
      scope: 'addresses',
    })

    const addCall = global.fetch.mock.calls.find(
      ([u, o]) =>
        String(u) === '/api/v1/collections/12/members' &&
        (o?.method || '').toUpperCase() === 'POST',
    )
    expect(JSON.parse(addCall[1].body)).toEqual({
      member_type: 'address',
      values: ['78_v33', '79_v33'],
    })
    expect(store.collectionId).toBe(12)
  })

  it('saveSelectionAsCollection replaces the members of an existing collection', async () => {
    const removed = []

    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/12/members',
      respond: () => jsonResponse({ items: ['80_v33'] }),
    })
    routes.push({
      method: 'POST',
      match: (p) => p === '/api/v1/collections/12/members/remove',
      respond: (url, opts) => {
        removed.push(JSON.parse(opts.body))
        return jsonResponse({ collection_id: 12, removed: 1 })
      },
    })

    const store = usePhotosStore()
    store.selectedClients = ['Маркет']

    await store.saveSelectionAsCollection({
      name: '',
      scope: 'clients',
      collectionId: 12,
    })

    expect(removed).toEqual([
      { member_type: 'client', values: ['80_v33'] },
    ])

    const addCall = global.fetch.mock.calls.find(
      ([u, o]) =>
        String(u) === '/api/v1/collections/12/members' &&
        (o?.method || '').toUpperCase() === 'POST',
    )
    expect(JSON.parse(addCall[1].body)).toEqual({
      member_type: 'client',
      values: ['Маркет'],
    })
  })

  it('выделение фото живёт только в памяти: ни читается, ни пишется в /v1/selection', async () => {
    // Сервер умеет хранить выделение, но владелец решил не сохранять его:
    // корзина — состояние страницы и в профиль не попадает (2026-10-24).
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/selection',
      respond: () => jsonResponse({ state: { selected: ['PH_a'] } }),
    })
    routes.push({
      method: 'PUT',
      match: (p) => p === '/api/v1/selection',
      respond: (url, opts) => jsonResponse({ state: JSON.parse(opts.body).state }),
    })

    const store = usePhotosStore()
    store.toggleSelected('PH_b')

    vi.useFakeTimers()
    await vi.advanceTimersByTimeAsync(900)
    vi.useRealTimers()

    expect(store.selected).toEqual(['PH_b'])
    expect(
      global.fetch.mock.calls.some(([url]) => String(url).includes('/v1/selection')),
    ).toBe(false)
  })

  it('clearSelection снимает выделение и не пишет на сервер', async () => {
    const store = usePhotosStore()
    store.toggleSelected('PH_x')
    store.clearSelection()

    vi.useFakeTimers()
    await vi.advanceTimersByTimeAsync(900)
    vi.useRealTimers()

    expect(store.selected).toEqual([])
    expect(
      global.fetch.mock.calls.some(([url, opts]) =>
        String(url).includes('/v1/selection') && (opts?.method || '') === 'PUT',
      ),
    ).toBe(false)
  })

  it('saveSelectionAsCollection is a no-op without a selection', async () => {
    const store = usePhotosStore()
    const id = await store.saveSelectionAsCollection({
      name: 'Пусто',
      scope: 'addresses',
    })

    expect(id).toBe(null)
    expect(
      global.fetch.mock.calls.some(([url]) =>
        String(url).includes('/collections'),
      ),
    ).toBe(false)
  })

  it('loadAddresses passes the current period to the address counters', async () => {
    let addressesUrl = ''

    routes.unshift({
      method: 'GET',
      match: (p) => p === '/api/v1/addresses',
      respond: (url) => {
        addressesUrl = String(url)
        return jsonResponse({ items: [] })
      },
    })

    const store = usePhotosStore()
    store.dateFrom = '2026-10-01'
    store.dateTo = '2026-10-31'
    store.dateMode = 'capture'

    await store.loadAddresses()

    expect(addressesUrl).toContain('date_from=2026-10-01')
    expect(addressesUrl).toContain('date_to=2026-10-31')
    expect(addressesUrl).toContain('date_mode=capture')
  })
})

describe('подборки и структурные фильтры', () => {
  it('ручное изменение выбора снимает активную подборку', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/7/members',
      respond: () => jsonResponse({ items: ['78_v33', '79_v33'] }),
    })

    const store = usePhotosStore()
    await store.applyCollection({
      collection_id: 7,
      name: 'Центр',
      scope: 'addresses',
    })

    expect(store.addressCollectionId).toBe(7)

    await store.applyFilters({
      addresses: ['78_v33'],
      collectionId: 7,
    })

    expect(store.addressCollectionId).toBe(null)
    expect(store.collectionId).toBe(null)
  })

  it('смена периода при том же выборе оставляет подборку активной', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/7/members',
      respond: () => jsonResponse({ items: ['78_v33', '79_v33'] }),
    })

    const store = usePhotosStore()
    await store.applyCollection({
      collection_id: 7,
      name: 'Центр',
      scope: 'addresses',
    })

    await store.applyFilters({
      addresses: ['79_v33', '78_v33'],
      dateFrom: '2026-10-01',
      collectionId: 7,
    })

    expect(store.addressCollectionId).toBe(7)
  })

  it('ИИ-результаты сохраняют структурные фильтры', async () => {
    const store = usePhotosStore()
    store.brand = 'СТС'
    store.tag = 'канал СТС'
    store.category = 'реклама'

    await store.applyNlResults(['PH_x'])

    const url = lastPhotosUrl()
    expect(url).toContain('brand=%D0%A1%D0%A2%D0%A1')
    expect(url).toContain('tag=')
    expect(url).toContain('category=')
  })

  it('сохранённый поиск включает бренд, тег и категорию', async () => {
    const store = usePhotosStore()
    store.query = 'вывеска'
    store.brand = 'СТС'
    store.tag = 'канал СТС'
    store.category = 'реклама'

    await store.saveCurrentSearch('Мой поиск')

    // Тело запроса ловит общий маршрут POST /v1/searches (savedSearchBodies).
    expect(savedSearchBodies[0].filters).toMatchObject({
      brand: 'СТС',
      tag: 'канал СТС',
      category: 'реклама',
    })
  })
})

describe('выделение фото', () => {
  it('сохраняется при смене фильтров: это «корзина», а не текущая страница', async () => {
    const store = usePhotosStore()
    store.selected = ['PH_x']

    await store.applyFilters({ q: 'новый запрос' })

    expect(store.selected).toEqual(['PH_x'])
  })
})

describe('сброс режима и подборки', () => {
  it('поздний ответ подборки не возвращает выбор после сброса', async () => {
    let resolveMembers = null
    const deferred = new Promise((resolve) => {
      resolveMembers = resolve
    })

    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/5/members',
      respond: () => deferred,
    })

    const store = usePhotosStore()
    const pending = store.applyCollection({
      collection_id: 5,
      name: 'Клиенты',
      scope: 'clients',
    })

    store.resetSelectionFilters()
    resolveMembers(jsonResponse({ items: ['Маркет'] }))
    await pending

    expect(store.selectedClients).toEqual([])
    expect(store.clientCollectionId).toBe(null)
  })
})

describe('пустая подборка', () => {
  it('не активируется и не притворяется фильтром', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/collections/5/members',
      respond: () => jsonResponse({ items: [] }),
    })

    const store = usePhotosStore()

    await expect(
      store.applyCollection({
        collection_id: 5,
        name: 'Пусто',
        scope: 'clients',
      }),
    ).rejects.toThrow('Подборка пуста')

    expect(store.selectedClients).toEqual([])
    expect(store.clientCollectionId).toBe(null)
  })
})

describe('сохранённый поиск', () => {
  it('хранит режим ○/△/□ вместе с фильтрами', async () => {
    const store = usePhotosStore()

    store.combine = 'client'
    store.selectedClients = ['Клиент А']

    await store.saveCurrentSearch('Мой поиск')

    expect(savedSearchBodies).toHaveLength(1)
    // Без режима тот же поиск давал другую выдачу: адреса и клиенты
    // складываются по-разному.
    expect(savedSearchBodies[0].filters.combine).toBe('client')
    expect(savedSearchBodies[0].filters.clients).toEqual(['Клиент А'])
  })
})

// Аудит скорости 28.10.2026: показ страницы не должен ждать счётчик, а смена
// группы обязана перезапрашивать грид даже когда он пуст.
describe('скорость списка фото', () => {
  it('страница берётся без счётчика, счётчик приходит отдельным запросом', async () => {
    const urls = []

    routes.photos = (url) => {
      urls.push(String(url))
      return jsonResponse({ items: [photo('PH_a')], next_cursor: null, total: 56934 })
    }

    const store = usePhotosStore()
    await store.refresh()

    // Страница: счётчика нет — он считается секунды и не должен её задерживать.
    expect(queryParam(urls.at(-1), 'count')).toBe('0')
    expect(urls.at(-1)).toContain('/v1/photos?')

    // Число для подписи приходит отдельным запросом (limit=1) и только после него.
    await vi.waitFor(() =>
      expect(urls.some((url) => queryParam(url, 'limit') === '1')).toBe(true),
    )
    await vi.waitFor(() => expect(store.total).toBe(56934))
  })

  it('пока счётчик не пришёл, выборка показывается без числа', async () => {
    routes.photos = () =>
      jsonResponse({ items: [photo('PH_a')], next_cursor: null, total: null })

    const store = usePhotosStore()
    await store.refresh()

    expect(store.total).toBe(null)
    expect(store.items).toHaveLength(1)
  })

  it('смена группы перезапрашивает грид, даже если он пуст', async () => {
    const urls = []

    routes.photos = (url) => {
      urls.push(String(url))
      return jsonResponse({ items: [], next_cursor: null, total: 0 })
    }

    const store = usePhotosStore()
    store.group = 'rostov'
    await store.refresh()

    // Пустая группа: строк нет, но грид уже грузился.
    expect(store.items).toHaveLength(0)
    const before = urls.filter((url) => url.includes('/v1/photos?')).length

    await store.setGroup('screens')

    expect(urls.filter((url) => url.includes('/v1/photos?')).length).toBeGreaterThan(before)
    expect(queryParam(urls.at(-1), 'group')).toBe('screens')
  })

  it('на старте группа только запоминается — лишнего запроса нет', async () => {
    const urls = []

    routes.photos = (url) => {
      urls.push(String(url))
      return jsonResponse({ items: [], next_cursor: null, total: 0 })
    }

    const store = usePhotosStore()
    await store.setGroup('cities')

    expect(store.group).toBe('cities')
    expect(urls.filter((url) => url.includes('/v1/photos?'))).toHaveLength(0)
  })
})
