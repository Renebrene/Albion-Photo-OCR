// Счётчик «За период N фото»: total приходит с первой страницей и не
// перезаписывается пустым значением при догрузке.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePhotosStore } from '../src/stores/photos'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('total в гриде', () => {
  it('хранит размер набора с первой страницы', async () => {
    global.fetch = vi.fn(async (url) => {
      const params = new URL(String(url), 'http://localhost').searchParams

      if (params.get('cursor')) {
        return json({ items: [], next_cursor: null, total: null })
      }

      return json({ items: [], next_cursor: 'PH_' + 'a'.repeat(24), total: 42 })
    })

    setActivePinia(createPinia())
    const store = usePhotosStore()

    await store.refresh()
    expect(store.total).toBe(42)

    await store.loadPage()
    expect(store.total).toBe(42)
  })

  it('сбрасывает total при обновлении фильтров', async () => {
    global.fetch = vi.fn(async () =>
      json({ items: [], next_cursor: null, total: 7 }),
    )

    setActivePinia(createPinia())
    const store = usePhotosStore()

    await store.refresh()
    expect(store.total).toBe(7)

    store.total = null
    await store.refresh()
    expect(store.total).toBe(7)
  })
})
