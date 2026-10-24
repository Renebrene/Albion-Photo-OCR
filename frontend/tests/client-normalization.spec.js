// Нормализация клиентов и брендов: сбой загрузки виден отдельно от «пусто».
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'
import { createPinia, setActivePinia } from 'pinia'

import ClientNormalization from '../src/components/ClientNormalization.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

let failing

function installFetch() {
  global.fetch = vi.fn(async (url) => {
    const path = String(url).split('?')[0]

    if (failing) return json({ detail: 'база недоступна' }, 500)

    if (path.endsWith('/v1/client-aliases')) return json({ items: [] })
    if (path.endsWith('/v1/client-aliases/qwen-names')) return json({ items: [] })
    if (path.endsWith('/v1/client-aliases/audit')) return json({ items: [] })

    return json({}, 404)
  })
}

function mountPanel() {
  setActivePinia(createPinia())

  return mount(ClientNormalization, { global: { plugins: [Quasar] } })
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('нормализация клиентов', () => {
  it('при сбое показывает причину и повтор, а не «Алиасов нет»', async () => {
    failing = true
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('база недоступна')
    expect(wrapper.text()).toContain('Повторить')
    // Пустота и сбой различимы: «нет данных» — только когда запрос прошёл.
    expect(wrapper.text()).not.toContain('Алиасов нет')
    expect(wrapper.text()).not.toContain('Пока нет распознанных названий')

    wrapper.unmount()
  })

  it('после успешной загрузки показывает обычное пустое состояние', async () => {
    failing = false
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('Алиасов нет')
    expect(wrapper.text()).not.toContain('Повторить')

    wrapper.unmount()
  })

  it('повтор перезапрашивает данные', async () => {
    failing = true
    installFetch()

    const wrapper = mountPanel()
    await flushPromises()

    failing = false

    // Кнопок повтора три (названия, сопоставления, история) — нажимаем все.
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const retry = wrapper
        .findAll('button')
        .find((item) => item.text().includes('Повторить'))

      if (!retry) break

      await retry.trigger('click')
      await flushPromises()
    }

    expect(wrapper.text()).toContain('Алиасов нет')
    expect(wrapper.text()).not.toContain('база недоступна')

    wrapper.unmount()
  })
})
