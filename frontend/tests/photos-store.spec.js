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

  it('adds the current selection to a collection', async () => {
    const store = usePhotosStore()
    store.selected = ['PH_a', 'PH_b']

    const added = await store.addSelectedToCollection(7)

    expect(added).toBe(2)
    const call = global.fetch.mock.calls.find(([url]) =>
      String(url).includes('/collections/7/members'),
    )
    expect(call[0]).toBe('/api/v1/collections/7/members')
    expect(call[1].method).toBe('POST')
    expect(JSON.parse(call[1].body)).toEqual({
      member_type: 'photo',
      values: ['PH_a', 'PH_b'],
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

  it('addSelectedToCollection is a no-op without a selection', async () => {
    const store = usePhotosStore()
    const added = await store.addSelectedToCollection(7)

    expect(added).toBe(0)
    expect(
      global.fetch.mock.calls.some(([url]) =>
        String(url).includes('/members'),
      ),
    ).toBe(false)
  })
})
