// Карточка просмотра: поздний ответ деталей предыдущего фото не должен
// перезаписывать открытое следующее (иначе редактор сохранит чужие поля).
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import AuthImage from '../src/components/AuthImage.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const photos = [
  {
    photo_id: 'PH_' + 'a'.repeat(24),
    filename: 'a.jpg',
    width: 100,
    height: 100,
    container_format: 'JPEG',
    address: '78_v33',
    simple_address: 'Адрес A',
    client: 'Клиент A',
    brand: 'Бренд A',
    source_directory: 'test',
    taken_at: '2025-07-17 11:43:19',
    size_bytes: 1,
  },
  {
    photo_id: 'PH_' + 'b'.repeat(24),
    filename: 'b.jpg',
    width: 100,
    height: 100,
    container_format: 'JPEG',
    address: '79_v33',
    simple_address: 'Адрес B',
    client: 'Клиент B',
    brand: 'Бренд B',
    source_directory: 'test',
    taken_at: '2025-07-17 11:43:19',
    size_bytes: 1,
  },
]

function installFetch(resolveA) {
  global.fetch = vi.fn((url) => {
    const path = new URL(String(url), 'http://localhost').pathname

    if (path.endsWith('/v1/photos')) {
      return Promise.resolve(
        json({ items: photos, next_cursor: null, total: photos.length }),
      )
    }

    if (path.endsWith('/details')) {
      if (path.includes(photos[0].photo_id)) return resolveA
      return Promise.resolve(
        json({ photo: { legal_address: 'Юр. B', simple_address: 'Адрес B' }, qwen: null }),
      )
    }

    if (path.endsWith('/qwen-history')) {
      return Promise.resolve(json({ items: [], text: '' }))
    }

    if (path.endsWith('/v1/addresses')) {
      return Promise.resolve(json({ items: [] }))
    }

    if (path.endsWith('/v1/clients')) {
      return Promise.resolve(json({ items: [] }))
    }

    if (path.endsWith('/v1/runs/activity')) {
      return Promise.resolve(json({ active: null }))
    }

    if (path.endsWith('/v1/qwen/settings')) {
      return Promise.resolve(json({ models: {} }))
    }

    return Promise.resolve(json({ items: [] }))
  })
}

const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

async function mountGrid() {
  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(Host, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()
  await nextTick()
  return wrapper
}

beforeEach(() => {
  Notify.create = vi.fn()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('карточка просмотра', () => {
  it('поздние детали предыдущего фото не перезаписывают открытое', async () => {
    let resolveA = null
    const detailsA = new Promise((resolve) => {
      resolveA = resolve
    })

    installFetch(detailsA)

    const wrapper = await mountGrid()
    const tiles = wrapper.findAllComponents(AuthImage)

    expect(tiles.length).toBeGreaterThanOrEqual(2)

    // Открываем A, затем B, пока ответ деталей A ещё не пришёл.
    await tiles[0].find('.auth-image-root').trigger('click')
    await flushPromises()
    await tiles[1].find('.auth-image-root').trigger('click')
    await flushPromises()
    await nextTick()

    resolveA(
      json({
        photo: { legal_address: 'Юр. A', simple_address: 'Адрес A' },
        qwen: null,
      }),
    )
    await flushPromises()
    await nextTick()

    // Диалог Quasar рендерится в портале — смотрим document.body.
    const text = document.body.textContent
    expect(text).toContain('Юр. B')
    expect(text).not.toContain('Юр. A')
    wrapper.unmount()
  })
})
