// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar, Notify } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import VideosGrid from '../src/pages/VideosGrid.vue'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

const item = {
  video_id: `VI_${'a'.repeat(24)}`,
  filename: 'clip.MP4',
  display_title: 'У входа',
  source_directory: 'проект/объект-1',
  container_format: 'mov,mp4,m4a',
  video_codec: 'h264',
  width: 1920,
  height: 1080,
  duration_seconds: 12.5,
  fps: 25,
  frame_count: 312,
  size_bytes: 5 * 1024 * 1024,
  taken_at: '2026-10-14T08:05:00Z',
  created_at: '2026-10-15T09:15:00Z',
}

let calls
let fetchMock

function response(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

beforeEach(() => {
  item.size_bytes = 5 * 1024 * 1024
  item.duration_seconds = 12.5
  // Флаг ставит только тест недоступного оригинала; остальные — файл на месте.
  item.available = true
  calls = []
  setActivePinia(createPinia())
  // Открытый режим (без аутентификации): спека проверяет полный доступ.
  useSessionStore().authEnabled = false
  global.fetch = fetchMock = vi.fn(async (url, options = {}) => {
    const path = String(url).split('?')[0]
    const method = (options.method || 'GET').toUpperCase()
    calls.push({ path, method, body: options.body })

    if (path.endsWith('/v1/videos') && method === 'GET') {
      return response({ items: [item], next_cursor: null })
    }
    if (path.endsWith('/playback-ticket') && method === 'POST') {
      return response({ url: `/api/v1/videos/${item.video_id}/stream`, expires_at: '2026-10-15T10:00:00Z' })
    }
    if (path.endsWith('/title') && method === 'PUT') {
      return response({ ...item, display_title: JSON.parse(options.body).display_title })
    }
    if (path.endsWith('/transcodes/strong_720p') && method === 'GET') {
      return response({ derivative_id: 12, status: 'DONE', profile: 'strong_720p', progress: { percent: 100 } })
    }
    if (path.endsWith('/transcodes') && method === 'POST') {
      return response({ derivative_id: 12, job_id: 34, status: 'DONE', profile: 'strong_720p' }, 202)
    }
    if (path.endsWith('/storyboard') && method === 'POST') {
      return response({ job_id: 45, status: 'PENDING', frame_count: 8 }, 202)
    }
    if (path.endsWith('/jobs/45') && method === 'GET') {
      return response({ id: 45, status: 'DONE', result: { frames: 8 } })
    }
    if (path.endsWith('/trim') && method === 'POST') {
      return response({ derivative_id: 31, job_id: 55, status: 'PENDING', start_seconds: 0, end_seconds: 12.5 }, 202)
    }
    if (path.endsWith('/trim') && method === 'GET') {
      return response({ derivative_id: 31, job_id: 55, status: 'DONE', start_seconds: 0, end_seconds: 12.5, progress: { percent: 100 } })
    }
    if (path.endsWith('/derivatives/31/download-ticket') && method === 'POST') {
      return response({ url: '/api/v1/videos/trim-download' })
    }
    return response({ detail: `no mock for ${method} ${path}` }, 500)
  })
})

describe('видеогалерея', () => {

  it('помечает видео без оригинала и объясняет это в карточке', async () => {
    item.available = false
    const wrapper = mountPage()
    await flushPromises()

    // Запись осталась, файла нет — видно прямо в плитке.
    expect(wrapper.text()).toContain('файл не найден')

    const detailsButton = wrapper.findAll('button').find((button) => button.html().includes('more_horiz'))
    await detailsButton.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('Оригинал видео недоступен')
    // Билет на воспроизведение не запрашивается: смотреть нечего.
    expect(calls.some((call) => call.path.endsWith('/playback-ticket'))).toBe(false)
    const trimButton = Array.from(document.body.querySelectorAll('button'))
      .find((button) => button.textContent.includes('Обрезать фрагмент'))
    expect(trimButton).toBeTruthy()
    expect(trimButton.disabled).toBe(true)

    wrapper.unmount()
  })

  function mountPage() {
    return mount(VideosGrid, {
      attachTo: document.body,
      global: {
        plugins: [Quasar],
        stubs: {
          AuthImage: true,
          QPage: { template: '<div class="test-page"><slot /></div>' },
        },
      },
    })
  }

  it('показывает filename, title, capture date, duration и MB', async () => {
    const wrapper = mountPage()
    await flushPromises()
    expect(calls.some((call) => call.path.endsWith('/v1/videos'))).toBe(true)
    expect(wrapper.text()).toContain('clip.MP4')
    expect(wrapper.text()).toContain('У входа')
    // Каталог больше не занимает отдельную строку — он в подсказке имени.
    expect(wrapper.find('.video-filename').attributes('title'))
      .toContain('проект/объект-1')
    // Дата, хроно и вес — одной компактной строкой.
    expect(wrapper.text()).toContain('14-10-26')
    expect(wrapper.text()).toContain('12.5 с')
    expect(wrapper.text()).toContain('5.0 МБ')
    expect(wrapper.text()).not.toContain('Выбрать все')

    wrapper.unmount()
  })

  it('гость не видит скачивание, сжатие и редактирование', async () => {
    const session = useSessionStore()
    session.authEnabled = true
    session.user = { name: 'guest', role: 'Гость' }

    const wrapper = mountPage()
    await flushPromises()

    const labels = wrapper.findAll('button').map((button) => button.text())
    expect(labels.some((text) => text.includes('Скачать'))).toBe(false)
    expect(labels.some((text) => text.includes('Сжать'))).toBe(false)

    const detailsButton = wrapper
      .findAll('button')
      .find((button) => button.html().includes('more_horiz'))
    await detailsButton.trigger('click')
    await flushPromises()

    expect(calls.some((call) => call.path.endsWith('/playback-ticket'))).toBe(false)
    expect(document.body.textContent).toContain('Просмотр доступен сотрудникам')
    expect(document.body.querySelector('input[maxlength="300"]')).toBeNull()
    expect(document.body.textContent).not.toContain('Обрезать фрагмент')

    wrapper.unmount()
  })

  it('открывает video detail и сохраняет одно пользовательское название', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const detailsButton = wrapper.findAll('button').find((button) => button.html().includes('more_horiz'))
    expect(detailsButton).toBeTruthy()
    await detailsButton.trigger('click')
    await flushPromises()

    expect(calls.some((call) => call.path.endsWith('/playback-ticket'))).toBe(true)
    const detailsCard = document.body.querySelector('.video-details-page')
    expect(detailsCard).toBeTruthy()
    expect(detailsCard.style.width).toBe('900px')
    expect(detailsCard.style.maxWidth).toBe('calc(100vw - 32px)')
    expect(document.body.querySelector('.q-dialog__inner--maximized')).toBeNull()
    const titleInput = document.body.querySelector('input[maxlength="300"]')
    expect(titleInput).toBeTruthy()
    titleInput.value = 'Камера восточного входа'
    titleInput.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()

    const save = Array.from(document.body.querySelectorAll('button')).find((button) => button.textContent.includes('Сохранить название'))
    expect(save).toBeTruthy()
    save.click()
    await flushPromises()

    const update = calls.find((call) => call.path.endsWith('/title') && call.method === 'PUT')
    expect(JSON.parse(update.body)).toEqual({ display_title: 'Камера восточного входа' })
    expect(wrapper.text()).toContain('Камера восточного входа')

    wrapper.unmount()
  })

  it('в режиме списка показывает title второй строкой', async () => {
    const wrapper = mountPage()
    await flushPromises()
    const listButton = wrapper.findAll('button').find((button) => button.html().includes('view_list'))
    expect(listButton).toBeTruthy()
    await listButton.trigger('click')
    await flushPromises()

    const row = wrapper.find('.video-list-item')
    expect(row.text()).toContain('clip.MP4')
    expect(row.text()).toContain('12.5 с')
    expect(row.text()).toContain('5.0 МБ')
    expect(row.find('.video-list-title').text()).toBe('У входа')

    wrapper.unmount()
  })

  it('opens trim editor, queues a selected range and offers the new clip', async () => {
    const wrapper = mountPage()
    await flushPromises()

    const detailsButton = wrapper.findAll('button').find((button) => button.html().includes('more_horiz'))
    await detailsButton.trigger('click')
    await flushPromises()

    const trimButton = Array.from(document.body.querySelectorAll('button')).find((button) => button.textContent.includes('Обрезать фрагмент'))
    expect(trimButton).toBeTruthy()
    trimButton.click()
    await flushPromises()

    expect(document.body.textContent).toContain('Ключевые кадры')
    expect(calls.some((call) => call.path.endsWith('/storyboard') && call.method === 'POST')).toBe(true)
    expect(document.body.textContent).toContain('Сохранить как новый клип')

    // Slider defaults are 0..duration and remain valid.
    const startField = Array.from(document.body.querySelectorAll('.q-field')).find((field) => field.textContent.includes('Начало'))
    expect(startField).toBeTruthy()
    const saveTrim = Array.from(document.body.querySelectorAll('button')).find((button) => button.textContent.includes('Сохранить как новый клип'))
    saveTrim.click()
    await flushPromises()

    const trimCall = calls.find((call) => call.path.endsWith('/trim') && call.method === 'POST')
    expect(trimCall).toBeTruthy()
    expect(JSON.parse(trimCall.body)).toEqual({ start_seconds: 0, end_seconds: 12.5 })
    expect(document.body.textContent).toContain('Скачать клип')
    wrapper.unmount()
  })

  it('keeps large videos visible and playable but disables editing', async () => {
    item.size_bytes = 1_610_612_737
    const wrapper = mountPage()
    await flushPromises()
    expect(wrapper.text()).toContain('clip.MP4')
    expect(wrapper.find('.video-card .q-checkbox').exists()).toBe(true)
    const detailsButton = wrapper.findAll('button').find((button) => button.html().includes('more_horiz'))
    await detailsButton.trigger('click')
    await flushPromises()
    expect(calls.some((call) => call.path.endsWith('/playback-ticket'))).toBe(true)
    const trimButton = Array.from(document.body.querySelectorAll('button')).find((button) => button.textContent.includes('Обрезать фрагмент'))
    expect(trimButton.disabled).toBe(true)
    wrapper.unmount()
    item.size_bytes = 5 * 1024 * 1024
  })

  it('disables editing above ten minutes but leaves playback available', async () => {
    item.duration_seconds = 600.1
    const wrapper = mountPage()
    await flushPromises()
    const detailsButton = wrapper.findAll('button').find((button) => button.html().includes('more_horiz'))
    await detailsButton.trigger('click')
    await flushPromises()
    expect(calls.some((call) => call.path.endsWith('/playback-ticket'))).toBe(true)
    const trimButton = Array.from(document.body.querySelectorAll('button')).find((button) => button.textContent.includes('Обрезать фрагмент'))
    expect(trimButton.disabled).toBe(true)
    wrapper.unmount()
  })

  it('queues one H.264 profile and offers its completed derivative', async () => {
    const wrapper = mountPage()
    await flushPromises()
    await wrapper.find('.video-card .q-checkbox').trigger('click')
    await flushPromises()

    const compress = wrapper.findAll('button').find((button) => button.text().includes('Сжать'))
    expect(compress).toBeTruthy()
    await compress.trigger('click')
    await flushPromises()

    const strong = Array.from(document.body.querySelectorAll('.q-item')).find((row) => row.textContent.includes('Сильно'))
    expect(strong).toBeTruthy()
    strong.click()
    await flushPromises()

    const queued = calls.find((call) => call.path.endsWith('/transcodes') && call.method === 'POST')
    expect(JSON.parse(queued.body)).toEqual({ profile: 'strong_720p' })
    expect(wrapper.text()).toContain('Скачать сжатое')
    wrapper.unmount()
  })
})

