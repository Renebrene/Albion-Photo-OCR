// Сортировка уходит на сервер: клиент не пересортировывает страницы.
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePhotosStore } from '../src/stores/photos'

let urls

function installFetch() {
  urls = []
  global.fetch = vi.fn(async (url) => {
    urls.push(String(url))
    return {
      ok: true,
      status: 200,
      json: async () => ({ items: [], next_cursor: null, total: 0 }),
    }
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  installFetch()
})

describe('сортировка выдачи', () => {
  it('по умолчанию просит сортировку по дате съёмки (свежие сверху)', async () => {
    const store = usePhotosStore()

    expect(store.sortKey).toBe('date')
    expect(store.sortDirection).toBe('desc')

    await store.refresh()

    expect(urls[0]).toContain('sort=date')
    expect(urls[0]).toContain('order=desc')
  })

  it('передаёт выбранный ключ и направление', async () => {
    const store = usePhotosStore()
    store.sortKey = 'address'
    store.sortDirection = 'asc'

    await store.refresh()

    expect(urls[0]).toContain('sort=address')
    expect(urls[0]).toContain('order=asc')
  })
})
