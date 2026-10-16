// Панель истории запусков «Обновления базы» (вкладка «Последний запуск»).
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import PipelineRunsPanel from '../src/components/PipelineRunsPanel.vue'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

async function mountPanel(payload, status = 200) {
  global.fetch = vi.fn(async () => json(payload, status))
  const wrapper = mount(PipelineRunsPanel, { global: { plugins: [Quasar] } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.restoreAllMocks()
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('История запусков', () => {
  it('скрывается, пока супервизор не развёрнут', async () => {
    const wrapper = await mountPanel({ detail: 'Not Found' }, 404)
    expect(wrapper.text()).toBe('')
  })

  it('показывает статус, стадии и длительность', async () => {
    const wrapper = await mountPanel({
      items: [
        {
          run_id: 3,
          mode: 'manual',
          status: 'DONE',
          started_at: '2026-10-16 12:00:00',
          finished_at: '2026-10-16 12:05:00',
          message: 'база обновлена',
          stages: [
            { stage: 'INGEST', status: 'DONE', started_at: '2026-10-16 12:00:00', finished_at: '2026-10-16 12:00:30', failed_count: 0 },
            { stage: 'QWEN', status: 'DONE', started_at: '2026-10-16 12:00:30', finished_at: '2026-10-16 12:05:00', failed_count: 1 },
          ],
        },
      ],
    })

    const text = wrapper.text()
    expect(text).toContain('#3')
    expect(text).toContain('завершён')
    expect(text).toContain('Загрузка')
    expect(text).toContain('30 с')
    expect(text).toContain('270 с')
    expect(text).toContain('ошибок: 1')
  })

  it('сообщает, когда запусков не было', async () => {
    const wrapper = await mountPanel({ items: [] })
    expect(wrapper.text()).toContain('Пока не было ни одного запуска')
  })
})
