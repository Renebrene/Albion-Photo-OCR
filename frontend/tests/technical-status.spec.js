// Технический раздел: планировщик, сводка последних запусков, статистика
// сортировки.
// @vitest-environment happy-dom

import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Notify, Quasar } from 'quasar'

import Automation from '../src/components/Automation.vue'
import LastRun from '../src/components/LastRun.vue'
import Processing from '../src/pages/Processing.vue'

Notify.create = vi.fn()

function json(body, status = 200) {
  return { ok: status < 400, status, json: async () => body }
}

afterEach(() => {
  document.body.innerHTML = ''
  delete global.fetch
})

function mountComponent(component) {
  return mount(component, {
    attachTo: document.body,
    global: { plugins: [Quasar] },
  })
}

it('планировщик: режим интервала/времени и последний запуск', async () => {
  const calls = []
  const settings = {
    enabled: false,
    interval_minutes: 60,
    mode: 'interval',
    daily_time: null,
    auto_qwen: false,
    last_tick: null,
    last_run: {
      run_id: 5,
      status: 'DONE',
      started_at: '2026-10-17T10:00:00',
      finished_at: '2026-10-17T10:05:00',
      counts: { jobs_done: 10 },
      message: null,
      error_count: 0,
      has_log: true,
    },
  }

  global.fetch = vi.fn(async (url, options = {}) => {
    calls.push({ url: String(url), method: options.method || 'GET' })
    if (options.method === 'PUT') return json(settings)
    if (String(url).includes('/v1/automation')) return json(settings)
    return json({ items: [] })
  })

  const wrapper = mountComponent(Automation)
  await flushPromises()

  const text = wrapper.text()
  expect(text).toContain('Планировщик')
  expect(text).toContain('По интервалу')
  expect(text).toContain('Запускать QWEN автоматически')
  expect(text).toContain('Последний запуск')
  expect(text).toContain('успешно')

  const daily = wrapper
    .findAll('button')
    .find((button) => button.text().includes('В определённое время'))
  await daily.trigger('click')
  await flushPromises()

  expect(
    calls.some((call) => call.method === 'PUT' && call.url.includes('/v1/automation')),
  ).toBe(true)

  wrapper.unmount()
})

it('последний запуск: сводка по видам, остановка и длительности этапов', async () => {
  const history = {
    items: [
      {
        run_id: 12,
        kind: 'pipeline',
        mode: 'manual',
        status: 'STOPPED',
        started_at: '2026-10-17T09:00:00',
        finished_at: '2026-10-17T09:10:00',
        message: 'остановлено пользователем',
        has_log: true,
        stages: [
          { stage: 'INGEST', status: 'DONE', seconds: 120 },
          { stage: 'DINO', status: 'RUNNING', seconds: null },
        ],
      },
      {
        run_id: 11,
        kind: 'ingest',
        mode: 'manual',
        status: 'DONE',
        started_at: '2026-10-17T08:00:00',
        finished_at: '2026-10-17T08:02:00',
        has_log: true,
      },
      {
        run_id: 10,
        kind: 'sort',
        mode: 'manual',
        status: 'DONE',
        started_at: '2026-10-17T07:00:00',
        finished_at: '2026-10-17T07:01:00',
        has_log: false,
      },
      {
        run_id: 9,
        kind: 'qwen',
        mode: 'manual',
        status: 'FAILED',
        started_at: '2026-10-17T06:00:00',
        finished_at: '2026-10-17T06:01:00',
        has_log: true,
      },
      {
        run_id: 8,
        kind: 'scheduler',
        mode: 'schedule',
        status: 'DONE',
        started_at: '2026-10-17T05:00:00',
        finished_at: '2026-10-17T05:01:00',
        has_log: true,
      },
    ],
  }

  global.fetch = vi.fn(async (url) => {
    const path = String(url)
    if (path.includes('/v1/runs/history')) return json(history)
    if (path.includes('/v1/runs/last')) {
      return json({ dino_batch: null, hybrid_run: null, jobs: {} })
    }
    return json({ items: [] })
  })

  const wrapper = mountComponent(LastRun)
  await flushPromises()

  const text = wrapper.text()
  expect(text).toContain('Последние запуски')
  expect(text).toContain('Обновление базы')
  expect(text).toContain('прервано')
  expect(text).toContain('Остановлено на этапе')
  expect(text).toContain('Загрузка: 120 с')
  expect(text).toContain('Ingest')
  expect(text).toContain('Сортировка')
  expect(text).toContain('Планировщик')

  wrapper.unmount()
})

it('сортировка: совпадения, статус и даты по режимам', async () => {
  const sortStatus = {
    last: {
      run_id: 7,
      status: 'DONE',
      has_log: true,
      stats: { matched: 12, total: 20, failed: 1 },
    },
    modes: {
      manual: { started_at: '2026-10-17T09:00:00' },
      schedule: { started_at: '2026-10-17T05:00:00' },
      outofqueue: null,
    },
    current: null,
    active: null,
  }

  global.fetch = vi.fn(async (url) => {
    const path = String(url)
    if (path.includes('/v1/sort/status')) return json(sortStatus)
    if (path.includes('/v1/runs/activity')) return json({ active: null })
    if (path.includes('/v1/batches/dino')) return json({ items: [] })
    if (path.includes('/v1/hybrid/runs')) return json({ items: [] })
    if (path.includes('/v1/jobs')) return json({ items: [] })
    return json({ items: [] })
  })

  const wrapper = mountComponent(Processing)
  await flushPromises()

  const text = wrapper.text()
  expect(text).toContain('Статистика сортировки')
  expect(text).toContain('Совпадений')
  expect(text).toContain('12')
  expect(text).toContain('20')
  expect(text).toContain('ОК')
  expect(text).toContain('Вручную')
  expect(text).toContain('По расписанию')
  expect(text).toContain('Вне очереди')

  wrapper.unmount()
})
