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
      { collection_id: 6, name: 'Мой район', scope: 'addresses', kind: 'Моя' },
    ]
    store.clientCollectionId = 5
    store.addressCollectionId = 6
    store.selectedClients = ['Клиент А']
    store.selectedAddresses = ['78_v33']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row')
    expect(tags.text()).toContain('Смена 1')
    expect(tags.text()).toContain('Мой район')
    expect(tags.text()).not.toContain('Клиент: Клиент А')

    // Подборки подсвечиваются цветом своей панели: адреса — primary,
    // клиенты — secondary.
    const items = wrapper.findAll('.q-item')
    const clientCollection = items.find((item) => item.text().includes('Смена 1'))
    const addressCollection = items.find((item) => item.text().includes('Мой район'))

    expect(clientCollection.classes()).toContain('bg-secondary')
    expect(addressCollection.classes()).toContain('bg-primary')
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

  it('выбор всего списка заменяет отдельные теги на «Все»', async () => {
    const wrapper = await mountGrid()

    // Отмечен весь список адресов (2 из 2) и клиентов (2 из 2).
    store.selectedAddresses = ['78_v33', '79_v33']
    store.selectedClients = ['Клиент А', 'Клиент Б']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row').text()
    expect(tags).not.toContain('Комарова 13')
    expect(tags).not.toContain('Клиент: Клиент А')
    expect(tags.split('Все').length - 1).toBe(2)
    wrapper.unmount()
  })

  it('кнопка «Все» в заголовке панели выбирает весь список', async () => {
    const wrapper = await mountGrid()

    const buttons = wrapper
      .findAll('button')
      .filter((button) => button.text().trim() === 'Все')

    expect(buttons.length).toBe(2)

    await buttons[0].trigger('click')
    await flushPromises()
    await nextTick()

    expect(wrapper.find('.tags-row').text()).toContain('Все')
    wrapper.unmount()
  })

  it('длинная строка тегов получает курсор-подсказку и листается колесом', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А', 'Клиент Б']
    store.selectedAddresses = ['78_v33']
    await flushPromises()
    await nextTick()

    const row = wrapper.find('.tags-row')
    expect(row.exists()).toBe(true)

    // happy-dom не считает раскладку: задаём размеры вручную и сообщаем
    // странице о resize, как это сделал бы браузер.
    Object.defineProperty(row.element, 'scrollWidth', { value: 600, configurable: true })
    Object.defineProperty(row.element, 'clientWidth', { value: 300, configurable: true })
    window.dispatchEvent(new Event('resize'))
    await nextTick()

    expect(row.classes()).toContain('is-scrollable')

    let scrollLeft = 0
    Object.defineProperty(row.element, 'scrollLeft', {
      configurable: true,
      get: () => scrollLeft,
      set: (value) => { scrollLeft = value },
    })

    await row.trigger('wheel', { deltaY: 120 })
    expect(scrollLeft).toBe(120)

    await row.trigger('wheel', { deltaY: -40 })
    expect(scrollLeft).toBe(80)
    wrapper.unmount()
  })

  it('новая подсказка поиска дополняет теги, а не стирает их', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    await flushPromises()
    await nextTick()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Название файла, клиент, бренд, адрес')

    await input.setValue('СТ')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    const suggestion = Array.from(document.body.querySelectorAll('.q-item')).find(
      (node) => node.textContent.includes('СТС'),
    )

    expect(suggestion).toBeTruthy()
    suggestion.click()
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Клиент: Клиент А')
    expect(tags).toContain('Бренд: СТС')
    wrapper.unmount()
  })
})
