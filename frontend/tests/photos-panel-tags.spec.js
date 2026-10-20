// Строка тегов между поиском и фильтрами: выбранные адреса, клиенты, бренд;
// «Все» для полного списка; поиск по клиенту/бренду идёт по всей базе.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import { usePhotosStore } from '../src/stores/photos'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const photo = {
  photo_id: 'PH_' + 'a'.repeat(24),
  filename: 'photo.jpg',
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

function installFetch() {
  global.fetch = vi.fn(async (url) => {
    const parsed = new URL(String(url), 'http://localhost')
    const path = parsed.pathname

    if (path.endsWith('/v1/photos')) {
      return json({ items: [photo], next_cursor: null, total: 1 })
    }

    if (path.endsWith('/v1/clients')) {
      return json({
        items: [
          { client: 'Клиент А', count: 2 },
          { client: 'Клиент Б', count: 1 },
        ],
      })
    }

    if (path.endsWith('/v1/addresses')) {
      return json({
        items: [
          {
            address: '78_v33',
            name: 'Комарова 13',
            simple_address: 'Комарова 13',
            legal_address: 'г. Ростов-на-Дону, ул. Комарова, 13',
            count: 2,
            period_count: 2,
          },
          {
            address: '79_v33',
            name: 'Ленина 5',
            simple_address: 'Ленина 5',
            legal_address: 'г. Ростов-на-Дону, ул. Ленина, 5',
            count: 1,
            period_count: 1,
          },
        ],
      })
    }

    if (path.endsWith('/v1/search/suggestions')) {
      return json({
        items: [{ value: 'СТС', kind: 'brand', uses: 6 }],
        layout: null,
      })
    }

    if (path.endsWith('/v1/runs/activity')) {
      return json({ active: null, message: null })
    }

    if (path.endsWith('/v1/qwen/settings')) return json({ models: {} })

    return json({ items: [] })
  })
}

const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

let store

async function mountGrid() {
  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(Host, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()
  await nextTick()

  store = usePhotosStore()
  return wrapper
}

beforeEach(() => {
  vi.useFakeTimers()
  Notify.create = vi.fn()
  installFetch()
})

afterEach(() => {
  vi.useRealTimers()
  delete global.fetch
  vi.restoreAllMocks()
})

describe('строка тегов', () => {
  it('показывает выбранного клиента и адрес, без слова «Адрес»', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    store.selectedAddresses = ['78_v33']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row')
    expect(tags.exists()).toBe(true)
    expect(tags.text()).toContain('Клиент: Клиент А')
    expect(tags.text()).toContain('Комарова 13')
    expect(tags.text()).not.toContain('Адрес:')
    expect(wrapper.text()).toContain('(выбрано 1)')
    wrapper.unmount()
  })

  it('показывает «Все», когда отмечен весь список клиентов', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А', 'Клиент Б']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row')
    expect(tags.text()).toContain('Все')
    expect(tags.text()).not.toContain('Клиент: Клиент А')
    wrapper.unmount()
  })

  it('показывает название подборки вместо отдельных клиентов', async () => {
    const wrapper = await mountGrid()

    store.collections = [
      { collection_id: 5, name: 'Смена 1', scope: 'clients', kind: 'Моя' },
    ]
    store.clientCollectionId = 5
    store.selectedClients = ['Клиент А']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row')
    expect(tags.text()).toContain('Смена 1')
    expect(tags.text()).not.toContain('Клиент: Клиент А')
    wrapper.unmount()
  })

  it('поиск по клиенту/бренду идёт по всей базе и даёт тег «Бренд:»', async () => {
    const wrapper = await mountGrid()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Поиск клиента или бренда')

    await input.setValue('СТ')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('СТС')
    expect(wrapper.text()).toContain('бренд')

    const item = wrapper
      .findAll('.q-item')
      .find((node) => node.text().includes('СТС'))

    await item.trigger('click')
    await flushPromises()
    await nextTick()

    expect(wrapper.find('.tags-row').text()).toContain('Бренд: СТС')
    wrapper.unmount()
  })

  it('в заголовке панели есть счётчик выбранного и знак вопроса', async () => {
    const wrapper = await mountGrid()

    expect(wrapper.text()).toContain('(выбрано 0)')
    expect(wrapper.find('.client-help').exists()).toBe(true)

    store.selectedClients = ['Клиент А']
    store.selectedBrand = null
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('(выбрано 1)')
    wrapper.unmount()
  })
})
