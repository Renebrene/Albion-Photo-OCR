// Значок QWEN внизу плитки грида: цвет говорит о состоянии и об источнике
// описания (владелец, 21.11.2026): красный — ошибка, оранжевый — в процессе,
// серый — описания нет, зелёный — кропы щита, голубой — полный кадр.
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

function photo(id, overrides = {}) {
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
    ...overrides,
  }
}

const photos = [
  photo('a', { qwen_status: 'FAILED', qwen_described: false }),
  photo('b', { qwen_status: 'PENDING', qwen_described: false }),
  photo('c', { qwen_status: 'DONE', qwen_described: true, qwen_source: 'crop' }),
  photo('d', { qwen_status: 'DONE', qwen_described: true, qwen_source: 'full' }),
  photo('e', { qwen_status: 'DONE', qwen_described: false }),
]

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

describe('значок QWEN в гриде', () => {
  it('различает ошибку, процесс, отсутствие и источник описания', async () => {
    const wrapper = await mountGrid()
    const grid = wrapper.findComponent(PhotosGrid)

    expect(grid.vm.qwenColor(photos[0])).toBe('negative')
    expect(grid.vm.qwenColor(photos[1])).toBe('orange')
    expect(grid.vm.qwenColor(photos[2])).toBe('positive')
    expect(grid.vm.qwenColor(photos[3])).toBe('light-blue')
    expect(grid.vm.qwenColor(photos[4])).toBe('grey')
  })

  it('подпись значка называет источник описания', async () => {
    const wrapper = await mountGrid()
    const grid = wrapper.findComponent(PhotosGrid)

    expect(grid.vm.qwenHint(photos[2])).toBe('QWEN: описание по кропам щита')
    expect(grid.vm.qwenHint(photos[3])).toBe('QWEN: описание по полному кадру')
    expect(grid.vm.qwenHint(photos[0])).toBe('QWEN: ошибка')
    expect(grid.vm.qwenHint(photos[4])).toBe('QWEN: описания нет')
  })

  it('цвет доходит до иконки в плитке', async () => {
    const wrapper = await mountGrid()
    const cards = wrapper.findAll('.photo-card')

    expect(cards).toHaveLength(photos.length)

    const iconOf = (card) =>
      card.findAll('.q-icon').find((icon) => icon.text().includes('auto_awesome'))

    expect(iconOf(cards[2]).classes()).toContain('text-positive')
    expect(iconOf(cards[3]).classes()).toContain('text-light-blue')
  })
})
