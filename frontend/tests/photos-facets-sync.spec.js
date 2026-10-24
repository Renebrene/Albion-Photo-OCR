// Панели: сбой одной не ломает галерею. Строки: обновляются на всех
// загруженных страницах, а не только на первой.
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePhotosStore } from '../src/stores/photos'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

beforeEach(() => {
  setActivePinia(createPinia())
})

describe('панели адресов, клиентов и подборок', () => {
  it('сбой одной панели не рисует ошибку в галерее', async () => {
    global.fetch = vi.fn(async (url) => {
      const path = String(url).split('?')[0]

      if (path.endsWith('/v1/searches')) {
        return json({ detail: 'searches are unavailable' }, 500)
      }

      return json({ items: [] })
    })

    const store = usePhotosStore()
    await store.loadFacets()

    // Ошибка панели — в панели; выдача грида остаётся рабочей.
    expect(store.facetsError).toBeTruthy()
    expect(store.error).toBe(null)
  })

  it('успешные панели применяются, даже если одна упала', async () => {
    global.fetch = vi.fn(async (url) => {
      const path = String(url).split('?')[0]

      if (path.endsWith('/v1/searches')) {
        return json({ detail: 'boom' }, 500)
      }

      if (path.endsWith('/v1/addresses')) {
        return json({ items: [{ address_id: 1, simple_address: 'Мира 1' }] })
      }

      return json({ items: [] })
    })

    const store = usePhotosStore()
    await store.loadFacets()

    expect(store.addresses).toHaveLength(1)
    expect(store.savedSearches).toEqual([])
    expect(store.facetsError).toBeTruthy()
  })
})

describe('фоновое обновление строк', () => {
  it('обновляет все загруженные страницы, а не только первую', async () => {
    const first = Array.from({ length: 100 }, (_, index) => ({
      photo_id: `PH_${index}`,
      client: 'старое',
    }))
    const second = Array.from({ length: 50 }, (_, index) => ({
      photo_id: `PH_${100 + index}`,
      client: 'старое',
    }))

    const pages = [
      {
        items: first.map((row) => ({ ...row, client: 'новое-1' })),
        next_cursor: 'cursor-2',
        total: 150,
      },
      {
        items: second.map((row) => ({ ...row, client: 'новое-2' })),
        next_cursor: null,
        total: 150,
      },
    ]

    let call = 0
    global.fetch = vi.fn(async () => json(pages[call++]))

    const store = usePhotosStore()
    store.items = [...first, ...second]

    await store.syncLoaded()

    expect(call).toBe(2)
    expect(store.items[0].client).toBe('новое-1')
    expect(store.items[99].client).toBe('новое-1')
    // Раньше строки после первой страницы не обновлялись вовсе.
    expect(store.items[100].client).toBe('новое-2')
    expect(store.items[149].client).toBe('новое-2')
  })

  it('не трогает строки, если фильтр сменился во время обхода', async () => {
    global.fetch = vi.fn(async () => {
      // Пока летел первый запрос, пользователь сменил фильтр.
      store.generation += 1

      return json({
        items: [{ photo_id: 'PH_0', client: 'новое' }],
        next_cursor: null,
        total: 1,
      })
    })

    const store = usePhotosStore()
    store.items = [{ photo_id: 'PH_0', client: 'старое' }]

    await store.syncLoaded()

    expect(store.items[0].client).toBe('старое')
  })
})
