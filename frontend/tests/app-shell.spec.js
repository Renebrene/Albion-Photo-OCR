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
import Technical from '../src/pages/Technical.vue'
import { setToken } from '../src/api/client'

const calls = []

// Уведомления в тестах не нужны, а их отсутствие прячет настоящую ошибку.
Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch({ loggedIn = true } = {}) {
  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url).split('?')[0]
    const method = (options.method || 'GET').toUpperCase()

    calls.push(path)

    if (path.endsWith('/v1/auth/me')) {
      return json({
        user: loggedIn
          ? { user_id: 1, name: 'Администратор', role: 'Администратор' }
          : null,
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

    if (path.endsWith('/v1/selection')) return json({ state: {} })

    if (path.endsWith('/v1/stats')) {
      return json({ photos: 1, addresses: 1, clients: 0, last_photo_at: null })
    }

    return json({ items: [] })
  })
}

beforeEach(() => {
  calls.length = 0

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
  async function mountShell() {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: PhotosGrid },
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

    // Подпись плитки: алиас адреса, имя файла, дата съёмки с весом, клиент.
    const caption = wrapper.text()

    expect(caption).toContain('Комарова 13')
    expect(caption).toContain('photo.jpg')
    expect(caption).toContain('17.07.2025 · 4.0 МБ')
    expect(caption).toContain('Клиент А')

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

    // Строка 1: адрес, дата съёмки и вес. Строка 2: имя файла, клиент, бренд.
    expect(text).toContain('Комарова 13 · 17.07.2025 · 4.0 МБ')
    expect(text).toContain('photo.jpg, Клиент А, Бренд Б')

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
