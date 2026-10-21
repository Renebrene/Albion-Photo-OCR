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
  setActivePinia(createPinia())

  routes = [
    { method: 'GET', match: (p) => p === '/api/v1/addresses', respond: () => jsonResponse({ items: [] }) },
    { method: 'GET', match: (p) => p === '/api/v1/clients', respond: () => jsonResponse({ items: [] }) },
    { method: 'GET', match: (p) => p === '/api/v1/collections', respond: () => jsonResponse({ items: [] }) },
    { method: 'GET', match: (p) => p === '/api/v1/searches', respond: () => jsonResponse({ items: [] }) },
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

function lastPhotosUrl() {
  const call = global.fetch.mock.calls
    .filter(([url]) => String(url).includes('/v1/photos'))
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

  it('loads and persists the per-manager selection', async () => {
    let saved = null
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/selection',
      respond: () => jsonResponse({ state: { selected: ['PH_a'] } }),
    })
    routes.push({
      method: 'PUT',
      match: (p) => p === '/api/v1/selection',
      respond: (url, opts) => {
        saved = JSON.parse(opts.body)
        return jsonResponse({ state: saved.state })
      },
    })

    const store = usePhotosStore()
    await store.loadSelectionState()

    expect(store.selected).toEqual(['PH_a'])
    expect(store.selectionPersist).toBe(true)

    vi.useFakeTimers()
    store.toggleSelected('PH_b')
    await vi.advanceTimersByTimeAsync(900)
    vi.useRealTimers()

    expect(saved).toEqual({ state: { selected: ['PH_a', 'PH_b'] } })
  })

  it('does not persist selection when not authenticated', async () => {
    routes.push({
      method: 'GET',
      match: (p) => p === '/api/v1/selection',
      respond: () => jsonResponse({ detail: 'authentication required' }, 401),
    })

    const store = usePhotosStore()
    await store.loadSelectionState()
    expect(store.selectionPersist).toBe(false)

    vi.useFakeTimers()
    store.toggleSelected('PH_x')
    await vi.advanceTimersByTimeAsync(900)
    vi.useRealTimers()

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
    const posts = []

    routes.push({
      method: 'POST',
      match: (p) => p === '/api/v1/searches',
      respond: (_url, options) => {
        posts.push(JSON.parse(options.body))
        return jsonResponse({ search_id: 1 })
      },
    })

    const store = usePhotosStore()
    store.query = 'вывеска'
    store.brand = 'СТС'
    store.tag = 'канал СТС'
    store.category = 'реклама'

    await store.saveCurrentSearch('Мой поиск')

    expect(posts[0].filters).toMatchObject({
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
