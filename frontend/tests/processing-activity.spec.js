// Кнопка «Запустить виртуальную сортировку» учитывает не только pipeline,
// но и scheduler/ручную сортировку через /v1/runs/activity.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import Processing from '../src/pages/Processing.vue'

Notify.create = vi.fn()

function json(body) {
  return { ok: true, status: 200, json: async () => body }
}

beforeEach(() => vi.restoreAllMocks())
afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

describe('сортировка: активный процесс', () => {
  it('блокирует ручной запуск во время pipeline и показывает стадию', async () => {
    global.fetch = vi.fn(async (url) => {
      const path = String(url)
      if (path.includes('/v1/runs/activity')) {
        return json({
          active: { kind: 'pipeline', run_id: 7, stage: 'DINO' },
          message: 'идёт «Обновление базы» (стадия DINO)',
        })
      }
      return json({ items: [], next_cursor: null })
    })

    const wrapper = mount(Processing, {
      attachTo: document.body,
      global: { plugins: [Quasar] },
    })
    await flushPromises()

    const button = wrapper
      .findAll('button')
      .find((item) => item.text().includes('Запустить виртуальную сортировку'))

    expect(button.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('стадия DINO')
    wrapper.unmount()
  })
})

describe('переключение вкладок', () => {
  it('не стирает несохранённый порог уверенности', async () => {
    global.fetch = vi.fn(async (url) => {
      const path = String(url)

      if (path.includes('/v1/hybrid/settings')) {
        // Сервер хранит 0.9: если бы вкладка перечитывала настройки, введённое
        // значение вернулось бы к серверному.
        return json({ low_score: 0.9, min_margin: 0, enabled: true })
      }

      return json({ items: [], next_cursor: null })
    })

    const wrapper = mount(Processing, {
      attachTo: document.body,
      global: { plugins: [Quasar] },
    })
    await flushPromises()

    wrapper.vm.lowScore = 0.75
    await flushPromises()

    // Переключаем вкладку так же, как пользователь.
    const hybridTab = wrapper
      .findAll('.q-tab')
      .find((item) => item.text().includes('HYBRID runs'))

    expect(hybridTab).toBeTruthy()
    await hybridTab.trigger('click')
    await flushPromises()

    expect(wrapper.vm.lowScore).toBe(0.75)
    wrapper.unmount()
  })
})
