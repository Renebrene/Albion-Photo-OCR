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
let importCalls

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

    // Сведённый вид: одна строка — одна сторона (адреса в фикстуре без стороны).
    if (method === 'GET' && path === '/api/v1/addresses/directory/grouped') {
      const items = directory.map((row, index) => ({
        base: row.legal_address,
        format: row.format || '',
        side: index === 0 ? 'A' : 'B',
        city: row.city || '',
        scope: row.scope || 'screens',
        simple: row.simple_address || '',
        count: 1,
        surfaces: [
          {
            address_id: row.address_id,
            legal_address: row.legal_address,
            side: index === 0 ? 'A' : 'B',
            fingerprints: row.fingerprints || [],
          },
        ],
      }))
      return jsonResponse({ items })
    }

    if (method === 'POST' && path === '/api/v1/addresses/directory') {
      posted.push(JSON.parse(options.body))
      return jsonResponse({ address_id: 5 }, 201)
    }

    if (method === 'PUT' && path.endsWith('/fingerprints')) {
      mappings.push(JSON.parse(options.body))
      return jsonResponse({ address_id: 1 })
    }

    if (method === 'POST' && path === '/api/v1/addresses/import') {
      importCalls.push(String(url))
      return jsonResponse({
        rows: 1567,
        created: 1472,
        updated: 95,
        skipped: 0,
        renamed: 0,
        dry_run: String(url).includes('dry_run=1'),
        errors: [],
      })
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
  importCalls = []
  directory = [
    {
      address_id: 1,
      legal_address: 'ООО «Ромашка», ул. Мира, 1',
      simple_address: 'Мира 1',
      active: true,
      sort_order: 0,
      fingerprints: ['78_v33'],
    },
    {
      address_id: 2,
      legal_address: 'ООО «Ромашка», ул. Мира, 1 (вторая сторона)',
      simple_address: 'Мира 1',
      active: true,
      sort_order: 1,
      fingerprints: ['79_v33'],
    },
  ]
  unassigned = ['83_v33', '89_v33']
  installFetch()
})

afterEach(() => {
  delete global.fetch
})

/** Выбрать файл в скрытом input — так же, как это делает браузер. */
async function chooseFile(wrapper, name = 'возможности.xlsx') {
  const input = wrapper.find('input[type="file"]')
  const file = new File(['данные'], name)

  Object.defineProperty(input.element, 'files', {
    value: [file],
    configurable: true,
  })

  await input.trigger('change')
  await flushPromises()
}

describe('AddressDirectory.vue', () => {
  it('нумерует строки и показывает сторону в адресе', async () => {
    // Отдельной колонки «Сторона» больше нет: сторона — часть строки адреса,
    // а первая колонка — порядковый номер (задание, 28.10.2026).
    const wrapper = mountDirectory()
    await flushPromises()

    const headers = wrapper.findAll('thead th').map((cell) => cell.text().trim())
    expect(headers).not.toContain('Сторона')
    expect(headers).toContain('№')

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBeGreaterThan(1)
    expect(rows[0].text()).toContain('1')
    expect(rows[1].text()).toContain('2')

    // Адрес строки — со стороной, как в списке выбора слепка.
    expect(rows[0].text()).toContain('A')
    expect(rows[1].text()).toContain('B')

    wrapper.unmount()
  })

  it('предпросмотр импорта считает, но не трогает справочник', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    global.fetch.mockClear()

    const preview = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Предпросмотр'))

    expect(preview).toBeTruthy()
    await preview.trigger('click')
    await chooseFile(wrapper)

    expect(importCalls).toHaveLength(1)
    expect(importCalls[0]).toContain('dry_run=1')
    expect(Notify.create).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Предпросмотр'),
      }),
    )

    // Справочник не перечитывался: предпросмотр ничего не менял.
    const reloaded = global.fetch.mock.calls.some(([url]) =>
      String(url).includes('/v1/addresses/directory'),
    )
    expect(reloaded).toBe(false)
  })

  it('обычный импорт идёт без dry_run и перечитывает справочник', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    global.fetch.mockClear()

    const button = wrapper
      .findAll('button')
      .find((element) => element.text().includes('Импорт из XLSX / CSV'))

    await button.trigger('click')
    await chooseFile(wrapper)

    expect(importCalls).toHaveLength(1)
    expect(importCalls[0]).not.toContain('dry_run')

    const reloaded = global.fetch.mock.calls.some(([url]) =>
      String(url).includes('/v1/addresses/directory'),
    )
    expect(reloaded).toBe(true)
  })

  it('renders the directory and the mapping of each address', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    expect(wrapper.text()).toContain('ООО «Ромашка», ул. Мира, 1')
    expect(wrapper.text()).toContain('Мира 1')
    expect(wrapper.text()).toContain('78_v33')
    expect(wrapper.text()).toContain('Адреса (2)')
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
        // Новый адрес попадает в открытую закладку («Экраны» по умолчанию).
        scope: 'screens',
      },
    ])
  })

  it('sends the selected fingerprints for an address', async () => {
    const wrapper = mountDirectory()
    await flushPromises()

    // В таблице строки — стороны; у этой одна поверхность, поэтому действие
    // применяется к ней без выбора.
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