describe('прогресс конвертации не привязан к выделению', () => {
  const second = {
    ...item,
    video_id: `VI_${'c'.repeat(24)}`,
    filename: 'ворота.MP4',
    display_title: 'У ворот',
  }

  function mountPage() {
    return mount(VideosGrid, {
      attachTo: document.body,
      global: {
        plugins: [Quasar],
        stubs: {
          AuthImage: true,
          QPage: { template: '<div class="test-page"><slot /></div>' },
        },
      },
    })
  }

  it('показывает идущее сжатие и «Отмена» после выбора другого видео', async () => {
    let cancelled = false
    const calls = []

    global.fetch = vi.fn(async (url, options = {}) => {
      const path = String(url).split('?')[0]
      const method = (options.method || 'GET').toUpperCase()
      calls.push({ path, method })

      if (path.endsWith('/v1/videos') && method === 'GET') {
        return response({ items: [item, second], next_cursor: null })
      }
      if (path.endsWith('/transcodes') && method === 'POST') {
        return response({ derivative_id: 21, job_id: 77, status: 'PENDING', profile: 'standard_1080p' }, 202)
      }
      if (path.endsWith('/transcodes/standard_1080p') && method === 'GET') {
        return response(
          cancelled
            ? { derivative_id: 21, job_id: 77, status: 'CANCELLED', profile: 'standard_1080p' }
            : {
                derivative_id: 21,
                job_id: 77,
                status: 'RUNNING',
                profile: 'standard_1080p',
                progress: { percent: 40 },
              },
        )
      }
      if (path.endsWith('/jobs/77/cancel') && method === 'POST') {
        cancelled = true
        return response({ ok: true })
      }
      return response({ detail: `no mock for ${method} ${path}` }, 500)
    })

    const wrapper = mountPage()
    await flushPromises()

    const checkboxes = wrapper.findAll('.video-card .q-checkbox')
    expect(checkboxes.length).toBe(2)
    await checkboxes[1].trigger('click')
    await flushPromises()

    const compress = wrapper.findAll('button').find((button) => button.text().includes('Сжать'))
    await compress.trigger('click')
    await flushPromises()

    const standard = Array.from(document.body.querySelectorAll('.q-item')).find((row) =>
      row.textContent.includes('Стандартно'),
    )
    standard.click()
    await flushPromises()

    // Задание идёт по второму видео.
    expect(wrapper.find('.video-transcode-status').text()).toContain('ворота.MP4')
    expect(wrapper.find('.video-transcode-status').text()).toContain('Стандартно · 1080p')
    expect(wrapper.find('.video-transcode-status').text()).toContain('RUNNING')
    // Сырой код профиля пользователю не показываем.
    expect(wrapper.find('.video-transcode-status').text()).not.toContain('standard_1080p')

    // Выбираем другое видео: блок и «Отмена» остаются на месте.
    await checkboxes[0].trigger('click')
    await flushPromises()

    const status = wrapper.find('.video-transcode-status')
    expect(status.exists()).toBe(true)
    expect(status.text()).toContain('ворота.MP4')

    const cancel = status.findAll('button').find((button) => button.text().includes('Отмена'))
    expect(cancel).toBeTruthy()
    await cancel.trigger('click')
    await flushPromises()

    expect(calls.some((call) => call.path.endsWith('/jobs/77/cancel'))).toBe(true)
    expect(wrapper.find('.video-transcode-status').text()).toContain('CANCELLED')

    wrapper.unmount()
  })
})

