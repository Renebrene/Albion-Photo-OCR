// Журнал посещений: «таблицы нет» (404) и «не удалось загрузить» — разное.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import VisitsAdmin from '../src/components/VisitsAdmin.vue'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function mountPanel() {
  return mount(VisitsAdmin, { global: { plugins: [Quasar] } })
}

afterEach(() => {
  delete global.fetch
  vi.restoreAllMocks()
})

describe('журнал посещений', () => {
  it('скрывается, когда таблицы нет (404)', async () => {
    global.fetch = vi.fn(async () => json({ detail: 'Not Found' }, 404))

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toBe('')
    wrapper.unmount()
  })

  it('при сбое остаётся и показывает причину с повтором', async () => {
    global.fetch = vi.fn(async () => json({ detail: 'нет связи с базой' }, 500))

    const wrapper = mountPanel()
    await flushPromises()

    // Раньше панель пряталась при любой ошибке: сетевой сбой выглядел как
    // «журнала нет».
    expect(wrapper.text()).toContain('Посещения (входы)')
    expect(wrapper.text()).toContain('нет связи с базой')
    expect(wrapper.text()).toContain('Повторить')

    wrapper.unmount()
  })

  it('после повтора показывает записи', async () => {
    let failing = true
    global.fetch = vi.fn(async () => {
      if (failing) return json({ detail: 'сбой' }, 500)
      return json({ items: [{ visit_id: 1, created_at: '2026-10-24T18:00:00', user_name: 'Albion', event: 'login' }] })
    })

    const wrapper = mountPanel()
    await flushPromises()

    failing = false
    const retry = wrapper.findAll('button').find((item) => item.text().includes('Повторить'))
    await retry.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Albion')
    expect(wrapper.text()).toContain('вход')
    wrapper.unmount()
  })
})
