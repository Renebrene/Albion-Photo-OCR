// Проверка папки INGEST: фото + видео, расширения, итоговый баннер, лог
// ошибок, выбор папки на сервере и запуск сканирования.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

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

function installFetch({ scan = scanWithErrors } = {}) {
  const calls = []

  global.fetch = vi.fn(async (url, options = {}) => {
    const path = String(url)
    calls.push({ path, method: options.method || 'GET' })

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

    await clickButton(wrapper, 'Сканировать')

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
