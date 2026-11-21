// «Похожие»: служебные данные кропа (номер вырезки и сходство CLIP) видит
// только администратор. Менеджер и гость получают карточку объявления без
// внутренней механики поиска (владелец, 21.11.2026).
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { h, nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QLayout, QPageContainer, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import PhotosGrid from '../src/pages/PhotosGrid.vue'
import { useSessionStore } from '../src/stores/session'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

const matches = [
  {
    region_id: 59455,
    photo_id: 'PH_' + 'a'.repeat(24),
    address: 'Нагибина M. пр-кт 19/1, A',
    brand: 'Тенет',
    taken_at: '2026-11-20T12:59:39',
    created_at: '2026-11-21T01:26:00',
    score: 0.9545,
    crop_index: 1,
  },
]

function installFetch() {
  global.fetch = vi.fn((url) => {
    const path = new URL(String(url), 'http://localhost').pathname

    if (path.endsWith('/v1/photos')) {
      return Promise.resolve(json({ items: [], next_cursor: null, total: 0 }))
    }

    return Promise.resolve(json({ items: [] }))
  })
}

const Host = {
  render: () =>
    h(QLayout, null, {
      default: () => h(QPageContainer, null, { default: () => h(PhotosGrid) }),
    }),
}

async function mountGridWithRole(role) {
  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(Host, { global: { plugins: [Quasar, pinia] } })
  await flushPromises()

  const session = useSessionStore()
  session.authEnabled = true
  session.user = { name: role, role }

  const grid = wrapper.findComponent(PhotosGrid)
  grid.vm.similarPhotoId = matches[0].photo_id
  grid.vm.similarItems = matches
  grid.vm.similarOpen = true
  await nextTick()
  await flushPromises()

  return wrapper
}

beforeEach(() => {
  Notify.create = vi.fn()
  installFetch()
})

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
  vi.restoreAllMocks()
})

describe('«Похожие»: служебные данные кропа', () => {
  it('администратор видит номер кропа и сходство', async () => {
    await mountGridWithRole('Администратор')

    expect(document.body.textContent).toContain('кроп 2')
    expect(document.body.textContent).toContain('0.95')
  })

  it('менеджер не видит ни номера кропа, ни сходства', async () => {
    await mountGridWithRole('Менеджер')

    expect(document.body.textContent).toContain('Тенет')
    expect(document.body.textContent).not.toContain('кроп')
    expect(document.body.textContent).not.toContain('0.95')
  })

  it('гость не видит ни номера кропа, ни сходства', async () => {
    await mountGridWithRole('Гость')

    expect(document.body.textContent).toContain('Тенет')
    expect(document.body.textContent).not.toContain('кроп')
    expect(document.body.textContent).not.toContain('0.95')
  })
})
