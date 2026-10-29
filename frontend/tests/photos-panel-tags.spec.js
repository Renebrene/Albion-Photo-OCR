// Строка тегов между поиском и фильтрами: выбранные адреса, клиенты, бренд;
// «Все» для полного списка; поиск по клиенту/бренду идёт по всей базе.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, QSelect, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import { useSessionStore } from '../src/stores/session'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import { addressEntryForPhoto } from '../src/utils/addressForPhoto'
import { useDisplayStore } from '../src/stores/display'
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

function installFetch({ clientsNextCursor = null, suggestions = null, matches = null } = {}) {
  global.fetch = vi.fn(async (url) => {
    const parsed = new URL(String(url), 'http://localhost')
    const path = parsed.pathname

    if (path.endsWith('/v1/photos')) {
      return json({ items: [photo], next_cursor: null, total: 1 })
    }

    if (path.endsWith('/v1/clients')) {
      // Продолжение списка: панель листает его при прокрутке.
      if (parsed.searchParams.get('cursor') === 'page-2') {
        return json({
          items: [{ kind: 'brand', name: 'СТС Строй', count: 4 }],
          next_cursor: null,
        })
      }

      return json({
        items: [
          { kind: 'client', name: 'Клиент А', count: 2 },
          { kind: 'client', name: 'Клиент Б', count: 1 },
        ],
        next_cursor: clientsNextCursor,
      })
    }

    if (path.endsWith('/v1/addresses')) {
      return json({
        items: [
          {
            address: 'addr:78',
            address_id: 78,
            fingerprints: ['78_v33'],
            name: 'Комарова 13',
            simple_address: 'Комарова 13',
            legal_address: 'г. Ростов-на-Дону, ул. Комарова, 13',
            count: 2,
            period_count: 2,
          },
          {
            address: 'addr:79',
            address_id: 79,
            fingerprints: ['79_v33'],
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
        items: suggestions || [
          { value: 'СТС', kind: 'brand', uses: 6 },
          { value: 'Клиент А', kind: 'client', uses: 2 },
        ],
        layout: null,
      })
    }

    if (path.endsWith('/v1/search/matches')) {
      return json(matches || { names: [], addresses: [] })
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
  // Открытый режим (без аутентификации): спека проверяет полный доступ.
  useSessionStore().authEnabled = false

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
  document.body.innerHTML = ''
})

describe('список клиентов и брендов', () => {
  it('подгружает продолжение по кнопке «Показать ещё»', async () => {
    installFetch({ clientsNextCursor: 'page-2' })

    const wrapper = await mountGrid()

    expect(wrapper.text()).toContain('Клиент А')

    const more = wrapper
      .findAll('.q-item')
      .find((node) => node.text().includes('Показать ещё'))

    expect(more).toBeTruthy()

    await more.trigger('click')
    await flushPromises()
    await nextTick()

    // Вторая страница дописана, кнопка исчезла: курсор исчерпан.
    expect(wrapper.text()).toContain('СТС Строй')
    expect(wrapper.text()).not.toContain('Показать ещё')
    wrapper.unmount()
  })
})

describe('строка тегов', () => {
  it('показывает выбранного клиента и адрес, без слова «Адрес»', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    store.selectedAddresses = ['addr:78']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row')
    expect(tags.exists()).toBe(true)
    expect(tags.text()).toContain('Клиент: Клиент А')
    expect(tags.text()).toContain('Комарова 13')
    expect(tags.text()).not.toContain('Адрес:')
    expect(wrapper.find('.client-summary').text()).toBe('(1)')
    wrapper.unmount()
  })

  it('отмеченные клиенты остаются отдельными тегами', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А', 'Клиент Б']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row').text()
    // «Все» больше не отдельное состояние клиентов: пустой выбор уже
    // означает «все клиенты базы».
    expect(tags).toContain('Клиент: Клиент А')
    expect(tags).toContain('Клиент: Клиент Б')
    expect(tags).not.toContain('Все')
    wrapper.unmount()
  })

  it('показывает название подборки вместо отдельных клиентов', async () => {
    const wrapper = await mountGrid()

    store.collections = [
      { collection_id: 5, name: 'Смена 1', scope: 'clients', kind: 'Моя' },
      { collection_id: 6, name: 'Мой район', scope: 'addresses', kind: 'Моя' },
    ]
    store.clientCollectionIds = [5]
    store.addressCollectionIds = [6]
    store.clientCollectionMembers = { 5: ['Клиент А'] }
    store.addressCollectionMembers = { 6: ['addr:78'] }
    store.clientCollectionId = 5
    store.addressCollectionId = 6
    store.selectedClients = ['Клиент А']
    store.selectedAddresses = ['addr:78']
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

  it('показывает несколько активных подборок одного вида', async () => {
    const wrapper = await mountGrid()

    store.collections = [
      { collection_id: 5, name: 'Смена 1', scope: 'clients' },
      { collection_id: 7, name: 'Смена 2', scope: 'clients' },
    ]
    store.clientCollectionIds = [5, 7]
    store.clientCollectionMembers = {
      5: ['Клиент А'], 7: ['Клиент Б'],
    }
    store.selectedClients = ['Клиент А', 'Клиент Б']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Смена 1')
    expect(tags).toContain('Смена 2')
    expect(tags).not.toContain('Клиент: Клиент А')
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

    expect(wrapper.find('.client-summary').text()).toBe('()')
    expect(wrapper.find('.client-help').exists()).toBe(true)

    store.selectedClients = ['Клиент А']
    store.selectedBrand = null
    await flushPromises()
    await nextTick()

    expect(wrapper.find('.client-summary').text()).toBe('(1)')
    wrapper.unmount()
  })

  it('выбранные адреса и клиенты остаются отдельными тегами', async () => {
    const wrapper = await mountGrid()

    // Отмечен весь список адресов (2 из 2) и клиентов (2 из 2).
    store.selectedAddresses = ['addr:78', 'addr:79']
    store.selectedClients = ['Клиент А', 'Клиент Б']
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Комарова 13')
    expect(tags).toContain('Клиент: Клиент А')
    // «Все» больше нет ни у адресов, ни у клиентов.
    expect(tags).not.toContain('Все')
    wrapper.unmount()
  })

  it('кнопки снятия выделения названы по своей панели', async () => {
    const wrapper = await mountGrid()

    // Раньше обе назывались «Очистить» — смысл был виден только по подсказке
    // (второй аудит, п. 4).
    expect(wrapper.find('.address-reset').text()).toBe('Снять адреса')
    expect(wrapper.find('.client-reset').text()).toBe('Снять клиентов')
    expect(wrapper.find('.address-reset').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.client-reset').attributes('disabled')).toBeDefined()
    wrapper.unmount()
  })

  it('кнопка сброса адресов очищает выбор и подборки', async () => {
    const wrapper = await mountGrid()

    store.selectedAddresses = ['addr:78']
    store.addressCollectionIds = [6]
    store.addressCollectionId = 6
    store.addressCollectionValues = ['addr:78']
    store.addressCollectionMembers = { 6: ['addr:78'] }
    await flushPromises()
    await nextTick()

    await wrapper.find('.address-reset').trigger('click')
    await flushPromises()
    await nextTick()

    expect(store.selectedAddresses).toEqual([])
    expect(store.addressCollectionIds).toEqual([])
    expect(store.addressCollectionId).toBe(null)
    // Без других тегов строка тегов не рисуется.
    expect(wrapper.find('.tags-row').exists()).toBe(false)
    wrapper.unmount()
  })

  it('смена режима не сбрасывает множественный выбор клиентов', async () => {
    const wrapper = await mountGrid()
    const display = useDisplayStore()

    store.selectedClients = ['Клиент А', 'Клиент Б']
    await flushPromises()
    await nextTick()

    // □ — приоритет клиентов: режим меняет только то, как складываются адреса
    // и клиенты, а сам выбор (в том числе множественный) остаётся. Раньше
    // переключение стирало его через resetSelectionFilters().
    display.addressClientMode = 'client'
    await flushPromises()
    await nextTick()

    expect(store.selectedClients).toEqual(['Клиент А', 'Клиент Б'])
    expect(store.combine).toBe('client')

    const tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Клиент: Клиент А')
    expect(tags).toContain('Клиент: Клиент Б')

    wrapper.unmount()
  })

  it('выбор клиента из поиска панели не сбрасывает адрес', async () => {
    const wrapper = await mountGrid()

    store.selectedAddresses = ['addr:78']
    await flushPromises()
    await nextTick()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Поиск клиента или бренда')

    await input.setValue('Клиент А')
    await flushPromises()
    await nextTick()

    const row = Array.from(wrapper.element.querySelectorAll('.q-item')).find(
      (node) => node.textContent.includes('Клиент А'),
    )
    row.click()
    await flushPromises()
    await nextTick()

    expect(store.selectedAddresses).toEqual(['addr:78'])
    const tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Комарова 13')
    expect(tags).toContain('Клиент: Клиент А')
    wrapper.unmount()
  })

  it('кнопка сброса клиентов очищает выбор и бренд', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    await flushPromises()
    await nextTick()

    // Бренд выбирается через главный поиск; здесь достаточно проверить
    // очистку клиентов и активной подборки.
    store.clientCollectionId = 5
    store.clientCollectionValues = ['Клиент А']

    await wrapper.find('.client-reset').trigger('click')
    await flushPromises()
    await nextTick()

    expect(store.selectedClients).toEqual([])
    expect(store.clientCollectionId).toBe(null)
    expect(wrapper.find('.tags-row').exists()).toBe(false)
    wrapper.unmount()
  })

  it('«Обновить» снимает выделение фото, а «Сбросить фильтры» — нет', async () => {
    const wrapper = await mountGrid()

    store.selected = ['PH_' + 'a'.repeat(24)]
    await wrapper.find('.grid-refresh').trigger('click')
    await flushPromises()
    await nextTick()

    expect(store.selected).toEqual([])

    store.selected = [photo.photo_id]
    await wrapper.find('.grid-reset').trigger('click')
    await flushPromises()
    await nextTick()

    // Корзина выделенных фото живёт отдельно от фильтров.
    expect(store.selected).toEqual([photo.photo_id])
    wrapper.unmount()
  })

  it('режим приоритета клиентов сужает адреса и пересчитывает счётчики', async () => {
    const wrapper = await mountGrid()
    const display = useDisplayStore()

    // Режим меняет только способ складывания адресов и клиентов: выбранные
    // клиенты и активная подборка остаются. Раньше переключение стирало выбор
    // через resetSelectionFilters(), и владелец попросил это убрать.
    store.collections = [
      { collection_id: 5, name: 'Клиенты', scope: 'clients' },
    ]
    store.selectedClients = ['Клиент А']
    // Подборка живёт парой: список идентификаторов и его состав.
    store.clientCollectionIds = [5]
    store.clientCollectionId = 5
    store.clientCollectionValues = ['Клиент А']
    display.addressClientMode = 'client'
    await flushPromises()
    await nextTick()

    expect(store.selectedClients).toEqual(['Клиент А'])
    expect(store.clientCollectionId).toBe(5)
    expect(wrapper.find('.tags-row').text()).toContain('Клиент: Клиент А')

    await store.loadAddresses()
    await flushPromises()

    const calls = () =>
      global.fetch.mock.calls
        .map(([url]) => String(url))
        .filter((url) => url.includes('/v1/addresses'))

    let params = new URL(calls().at(-1), 'http://localhost').searchParams
    expect(params.getAll('client')).toEqual(['Клиент А'])
    expect(wrapper.text()).toContain('□')

    // Сняли выбор — адреса и их счётчики возвращаются к полному списку.
    store.selectedClients = []
    await store.loadAddresses()
    await flushPromises()

    params = new URL(calls().at(-1), 'http://localhost').searchParams
    expect(params.getAll('client')).toEqual([])
    wrapper.unmount()
  })

  it('текстовый поиск не блокирует панель клиентов', async () => {
    const wrapper = await mountGrid()

    const search = wrapper
      .findAll('input')
      .find(
        (item) =>
          item.attributes('placeholder')
          === 'Название файла, клиент, бренд, адрес',
      )

    await search.setValue('вывеска')
    await search.trigger('keyup.enter')
    await flushPromises()

    const clientInput = wrapper
      .findAll('input')
      .find(
        (item) => item.attributes('placeholder') === 'Поиск клиента или бренда',
      )

    expect(clientInput.attributes('disabled')).toBeUndefined()

    const clientItem = wrapper
      .findAll('.q-item')
      .find((node) => node.text().includes('Клиент А'))

    await clientItem.trigger('click')
    await flushPromises()

    const url = global.fetch.mock.calls
      .map(([value]) => String(value))
      .filter((value) => value.includes('/v1/photos?'))
      .at(-1)
    const params = new URL(url, 'http://localhost').searchParams

    expect(params.get('q')).toBe('вывеска')
    expect(params.getAll('client')).toEqual(['Клиент А'])
    wrapper.unmount()
  })

  it('клик по счётчику выделения снимает выбор', async () => {
    const wrapper = await mountGrid()

    store.selected = ['PH_' + 'a'.repeat(24)]
    await nextTick()

    const badge = wrapper.find('.selection-badge')
    expect(badge.exists()).toBe(true)

    await badge.trigger('click')
    expect(store.selected).toEqual([])
    wrapper.unmount()
  })

  it('при активном фильтре подпись говорит «В выборке», а не «За период»', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    await nextTick()

    expect(wrapper.text()).toContain('В выборке 1 фото')
    expect(wrapper.text()).not.toContain('За период 1 фото')
    wrapper.unmount()
  })

  it('Enter в пустом поиске адресов ничего не выбирает', async () => {
    const wrapper = await mountGrid()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Поиск адреса')

    await input.trigger('keyup.enter')
    await flushPromises()

    expect(store.selectedAddresses).toEqual([])
    wrapper.unmount()
  })

  it('кнопка «Поиск» не отправляет событие клика как текст запроса', async () => {
    const wrapper = await mountGrid()

    global.fetch.mockClear()

    const button = wrapper.find('.apply-search')

    expect(button.exists()).toBe(true)
    await button.trigger('click')
    await flushPromises()

    const photoCalls = global.fetch.mock.calls
      .map(([url]) => String(url))
      .filter((url) => url.includes('/v1/photos?'))

    expect(photoCalls.length).toBeGreaterThan(0)

    const params = new URL(photoCalls.at(-1), 'http://localhost').searchParams
    expect(params.get('q')).toBeNull()
    wrapper.unmount()
  })

  it('пустая выдача объясняет фильтры и даёт снять бренд/тег', async () => {
    const wrapper = await mountGrid()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Поиск клиента или бренда')

    await input.setValue('СТ')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    const item = wrapper
      .findAll('.q-item')
      .find((node) => node.text().includes('СТС'))

    await item.trigger('click')
    await flushPromises()
    await nextTick()

    store.items = []
    await nextTick()

    expect(wrapper.text()).toContain('Активные фильтры')
    expect(wrapper.text()).toContain('Бренд: СТС')

    const clear = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Снять бренд и тег')

    expect(clear).toBeTruthy()
    await clear.trigger('click')
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).not.toContain('Бренд: СТС')
    wrapper.unmount()
  })

  it('длинная строка тегов получает курсор-подсказку и листается колесом', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А', 'Клиент Б']
    store.selectedAddresses = ['addr:78']
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

  it('показывает выбранного клиента, которого нет в списке топ-100', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['AAA Моторс-Запад']
    await flushPromises()
    await nextTick()

    const row = Array.from(wrapper.element.querySelectorAll('.q-item')).find(
      (node) =>
        node.textContent.includes('AAA Моторс-Запад')
        && node.textContent.includes('выбран'),
    )

    expect(row).toBeTruthy()
    // Заголовок панели и список больше не расходятся.
    expect(wrapper.text()).toContain('(1)')
    wrapper.unmount()
  })

  it('выбор бренда в панели не сбрасывает выбранных клиентов', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    await flushPromises()
    await nextTick()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Поиск клиента или бренда')

    await input.setValue('СТ')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    const row = Array.from(wrapper.element.querySelectorAll('.q-item')).find(
      (node) => node.textContent.includes('СТС'),
    )

    expect(row).toBeTruthy()
    row.click()
    await flushPromises()
    await nextTick()

    // Бренд добавляется к клиенту (OR), а не заменяет его.
    expect(store.selectedClients).toEqual(['Клиент А'])
    let tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Клиент: Клиент А')
    expect(tags).toContain('Бренд: СТС')

    // Сброс убирает и клиента, и бренд: пустой выбор = все клиенты базы.
    await wrapper.find('.client-reset').trigger('click')
    await flushPromises()
    await nextTick()

    expect(store.selectedClients).toEqual([])
    expect(wrapper.find('.tags-row').exists()).toBe(false)
    wrapper.unmount()
  })

  it('«В подборку» берёт юридический адрес, а не старый слепок', () => {
    const entry = addressEntryForPhoto(
      [
        {
          address: 'addr:78', name: 'Комарова 13',
          simple_address: 'Комарова 13',
          legal_address: 'г. Ростов-на-Дону, ул. Комарова, 13',
          fingerprints: ['78_v33'],
        },
        {
          address: 'addr:79', name: 'Ленина 5',
          simple_address: 'Ленина 5',
          legal_address: 'г. Ростов-на-Дону, ул. Ленина, 5',
          fingerprints: ['79_v33'],
        },
      ],
      {
        photo_id: 'PH_override',
        address: '78_v33',
        legal_address: 'г. Ростов-на-Дону, ул. Ленина, 5',
        simple_address: 'Ленина 5',
      },
    )

    expect(entry.address).toBe('addr:79')
  })

  it('подсказки работают с первого символа после выбора подсказки', async () => {
    const wrapper = await mountGrid()

    const suggestionCalls = () =>
      global.fetch.mock.calls.filter(([url]) =>
        String(url).includes('/v1/search/suggestions'),
      ).length

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Название файла, клиент, бренд, адрес')

    await input.setValue('СТ')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    const item = Array.from(document.body.querySelectorAll('.q-item'))
      .find((node) => node.textContent.includes('СТС'))
    item.click()
    await flushPromises()
    await nextTick()

    const before = suggestionCalls()
    await input.setValue('Лен')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()

    expect(suggestionCalls()).toBeGreaterThan(before)
    wrapper.unmount()
  })

  it('не показывает в подсказках уже выбранный клиент', async () => {
    const wrapper = await mountGrid()

    store.selectedClients = ['Клиент А']
    await flushPromises()
    await nextTick()

    const input = wrapper
      .findAll('input')
      .find((item) => item.attributes('placeholder') === 'Название файла, клиент, бренд, адрес')

    await input.setValue('Клиент')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    const suggestions = Array.from(
      document.body.querySelectorAll('.q-menu .q-item'),
    ).map((node) => node.textContent)

    expect(suggestions.some((text) => text.includes('Клиент А'))).toBe(false)
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

  it('склеенная подсказка применяет все роли, а не только первую', async () => {
    // «Байков» — и тег, и бренд: строка «тег · бренд» должна искать по обоим,
    // иначе часть фото пропадает (владелец, 29.10.2026).
    installFetch({
      suggestions: [
        { value: 'Байков', kind: 'tag', uses: 9 },
        { value: 'Байков', kind: 'brand', uses: 3 },
      ],
    })

    const wrapper = await mountGrid()

    const input = wrapper
      .findAll('input')
      .find(
        (item) =>
          item.attributes('placeholder')
          === 'Название файла, клиент, бренд, адрес',
      )

    await input.setValue('Бай')
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    await nextTick()

    const suggestion = Array.from(document.body.querySelectorAll('.q-item')).find(
      (node) => node.textContent.includes('Байков'),
    )

    expect(suggestion.textContent).toContain('тег · бренд')

    suggestion.click()
    await flushPromises()
    await nextTick()

    const tags = wrapper.find('.tags-row').text()
    expect(tags).toContain('Бренд: Байков')
    expect(tags).toContain('Тег: Байков')

    wrapper.unmount()
  })

  it('подсвечивает адреса и клиентов, где встречается запрос', async () => {
    // Поиск по тегу не должен менять списки панелей: он только отмечает
    // строки, у которых есть подходящие фото (владелец, 29.10.2026).
    installFetch({
      matches: { names: ['Клиент А'], addresses: ['78_v33'] },
    })

    const wrapper = await mountGrid()

    const input = wrapper
      .findAll('input')
      .find(
        (item) =>
          item.attributes('placeholder')
          === 'Название файла, клиент, бренд, адрес',
      )

    await input.setValue('Байков')
    await input.trigger('keyup.enter')
    await flushPromises()
    await vi.runAllTimersAsync()
    await nextTick()

    const marked = wrapper.findAll('.panel-match')
    expect(marked.length).toBeGreaterThan(0)

    const text = marked.map((node) => node.text()).join(' | ')
    expect(text).toContain('Комарова 13')
    expect(text).toContain('Клиент А')
    // Второй адрес под запрос не попал — он остаётся без подсветки.
    expect(text).not.toContain('Ленина 5')

    wrapper.unmount()
  })
})

describe('период без дат', () => {
  it('говорит «Укажите даты», а не «За период N фото»', async () => {
    const wrapper = await mountGrid()

    // Выбираем «Период…» так же, как это делает пользователь, — через поле.
    const periodSelect = wrapper
      .findAllComponents(QSelect)
      .find((node) => node.props('label') === 'Период')

    expect(periodSelect).toBeTruthy()
    await periodSelect.setValue('custom')
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('Укажите даты')
    expect(wrapper.text()).not.toContain('За период 1 фото')

    wrapper.unmount()
  })
})

describe('уход со страницы', () => {
  it('отпускает blob предпросмотра и не продолжает опрос заданий', async () => {
    const revoke = vi.fn()
    global.URL.revokeObjectURL = revoke

    const wrapper = await mountGrid()

    // Blob предпросмотра в окне ручного описания: раньше он висел до
    // перезагрузки страницы. Ставим его самому гриду (mountGrid оборачивает
    // его в Host).
    const grid = wrapper.findComponent(PhotosGrid)
    grid.vm.manualPreviewUrl = 'blob:preview'
    grid.vm.manualFile = { name: 'фото.jpg' }

    wrapper.unmount()

    expect(revoke).toHaveBeenCalledWith('blob:preview')
  })
})

describe('сторона в тегах', () => {
  // Панель отдаёт строку-сторону: у неё несколько поверхностей (`ids`), а клик
  // отмечает их все. Требование владельца (28.10.2026): в тегах видно сторону,
  // как в списках, и тег на сторону один.
  function installSides() {
    global.fetch = vi.fn(async (url) => {
      const parsed = new URL(String(url), 'http://localhost')

      if (parsed.pathname.endsWith('/v1/photos')) {
        return json({ items: [photo], next_cursor: null, total: 1 })
      }

      if (parsed.pathname.endsWith('/v1/addresses')) {
        return json({
          items: [
            {
              address: 'addr:78',
              address_id: 78,
              ids: [78, 79],
              side: 'A',
              name: 'Комарова 13',
              simple_address: 'Комарова 13',
              legal_address: 'Комарова, 13, A',
              count: 2,
              period_count: 2,
            },
            {
              address: 'addr:80',
              address_id: 80,
              ids: [80],
              side: 'Б',
              name: 'Комарова 13',
              simple_address: 'Комарова 13',
              legal_address: 'Комарова, 13, Б',
              count: 1,
              period_count: 1,
            },
          ],
        })
      }

      return json({ items: [], next_cursor: null })
    })
  }

  it('на сторону приходится один тег с названием из списка', async () => {
    installSides()
    const wrapper = await mountGrid()

    // Клик по стороне отмечает все поверхности: 78 и 79.
    store.selectedAddresses = ['addr:78', 'addr:79']
    await flushPromises()
    await nextTick()

    const text = wrapper.find('.tags-row').text()

    // Название — как в списке; букву стороны не дописываем: она уже в названии
    // из каталога (владелец, 28.10.2026).
    expect(text).toContain('Комарова 13')
    expect(text).not.toContain(', A')
    // Значения поверхностей в теги не попадают.
    expect(text).not.toContain('addr:')
    expect(wrapper.findAll('.tags-row .q-chip')).toHaveLength(1)

    wrapper.unmount()
  })

  it('у каждой выбранной стороны свой тег', async () => {
    installSides()
    const wrapper = await mountGrid()

    store.selectedAddresses = ['addr:78', 'addr:80']
    await flushPromises()
    await nextTick()

    // У чипа в тексте ещё подпись кнопки снятия («cancel»). Стороны с разными
    // поверхностями дают отдельные теги, даже если названия совпадают.
    const labels = wrapper
      .findAll('.tags-row .q-chip')
      .map((chip) => chip.text().replace('cancel', '').trim())

    expect(labels).toEqual(['Комарова 13', 'Комарова 13'])

    wrapper.unmount()
  })

  it('снятие тега снимает всю сторону, а не одну поверхность', async () => {
    installSides()
    const wrapper = await mountGrid()

    store.selectedAddresses = ['addr:78', 'addr:79', 'addr:80']
    await flushPromises()
    await nextTick()

    // Убираем первую сторону (A): остаются только её соседи из Б.
    const chips = wrapper.findAll('.tags-row .q-chip')
    await chips[0].find('.q-chip__icon--remove').trigger('click')
    await flushPromises()

    expect(store.selectedAddresses).toEqual(['addr:80'])

    wrapper.unmount()
  })
})
