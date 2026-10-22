// Категория подставляется в подпись ТОЛЬКО когда не распознаны и клиент, и
// бренд. Если известен хотя бы один — прочерк на месте второго честнее.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function photo(overrides = {}) {
  return {
    photo_id: 'PH_' + 'a'.repeat(24),
    filename: 'photo.jpg',
    width: 100,
    height: 100,
    container_format: 'JPEG',
    address: '78_v33',
    simple_address: 'Комарова 13',
    source_directory: 'test',
    taken_at: '2025-07-17 11:43:19',
    size_bytes: 1,
    ...overrides,
  }
}

function installFetch(item) {
  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]

    if (path.endsWith('/v1/photos')) {
      return json({ items: [item], next_cursor: null, total: 1 })
    }

    return json({ items: [] })
  })
}

const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

async function mountGrid(item) {
  installFetch(item)

  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(Host, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()

  return wrapper
}

beforeEach(() => {
  Notify.create = vi.fn()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('категория вместо клиента и бренда', () => {
  it('показывается, когда не распознаны оба', async () => {
    const wrapper = await mountGrid(
      photo({ client: null, brand: null, category: 'Автосалоны' }),
    )

    expect(wrapper.text()).toContain('Автосалоны')
    wrapper.unmount()
  })

  it('не подменяет бренд, если клиент известен', async () => {
    const wrapper = await mountGrid(
      photo({ client: 'Клиент А', brand: null, category: 'Автосалоны' }),
    )

    expect(wrapper.text()).toContain('Клиент А')
    expect(wrapper.text()).not.toContain('Автосалоны')
    wrapper.unmount()
  })
})
