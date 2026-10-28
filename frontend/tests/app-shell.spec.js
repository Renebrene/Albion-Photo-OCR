// Смок оболочки: приложение монтируется, входит по сессии и запрашивает фото.
// Такой тест ловит поломки на старте (плохой импорт, ошибка в setup, сломанный
// маршрут), из-за которых страница открывается пустой и не зовёт API.
// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from '../src/App.vue'
import Help from '../src/pages/Help.vue'
import PhotosGrid from '../src/pages/PhotosGrid.vue'
import VideosGrid from '../src/pages/VideosGrid.vue'
import Technical from '../src/pages/Technical.vue'
import { setToken } from '../src/api/client'
import { useDisplayStore } from '../src/stores/display'
import { usePhotosStore } from '../src/stores/photos'

const calls = []
const urls = []
// Тела запросов архива: по ним видно имена файлов, которые ушли на сервер.
const archiveBodies = []
// Тела записей в /v1/selection: по ним видно, что именно сохраняется.
const selectionBodies = []

// Уведомления в тестах не нужны, а их отсутствие прячет настоящую ошибку.
Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch({
  loggedIn = true,
  role = 'Администратор',
  photoPages = null,
  selection = {},
} = {}) {
  let photoPageIndex = 0

  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url).split('?')[0]
    const method = (options.method || 'GET').toUpperCase()

    calls.push(path)
    urls.push(String(url))

    // Роль приходит в /auth/me и определяет, что видит пользователь.
    if (path.endsWith('/v1/auth/me')) {
      return json({
        user: loggedIn ? { user_id: 1, name: role, role } : null,
        auth_enabled: true,
      })
    }

    if (path.endsWith('/v1/auth/login') && method === 'POST') {
      return json({
        token: 'fresh-token',
        user: { user_id: 1, name: 'Администратор', role: 'Администратор' },
      })
    }

    if (path.endsWith('/v1/photos')) {
      if (photoPages) {
        const page = photoPages[Math.min(photoPageIndex, photoPages.length - 1)]
        photoPageIndex += 1
        return json(page)
      }

      return json({
        items: [
          {
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
          },
        ],
        next_cursor: null,
      })
    }

    if (path.endsWith('/v1/photos/archive') && method === 'POST') {
      archiveBodies.push(JSON.parse(options.body))
      return {
        ok: true,
        status: 200,
        blob: async () => new Blob(['zip-bytes'], { type: 'application/zip' }),
      }
    }

    if (path.endsWith('/v1/selection')) {
      if (method === 'PUT') {
        selectionBodies.push(JSON.parse(options.body))
      }

      return json({ state: selection })
    }

    if (path.endsWith('/v1/addresses/directory')) {
      return json({
        items: [
          {
            address_id: 5,
            legal_address: 'г. Ростов-на-Дону, ул. Комарова, 13',
            simple_address: 'Комарова 13',
            active: true,
            sort_order: 0,
            fingerprints: [],
          },
        ],
      })
    }

    if (path.endsWith('/qwen-history')) {
      return json({
        items: [{
          history_id: 1,
          status: 'DONE',
          description: 'Прежнее описание',
          client: 'Старый клиент',
          brand: 'Старый бренд',
          category: 'Реклама',
          tags: ['тег'],
          qwen_model: 'old-model',
          replaced_at: '2026-10-01T10:00:00',
        }],
      })
    }

    if (path.endsWith('/details')) {
      return json({
        photo: {
          photo_id: 'PH_' + 'a'.repeat(24),
          filename: 'photo.jpg',
          client: 'Клиент А',
          brand: 'Бренд Б',
          source_directory: 'test',
        },
        qwen: {
          status: 'DONE',
          description: 'Описание сцены',
          client: 'Клиент А',
          brand: 'Бренд Б',
          category: 'Реклама товаров',
          tags: [],
        },
        address_override: null,
      })
    }

    if (path.endsWith('/v1/search/suggestions')) {
      return json({
        items: [{ value: 'Рязанка', kind: 'brand', uses: 4 }],
        layout: {
          query: 'комарова',
          items: [{ value: 'Комарова 13', kind: 'address', uses: 7 }],
        },
      })
    }

    if (path.endsWith('/v1/videos')) return json({ items: [], next_cursor: null })

    if (path.endsWith('/v1/media/statistics')) {
      return json({ photos: 1, videos: 0, months: [] })
    }

    if (path.endsWith('/v1/stats')) {
      return json({
        photos: 1,
        videos: 0,
        period_photos: 1,
        period_videos: 0,
        addresses: 1,
        clients: 0,
        last_photo_at: null,
        last_video_at: null,
      })
    }

    if (path.endsWith('/v1/media/statistics')) return json({ photos: 1, videos: 0, months: [] })

    return json({ items: [] })
  })
}

