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

  it('countFiltered запрашивает только total с текущими фильтрами', async () => {
    const urls = []

    global.fetch = vi.fn(async (url) => {
      urls.push(String(url))
      const params = new URL(String(url), 'http://localhost').searchParams

      // Первая страница грида, затем дешёвая проверка размера выборки.
      if (params.get('limit') === '1') {
        return json({ items: [], next_cursor: null, total: 5 })
      }

      return json({ items: [], next_cursor: null, total: 12 })
    })

    setActivePinia(createPinia())
    const store = usePhotosStore()

    store.query = 'СТС'
    store.dateMode = 'capture'

    await store.refresh()
    expect(store.total).toBe(12)

    const total = await store.countFiltered()
    expect(total).toBe(5)

    const probe = new URL(urls.at(-1), 'http://localhost').searchParams
    expect(probe.get('limit')).toBe('1')
    expect(probe.get('q')).toBe('СТС')
    expect(probe.get('date_mode')).toBe('capture')
  })

  it('countFiltered возвращает null при ошибке', async () => {
    global.fetch = vi.fn(async () => json({ detail: 'boom' }, 500))

    setActivePinia(createPinia())
    const store = usePhotosStore()

    await expect(store.countFiltered()).resolves.toBeNull()
  })
})

describe('фоновая синхронизация и ИИ-поиск', () => {
  it('syncLoaded не превышает серверный лимит на страницу', async () => {
    let seenLimit = null

    global.fetch = vi.fn(async (url) => {
      const params = new URL(String(url), 'http://localhost').searchParams
      seenLimit = params.get('limit')
      return json({ items: [], next_cursor: null, total: 150 })
    })

    setActivePinia(createPinia())
    const store = usePhotosStore()

    store.items = Array.from({ length: 150 }, (_, index) => ({
      photo_id: `PH_${String(index).padStart(24, '0')}`,
      filename: `${index}.jpg`,
    }))

    await store.syncLoaded()

    // API принимает не больше 100 строк на страницу; грид просит свой размер
    // (50 после аудита 28.10.2026) и никогда не выходит за лимит.
    expect(Number(seenLimit)).toBeLessThanOrEqual(100)
    expect(seenLimit).toBe('50')
  })

  it('applyNlResults обрезает ids до серверного лимита 200', async () => {
    let seenIds = 0

    global.fetch = vi.fn(async (url) => {
      const text = String(url)

      // applyFilters после страницы обновляет и счётчики адресов.
      if (!text.includes('/v1/photos')) return json({ items: [] })

      const params = new URL(text, 'http://localhost').searchParams
      seenIds = params.getAll('ids').length
      return json({ items: [], next_cursor: null, total: 0 })
    })

    setActivePinia(createPinia())
    const store = usePhotosStore()

    await store.applyNlResults(
      Array.from({ length: 300 }, (_, index) => `PH_${index}`),
    )

    expect(seenIds).toBe(200)
  })
})

describe('гонка запросов', () => {
  it('поздний ответ старого фильтра не попадает в новую выдачу', async () => {
    let resolveOld = null
    const oldResponse = new Promise((resolve) => {
      resolveOld = resolve
    })

    global.fetch = vi.fn((url) => {
      const params = new URL(String(url), 'http://localhost').searchParams

      if (params.get('q') === 'old') return oldResponse

      return Promise.resolve(
        json({
          items: [{ photo_id: 'PH_new' }],
          next_cursor: null,
          total: 1,
        }),
      )
    })

    setActivePinia(createPinia())
    const store = usePhotosStore()

    store.query = 'old'
    const pending = store.loadPage()

    store.query = 'new'
    await store.refresh()

    resolveOld(
      json({
        items: [{ photo_id: 'PH_old' }],
        next_cursor: 'PH_old_cursor',
        total: 99,
      }),
    )
    await pending

    expect(store.items.map((item) => item.photo_id)).toEqual(['PH_new'])
    expect(store.nextCursor).toBeNull()
    expect(store.total).toBe(1)
  })
})
