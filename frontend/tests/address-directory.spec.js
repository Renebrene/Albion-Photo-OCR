// Component test: the address directory tab loads rows, validates the input
// and posts what the API expects. Driven by a stubbed global.fetch.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import AddressDirectory from '../src/components/AddressDirectory.vue'

Notify.create = vi.fn()

let directory
let unassigned
let posted
let mappings

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function installFetch() {
  global.fetch = vi.fn(async (url, options = {}) => {
    const method = (options.method || 'GET').toUpperCase()
    const path = String(url).split('?')[0]

    if (method === 'GET' && path === '/api/v1/addresses/directory') {
      return jsonResponse({ items: directory })
    }

    if (method === 'GET' && path === '/api/v1/addresses/unassigned') {
      return jsonResponse({ items: unassigned })
    }

    if (method === 'POST' && path === '/api/v1/addresses/directory') {
      posted.push(JSON.parse(options.body))
      return jsonResponse({ address_id: 5 }, 201)
    }

    if (method === 'PUT' && path.endsWith('/fingerprints')) {
      mappings.push(JSON.parse(options.body))
      return jsonResponse({ address_id: 1 })
    }

    return jsonResponse({ detail: `no route for ${method} ${path}` }, 500)
  })
}

function mountDirectory() {
  return mount(AddressDirectory, { global: { plugins: [Quasar] } })
}

beforeEach(() => {
  posted = []
  mappings = []
  directory = [
    {
      address_id: 1,
      legal_address: 'ООО «Ромашка», ул. Мира, 1',
      simple_address: 'Мира 1',
      active: true,
      sort_order: 0,
      fingerprints: ['78_v33'],
    },
  ]
  unassigned = ['83_v33', '89_v33']
  installFetch()
})

afterEach(() => {
  delete global.fetch
})

describe('AddressDirectory.vue', () => {
  it('renders the directory and the mapping of each address', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    expect(wrapper.text()).toContain('ООО «Ромашка», ул. Мира, 1')
    expect(wrapper.text()).toContain('Мира 1')
    expect(wrapper.text()).toContain('78_v33')
    expect(wrapper.text()).toContain('Адреса (1)')
  })

  it('refuses to create an address without any name', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    await wrapper.findAll('button').find((btn) => btn.text().includes('Добавить')).trigger('click')
    await flushPromises()

    expect(posted).toEqual([])
    expect(Notify.create).toHaveBeenCalled()
  })

  it('posts the new address as the API expects', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('ООО «Тюльпан», ул. Садовая, 7')
    await inputs[1].setValue('Садовая 7')
    await wrapper.findAll('button').find((btn) => btn.text().includes('Добавить')).trigger('click')
    await flushPromises()

    expect(posted).toEqual([
      {
        legal_address: 'ООО «Тюльпан», ул. Садовая, 7',
        simple_address: 'Садовая 7',
      },
    ])
  })

  it('sends the selected fingerprints for an address', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    // Open the mapping dialog of the only row and keep its current id.
    // Quasar renders dialogs in a portal, so the dialog content lives in the
    // document body rather than inside the mounted wrapper.
    await wrapper.findAll('button').find((btn) => btn.html().includes('link')).trigger('click')
    await flushPromises()

    const checkboxes = [...document.body.querySelectorAll('.q-checkbox')]
    expect(checkboxes.length).toBe(3) // 78_v33 (current) + 83_v33 + 89_v33

    checkboxes[1].click()
    await flushPromises()

    const save = [...document.body.querySelectorAll('button')].find(
      (button) => button.textContent.trim() === 'Сохранить',
    )
    save.click()
    await flushPromises()

    expect(mappings).toEqual([{ fingerprints: ['78_v33', '83_v33'] }])
  })
})
