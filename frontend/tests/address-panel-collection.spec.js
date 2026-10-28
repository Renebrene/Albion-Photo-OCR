// Панель адресов грузится в составе активной подборки: выбранная подборка
// оставляет в списке только свои адреса, снятие возвращает полный список
// (задание, 28.10.2026).
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { usePhotosStore } from '../src/stores/photos'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const photo = {
  photo_id: 'PH_' + 'a'.repeat(24),
  filename: 'photo.jpg',
  width: 100,
  height: 100,
  container_format: 'JPEG',
  address: 'addr:7',
  simple_address: 'Комарова 13',
}

let urls

beforeEach(() => {
  urls = []
  window.localStorage.clear()
  setActivePinia(createPinia())

  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]
    urls.push(String(url))

    if (path.endsWith('/v1/photos')) {
      return json({ items: [photo], next_cursor: null, total: 1 })
    }

    if (path.endsWith('/v1/addresses')) {
      return json({ items: [{ address: 'addr:7', name: 'Комарова 13', count: 1 }] })
    }

    if (path.endsWith('/members')) {
      return json({ items: ['addr:7'] })
    }

    return json({ items: [] })
  })
})

function panelUrls() {
  return urls.filter((url) => url.includes('/v1/addresses'))
}

describe('панель адресов и подборки', () => {
  it('выбор подборки грузит список её составом', async () => {
    const store = usePhotosStore()
    store.group = 'screens'

    await store.applyCollection({
      collection_id: 5,
      scope: 'addresses',
      members: 1,
    })

    const last = panelUrls().pop()
    expect(last).toContain('collection_id=5')
    // Панель показывает адреса той же группы, что и грид.
    expect(last).toContain('group=screens')
  })

  it('клиентская подборка тоже сужает список адресов', async () => {
    const store = usePhotosStore()
    store.group = 'cities'

    await store.applyCollection({
      collection_id: 9,
      scope: 'clients',
      members: 1,
    })

    expect(panelUrls().pop()).toContain('collection_id=9')
  })

  it('снятие подборки возвращает полный список', async () => {
    const store = usePhotosStore()
    store.group = 'screens'
    const collection = { collection_id: 5, scope: 'addresses', members: 1 }

    await store.applyCollection(collection)
    urls = []

    await store.applyCollection(collection)

    const last = panelUrls().pop()
    expect(last).not.toContain('collection_id')
    expect(last).toContain('group=screens')
  })

  it('смена группы снимает подборку другой группы', async () => {
    const store = usePhotosStore()
    store.group = 'screens'

    await store.applyCollection({
      collection_id: 5,
      scope: 'addresses',
      members: 1,
    })

    expect(store.addressCollectionIds).toEqual([5])

    urls = []
    await store.setGroup('cities')

    expect(store.addressCollectionIds).toEqual([])
    const last = panelUrls().pop()
    expect(last).not.toContain('collection_id')
    expect(last).toContain('group=cities')
  })
})
