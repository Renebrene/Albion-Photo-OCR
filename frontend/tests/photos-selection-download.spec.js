// Выгрузка выбранных фото: имена берутся у сервера, а сервер ограничивает
// страницу сотней строк.
//
// Регрессия: `photosForSelection` спрашивал по 200 идентификаторов и передавал
// `limit=200`, сервер отвечал 422, ошибка глушилась — и все выбранные, но не
// загруженные в грид фото сохранялись как `photo.jpg`.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import { usePhotosStore } from '../src/stores/photos'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

// Что увидел сервер: страницы с идентификаторами и тело запроса на архив.
let idsRequests
let archiveBody
let idsStatus

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function photo(photoId, filename = 'photo.jpg') {
  return {
    photo_id: photoId,
    filename,
    width: 100,
    height: 100,
    container_format: 'JPEG',
    address: '78_v33',
    simple_address: 'Комарова 13',
    client: 'Клиент А',
    brand: 'Бренд Б',
    source_directory: 'test',
    taken_at: '2025-07-17 11:43:19',
    size_bytes: 4194304,
  }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const parsed = new URL(String(url), 'http://localhost')
    const path = parsed.pathname
    const method = (options.method || 'GET').toUpperCase()

    if (path.endsWith('/v1/photos') && method === 'GET') {
      const ids = parsed.searchParams.getAll('ids')

      if (ids.length) {
        idsRequests.push({
          limit: Number(parsed.searchParams.get('limit')),
          ids,
        })

        if (idsStatus !== 200) {
          return json({ detail: [{ msg: 'Input should be less than or equal to 100' }] }, idsStatus)
        }

        return json({
          items: ids.map((id, index) => photo(id, `real-${index}.JPG`)),
          next_cursor: null,
          total: ids.length,
        })
      }

      // Первая страница грида: одно фото, чтобы грид отрисовался.
      return json({ items: [photo(`PH_${'a'.repeat(24)}`)], next_cursor: null, total: 1 })
    }

    if (path.endsWith('/v1/photos/archive')) {
      archiveBody = JSON.parse(options.body)
      return { ok: true, status: 200, blob: async () => new Blob(['zip']) }
    }

    if (path.endsWith('/v1/selection')) return json({ state: {} })
    if (path.endsWith('/v1/qwen/settings')) return json({ models: {} })

    return json({ items: [] })
  })
}

// QPage рендерится только внутри QLayout/QPageContainer — как в App.vue.
const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

async function mountGrid() {
  const pinia = createPinia()
  setActivePinia(pinia)

  // Открытый локальный режим: выгрузка коллективных действий доступна.
  useSessionStore().authEnabled = false

  const wrapper = mount(Host, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()
  return wrapper
}

function clickButton(wrapper, label) {
  const button = wrapper.findAll('button').find((item) => item.text().includes(label))
  expect(button, `кнопка «${label}» не найдена`).toBeTruthy()
  return button.trigger('click')
}

function selectedIds(count) {
  return Array.from({ length: count }, (_, index) => `PH_${String(index).padStart(24, '0')}`)
}

beforeEach(() => {
  idsRequests = []
  archiveBody = null
  idsStatus = 200
  Notify.create = vi.fn()
  installFetch()
})

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('выгрузка выбранных фото', () => {
  it('спрашивает имена страницами не больше 100 — предел сервера', async () => {
    const wrapper = await mountGrid()

    usePhotosStore().selected = selectedIds(150)
    await flushPromises()

    await clickButton(wrapper, 'ZIP')
    await flushPromises()

    expect(idsRequests).toHaveLength(2)
    expect(idsRequests.map((request) => request.ids.length)).toEqual([100, 50])
    // Именно это ломало выгрузку: limit=200 сервер отклонял с 422.
    for (const request of idsRequests) {
      expect(request.limit).toBeLessThanOrEqual(100)
      expect(request.limit).toBe(request.ids.length)
    }
  })

  it('берёт имена с сервера, а не подставляет photo.jpg', async () => {
    const wrapper = await mountGrid()

    usePhotosStore().selected = selectedIds(3)
    await flushPromises()

    await clickButton(wrapper, 'ZIP')
    await flushPromises()

    expect(archiveBody).toBeTruthy()
    expect(archiveBody.items.map((item) => item.name)).toEqual([
      'real-0.JPG',
      'real-1.JPG',
      'real-2.JPG',
    ])
  })

  it('сообщает, если имена получить не удалось, и всё равно собирает архив', async () => {
    idsStatus = 422

    const wrapper = await mountGrid()

    usePhotosStore().selected = selectedIds(2)
    await flushPromises()

    await clickButton(wrapper, 'ZIP')
    await flushPromises()

    // Архив собран: выгрузка не должна пропадать из-за имён.
    expect(archiveBody).toBeTruthy()

    const warning = Notify.create.mock.calls
      .map(([payload]) => payload)
      .find((payload) => payload.type === 'warning' && String(payload.message).includes('photo.jpg'))

    expect(warning).toBeTruthy()
  })
})
