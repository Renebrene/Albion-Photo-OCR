// @vitest-environment happy-dom

// pollUntil: ретраи на сетевых сбоях, отмена поколением, терминальное
// состояние и таймаут.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { pollUntil } from '../src/composables/pollUntil'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

async function run(promise) {
  await vi.advanceTimersByTimeAsync(10_000)
  return promise
}

describe('pollUntil', () => {
  it('возвращает данные на терминальном состоянии', async () => {
    let calls = 0
    const outcome = await run(
      pollUntil(
        async () => ({ status: ++calls >= 3 ? 'DONE' : 'RUNNING' }),
        (job) => job.status === 'DONE',
        { tries: 10, stepMs: 100 },
      ),
    )

    expect(outcome.data.status).toBe('DONE')
    expect(calls).toBe(3)
  })

  it('переживает один сетевой сбой и продолжает опрос', async () => {
    let calls = 0
    const outcome = await run(
      pollUntil(
        async () => {
          calls += 1
          if (calls === 1) throw new Error('network')

          return { status: calls === 2 ? 'RUNNING' : 'DONE' }
        },
        (job) => job.status === 'DONE',
        { tries: 10, stepMs: 100 },
      ),
    )

    expect(outcome.data.status).toBe('DONE')
    expect(outcome.error).toBeUndefined()
  })

  it('сдаётся после трёх подряд сбоев', async () => {
    const outcome = await run(
      pollUntil(
        async () => {
          throw new Error('network')
        },
        () => false,
        { tries: 10, stepMs: 100 },
      ),
    )

    expect(outcome.error.message).toBe('network')
  })

  it('останавливается, когда поколение сменилось', async () => {
    const outcome = await run(
      pollUntil(
        async () => ({ status: 'RUNNING' }),
        () => false,
        { tries: 10, stepMs: 100, isCancelled: () => true },
      ),
    )

    expect(outcome.cancelled).toBe(true)
  })

  it('возвращает таймаут, если задание не завершилось', async () => {
    const outcome = await run(
      pollUntil(
        async () => ({ status: 'RUNNING' }),
        () => false,
        { tries: 3, stepMs: 100 },
      ),
    )

    expect(outcome.timeout).toBe(true)
  })
})

describe('скрытая вкладка', () => {
  it('не опрашивает API, пока страница не видна', async () => {
    let hidden = true
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => hidden,
    })

    const calls = []
    const pending = pollUntil(
      async () => {
        calls.push(1)
        return { status: 'DONE' }
      },
      (data) => data.status === 'DONE',
      { tries: 10, stepMs: 100 },
    )

    // Проходит время, но вкладка скрыта — запросов нет вовсе.
    await vi.advanceTimersByTimeAsync(1000)
    expect(calls).toEqual([])

    hidden = false

    const outcome = await run(pending)

    expect(outcome.data).toEqual({ status: 'DONE' })
    // Скрытое время не «съело» попытки: опрос дождался возвращения.
    expect(calls.length).toBe(1)

    delete document.hidden
  })
})
