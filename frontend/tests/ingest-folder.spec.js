// Проверка папки INGEST: фото + видео, расширения, итоговый баннер, лог
// ошибок, выбор папки на сервере и запуск сканирования.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QSelect, Quasar } from 'quasar'

import IngestFolder from '../src/components/IngestFolder.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const folderState = {
  configured: '/photos',
  exists: true,
  photos: 2,
  videos: 0,
  bytes: 30,
  photo_bytes: 30,
  video_bytes: 0,
  extensions: { '.jpg': 2 },
  problem_count: 0,
  problems: [],
  preliminary: true,
  truncated: false,
  timed_out: false,
}

const scanWithErrors = {
  ...folderState,
  path: '/photos',
  photos: 3,
  videos: 2,
  media_files: 5,
  bytes: 100,
  photo_bytes: 40,
  video_bytes: 60,
  extensions: { '.jpg': 3, '.mov': 1, '.mp4': 1 },
  problem_count: 1,
  problems: [{ filename: 'empty.mp4', reason: 'файл пуст' }],
}

function installFetch({ scan = scanWithErrors, previews = null } = {}) {
  const calls = []

  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url)
    calls.push({
      path,
      method: options.method || 'GET',
      body: options.body ? JSON.parse(options.body) : null,
    })

    if (path.includes('/v1/previews/backfill')) {
      return json(previews || { selected: 3, queued: 3, already_active: 0 })
    }
    if (path.includes('/v1/ingest/scan')) return json(scan)
    if (path.includes('/v1/ingest/run')) return json({ job_id: 42 })
    if (path.includes('/v1/fingerprints/browse')) {
      return json({
        path: '/photos',
        parent: null,
        dirs: [{ name: 'sub', path: '/photos/sub', photos: 3 }],
        photos: 2,
      })
    }
    if (options.method === 'PUT') return json(folderState)
    return json(folderState)
  })

  return calls
}

function mountFolder() {
  return mount(IngestFolder, {
    attachTo: document.body,
    global: { plugins: [Quasar] },
  })
}

async function clickButton(wrapper, label) {
  const button = wrapper
    .findAll('button')
    .find((item) => item.text().includes(label))

  if (button) {
    await button.trigger('click')
    await flushPromises()
    return
  }

  // Кнопки в q-dialog рендерятся порталом в document.body.
  const domButton = [...document.querySelectorAll('button')].find((item) =>
    (item.textContent || '').includes(label),
  )

  expect(domButton, `кнопка «${label}»`).toBeTruthy()
  domButton.click()
  await flushPromises()
}

beforeEach(() => vi.restoreAllMocks())
afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

describe('папка INGEST', () => {
  it('показывает статистику справа и баннер с ошибками после проверки', async () => {
    installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Проверить')

    const text = wrapper.text()
    expect(text).toContain('Статистика папки')
    expect(text).toContain('Фото')
    expect(text).toContain('3')
    expect(text).toContain('Видео')
    expect(text).toContain('.mp4: 1')
    expect(text).toContain('ОК, но есть ошибки: 1')
    expect(text).toContain('«Сортировка»')

    // Лог ошибок открывается отдельным окном.
    await clickButton(wrapper, 'Лог ошибок')
    expect(document.body.textContent).toContain('empty.mp4')
    expect(document.body.textContent).toContain('файл пуст')
  })

  it('показывает «Всё ОК», когда ошибок нет', async () => {
    installFetch({ scan: { ...folderState, photos: 5, videos: 1 } })
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Проверить')

    expect(wrapper.text()).toContain('Всё ОК')
    expect(wrapper.text()).toContain('Переходите к этапу «Сортировка»')
  })

  it('сканирование активно сразу после выбора пути', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    const input = wrapper.find('input')
    await input.setValue('/another-folder')
    await flushPromises()

    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run).toBeTruthy()
  })

  it('выбирает папку во встроенном браузере сервера', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Выбрать на сервере')

    expect(document.body.textContent).toContain('/photos/sub')
    expect(calls.some((call) => call.path.includes('/v1/fingerprints/browse'))).toBe(true)

    await clickButton(wrapper, 'Выбрать эту папку')
    expect(
      calls.some(
        (call) => call.path.includes('/v1/ingest/folder') && call.method === 'PUT',
      ),
    ).toBe(true)
  })
})

// ---- глубина сканирования по времени -------------------------------------
// Тот же выбор «Дата» + «Период…», что и в фильтре Грида; без периода
// запрос уходит ровно таким же, как до появления глубины.

function selectByLabel(wrapper, label) {
  return wrapper
    .findAllComponents(QSelect)
    .find((item) => String(item.props('label')) === label)
}

describe('глубина сканирования по времени', () => {
  it('без периода не отправляет границы и не считает split', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body).toEqual({ path: '/photos' })
  })

  it('«Сегодня» отправляет границы по локальной дате', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'today')
    await flushPromises()
    await clickButton(wrapper, 'Инспектировать')

    const today = new Date()
    const pad = (value) => String(value).padStart(2, '0')
    const expected = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body).toEqual({
      path: '/photos',
      date_from: expected,
      date_to: expected,
      date_mode: 'upload',
    })
  })

  it('режим «Дата съёмки» доезжает до сервера', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Дата').vm.$emit('update:model-value', 'capture')
    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'week')
    await flushPromises()
    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body.date_mode).toBe('capture')
    expect(run.body.date_from).toBeTruthy()
  })

  it('«Период…» без дат ничего не ограничивает', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'custom')
    await flushPromises()
    await clickButton(wrapper, 'Инспектировать')

    const run = calls.find((call) => call.path.includes('/v1/ingest/run'))
    expect(run.body).toEqual({ path: '/photos' })
  })

  it('«Проверить» с периодом показывает счёт вне периода', async () => {
    installFetch({
      scan: {
        ...scanWithErrors,
        excluded_by_period: 4,
        in_period: 1,
        period_applied: true,
      },
    })
    const wrapper = mountFolder()
    await flushPromises()

    await selectByLabel(wrapper, 'Период').vm.$emit('update:model-value', 'today')
    await flushPromises()
    await clickButton(wrapper, 'Проверить')

    expect(wrapper.text()).toContain('В периоде')
    expect(wrapper.text()).toContain('Вне периода')
    expect(wrapper.text()).toContain('4')
  })
})

// ---- пересоздание превью ---------------------------------------------------

describe('пересоздание превью', () => {
  it('ставит задания и сообщает результат', async () => {
    const calls = installFetch()
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Пересоздать превью')

    const call = calls.find((item) => item.path.includes('/v1/previews/backfill'))
    expect(call).toBeTruthy()
    expect(call.method).toBe('POST')
    expect(call.body).toEqual({})
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining('заданий: 3') }),
    )
  })

  it('предупреждает про фото с недоступным оригиналом', async () => {
    installFetch({
      previews: { selected: 2, queued: 2, already_active: 0, originals_missing: 5 },
    })
    const wrapper = mountFolder()
    await flushPromises()

    await clickButton(wrapper, 'Пересоздать превью')

    const notice = Notify.create.mock.calls.at(-1)[0]
    expect(notice.type).toBe('warning')
    expect(notice.message).toContain('Оригинал недоступен у 5 фото')
  })
})
