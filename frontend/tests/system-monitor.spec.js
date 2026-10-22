// Система: пороги и алерты в техразделе.
// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Quasar } from 'quasar'

import SystemMonitor from '../src/components/SystemMonitor.vue'

function json(body) {
  return { ok: true, status: 200, json: async () => body }
}

beforeEach(() => {
  vi.useFakeTimers()
  global.fetch = vi.fn(async () => json({
    cpu_count: 12,
    cpu_percent: 94,
    load_avg: [3, 2, 1],
    memory: { total: 32 * 1024 ** 3, used: 26 * 1024 ** 3, percent: 81 },
    disk: { total: 1000 * 1024 ** 3, used: 800 * 1024 ** 3, percent: 80 },
    network: { bytes_recv: 1, bytes_sent: 1, rate_mbps: 0.2, errors: 0, drops: 0 },
    gpus: [{ index: 0, name: 'RTX', utilization: 95, memory_percent: 91, temperature: 70 }],
    temperatures: [{ sensor: 'cpu', label: 'Tctl', current: 85 }],
    uptime_sec: 100,
    security: {
      login_failures: 12,
      login_failures_by_ip: { '10.0.0.5': 12 },
      login_failure_limit: 10,
      login_failure_window_sec: 600,
      requests_by_ip: {},
      request_limit: 300,
    },
    alerts: [
      { code: 'memory_high', severity: 'warning', message: 'Память выше порога' },
      { code: 'login_failures', severity: 'critical', message: 'Много неудачных входов' },
    ],
  }))
})

afterEach(() => {
  vi.useRealTimers()
  delete global.fetch
  document.body.innerHTML = ''
})

describe('системный монитор', () => {
  it('показывает алерты, GPU и счётчик неудачных входов', async () => {
    const wrapper = mount(SystemMonitor, { global: { plugins: [Quasar] } })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Память выше порога')
    expect(text).toContain('Много неудачных входов')
    expect(text).toContain('GPU 0')
    expect(text).toContain('неудачных входов: 12')
    expect(text).toContain('10.0.0.5')
    wrapper.unmount()
  })
})
