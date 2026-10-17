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

const calls = []
const urls = []

// Уведомления в тестах не нужны, а их отсутствие прячет настоящую ошибку.
Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch({
  loggedIn = true,
  role = 'Администратор',
  photoPages = null,
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
            taken_at: '2025-07-17 11:43:19',
            size_bytes: 4194304,
          },
        ],
        next_cursor: null,
      })
    }

    if (path.endsWith('/v1/photos/archive') && method === 'POST') {
      return {
        ok: true,
        status: 200,
        blob: async () => new Blob(['zip-bytes'], { type: 'application/zip' }),
      }
    }

    if (path.endsWith('/v1/selection')) return json({ state: {} })

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
      return json({ photos: 1, videos: 0, addresses: 1, clients: 0, last_photo_at: null, last_video_at: null })
    }

    if (path.endsWith('/v1/media/statistics')) return json({ photos: 1, videos: 0, months: [] })

    return json({ items: [] })
  })
}

beforeEach(() => {
  calls.length = 0
  urls.length = 0

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
  async function mountShell({ role = null } = {}) {
    // Роль задаётся до монтирования: /auth/me отвечает уже от её имени.
    if (role) installFetch({ role })

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
    expect(caption).toContain('17.07.2025 · 4.0 МБ')
    expect(caption).toContain('Клиент А · Бренд Б')

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

    // Строка 1: адрес, дата съёмки и вес. Строка 2: имя файла и клиент/бренд.
    expect(text).toContain('Комарова 13 · 17.07.2025 · 4.0 МБ')
    expect(text).toContain('photo.jpg')
    expect(text).toContain('Клиент А · Бренд Б')

    wrapper.unmount()
  })

  it('ZIP собирает выбранные фото одним архивом', async () => {
    Notify.create.mockClear()
    global.URL.createObjectURL = vi.fn(() => 'blob:zip')
    global.URL.revokeObjectURL = vi.fn()

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

  it('при входе показывает все фото без старых выделений', async () => {
    installFetch()

    // Сервер мог сохранить выделение от прошлой сессии — оно игнорируется.
    const baseFetch = global.fetch
    global.fetch = vi.fn(async (url, options) => {
      if (String(url).includes('/v1/selection')) {
        return json({ state: { selected: ['78_v33'] } })
      }
      return baseFetch(url, options)
    })

    const wrapper = await mountShell()
    await flushPromises()

    const photosCall = urls.find((url) => url.includes('/v1/photos?'))
    expect(photosCall).toBeTruthy()
    expect(photosCall).not.toContain('address=')
    expect(photosCall).not.toContain('client=')
    expect(photosCall).not.toContain('q=')

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

    expect(wrapper.text()).toContain('Фотогалерея')
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

  it('Гость видит грид, но без поиска по файлу, скачивания и техраздела', async () => {
    const wrapper = await mountShell({ role: 'Гость' })
    const html = wrapper.html()

    // Разрешено: грид, фильтры, текстовая строка поиска, видео.
    expect(wrapper.text()).toContain('Фотогалерея')
    expect(wrapper.text()).toContain('Видео')
    expect(
      wrapper.find('input[placeholder*="Название файла"]').exists(),
    ).toBe(true)

    // Запрещено: поиск по фото/видео, скачивание, подборки, техраздел.
    expect(html).not.toContain('photo_camera')
    expect(wrapper.text()).not.toContain('Скачать')
    expect(wrapper.text()).not.toContain('В подборку')
    expect(html).not.toContain('/technical')

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

  it('во время текстового поиска панель клиентов/брендов неактивна', async () => {
    const wrapper = await mountShell()

    const clientCard = document.querySelector('.right-panel .q-card')

    expect(clientCard).toBeTruthy()
    expect(clientCard.classList.contains('panel-inactive')).toBe(false)

    const searchInput = wrapper
      .findAll('input')
      .find((input) => (input.attributes('placeholder') || '').includes('Название файла'))

    await searchInput.setValue('Рязанка')
    await flushPromises()

    expect(clientCard.classList.contains('panel-inactive')).toBe(true)

    // Очистка возвращает панель в строй.
    await searchInput.setValue('')
    await flushPromises()

    expect(clientCard.classList.contains('panel-inactive')).toBe(false)

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
    wrapper.findComponent(PhotosGrid).vm.pickSuggestion('Рязанка')
    await flushPromises()

    const photoRequests = urls.filter((url) => url.includes('/v1/photos?'))
    expect(new URL(photoRequests[photoRequests.length - 1], 'http://localhost').searchParams.get('q'))
      .toBe('Рязанка')

    wrapper.unmount()
  })

  it('переключает верхнюю кнопку на отдельную видеогалерею', async () => {
    const wrapper = await mountShell()
    const videosTab = wrapper.findAll('a').find((item) => item.text().includes('Видео'))

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
})
