// Component test: Settings.vue shows QWEN status and disables retry when
// there are no failed photos. Driven by a stubbed global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import Settings from '../src/pages/Settings.vue'

// Quasar's Notify is a plugin singleton; outside a full app it may not be
// installed, so give it a no-op create() for the component to call.
Notify.create = vi.fn()

let stats
let enqueued

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    if (method === 'GET' && path === '/api/v1/qwen/models') {
      return jsonResponse({
        current: 'qwen3-vl:4b-instruct',
        available: [{ name: 'qwen3-vl:4b-instruct', size: 3_000_000_000 }],
      })
    }

    if (method === 'GET' && path === '/api/v1/qwen/stats') {
      return jsonResponse(stats)
    }

    if (method === 'POST' && path === '/api/v1/jobs/qwen') {
      enqueued.push(JSON.parse(options.body))
      return jsonResponse({ jobs: 2, first_job_id: 1 }, 202)
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })
}

function mountSettings() {
  return mount(Settings, { global: { plugins: [Quasar] } })
}

beforeEach(() => {
  enqueued = []
  stats = { counts: { DONE: 256 }, failed_photo_ids: [] }
  installFetch()
})

afterEach(() => {
  delete global.fetch
})

describe('Settings.vue', () => {
  it('renders QWEN status counts', async () => {
    stats = { counts: { DONE: 255, FAILED: 1 }, failed_photo_ids: ['PH_bad'] }

    const wrapper = mountSettings()
    await flushPromises()

    expect(wrapper.text()).toContain('DONE: 255')
    expect(wrapper.text()).toContain('FAILED: 1')
  })

  it('disables retry when there are no failed photos', async () => {
    const wrapper = mountSettings()
    await flushPromises()

    const retry = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Повторить для упавших'))

    expect(retry).toBeTruthy()
    expect(retry.attributes('disabled')).toBeDefined()
  })

  it('enqueues failed photos when retry is clicked', async () => {
    stats = { counts: { FAILED: 2 }, failed_photo_ids: ['PH_a', 'PH_b'] }

    const wrapper = mountSettings()
    await flushPromises()

    const retry = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Повторить для упавших'))
    expect(retry.text()).toContain('(2)')

    await retry.trigger('click')
    await flushPromises()

    expect(enqueued).toEqual([{ photo_ids: null, only_failed: true }])
  })
})
