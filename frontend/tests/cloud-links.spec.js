// Cloud export dialog and the owner/all links panel.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import CloudLinkButton from '../src/components/CloudLinkButton.vue'
import MediaLinksPanel from '../src/components/MediaLinksPanel.vue'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function mountCloud() {
  return mount(CloudLinkButton, {
    attachTo: document.body,
    props: { photoIds: ['PH_' + 'a'.repeat(24)] },
    global: { plugins: [Quasar] },
  })
}

const ready = {
  link_id: 5,
  media_kind: 'photo',
  media_id: 'PH_' + 'a'.repeat(24),
  status: 'READY',
  url: 'https://files.example.ru/a.jpg',
  expires_at: '2027-01-15T10:00:00Z',
  error_message: null,
}

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('облачные ссылки', () => {
  it('ставит загрузку в очередь и показывает готовую ссылку', async () => {
    global.fetch = vi.fn(async () => json({ items: [ready], job_ids: [12], configured: true }, 202))
    const wrapper = mountCloud()

    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(global.fetch).toHaveBeenCalledTimes(1)
    expect(global.fetch.mock.calls[0][0]).toContain('/v1/media-links')
    expect(document.body.textContent).toContain('Ссылки Albion')
    const linkInput = document.body.querySelector('input')
    expect(linkInput?.value).toBe('https://files.example.ru/a.jpg')
    wrapper.unmount()
  })

  it('обновляет PENDING на FAILED и показывает безопасную ошибку', async () => {
    const pending = { ...ready, status: 'PENDING', url: null, expires_at: null }
    const failed = { ...pending, status: 'FAILED', error_message: 'Albion отклонил API-ключ' }
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce(json({ items: [pending], job_ids: [12], configured: true }, 202))
      .mockResolvedValueOnce(json({ items: [failed], configured: true }))

    const wrapper = mountCloud()
    await wrapper.find('button').trigger('click')
    await flushPromises()

    const pollUrl = new URL(global.fetch.mock.calls[1][0], 'http://localhost')
    expect(pollUrl.searchParams.get('include_unready')).toBe('true')
    expect(pollUrl.searchParams.get('all')).toBe('false')
    expect(document.body.textContent).toContain('FAILED')
    expect(document.body.textContent).toContain('Albion отклонил API-ключ')
    wrapper.unmount()
  })

  it('не отправляет пустой выбор', async () => {
    global.fetch = vi.fn()
    const wrapper = mount(CloudLinkButton, {
      props: { photoIds: [], videoIds: [] },
      global: { plugins: [Quasar] },
    })
    await wrapper.find('button').trigger('click')
    expect(global.fetch).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})

describe('панель ссылок', () => {
  it('показывает предупреждение, если Albion не настроен', async () => {
    global.fetch = vi.fn(async () => json({ items: [], configured: false }))
    const wrapper = mount(MediaLinksPanel, { global: { plugins: [Quasar] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Albion не настроен')
    expect(wrapper.text()).toContain('Пока нет действующих ссылок.')
    wrapper.unmount()
  })

  it('в режиме all показывает владельца ссылки', async () => {
    global.fetch = vi.fn(async () => json({
      items: [{ ...ready, owner_name: 'Администратор', created_at: '2026-10-17T09:00:00Z' }],
      configured: true,
    }))
    const wrapper = mount(MediaLinksPanel, {
      props: { all: true },
      global: { plugins: [Quasar] },
    })
    await flushPromises()

    expect(global.fetch.mock.calls[0][0]).toContain('all=true')
    expect(wrapper.text()).toContain('Администратор')
    expect(wrapper.text()).toContain('https://files.example.ru/a.jpg')
    wrapper.unmount()
  })

  it('после трёх сбоев опроса показывает «статус неизвестен» и повтор', async () => {
    const pending = { ...ready, status: 'PENDING', url: null }
    let polls = 0

    global.fetch = vi.fn(async (url, options = {}) => {
      const method = (options.method || 'GET').toUpperCase()

      if (method === 'POST') {
        return json({ items: [pending], job_ids: [12], configured: true }, 202)
      }

      polls += 1
      // Опрос падает: раньше это навсегда останавливало отслеживание.
      throw new Error(`network ${polls}`)
    })

    vi.useFakeTimers()
    const wrapper = mountCloud()

    await wrapper.find('button').trigger('click')
    await flushPromises()

    for (let i = 0; i < 3; i += 1) {
      await vi.advanceTimersByTimeAsync(2100)
      await flushPromises()
    }

    expect(polls).toBeGreaterThanOrEqual(3)
    expect(document.body.textContent).toContain('Проверить ещё раз')
    expect(document.body.textContent).toContain('Статус неизвестен')

    wrapper.unmount()
    vi.useRealTimers()
  })
})
