// Отмена умного поиска по файлу: закрытие/очистка не должны оставлять
// невидимый ids-фильтр и не должны применять поздний результат.
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

const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

let store
let cancelCalls
let uploadResponse

function installFetch() {
  cancelCalls = []
  uploadResponse = null

  global.fetch = vi.fn(async (url, options = {}) => {
    const path = new URL(String(url), 'http://localhost').pathname
    const method = (options.method || 'GET').toUpperCase()

    if (method === 'POST' && path.endsWith('/v1/search/media')) {
      return uploadResponse || json({ job_id: 7 })
    }

    if (method === 'POST' && /\/v1\/jobs\/\d+\/cancel$/.test(path)) {
      cancelCalls.push(path)
      return json({ status: 'CANCELLED' })
    }

    if (path.endsWith('/v1/jobs/media-search/7')) {
      return json({
        job_id: 7,
        status: 'DONE',
        result: { photo_ids: ['PH_late'] },
      })
    }

    if (path.endsWith('/v1/photos')) {
      return json({ items: [], next_cursor: null, total: 0 })
    }

    if (path.endsWith('/v1/runs/activity')) {
      return json({ active: null, message: null })
    }

    if (path.endsWith('/v1/qwen/settings')) return json({ models: {} })

    return json({ items: [] })
  })
}

async function mountGrid() {
  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(Host, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()
  await nextTick()

  store = usePhotosStore()
  return wrapper
}

async function chooseFile(wrapper) {
  const input = wrapper.find('input[type=file]')
  const file = new File(['jpeg'], 'billboard.jpg', { type: 'image/jpeg' })

  Object.defineProperty(input.element, 'files', {
    value: [file],
    configurable: true,
  })

  await input.trigger('change')
  await flushPromises()
  await nextTick()
}

function buttonWithText(wrapper, text) {
  return wrapper
    .findAll('button')
    .find((button) => button.text().includes(text))
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

describe('отмена умного поиска', () => {
  it('очистка файла отменяет job и не применяет поздний ids-фильтр', async () => {
    let resolveUpload

    uploadResponse = new Promise((resolve) => {
      resolveUpload = resolve
    })

    const wrapper = await mountGrid()
    await chooseFile(wrapper)

    const run = buttonWithText(wrapper, 'ИИ-поиск')
    expect(run).toBeTruthy()
    await run.trigger('click')
    await nextTick()

    // Ответ upload ещё не пришёл — очищаем выбранный файл.
    const chip = wrapper.findComponent({ name: 'QChip' })
    expect(chip.exists()).toBe(true)
    chip.vm.$emit('remove')
    await flushPromises()

    resolveUpload(json({ job_id: 7 }))
    await flushPromises()
    await nextTick()

    expect(cancelCalls).toEqual(['/api/v1/jobs/7/cancel'])
    expect(store.nlIds).toEqual([])
    expect(wrapper.text()).not.toContain('billboard.jpg')
    wrapper.unmount()
  })

  it('кнопка «Стоп» останавливает опрос и не применяет результат', async () => {
    const wrapper = await mountGrid()
    await chooseFile(wrapper)

    await buttonWithText(wrapper, 'ИИ-поиск').trigger('click')
    await flushPromises()
    await nextTick()

    const stop = buttonWithText(wrapper, 'Стоп')
    expect(stop).toBeTruthy()
    await stop.trigger('click')
    await flushPromises()

    // Даже если бы опрос продолжился, результат уже не должен примениться.
    await vi.advanceTimersByTimeAsync(4000)
    await flushPromises()

    expect(cancelCalls).toEqual(['/api/v1/jobs/7/cancel'])
    expect(store.nlIds).toEqual([])
    wrapper.unmount()
  })
})
