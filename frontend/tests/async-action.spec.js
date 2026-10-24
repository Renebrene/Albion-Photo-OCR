// useAsyncAction: защита от повторного входа и флаг занятости для кнопок.
import { describe, expect, it, vi } from 'vitest'

import { useAsyncAction } from '../src/composables/useAsyncAction'

describe('useAsyncAction', () => {
  it('не пускает второй вызов, пока идёт первый', async () => {
    const { busy, run } = useAsyncAction()
    const action = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 5))
      return 'ok'
    })

    const first = run(action)
    const second = run(action)

    expect(busy.value).toBe(true)
    await expect(first).resolves.toBe('ok')
    await expect(second).resolves.toBeUndefined()
    expect(action).toHaveBeenCalledTimes(1)
    expect(busy.value).toBe(false)
  })

  it('снимает флаг занятости после ошибки', async () => {
    const { busy, run } = useAsyncAction()

    await expect(
      run(async () => {
        throw new Error('boom')
      }),
    ).rejects.toThrow('boom')

    expect(busy.value).toBe(false)
  })

  it('разные действия не блокируют друг друга', async () => {
    const first = useAsyncAction()
    const second = useAsyncAction()

    const a = first.run(async () => 'a')
    const b = second.run(async () => 'b')

    await expect(a).resolves.toBe('a')
    await expect(b).resolves.toBe('b')
  })
})
