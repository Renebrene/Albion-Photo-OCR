// Tests for the API client wrapper (URL building, auth header, errors).
// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  fetchPhotos,
  getToken,
  setToken,
  uploadPhotos,
  createHybridRun,
} from '../src/api/client'

// Minimal localStorage so the token helper works under the node environment.
if (!globalThis.localStorage) {
  const memory = new Map()
  globalThis.localStorage = {
    getItem: (key) => (memory.has(key) ? memory.get(key) : null),
    setItem: (key, value) => memory.set(key, String(value)),
    removeItem: (key) => memory.delete(key),
    clear: () => memory.clear(),
  }
}

function mockFetchOnce(response) {
  global.fetch = vi.fn().mockResolvedValue(response)
}

function okJson(body) {
  return { ok: true, status: 200, json: async () => body }
}

function errJson(status, body) {
  return { ok: false, status, json: async () => body }
}

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    delete global.fetch
  })

  it('stores and clears the bearer token', () => {
    expect(getToken()).toBeNull()
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('sends Authorization only when a token is set', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({ limit: 5 })
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()

    setToken('tok')
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({ limit: 5 })
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe(
      'Bearer tok',
    )
  })

  it('builds repeated address/client/ids params', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({
      limit: 50,
      q: 'Luvio',
      address: ['78_v33', '79_v33'],
      client: ['Маркет'],
      ids: ['PH_a', 'PH_b'],
      collection_id: 3,
    })

    const url = global.fetch.mock.calls[0][0]
    expect(url).toContain('address=78_v33&address=79_v33')
    expect(url).toContain('client=%D0%9C%D0%B0%D1%80%D0%BA%D0%B5%D1%82')
    expect(url).toContain('ids=PH_a&ids=PH_b')
    expect(url).toContain('q=Luvio')
    expect(url).toContain('collection_id=3')
  })

  it('throws a generic error on a failed GET', async () => {
    mockFetchOnce({ ok: false, status: 500, json: async () => ({}) })
    await expect(fetchPhotos({ limit: 5 })).rejects.toThrow('API error 500')
  })

  it('surfaces the server detail on a failed POST', async () => {
    mockFetchOnce(errJson(409, { detail: 'conflict here' }))
    await expect(createHybridRun(1)).rejects.toThrow('conflict here')
  })

  it('uploads files as multipart FormData', async () => {
    mockFetchOnce(okJson({ items: [], accepted: 1 }))
    const file = new File([new Uint8Array([1, 2, 3])], 'a.jpg', {
      type: 'image/jpeg',
    })

    await uploadPhotos([file])

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/upload')
    expect(options.method).toBe('POST')
    expect(options.body).toBeInstanceOf(FormData)
    // Browser must set the multipart boundary itself.
    expect(options.headers['Content-Type']).toBeUndefined()
  })
})
