// Фильтры живут и в адресе страницы: обновление (F5) и чужая ссылка
// восстанавливают то же самое.
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import { useDisplayStore } from '../src/stores/display'
import { useSessionStore } from '../src/stores/session'

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
  taken_at: '2025-07-17 11:43:19',
  size_bytes: 4194304,
}

let photoUrls

beforeEach(() => {
  photoUrls = []
  // Настройки отображения (включая сохранённые фильтры) живут в localStorage:
  // без очистки следующий тест унаследует срез предыдущего.
  window.localStorage.clear()
  setActivePinia(createPinia())
  useSessionStore().authEnabled = false

  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]

    if (path.endsWith('/v1/photos')) {
      photoUrls.push(String(url))
      return json({ items: [photo], next_cursor: null, total: 1 })
    }

    if (path.endsWith('/v1/addresses')) {
      return json({ items: [{ address: 'addr:78', name: 'Комарова 13', count: 1 }] })
    }

    if (path.endsWith('/v1/clients') || path.endsWith('/v1/collections') || path.endsWith('/v1/searches')) {
      return json({ items: [] })
    }

    return json({})
  })
})

async function mountPage(query = '') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  })

  await router.push(`/${query}`)
  await router.isReady()

  const wrapper = mount(PhotosGrid, {
    global: {
      plugins: [Quasar, router],
      stubs: { AuthImage: true, QPage: { template: '<div><slot /></div>' } },
    },
  })

  await flushPromises()
  await nextTick()

  return { wrapper, router }
}

function lastPhotoParams() {
  return new URL(photoUrls.at(-1), 'http://localhost').searchParams
}

describe('фильтры в адресе страницы', () => {
  it('восстанавливает фильтры из ссылки', async () => {
    const { wrapper } = await mountPage('?q=вывеска&address=addr:78&mode=client')

    const params = lastPhotoParams()

    expect(params.get('q')).toBe('вывеска')
    expect(params.getAll('address')).toEqual(['addr:78'])
    expect(params.get('combine')).toBe('client')

    wrapper.unmount()
  })

  it('период из ссылки применяется как фильтр дат', async () => {
    const { wrapper } = await mountPage('?period=today')

    const params = lastPhotoParams()

    // «Сегодня» — конкретные календарные сутки, а не «за неделю» по умолчанию.
    expect(params.get('date_from')).toBeTruthy()
    expect(params.get('date_from')).toBe(params.get('date_to'))

    wrapper.unmount()
  })

  it('восстанавливает сохранённые период и сортировку, когда адрес пуст', async () => {
    const display = useDisplayStore()
    display.filters = {
      period: 'today',
      from: null,
      to: null,
      sortKey: 'filename',
      sortDirection: 'asc',
    }

    const { wrapper, router } = await mountPage()

    const params = lastPhotoParams()

    // Привычный срез пользователя: сортировка по имени и «сегодня».
    expect(params.get('sort')).toBe('filename')
    expect(params.get('order')).toBe('asc')
    expect(params.get('date_from')).toBeTruthy()
    expect(params.get('date_from')).toBe(params.get('date_to'))

    // Адрес повторяет то, что показано, — ссылку можно передать коллеге.
    expect(router.currentRoute.value.query.sort).toBe('filename')
    expect(router.currentRoute.value.query.period).toBe('today')

    wrapper.unmount()
  })

  it('фильтры из адреса главнее сохранённых и не переписывают их', async () => {
    const display = useDisplayStore()
    display.filters = {
      period: 'month',
      from: null,
      to: null,
      sortKey: 'filename',
      sortDirection: 'asc',
    }

    const { wrapper } = await mountPage('?sort=address&order=desc')

    const params = lastPhotoParams()

    // Ссылка применила своё…
    expect(params.get('sort')).toBe('address')
    expect(params.get('order')).toBe('desc')

    // …но чужой срез не стал «привычным» у пользователя.
    expect(display.filters.sortKey).toBe('filename')
    expect(display.filters.period).toBe('month')

    wrapper.unmount()
  })

  it('сторона с несколькими поверхностями выбирается целиком', async () => {
    // Список адресов приходит сведённым к сторонам: у строки несколько id.
    const base = global.fetch
    global.fetch = vi.fn(async (url, options = {}) => {
      const path = String(url).split('?')[0]
      if (path.endsWith('/v1/addresses')) {
        return json({
          items: [
            {
              address: 'addr:78',
              address_id: 78,
              ids: [78, 79],
              name: 'Комарова 13',
              simple_address: 'Комарова',
              legal_address: 'Комарова 13',
              count: 4,
              period_count: 2,
            },
          ],
        })
      }
      return base(url, options)
    })

    const { wrapper } = await mountPage()

    await wrapper.findAll('.address-name').at(0).trigger('click')
    await flushPromises()

    // Выбраны обе поверхности стороны — иначе грид показал бы половину.
    expect(lastPhotoParams().getAll('address')).toEqual(['addr:78', 'addr:79'])

    wrapper.unmount()
  })

  it('без фильтров в адресе страница открывается как обычно', async () => {
    const { wrapper, router } = await mountPage()

    expect(router.currentRoute.value.query).toEqual({})
    expect(lastPhotoParams().get('q')).toBe(null)

    wrapper.unmount()
  })

  it('применённый фильтр попадает в адрес', async () => {
    const { wrapper, router } = await mountPage()

    const input = wrapper
      .findAll('input')
      .find(
        (item) => item.attributes('placeholder') === 'Название файла, клиент, бренд, адрес',
      )

    await input.setValue('ворота')
    await input.trigger('keyup.enter')
    await flushPromises()
    await nextTick()

    expect(router.currentRoute.value.query.q).toBe('ворота')
    wrapper.unmount()
  })

  it('направление сортировки попадает в адрес', async () => {
    const { wrapper, router } = await mountPage()

    // По умолчанию сортировка «по убыванию»: кнопка со стрелкой вниз.
    const toggle = wrapper
      .findAll('button')
      .find((item) => item.text().includes('arrow_downward'))
    expect(toggle, 'кнопка направления сортировки не найдена').toBeTruthy()

    await toggle.trigger('click')
    await flushPromises()
    await nextTick()

    expect(router.currentRoute.value.query.order).toBe('asc')
    wrapper.unmount()
  })

  it('источник даты из настроек не затирается открытием страницы', async () => {
    // Пользователь выбрал «Дата загрузки» в «Отображении» — открытие грида
    // не должно возвращать его к «Дате съёмки» (второй аудит, п. 3).
    useDisplayStore().dateFilterMode = 'upload'

    const { wrapper } = await mountPage()

    expect(useDisplayStore().dateFilterMode).toBe('upload')
    expect(lastPhotoParams().get('date_mode')).toBe('upload')

    wrapper.unmount()
  })

  it('переключение источника даты перезапрашивает грид', async () => {
    const { wrapper } = await mountPage()

    expect(lastPhotoParams().get('date_mode')).toBe('capture')

    const requestsBefore = photoUrls.length
    useDisplayStore().dateFilterMode = 'upload'
    await flushPromises()
    await nextTick()

    expect(photoUrls.length).toBeGreaterThan(requestsBefore)
    expect(lastPhotoParams().get('date_mode')).toBe('upload')
    // Источник даты — часть выдачи, значит он и в адресе.
    expect(useDisplayStore().dateFilterMode).toBe('upload')

    wrapper.unmount()
  })
})
