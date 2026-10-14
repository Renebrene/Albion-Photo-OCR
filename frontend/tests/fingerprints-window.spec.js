// Component test: the fingerprint management window renders the registry,
// syncs with the disk and shows the version journal. Stubbed global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import FingerprintsList from '../src/components/FingerprintsList.vue'
import { setToken } from '../src/api/client'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

let registry
let versions
let syncCalls
let updates
let imageCalls

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    // The preview goes through the authenticated image loader, not an <img>.
    if (method === 'GET' && path.endsWith('/preview')) {
      imageCalls.push({
        url: String(url),
        auth: (options.headers || {}).Authorization || '',
      })
      return {
        ok: true,
        status: 200,
        blob: async () => new Blob([new Uint8Array([0xff, 0xd8, 0xff])]),
      }
    }

    if (method === 'GET' && path.endsWith('/v1/fingerprints/browse')) {
      // The root of the picker: a folder that has no photos directly in it.
      return jsonResponse({
        path: null,
        parent: null,
        photos: 0,
        dirs: [{ name: '/home/alexice', path: '/home/alexice', photos: 0 }],
      })
    }

    if (method === 'GET' && path.endsWith('/v1/fingerprints/registry')) {
      return jsonResponse({ items: registry })
    }

    if (method === 'POST' && path.endsWith('/v1/fingerprints/sync')) {
      syncCalls.push(path)
      return jsonResponse({
        on_disk: registry.length,
        created: [],
        updated: [],
        versions_added: [],
      })
    }

    if (method === 'GET' && path.endsWith('/versions')) {
      return jsonResponse({ items: versions })
    }

    if (method === 'PUT' && path.includes('/v1/fingerprints/registry/')) {
      updates.push(JSON.parse(options.body))
      return jsonResponse(registry[0])
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })
}

function mountWindow() {
  return mount(FingerprintsList, { global: { plugins: [Quasar] } })
}

beforeEach(() => {
  syncCalls = []
  updates = []
  imageCalls = []
  versions = [
    {
      version_id: 1,
      algorithm_version: '3.3',
      images_count: 81,
      image_names: ['78_001.JPG', '78_002.JPG'],
      source_folder: null,
      is_current: true,
      created_at: '2026-10-14T10:00:00',
      recreated_at: null,
    },
  ]
  registry = [
    {
      fingerprint_id: '78_v33',
      display_name: '',
      // Name resolved by the API: no manual name, so the address alias.
      name: 'Мира 1',
      description: '',
      algorithm_version: '3.3',
      model: 'dinov2_vitb14',
      dimension: 768,
      images_count: 81,
      source_folder: null,
      active: true,
      on_disk: true,
      address: { address_id: 1, legal_address: 'ООО «Ромашка»', simple_address: 'Мира 1' },
      current_version: { images_count: 81, created_at: '2026-10-14T10:00:00' },
    },
    {
      fingerprint_id: '90_v33',
      display_name: 'Малая подборка',
      // A name typed by hand wins over the alias.
      name: 'Малая подборка',
      description: '',
      algorithm_version: '3.3',
      model: 'dinov2_vitb14',
      dimension: 768,
      images_count: 19,
      source_folder: null,
      active: true,
      on_disk: false,
      address: null,
      current_version: { images_count: 19, created_at: '2026-10-14T10:00:00' },
    },
  ]
  setActivePinia(createPinia())
  // The maintenance buttons are administrator-only.
  useSessionStore().user = { user_id: 1, name: 'Администратор', role: 'Администратор' }
  // Images are fetched with the bearer token, so a session must exist.
  setToken('test-token')
  installFetch()
})

afterEach(() => {
  setToken(null)
  delete global.fetch
})

describe('FingerprintsList.vue', () => {
  it('renders the registry with legal address, photo count and disk state', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    expect(wrapper.text()).toContain('Слепки (2)')
    expect(wrapper.text()).toContain('78_v33')
    // The address column shows the legal name, not the alias.
    expect(wrapper.text()).toContain('ООО «Ромашка»')
    expect(wrapper.text()).toContain('Малая подборка')
    expect(wrapper.text()).toContain('19')
  })

  it('shows the address alias in the name column', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    // Columns: ID, Превью, Имя, Адрес, Фото, ...
    const cells = wrapper.findAll('tbody tr').at(0).findAll('td')

    expect(cells.at(0).text()).toContain('78_v33')
    expect(cells.at(2).text()).toBe('Мира 1')
    expect(cells.at(3).text()).toContain('ООО «Ромашка»')
  })

  it('offers a preview of the source photos', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    expect(wrapper.html()).toContain('photo_library')
  })

  it('asks for the saved preview through the authenticated loader', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((button) => button.html().includes('edit'))
      .trigger('click')
    await flushPromises()

    const call = imageCalls.find((item) => item.url.includes('/preview'))

    expect(call).toBeTruthy()
    expect(call.url).toContain('/v1/fingerprints/registry/78_v33/preview')
    // A plain <img> cannot carry the token, which is why this goes through
    // AuthImage - the request must be authorised.
    expect(call.auth).toContain('Bearer')
  })

  it('shows a dash when a fingerprint has no address yet', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    // 90_v33 has no mapping: the address cell falls back to a dash.
    const rows = wrapper.findAll('tbody tr')
    const second = rows.at(1).text()
    expect(second).toContain('90_v33')
    expect(second).toContain('—')
  })

  it('syncs with the disk from the toolbar', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Синхронизировать'))
      .trigger('click')
    await flushPromises()

    expect(syncCalls).toHaveLength(1)
    expect(Notify.create).toHaveBeenCalled()
  })

  it('lists folders without photos in the batch picker so it can be walked', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Батч-сборка'))
      .trigger('click')
    await flushPromises()

    // The dialog renders in a portal, so its buttons live in document.body.
    const show = [...document.body.querySelectorAll('button')].find((button) =>
      button.textContent.includes('Показать подпапки'),
    )
    show.click()
    await flushPromises()

    const dialog = document.body.textContent

    expect(dialog).toContain('/home/alexice')
    expect(dialog).toContain('0 фото')
  })

  it('opens the version journal of a fingerprint', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    await wrapper.findAll('button').find((b) => b.html().includes('history')).trigger('click')
    await flushPromises()

    const dialog = document.body.textContent
    expect(dialog).toContain('Версии 78_v33')
    expect(dialog).toContain('81 фото')
    expect(dialog).toContain('текущая')
    expect(dialog).toContain('имена файлов (2)')
  })
})