beforeEach(() => {
  calls.length = 0
  urls.length = 0
  selectionBodies.length = 0

  // В сборке это подставляет Vite (define), в тестах переменной нет —
  // приложение обязано подняться и без неё (подпись сборки просто прочерк).
  delete globalThis.__APP_BUILD__

  // happy-dom не умеет ResizeObserver, а грид следит за своей шириной.
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  setToken('test-token')
  installFetch()
})

describe('оболочка приложения', () => {
  async function mountShell({ role = null, selection = {} } = {}) {
    // Роль задаётся до монтирования: /auth/me отвечает уже от её имени.
    if (role) {
      installFetch({ role, selection })
    } else if (Object.keys(selection).length) {
      installFetch({ selection })
    }

    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: PhotosGrid },
        { path: '/videos', component: VideosGrid },
        { path: '/technical', component: Technical },
        { path: '/help', component: Help },
      ],
    })

    const pinia = createPinia()
    setActivePinia(pinia)

    await router.push('/')
    await router.isReady()

    const wrapper = mount(App, {
      global: { plugins: [Quasar, pinia, router] },
      attachTo: document.body,
    })

    await flushPromises()

    return wrapper
  }

  it('монтируется и запрашивает фотографии', async () => {
    const wrapper = await mountShell()

    expect(calls).toContain('/api/v1/auth/me')
    expect(calls.some((path) => path.endsWith('/v1/photos'))).toBe(true)

    // Вход не показывается: сессия живая.
    expect(wrapper.text()).not.toContain('Войти')

    // Подпись плитки: алиас адреса, имя файла, дата съёмки с весом,
    // результат распознавания — клиент и бренд.
    const caption = wrapper.text()

    expect(caption).toContain('Комарова 13')
    expect(caption).toContain('photo.jpg')
    expect(caption).toContain('17.07.2025 · 11:43:19')
    expect(caption).toContain('Клиент А, Бренд Б')
    // В плитке путь к каталогу убран; он остаётся в списке и окне просмотра.
    expect(caption).not.toContain('Каталог: test')

    // Подвал: общий итог, счётчики за период и последнее медиа.
    expect(caption).toContain('Всего медиа')
    expect(caption).toContain('За период')
    expect(caption).toContain('Последнее медиа')

    wrapper.unmount()
  })

  it('технический раздел по умолчанию открывает «Загрузку»', async () => {
    const wrapper = await mountShell()

    await wrapper.vm.$router.push('/technical')
    await flushPromises()

    const technical = wrapper.findComponent(Technical)
    expect(technical.exists()).toBe(true)
    expect(technical.vm.tab).toBe('ingest')

    wrapper.unmount()
  })

  it('в списке подпись идёт двумя строками', async () => {
    const wrapper = await mountShell()

    // Переключаем вид на «Список»: вторая кнопка переключателя.
    const listButton = wrapper
      .findAll('button')
      .find((button) => button.html().includes('view_list'))

    expect(listButton).toBeTruthy()

    await listButton.trigger('click')
    await flushPromises()

    const rows = wrapper.findAll('.q-list .q-item')
    const row = rows.find((item) => item.text().includes('photo.jpg'))

    expect(row).toBeTruthy()

    const text = row.text().replace(/\s+/g, ' ')

    // По умолчанию в списке: строка 1 — адрес, строка 2 — имя файла и клиент.
    // Дата/размер/бренд появляются, только если включены в настройках списка.
    expect(text).toContain('Комарова 13')
    expect(text).toContain('photo.jpg')
    expect(text).toContain('Клиент А')
    expect(text).not.toContain('17.07.2025')

    wrapper.unmount()
  })

  it('ZIP собирает выбранные фото одним архивом', async () => {
    Notify.create.mockClear()
    global.URL.createObjectURL = vi.fn(() => 'blob:zip')
    global.URL.revokeObjectURL = vi.fn()

    archiveBodies.length = 0

    const wrapper = await mountShell()
    const grid = wrapper.findComponent(PhotosGrid)
    const photoId = 'PH_' + 'a'.repeat(24)

    grid.vm.store.toggleSelected(photoId)
    await flushPromises()

    await grid.vm.downloadZip()
    await flushPromises()

    expect(calls).toContain('/api/v1/photos/archive')
    expect(Notify.create).toHaveBeenCalled()
    expect(Notify.create.mock.calls.at(-1)[0]).toMatchObject({
      type: 'positive',
      message: 'Архив собран: 1 фото',
    })

    wrapper.unmount()
  })

  it('имя файла для незагруженного фото берётся с сервера', async () => {
    Notify.create.mockClear()
    global.URL.createObjectURL = vi.fn(() => 'blob:zip')
    global.URL.revokeObjectURL = vi.fn()

    const missingId = 'PH_' + 'z'.repeat(24)
    const baseFetch = global.fetch

    // Выделенное фото не загружено в грид: имя для архива приходит из ответа
    // на запрос по идентификаторам.
    global.fetch = vi.fn(async (url, options = {}) => {
      const parsed = new URL(String(url), 'http://localhost')

      if (
        parsed.pathname.endsWith('/v1/photos')
        && parsed.searchParams.getAll('ids').includes(missingId)
      ) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            items: [
              {
                photo_id: missingId,
                filename: 'ворота-восточные.jpg',
                width: 100,
                height: 100,
                container_format: 'JPEG',
                address: '78_v33',
                simple_address: 'Комарова 13',
                taken_at: '2025-07-17 11:43:19',
                size_bytes: 1024,
              },
            ],
            next_cursor: null,
          }),
        }
      }

      return baseFetch(url, options)
    })

    archiveBodies.length = 0

    const wrapper = await mountShell()
    const grid = wrapper.findComponent(PhotosGrid)

    grid.vm.store.toggleSelected(missingId)
    await flushPromises()

    await grid.vm.downloadZip()
    await flushPromises()

    // Раньше было «photo.jpg»: имя брали только из загруженных карточек.
    expect(archiveBodies.at(-1).items).toEqual([
      { photo_id: missingId, name: 'ворота-восточные.jpg' },
    ])

    wrapper.unmount()
  })

  it('догружает следующие страницы, если грид ещё не прокручивается', async () => {
    const photo = (index) => ({
      photo_id: `PH_${String(index).padStart(24, '0')}`,
      filename: `photo-${index}.jpg`,
      width: 100,
      height: 100,
      container_format: 'JPEG',
      address: '78_v33',
      simple_address: 'Комарова 13',
      taken_at: '2025-07-17 11:43:19',
      size_bytes: 1024,
    })

    installFetch({
      photoPages: [
        { items: [photo(1)], next_cursor: 'cursor-1' },
        { items: [photo(2)], next_cursor: 'cursor-2' },
        { items: [photo(3)], next_cursor: null },
      ],
    })

    const oldClientHeight = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'clientHeight',
    )
    const oldScrollHeight = Object.getOwnPropertyDescriptor(
      HTMLElement.prototype,
      'scrollHeight',
    )

    Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
      configurable: true,
      get() { return this.classList?.contains('grid-scroll') ? 600 : 0 },
    })
    Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
      configurable: true,
      get() {
        if (!this.classList?.contains('grid-scroll')) return 0
        return this.querySelectorAll('.photo-card').length >= 2 ? 800 : 500
      },
    })

    let wrapper

    try {
      wrapper = await mountShell()
      const grid = wrapper.findComponent(PhotosGrid)
      const scroll = grid.find('.grid-scroll').element

      // No scroll event is sent: the first page underfills the viewport, so
      // auto-fill fetches one more page and stops once scrolling is possible.
      await new Promise((resolve) => setTimeout(resolve, 0))
      await flushPromises()

      expect(scroll.scrollHeight).toBeGreaterThan(scroll.clientHeight)
      expect(calls.filter((path) => path.endsWith('/v1/photos'))).toHaveLength(2)
      expect(grid.vm.items).toHaveLength(2)
      expect(grid.text()).toContain('Показано 2 фото; есть ещё')

      const loadMore = wrapper
        .findAll('button')
        .find((button) => button.text().includes('Загрузить ещё'))
      expect(loadMore).toBeTruthy()
      await loadMore.trigger('click')
      await flushPromises()

      expect(calls.filter((path) => path.endsWith('/v1/photos'))).toHaveLength(3)
      expect(grid.vm.items).toHaveLength(3)
      expect(grid.text()).toContain('Показаны все фото')
    } finally {
      wrapper?.unmount()
      if (oldClientHeight) {
        Object.defineProperty(HTMLElement.prototype, 'clientHeight', oldClientHeight)
      } else {
        delete HTMLElement.prototype.clientHeight
      }
      if (oldScrollHeight) {
        Object.defineProperty(HTMLElement.prototype, 'scrollHeight', oldScrollHeight)
      } else {
        delete HTMLElement.prototype.scrollHeight
      }
    }
  })

  it('очистка строки поиска обновляет грид автоматически', async () => {
    const wrapper = await mountShell()

    const searchInput = wrapper
      .findAll('input')
      .find((input) => (input.attributes('placeholder') || '').includes('Название файла'))

    expect(searchInput).toBeTruthy()

    await searchInput.setValue('Рязанка')
    await searchInput.trigger('keyup.enter')
    await flushPromises()

    // Нажимаем именно кнопку очистки Quasar (не setValue('')): она присылает
    // update:model-value(null) и @clear.
    const field = searchInput.element.closest('.q-field')
    const clearIcon = field.querySelector('.q-field__append .q-icon')

    expect(clearIcon).toBeTruthy()
    clearIcon.click()
    await flushPromises()

    const photoRequests = urls.filter((url) => url.includes('/v1/photos?'))
    const last = photoRequests[photoRequests.length - 1]

    // Последний запрос — уже без строки поиска: грид вернулся к полному списку.
    expect(photoRequests.length).toBeGreaterThanOrEqual(3)
    expect(new URL(last, 'http://localhost').searchParams.get('q')).toBeNull()

    wrapper.unmount()
  })

  it('фильтры адресов и клиентов не восстанавливаются при входе', async () => {
    installFetch({ selection: { selected: ['PH_' + 'b'.repeat(24)] } })

    const wrapper = await mountShell()
    await flushPromises()

    const photosCall = urls.find((url) => url.includes('/v1/photos?'))
    expect(photosCall).toBeTruthy()
    expect(photosCall).not.toContain('address=')
    expect(photosCall).not.toContain('client=')
    expect(photosCall).not.toContain('q=')

    wrapper.unmount()
  })

  it('выделение фото не восстанавливается из состояния на сервере', async () => {
    installFetch({ selection: { selected: ['PH_' + 'b'.repeat(24)] } })

    const wrapper = await mountShell()
    await flushPromises()

    // Корзина выделенных — состояние страницы, а не профиля: вход всегда
    // начинается с пустого набора (решение владельца, 2026-10-24).
    expect(usePhotosStore().selected).toEqual([])

    wrapper.unmount()
  })

  it('выделение фото не записывается на сервер', async () => {
    installFetch({ selection: { selected: [] } })

    const wrapper = await mountShell()
    await flushPromises()

    const photoId = 'PH_' + 'd'.repeat(24)
    usePhotosStore().toggleSelected(photoId)
    await new Promise((resolve) => setTimeout(resolve, 900))
    await flushPromises()

    // Выделение живёт только в памяти; в /v1/selection уходят лишь настройки
    // отображения, поэтому смотрим записи именно с selected.
    expect(selectionBodies.filter((body) => body.state?.selected !== undefined)).toEqual([])
    expect(usePhotosStore().selected).toEqual([photoId])

    wrapper.unmount()
  })

  it('возвращение на страницу фото снимает выделение', async () => {
    installFetch({ selection: { selected: [] } })

    const wrapper = await mountShell()
    await flushPromises()

    usePhotosStore().toggleSelected('PH_' + 'g'.repeat(24))
    await flushPromises()
    expect(usePhotosStore().selected).toHaveLength(1)

    await wrapper.vm.$router.push('/videos')
    await flushPromises()
    await wrapper.vm.$router.push('/')
    await flushPromises()

    expect(usePhotosStore().selected).toEqual([])

    wrapper.unmount()
  })

  it('кнопка «Обновить» снимает выделение', async () => {
    installFetch({ selection: { selected: [] } })

    const wrapper = await mountShell()
    await flushPromises()

    usePhotosStore().toggleSelected('PH_' + 'h'.repeat(24))
    await flushPromises()

    await wrapper.find('.grid-refresh').trigger('click')
    await flushPromises()

    expect(usePhotosStore().selected).toEqual([])

    wrapper.unmount()
  })

  it('в скрытой вкладке счётчики подвала не опрашиваются', async () => {
    // happy-dom отдаёт document.hidden только для чтения.
    const setHidden = (value) =>
      Object.defineProperty(document, 'hidden', { value, configurable: true })

    setHidden(true)
    vi.useFakeTimers()

    try {
      const wrapper = await mountShell()
      await flushPromises()

      const statsCalls = () => urls.filter((url) => url.includes('/v1/stats')).length
      const before = statsCalls()

      // Минута прошла, но окно скрыто — в API не стучимся.
      await vi.advanceTimersByTimeAsync(60_000)
      expect(statsCalls()).toBe(before)

      // Вернулись во вкладку: числа обновляются сразу, не ожидая следующей минуты.
      setHidden(false)
      document.dispatchEvent(new Event('visibilitychange'))
      await flushPromises()

      expect(statsCalls()).toBeGreaterThan(before)
      wrapper.unmount()
    } finally {
      vi.useRealTimers()
      setHidden(false)
    }
  })


  it('во время прогона строку о стадии показывает шапка, рядом с кнопкой', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      const path = String(url).split('?')[0]

      if (path.endsWith('/v1/runs/activity')) {
        return json({
          active: { kind: 'pipeline', run_id: 1, stage: 'HYBRID' },
          message: 'идёт «Обновление базы» (стадия HYBRID)',
        })
      }
      if (path.endsWith('/v1/pipeline/current')) {
        return json({
          run: {
            run_id: 1, status: 'RUNNING', stage: 'HYBRID', stages: [
              { stage: 'HYBRID', done_count: 697, failed_count: 0, total_count: 935 },
            ],
          },
        })
      }

      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    const header = wrapper.find('header')

    expect(header.text()).toContain('Обновление базы')
    // Этапы со счётчиками: имя этапа словами владельца и «сделано / всего».
    expect(header.text()).toContain('Сортировка · Гибрид 697 / 935')

    wrapper.unmount()
  })

  it('после завершения прогона строки в шапке нет', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).split('?')[0].endsWith('/v1/runs/activity')) {
        return json({ active: null })
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    expect(wrapper.find('header').text()).not.toContain('совпадений')

    wrapper.unmount()
  })

  it('в открытом демо-режиме доступны вкладки и техраздел', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).includes('/v1/auth/me')) {
        return json({ user: null, auth_enabled: false })
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    // Главный экран теперь первая подборка, «Видео» — кнопка справа.
    expect(wrapper.text()).toContain('Видеоэкраны')
    expect(wrapper.text()).toContain('Видео')
    expect(wrapper.html()).toContain('/technical')
    expect(wrapper.text()).toContain('Обновление базы')

    wrapper.unmount()
  })

  it('Менеджер без техраздела, но с запуском обновления базы', async () => {
    const wrapper = await mountShell({ role: 'Менеджер' })

    expect(wrapper.text()).toContain('Обновление базы')
    expect(wrapper.html()).not.toContain('/technical')

    wrapper.unmount()
  })

  it('Менеджеру счётчики подвала не запрашиваются', async () => {
    const wrapper = await mountShell({ role: 'Менеджер' })

    // Подвал остаётся: переключатель режима, руководство, метка сборки.
    expect(wrapper.find('footer').exists()).toBe(true)
    expect(wrapper.find('footer').text()).toContain('Руководство пользователя')
    expect(wrapper.find('footer').text()).toContain('сборка')

    // А дорогой запрос счётчиков по всему корпусу не уходит вовсе.
    expect(wrapper.find('footer').text()).not.toContain('Всего медиа')
    expect(calls).not.toContain('/api/v1/stats')

    wrapper.unmount()
  })

  it('Гость видит грид, но без поиска по файлу, скачивания и техраздела', async () => {
    const wrapper = await mountShell({ role: 'Гость' })
    const html = wrapper.html()

    // Разрешено: грид, фильтры, текстовая строка поиска, видео.
    expect(wrapper.text()).toContain('Видеоэкраны')
    expect(wrapper.text()).toContain('Видео')
    expect(
      wrapper.find('input[placeholder*="Название файла"]').exists(),
    ).toBe(true)

    // Запрещено: поиск по фото/видео, скачивание, подборки, техраздел.
    expect(html).not.toContain('photo_camera')
    expect(wrapper.text()).not.toContain('Скачать')
    expect(wrapper.text()).not.toContain('В подборку')
    expect(wrapper.text()).not.toContain('Обновление базы')
    expect(html).not.toContain('/technical')

    wrapper.unmount()
  })

  it('показывает клиента и бренд в карточке QWEN и в форме редактирования', async () => {
    const wrapper = await mountShell()
    const grid = wrapper.findComponent(PhotosGrid)

    await grid.vm.open({
      photo_id: 'PH_' + 'a'.repeat(24),
      filename: 'photo.jpg',
      address: '78_v33',
      simple_address: 'Комарова 13',
    })
    await flushPromises()

    expect(document.body.textContent).toContain('Клиент А')
    expect(document.body.textContent).toContain('Бренд Б')
    expect(grid.vm.qwenHistoryText).toContain('клиент: Старый клиент, бренд: Старый бренд')
    expect(grid.vm.qwenHistoryText).toContain('Прежнее описание')

    const edit = Array.from(document.body.querySelectorAll('button'))
      .find((button) => button.textContent.includes('Редактировать'))
    expect(edit).toBeTruthy()
    edit.click()
    await flushPromises()

    const labels = Array.from(document.body.querySelectorAll('.q-field__label'))
      .map((label) => label.textContent.trim())
    // Поля приходят из общей формы PhotoFieldsForm (одна на правку и поиск).
    expect(labels).toEqual(
      expect.arrayContaining(['Описание', 'Клиент', 'Бренд', 'Категория', 'Теги (через запятую)']),
    )

    wrapper.unmount()
  })

  it('карточка позволяет исправить юридический адрес', async () => {
    const wrapper = await mountShell()
    const grid = wrapper.findComponent(PhotosGrid)

    await grid.vm.open({
      photo_id: 'PH_' + 'a'.repeat(24),
      filename: 'photo.jpg',
      address: '78_v33',
      simple_address: 'Комарова 13',
    })
    await flushPromises()

    await grid.vm.openAddressEditor()
    await flushPromises()

    expect(document.body.textContent).toContain('Выберите адрес из справочника')

    grid.vm.addressChoice = 5
    await grid.vm.saveAddressOverride()
    await flushPromises()

    const saved = urls.find((url) => url.endsWith('/address'))
    expect(saved).toBeTruthy()

    wrapper.unmount()
  })

  it('во время текстового поиска панель клиентов/брендов остаётся доступной', async () => {
    const wrapper = await mountShell()

    const clientCard = document.querySelector('.right-panel .q-card')

    expect(clientCard).toBeTruthy()
    expect(clientCard.classList.contains('panel-inactive')).toBe(false)

    const searchInput = wrapper
      .findAll('input')
      .find((input) => (input.attributes('placeholder') || '').includes('Название файла'))

    await searchInput.setValue('Рязанка')
    await flushPromises()

    // Текст и панельные фильтры применяются вместе, панель не блокируется.
    expect(clientCard.classList.contains('panel-inactive')).toBe(false)

    const clientInput = wrapper
      .findAll('input')
      .find((input) =>
        (input.attributes('placeholder') || '').includes('Поиск клиента или бренда'),
      )

    expect(clientInput.attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })

  it('подсказывает теги и определяет неверную раскладку', async () => {
    const wrapper = await mountShell()

    const searchInput = wrapper
      .findAll('input')
      .find((input) => (input.attributes('placeholder') || '').includes('Название файла'))

    await searchInput.setValue('rjvfhjdf')

    // Подсказки запрашиваются с задержкой 250 мс.
    await new Promise((resolve) => setTimeout(resolve, 320))
    await flushPromises()

    const menuText = document.body.textContent || ''

    expect(menuText).toContain('Похоже, набрано в другой раскладке')
    expect(menuText).toContain('комарова')
    expect(menuText).toContain('Рязанка')

    const suggestion = [...document.querySelectorAll('.q-menu .q-item')].find(
      (item) => item.textContent.includes('Рязанка'),
    )

    expect(suggestion).toBeTruthy()

    // Клик по пункту меню в happy-dom не доходит до обработчика Quasar —
    // вызываем тот же метод, который привязан к пункту.
    wrapper.findComponent(PhotosGrid).vm.pickSuggestion({
      value: 'Рязанка',
      kind: 'brand',
    })
    await flushPromises()

    // Подсказка — это точный фильтр, а не текст запроса: «СТС» не должен
    // находить «Ростсельмаш» как подстроку адреса.
    const photoRequests = urls.filter((url) => url.includes('/v1/photos?'))
    const last = new URL(photoRequests[photoRequests.length - 1], 'http://localhost')
    expect(last.searchParams.get('brand')).toBe('Рязанка')
    expect(last.searchParams.get('q')).toBe(null)

    wrapper.unmount()
  })

  it('верхняя панель: подборки между разделителями, «Видео» — того же вида', async () => {
    const wrapper = await mountShell()
    const html = wrapper.html()

    // Одинаковая подпись и выравнивание: главный экран — первая подборка.
    const labels = wrapper
      .findAll('.header-group')
      .map((button) => button.text().replace(/\s+/g, ' ').trim())

    expect(labels).toEqual([
      'Видеоэкраны',
      'Р-н-Д 6х3',
      'Города области',
      'Область и трассы 6х3',
      'Р-н-Д малые форматы',
      'Видео',
    ])

    // Разделители по краям блока подборок: слева «Обновление базы», справа «Видео».
    expect(wrapper.findAll('.header-divider').length).toBe(2)
    expect(html.indexOf('header-divider')).toBeLessThan(html.indexOf('header-groups'))
    expect(html.indexOf('header-groups')).toBeLessThan(html.lastIndexOf('header-divider'))
    expect(html.indexOf('Обновление базы')).toBeLessThan(html.indexOf('header-divider'))

    wrapper.unmount()
  })

  it('«Видеоэкраны» фильтрует грид, «Видео» открывает галерею', async () => {
    const wrapper = await mountShell()
    const photos = usePhotosStore()
    const button = (label) =>
      wrapper
        .findAll('.header-group')
        .find((item) => item.text().replace(/\s+/g, ' ').trim() === label)

    // По умолчанию активен главный экран, и фильтр уже уходит в запрос.
    expect(button('Видеоэкраны').classes()).toContain('header-group--active')
    expect(urls.some((url) => url.includes('group=screens'))).toBe(true)

    await button('Города области').trigger('click')
    await flushPromises()

    expect(photos.group).toBe('cities')
    expect(urls.some((url) => url.includes('group=cities'))).toBe(true)
    expect(button('Города области').classes()).toContain('header-group--active')
    expect(button('Видеоэкраны').classes()).not.toContain('header-group--active')

    // «Видео» — такая же кнопка и подсвечивается на своей странице.
    await button('Видео').trigger('click')
    await flushPromises()

    expect(calls.some((path) => path.endsWith('/v1/videos'))).toBe(true)
    expect(button('Видео').classes()).toContain('header-group--active')
    expect(button('Города области').classes()).not.toContain('header-group--active')

    wrapper.unmount()
  })

  it('переключает верхнюю кнопку на отдельную видеогалерею', async () => {
    const wrapper = await mountShell()
    // Вкладка фото теперь тоже начинается с «Видеоэкраны…» — отличаем по тексту.
    const videosTab = wrapper
      .findAll('a')
      .find((item) => {
        const text = item.text()
        return text.includes('Видео') && !text.includes('экраны')
      })

    expect(videosTab).toBeTruthy()
    await videosTab.trigger('click')
    await flushPromises()

    expect(calls.some((path) => path.endsWith('/v1/videos'))).toBe(true)
    expect(wrapper.text()).toContain('Видео не найдено')
    wrapper.unmount()
  })

  it('после входа сразу открывает галерею с фотографиями', async () => {
    installFetch({ loggedIn: false })

    const wrapper = await mountShell()

    // Экран входа.
    expect(wrapper.text()).toContain('Войти')
    expect(wrapper.text()).toContain('Гостевой доступ')
    expect(wrapper.text()).toContain('альбион')
    expect(wrapper.text()).toContain('Настройки гостя между входами не сохраняются')

    const inputs = wrapper.findAll('input')

    await inputs[0].setValue('Администратор')
    await inputs[1].setValue('secret')

    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Войти'))
      .trigger('click')

    await flushPromises()

    expect(calls).toContain('/api/v1/auth/login')
    // Сразу после входа оболочка обязана запросить фотографии.
    expect(calls.some((path) => path.endsWith('/v1/photos'))).toBe(true)
    expect(calls).toContain('/api/v1/stats')

    wrapper.unmount()
  })

  it('переключатель режима адреса/клиенты живёт в подвале', async () => {
    const wrapper = await mountShell()
    const display = useDisplayStore()

    const square = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '□')

    expect(square).toBeTruthy()
    await square.trigger('click')

    expect(display.addressClientMode).toBe('client')

    wrapper.unmount()
  })

  it('прячет короткое имя адреса в плитке по настройке', async () => {
    installFetch()
    const wrapper = await mountShell()
    await flushPromises()

    expect(wrapper.text()).toContain('Комарова 13')

    const display = useDisplayStore()
    display.tileShowAddressName = false
    await flushPromises()

    // Вместо короткого адреса — реальное имя файла.
    expect(wrapper.text()).not.toContain('Комарова 13')
    expect(wrapper.text()).toContain('photo.jpg')

    display.tileShowAddressName = true
    wrapper.unmount()
  })

  it('показывает прогресс распознавания как «обработано / всего»', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).split('?')[0].endsWith('/v1/qwen/stats')) {
        return json({
          photos: 56870,
          processed: 12383,
          remaining: 44487,
          jobs: { pending: 4211, running: 2, paused: 0 },
          batch: {
            title: 'QWEN: дозаполнение 2026-08-01 — 2026-11-01',
            status: 'RUNNING',
            total: 16597,
            done: 12383,
            failed: 1,
          },
        })
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    const header = wrapper.find('header').text()
    // Обработано / всего, причём пропущенное считается обработанным — иначе
    // счётчик застревает на «16594 / 16597». Сколько именно пропущено, видно
    // рядом.
    expect(header).toContain('Описание 12384 / 16597 (пропущено 1)')
    wrapper.unmount()
  })

  it('после последнего этапа в шапке остаётся только «База обновлена»', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).split('?')[0].endsWith('/v1/qwen/stats')) {
        return json({
          photos: 56870,
          processed: 12050,
          remaining: 44820,
          jobs: { pending: 0, running: 0, paused: 0 },
          batch: null,
        })
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    // Очередь пуста — данных о процессах в шапке нет: ни «Описание 12050», ни
    // мигающей точки. Остаётся состояние «База обновлена» с датой.
    const header = wrapper.find('header').text()

    expect(header).not.toContain('12050')
    expect(header).not.toContain('Описание')

    wrapper.unmount()
  })

  it('при сбое /auth/me показывает вход с причиной и повтором', async () => {
    installFetch()
    const baseFetch = global.fetch
    let failNext = true

    global.fetch = vi.fn(async (url, options) => {
      if (String(url).split('?')[0].endsWith('/v1/auth/me') && failNext) {
        return json({ detail: 'boom' }, 500)
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    // Открытый режим не включается сам: виден экран входа, галерея не смонтирована.
    expect(wrapper.text()).toContain('Вход')
    expect(wrapper.text()).toContain('Нет связи с сервером')
    expect(wrapper.find('.photos-page').exists()).toBe(false)

    // Сервер ответил — «Повторить» пускает в приложение.
    failNext = false
    const retry = wrapper.findAll('button').find((b) => b.text().includes('Повторить'))
    expect(retry).toBeTruthy()
    await retry.trigger('click')
    await flushPromises()

    expect(wrapper.text()).not.toContain('Нет связи с сервером')
    expect(wrapper.find('.photos-page').exists()).toBe(true)
    wrapper.unmount()
  })

  it('при открытом режиме сервера входа не требует', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).split('?')[0].endsWith('/v1/auth/me')) {
        return json({ user: null, auth_enabled: false })
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Нет связи с сервером')
    expect(wrapper.find('.photos-page').exists()).toBe(true)
    wrapper.unmount()
  })

  it('показывает кнопку, когда на сервере уже другая сборка', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).endsWith('/build.json')) {
        return { ok: true, status: 200, json: async () => ({ build: '01.01, 00:00' }) }
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    expect(wrapper.find('footer').text()).toContain('Доступна новая сборка')
    wrapper.unmount()
  })

  it('молчит, когда метка совпадает с серверной', async () => {
    installFetch()
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).endsWith('/build.json')) {
        // __APP_BUILD__ в тестовой сборке — '—'.
        return { ok: true, status: 200, json: async () => ({ build: '—' }) }
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    expect(wrapper.find('footer').text()).not.toContain('Доступна новая сборка')
    wrapper.unmount()
  })
})
