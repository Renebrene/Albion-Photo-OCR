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
