// Проверка папки INGEST: фото + видео, расширения, проблемы, запуск только
// после проверки текущего пути.
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

const scanResult = {
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

function mountFolder() {
  global.fetch = vi.fn(async (url, options = {}) => {
    if (String(url).includes('/v1/ingest/scan')) return json(scanResult)
    if (options.method === 'PUT') return json(folderState)
    return json(folderState)
  })

  return mount(IngestFolder, {
    attachTo: document.body,
    global: { plugins: [Quasar] },
  })
}

beforeEach(() => vi.restoreAllMocks())
afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

describe('папка INGEST', () => {
  it('показывает фото, видео, объём, расширения и проблемы после проверки', async () => {
    const wrapper = mountFolder()
    await flushPromises()

    const checkButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Проверить'))
    await checkButton.trigger('click')
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('фото: 3')
    expect(text).toContain('видео: 2')
    expect(text).toContain('проблем: 1')
    expect(text).toContain('.mp4: 1')
    expect(text).toContain('empty.mp4 — файл пуст')
    expect(text).toContain('Проверка предварительная')
  })

  it('не даёт запустить ingest после изменения пути без новой проверки', async () => {
    const wrapper = mountFolder()
    await flushPromises()

    const input = wrapper.find('input')
    await input.setValue('/another-folder')

    const start = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Запустить ingest'))

    expect(start.attributes('disabled')).toBeDefined()
  })
})
