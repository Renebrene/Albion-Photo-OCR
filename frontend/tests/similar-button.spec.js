// Кнопка «Похожие» гаснет у фото без кропа щита: индексу CLIP искать не по
// чему, а сервер ответил бы 404. Вместо красной ошибки — подсказка
// «щит не найден» (владелец, 21.11.2026).
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function photo(id, hasCrop) {
  return {
    photo_id: 'PH_' + id.repeat(24),
    filename: `${id}.jpg`,
    width: 100,
    height: 100,
    container_format: 'JPEG',
    address: '78_v33',
    simple_address: `Адрес ${id}`,
    client: 'Клиент',
    brand: 'Бренд',
    source_directory: 'test',
    source_root: 'TEST',
    taken_at: '2025-07-17 11:43:19',
    size_bytes: 1,
    has_billboard_crop: hasCrop,
  }
}

const photos = [photo('a', true), photo('b', false)]

function installFetch() {
  global.fetch = vi.fn((url) => {
    const path = new URL(String(url), 'http://localhost').pathname

    if (path.endsWith('/v1/photos')) {
      return Promise.resolve(
        json({ items: photos, next_cursor: null, total: photos.length }),
      )
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
  installFetch()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('кнопка «Похожие» и кроп щита', () => {
  it('активна только у фото с кропом', async () => {
    const wrapper = await mountGrid()
    const buttons = wrapper.findAll('.photo-similar')

    expect(buttons).toHaveLength(2)
    expect(buttons[0].classes()).not.toContain('disabled')
    expect(buttons[1].classes()).toContain('disabled')
  })

  it('без кропа диалог не открывается и ошибки нет', async () => {
    const wrapper = await mountGrid()
    const grid = wrapper.findComponent(PhotosGrid)

    await grid.vm.openSimilar(photos[1])
    await nextTick()

    expect(grid.vm.similarOpen).toBe(false)
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'info',
        message: expect.stringContaining('Щит на фото не найден'),
      }),
    )
  })
})
