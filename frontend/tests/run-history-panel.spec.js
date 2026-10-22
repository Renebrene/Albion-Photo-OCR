// Unified history panel and safe plain-text run log.
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import RunHistoryPanel from '../src/components/RunHistoryPanel.vue'

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

function mountPanel(history = { items: [] }, options = {}) {
  const responses = [json(history, options.historyStatus || 200)]
  global.fetch = vi.fn(async () => responses.shift() || json({}))
  const wrapper = mount(RunHistoryPanel, {
    attachTo: document.body,
    global: { plugins: [Quasar] },
  })
  return { wrapper, responses }
}

beforeEach(() => vi.restoreAllMocks())
afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

describe('общая история запусков', () => {
  it('показывает записи разных видов, счётчики и кнопку лога', async () => {
    const { wrapper } = mountPanel({ items: [
      {
        run_id: 21, kind: 'ingest', mode: 'manual', status: 'PARTIAL',
        title: 'Инспектирование: новые фото', created_at: '2026-10-17T01:00:00Z',
        counts: { total: 4, done: 3, failed: 1 }, error_count: 1,
        message: 'часть файлов пропущена', has_log: true, stages: [],
      },
      {
        run_id: 20, kind: 'pipeline', mode: 'schedule', status: 'DONE',
        title: 'Обновление базы', started_at: '2026-10-16T12:00:00Z',
        counts: { total: 3, done: 3, jobs_total: 2, jobs_done: 2 },
        error_count: 0, has_log: false,
        stages: [{ stage: 'DINO', status: 'DONE', seconds: 1.25 }],
      },
      {
        run_id: 19, kind: 'sort', mode: 'manual', status: 'RUNNING',
        title: 'DINO batch #19', started_at: '2026-10-16T11:00:00Z',
        counts: {
          total: 4, done: 0, failed: 0, jobs_total: 2, jobs_done: 1,
          by_stage: {
            DINO: { required: true, total: 4, done: 4, failed: 0 },
            HYBRID: { required: true, total: 4, done: 0, failed: 0 },
          },
        },
        error_count: 0, has_log: false, stages: [],
      },
    ] })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('История запусков')
    expect(text).toContain('Инспектирование: новые фото')
    expect(text).toContain('частично')
    expect(text).toContain('готово 3/4')
    expect(text).toContain('Обновление базы')
    expect(text).toContain('по расписанию')
    expect(text).toContain('DINO: DONE  (1.25 с)')
    expect(text).toContain('DINO 4/4')
    expect(text).toContain('HYBRID 0/4')
    expect(text).toContain('Открыть лог')
  })

  it('показывает пустое состояние', async () => {
    const { wrapper } = mountPanel()
    await flushPromises()
    expect(wrapper.text()).toContain('Пока нет записей в общей истории.')
  })

  it('показывает ошибку загрузки истории', async () => {
    global.fetch = vi.fn(async () => json({ detail: 'forbidden' }, 403))
    const wrapper = mount(RunHistoryPanel, { global: { plugins: [Quasar] } })
    await flushPromises()
    expect(wrapper.text()).toContain('API error 403')
  })

  it('открывает лог как текст и сообщает, если он уже удалён', async () => {
    const { wrapper } = mountPanel({ items: [
      { run_id: 8, kind: 'qwen', mode: 'manual', status: 'FAILED', title: 'QWEN',
        counts: {}, error_count: 1, has_log: true, stages: [] },
    ] })
    await flushPromises()
    global.fetch.mockResolvedValueOnce({ ok: true, status: 200, text: async () => '<script>safe text</script>' })
    await wrapper.find('button[aria-label="Открыть лог 8"]').trigger('click')
    await flushPromises()
    expect(document.body.querySelector('pre.run-log')?.textContent).toBe('<script>safe text</script>')
    expect(global.fetch.mock.calls.at(-1)[0]).toContain('/v1/runs/history/8/log')

    const runRow = wrapper.find('[data-run-id="8"]')
    global.fetch.mockResolvedValueOnce({ ok: false, status: 404 })
    await runRow.find('button[aria-label="Открыть лог 8"]').trigger('click')
    await flushPromises()
    expect(document.body.textContent).toContain('Лог для этого запуска отсутствует или уже удалён.')
  })
})
