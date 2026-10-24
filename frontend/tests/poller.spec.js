// @vitest-environment happy-dom
// Общий поллер: без наложения, с паузой на скрытой вкладке и отменой.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createPoller } from '../src/composables/usePoller'

function setHidden(value) {
  // happy-dom отдаёт document.hidden только для чтения.
  Object.defineProperty(document, 'hidden', { value, configurable: true })
}

beforeEach(() => {
  vi.useFakeTimers()
  setHidden(false)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('createPoller', () => {
  it('не запускает второй тик, пока идёт первый', async () => {
    let resolveTask
    const task = vi.fn(
      () => new Promise((resolve) => { resolveTask = resolve }),
    )
    const poller = createPoller(task, { intervalMs: 100 })

    poller.start()
    await vi.advanceTimersByTimeAsync(350)

    expect(task).toHaveBeenCalledTimes(1)

    resolveTask()
    await vi.advanceTimersByTimeAsync(150)

    expect(task).toHaveBeenCalledTimes(2)
    poller.stop()
  })

  it('пропускает тик на скрытой вкладке и опрашивает при возврате', async () => {
    const task = vi.fn(async () => {})
    const poller = createPoller(task, { intervalMs: 100 })

    setHidden(true)
    poller.start()
    await vi.advanceTimersByTimeAsync(300)
    expect(task).not.toHaveBeenCalled()

    setHidden(false)
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(task).toHaveBeenCalledTimes(1)

    poller.stop()
  })

  it('после stop ответы больше не применяются', async () => {
    let resolveTask
    const seen = []
    const task = vi.fn(
      (my) => new Promise((resolve) => {
        resolveTask = () => {
          if (poller.isCurrent(my)) seen.push('applied')
          resolve()
        }
      }),
    )
    const poller = createPoller(task, { intervalMs: 100 })

    poller.start()
    await vi.advanceTimersByTimeAsync(100)
    poller.stop()
    resolveTask()
    await vi.advanceTimersByTimeAsync(0)

    expect(seen).toEqual([])
  })

  it('stop снимает таймер: новых тиков нет', async () => {
    const task = vi.fn(async () => {})
    const poller = createPoller(task, { intervalMs: 100 })

    poller.start()
    await vi.advanceTimersByTimeAsync(250)
    const before = task.mock.calls.length
    poller.stop()
    await vi.advanceTimersByTimeAsync(1000)

    expect(task.mock.calls.length).toBe(before)
    expect(poller.running).toBe(false)
  })

  it('immediate делает первый опрос сразу', async () => {
    const task = vi.fn(async () => {})
    const poller = createPoller(task, { intervalMs: 1000, immediate: true })

    poller.start()
    await vi.advanceTimersByTimeAsync(0)

    expect(task).toHaveBeenCalledTimes(1)
    poller.stop()
  })
})
