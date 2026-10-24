// Кэш авторизованных картинок: blob не переходит между сессиями, крупные
// оригиналы не задерживаются в «недавних».
// @vitest-environment happy-dom

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  acquireImageUrl,
  clearImageCache,
  releaseImageUrl,
} from '../src/api/client'

let created
let revoked
let blobSize
let fetchCalls

function installBlobEnvironment() {
  created = []
  revoked = []
  fetchCalls = 0

  let counter = 0
  URL.createObjectURL = vi.fn(() => {
    counter += 1
    const url = `blob:test-${counter}`
    created.push(url)
    return url
  })
  URL.revokeObjectURL = vi.fn((url) => revoked.push(url))

  global.fetch = vi.fn(async () => {
    fetchCalls += 1
    return {
      ok: true,
      status: 200,
      blob: async () => ({ size: blobSize }),
    }
  })
}

beforeEach(() => {
  blobSize = 13 * 1024
  installBlobEnvironment()
})

afterEach(() => {
  clearImageCache()
  delete global.fetch
})

describe('кэш картинок', () => {
  it('повторный запрос берёт blob из кэша, освобождение — из «недавних»', async () => {
    const first = await acquireImageUrl('/api/v1/photos/a/small')
    const second = await acquireImageUrl('/api/v1/photos/a/small')

    expect(first).toBe(second)
    expect(fetchCalls).toBe(1)

    releaseImageUrl('/api/v1/photos/a/small')
    releaseImageUrl('/api/v1/photos/a/small')

    // После полного освобождения blob переехал в «недавние» — без сети.
    const third = await acquireImageUrl('/api/v1/photos/a/small')
    expect(third).toBe(first)
    expect(fetchCalls).toBe(1)
  })

  it('крупный оригинал не задерживается в «недавних»', async () => {
    blobSize = 5 * 1024 * 1024
    const url = '/api/v1/photos/a/original'

    const first = await acquireImageUrl(url)
    releaseImageUrl(url)

    // Сразу освобождён, в recent не попал.
    expect(revoked).toContain(first)

    const second = await acquireImageUrl(url)
    expect(second).not.toBe(first)
    expect(fetchCalls).toBe(2)
  })

  it('после смены сессии кэш не отдаётся прошлому пользователю', async () => {
    const url = '/api/v1/photos/a/original'
    const first = await acquireImageUrl(url)

    clearImageCache()

    expect(revoked).toContain(first)

    const second = await acquireImageUrl(url)
    expect(second).not.toBe(first)
    expect(fetchCalls).toBe(2)
  })

  it('загрузка, начатая до смены сессии, не попадает в кэш', async () => {
    let resolveFetch
    global.fetch = vi.fn(
      () =>
        new Promise((resolve) => {
          resolveFetch = () =>
            resolve({ ok: true, status: 200, blob: async () => ({ size: 1024 }) })
        }),
    )

    const pending = acquireImageUrl('/api/v1/photos/a/original')

    // Пользователь вышел, пока картинка грузилась.
    clearImageCache()
    resolveFetch()

    await expect(pending).rejects.toThrow('image session changed')
    expect(created).toHaveLength(0)
  })
})
