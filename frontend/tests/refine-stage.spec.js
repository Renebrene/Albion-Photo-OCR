// «Уточнение» доступно только тогда, когда есть что сравнивать: QWEN
// участвует в прогоне или в базе уже лежат его описания.
// @vitest-environment happy-dom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, QToggle, Quasar } from 'quasar'

import RefineStage from '../src/components/RefineStage.vue'

Notify.create = vi.fn()

function installFetch(payload) {
  global.fetch = vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => payload,
  }))
}

async function mountStage(payload) {
  installFetch(payload)
  const wrapper = mount(RefineStage, { global: { plugins: [Quasar] } })
  await flushPromises()
  return wrapper
}

afterEach(() => {
  delete global.fetch
})

describe('этап «Уточнение»', () => {
  it('выключатель доступен, когда QWEN дал результаты', async () => {
    const wrapper = await mountStage({
      enabled: false,
      available: true,
      gap_seconds: 30,
      crop_retention_days: 7,
      photos_ready: 12,
    })

    const toggle = wrapper.findComponent(QToggle)
    expect(toggle.props('disable')).toBe(false)
    expect(wrapper.text()).not.toContain('Этап недоступен')
  })

  it('без QWEN выключатель заблокирован и объяснён', async () => {
    const wrapper = await mountStage({
      enabled: false,
      available: false,
      gap_seconds: 30,
      crop_retention_days: 7,
      photos_ready: 0,
    })

    expect(wrapper.findComponent(QToggle).props('disable')).toBe(true)
    expect(wrapper.text()).toContain('Этап недоступен')
    expect(wrapper.text()).toContain('Запускать QWEN в «Обновлении базы»')
  })
})
