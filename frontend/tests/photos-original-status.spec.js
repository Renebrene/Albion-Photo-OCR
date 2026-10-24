// Доступность оригинала: проверяется при открытии фото, до нажатия
// «посмотреть/скачать». Если оригинала нет — предупреждение вместо ошибки
// загрузки, кнопки оригинала выключены, запись и превью остаются.
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

/** statuses[photo_id] — ответ /original/status для конкретного фото. */
function installFetch(statuses = {}) {
  const calls = []

  global.fetch = vi.fn((url) => {
    const path = new URL(String(url), 'http://localhost').pathname
    calls.push(path)

    if (path.endsWith('/original/status')) {
      const photoId = path.split('/').slice(-3)[0]
      const answer = statuses[photoId] || {
        photo_id: photoId,
        available: true,
        reason: 'ok',
      }

      return Promise.resolve(json(answer))
    }

    if (path.endsWith('/v1/photos')) {
      return Promise.resolve(
        json({ items: photos, next_cursor: null, total: photos.length }),
      )
    }

    if (path.endsWith('/details')) {
      return Promise.resolve(json({ photo: { legal_address: '', simple_address: '' }, qwen: null }))
    }

    if (path.endsWith('/qwen-history')) {
      return Promise.resolve(json({ items: [], text: '' }))
    }

    return Promise.resolve(json({ items: [] }))
  })

  return calls
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

async function openPhoto(wrapper, index) {
  const tiles = wrapper.findAllComponents(AuthImage)
  await tiles[index].find('.auth-image-root').trigger('click')
  await flushPromises()
  await nextTick()
}

beforeEach(() => {
  Notify.create = vi.fn()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('доступность оригинала', () => {
  it('запрашивает статус при открытии фото', async () => {
    const calls = installFetch()
    const wrapper = await mountGrid()

    await openPhoto(wrapper, 0)

    expect(calls.some((path) => path.endsWith('/original/status'))).toBe(true)
  })

  it('пропавший оригинал: предупреждение, а не ошибка загрузки', async () => {
    installFetch({
      [photos[0].photo_id]: {
        photo_id: photos[0].photo_id,
        available: false,
        reason: 'missing',
      },
    })
    const wrapper = await mountGrid()

    await openPhoto(wrapper, 0)

    expect(document.body.textContent).toContain('Оригинал недоступен')
    expect(document.body.textContent).toContain('файл не найден')
    expect(document.body.textContent).toContain('Используйте')
    // Превью продолжает показываться — запись фото не потеряна.
    expect(wrapper.findAllComponents(AuthImage).length).toBeGreaterThan(0)
  })

  it('доступный оригинал: баннера нет', async () => {
    installFetch()
    const wrapper = await mountGrid()

    await openPhoto(wrapper, 0)

    expect(document.body.textContent).not.toContain('Оригинал недоступен')
  })

  it('поздний статус предыдущего фото не перезаписывает открытое', async () => {
    let resolveA = null
    const slowStatusA = new Promise((resolve) => {
      resolveA = resolve
    })

    const statuses = {
      [photos[0].photo_id]: slowStatusA,
      [photos[1].photo_id]: {
        photo_id: photos[1].photo_id,
        available: true,
        reason: 'ok',
      },
    }

    global.fetch = vi.fn((url) => {
      const path = new URL(String(url), 'http://localhost').pathname

      if (path.endsWith('/original/status')) {
        const photoId = path.split('/').slice(-3)[0]
        const answer = statuses[photoId]
        return Promise.resolve(answer instanceof Promise ? answer : json(answer))
      }
      if (path.endsWith('/v1/photos')) {
        return Promise.resolve(
          json({ items: photos, next_cursor: null, total: photos.length }),
        )
      }
      if (path.endsWith('/details')) {
        return Promise.resolve(json({ photo: { legal_address: '', simple_address: '' }, qwen: null }))
      }
      if (path.endsWith('/qwen-history')) {
        return Promise.resolve(json({ items: [], text: '' }))
      }
      return Promise.resolve(json({ items: [] }))
    })

    const wrapper = await mountGrid()

    await openPhoto(wrapper, 0)
    await openPhoto(wrapper, 1)

    // Статус A приходит с опозданием и сообщает, что оригинала нет.
    resolveA(
      json({ photo_id: photos[0].photo_id, available: false, reason: 'missing' }),
    )
    await flushPromises()
    await nextTick()

    expect(document.body.textContent).not.toContain('Оригинал недоступен')
  })

  it('ошибка проверки не блокирует кнопки оригинала', async () => {
    global.fetch = vi.fn((url) => {
      const path = new URL(String(url), 'http://localhost').pathname

      if (path.endsWith('/original/status')) {
        return Promise.resolve(json({ detail: 'nope' }, 503))
      }
      if (path.endsWith('/v1/photos')) {
        return Promise.resolve(
          json({ items: photos, next_cursor: null, total: photos.length }),
        )
      }
      if (path.endsWith('/details')) {
        return Promise.resolve(json({ photo: { legal_address: '', simple_address: '' }, qwen: null }))
      }
      if (path.endsWith('/qwen-history')) {
        return Promise.resolve(json({ items: [], text: '' }))
      }
      return Promise.resolve(json({ items: [] }))
    })

    const wrapper = await mountGrid()

    await openPhoto(wrapper, 0)

    expect(document.body.textContent).not.toContain('Оригинал недоступен')
  })
})
