// Component test: the fingerprint management window renders the registry,
// syncs with the disk and shows the version journal. Stubbed global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import FingerprintsList from '../src/components/FingerprintsList.vue'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

let registry
let versions
let syncCalls
let updates

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

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
  installFetch()
})

afterEach(() => {
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

  it('shows the saved preview in the edit dialog', async () => {
    const wrapper = mountWindow()
    await flushPromises()

    await wrapper
      .findAll('button')
      .find((button) => button.html().includes('edit'))
      .trigger('click')
    await flushPromises()

    const image = [...document.body.querySelectorAll('img')].find((node) =>
      (node.getAttribute('src') || '').includes('/preview'),
    )

    expect(image).toBeTruthy()
    expect(image.getAttribute('src')).toBe(
      '/api/v1/fingerprints/registry/78_v33/preview',
    )
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