describe('смена фильтра во время загрузки', () => {
  it('сброс не теряется, если страница ещё грузится', async () => {
    const { useVideosStore } = await import('../src/stores/videos')
    const { createPinia: makePinia, setActivePinia: activate } = await import('pinia')

    activate(makePinia())

    const store = useVideosStore()
    const calls = []
    let resolveFirst

    global.fetch = vi.fn((url) => {
      const path = String(url).split('?')[0]
      calls.push(String(url))

      if (calls.length === 1) {
        // Первый запрос «висит»: пользователь в это время меняет фильтр.
        return new Promise((resolve) => {
          resolveFirst = () =>
            resolve(response({ items: [{ ...item, video_id: 'VI_' + 'b'.repeat(24) }], next_cursor: null }))
        })
      }

      return Promise.resolve(response({ items: [item], next_cursor: null }))
    })

    const pending = store.loadPage()
    store.query = 'Малиновского'
    const reset = store.loadPage({ reset: true })

    resolveFirst()
    await pending
    await reset

    // Новый фильтр применился: список — результат второго запроса.
    expect(store.items.map((row) => row.video_id)).toEqual([item.video_id])
    expect(calls[1]).toContain(encodeURIComponent('Малиновского'))
  })
})

describe('обновление после конвертации', () => {
  it('перечитывает открытые страницы, не сбрасывая список к первой', async () => {
    const { useVideosStore } = await import('../src/stores/videos')
    const { createPinia: makePinia, setActivePinia: activate } = await import('pinia')

    activate(makePinia())

    const rows = Array.from({ length: 120 }, (_, index) => ({
      ...item,
      video_id: `VI_${String(index).padStart(24, '0')}`,
    }))

    const pages = [
      { items: rows.slice(0, 50), next_cursor: 'c2' },
      { items: rows.slice(50, 100), next_cursor: 'c3' },
      { items: rows.slice(100, 120), next_cursor: null },
    ]

    global.fetch = vi.fn(async (url) => {
      const cursor = new URL(String(url), 'http://localhost').searchParams.get('cursor')

      if (cursor === 'c2') return response(pages[1])
      if (cursor === 'c3') return response(pages[2])

      return response(pages[0])
    })

    const store = useVideosStore()
    await store.loadPage({ reset: true })
    await store.loadPage()

    expect(store.items).toHaveLength(100)

    await store.refreshLoaded()

    // Обе страницы снова на месте: сброс к первой отбрасывал прокрутку.
    expect(store.items.length).toBeGreaterThanOrEqual(100)
  })
})
