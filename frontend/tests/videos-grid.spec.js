// @vitest-environment happy-dom

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar, Notify } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import VideosGrid from '../src/pages/VideosGrid.vue'

Notify.create = vi.fn()

const item = {
  video_id: `VI_${'a'.repeat(24)}`,
  filename: 'clip.MP4',
  display_title: 'У входа',
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
  calls = []
  setActivePinia(createPinia())
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
    return response({ detail: `no mock for ${method} ${path}` }, 500)
  })
})

describe('видеогалерея', () => {
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
    expect(wrapper.text()).toContain('14-10-26')
    expect(wrapper.text()).toContain('12.5 с / 5.0 МБ')
    expect(wrapper.text()).not.toContain('Выбрать все')

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
})
