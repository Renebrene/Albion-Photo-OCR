// Tests for the API client wrapper (URL building, auth header, errors).
// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  buildFingerprintBatch,
  cancelJob,
  fetchFingerprintBatch,
  pauseJob,
  resumeJob,
  fetchMediaSearchJob,
  fetchPhotos,
  fetchRunActivity,
  fetchRunHistory,
  fetchRunLog,
  getToken,
  setToken,
  searchByMedia,
  searchByQuery,
  uploadPhotos,
  createHybridRun,
} from '../src/api/client'

// Minimal localStorage so the token helper works under the node environment.
if (!globalThis.localStorage) {
  const memory = new Map()
  globalThis.localStorage = {
    getItem: (key) => (memory.has(key) ? memory.get(key) : null),
    setItem: (key, value) => memory.set(key, String(value)),
    removeItem: (key) => memory.delete(key),
    clear: () => memory.clear(),
  }
}

function mockFetchOnce(response) {
  global.fetch = vi.fn().mockResolvedValue(response)
}

function okJson(body) {
  return { ok: true, status: 200, json: async () => body }
}

function errJson(status, body) {
  return { ok: false, status, json: async () => body }
}

describe('api client', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    delete global.fetch
  })

  it('stores and clears the bearer token', () => {
    expect(getToken()).toBeNull()
    setToken('abc')
    expect(getToken()).toBe('abc')
    setToken(null)
    expect(getToken()).toBeNull()
  })

  it('sends Authorization only when a token is set', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({ limit: 5 })
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()

    setToken('tok')
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({ limit: 5 })
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBe(
      'Bearer tok',
    )
  })

  it('builds repeated address/client/ids params', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({
      limit: 50,
      q: 'Luvio',
      address: ['78_v33', '79_v33'],
      client: ['Маркет'],
      ids: ['PH_a', 'PH_b'],
      collection_id: 3,
    })

    const url = global.fetch.mock.calls[0][0]
    expect(url).toContain('address=78_v33&address=79_v33')
    expect(url).toContain('client=%D0%9C%D0%B0%D1%80%D0%BA%D0%B5%D1%82')
    expect(url).toContain('ids=PH_a&ids=PH_b')
    expect(url).toContain('q=Luvio')
    expect(url).toContain('collection_id=3')
  })

  it('passes the date filter source only when set', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({ limit: 5, date_mode: 'capture' })
    expect(global.fetch.mock.calls[0][0]).toContain('date_mode=capture')
  })

  it('omits the date filter source by default', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchPhotos({ limit: 5 })
    expect(global.fetch.mock.calls[0][0]).not.toContain('date_mode')
  })

  it('throws a generic error on a failed GET', async () => {
    mockFetchOnce({ ok: false, status: 500, json: async () => ({}) })
    await expect(fetchPhotos({ limit: 5 })).rejects.toThrow('API error 500')
  })

  it('fetches the active recognition operation', async () => {
    mockFetchOnce(okJson({ active: { kind: 'scheduler', run_id: 4 }, message: 'идёт тик планировщика' }))
    const result = await fetchRunActivity()
    expect(global.fetch.mock.calls[0][0]).toContain('/v1/runs/activity')
    expect(result.active.kind).toBe('scheduler')
  })

  it('fetches run history with optional kind and limit', async () => {
    mockFetchOnce(okJson({ items: [] }))
    await fetchRunHistory({ kind: 'qwen', limit: 12 })
    expect(global.fetch.mock.calls[0][0]).toContain('/v1/runs/history?limit=12&kind=qwen')
    expect(global.fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()
  })

  it('fetches a run log as authenticated plain text', async () => {
    setToken('secret')
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200, text: async () => 'run log' })
    await expect(fetchRunLog(42)).resolves.toBe('run log')
    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/runs/history/42/log')
    expect(options.headers.Authorization).toBe('Bearer secret')
  })

  it('surfaces run-log missing and authorization errors', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(fetchRunLog(2)).rejects.toThrow('API error 404')
    mockFetchOnce({ ok: false, status: 403 })
    await expect(fetchRunLog(2)).rejects.toThrow('API error 403')
  })

  it('surfaces the server detail on a failed POST', async () => {
    mockFetchOnce(errJson(409, { detail: 'conflict here' }))
    await expect(createHybridRun(1)).rejects.toThrow('conflict here')
  })

  it('uploads files as multipart FormData', async () => {
    mockFetchOnce(okJson({ items: [], accepted: 1 }))
    const file = new File([new Uint8Array([1, 2, 3])], 'a.jpg', {
      type: 'image/jpeg',
    })

    await uploadPhotos([file])

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/upload')
    expect(options.method).toBe('POST')
    expect(options.body).toBeInstanceOf(FormData)
    // Browser must set the multipart boundary itself.
    expect(options.headers['Content-Type']).toBeUndefined()
  })

  it('sends one image as a media-search query', async () => {
    mockFetchOnce(okJson({ job_id: 7 }))
    const file = new File([new Uint8Array([1, 2, 3])], 'banner.jpg', {
      type: 'image/jpeg',
    })

    const result = await searchByMedia(file)

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/search/media')
    expect(options.method).toBe('POST')
    expect(options.body).toBeInstanceOf(FormData)
    expect(options.headers['Content-Type']).toBeUndefined()
    expect(result).toEqual({ job_id: 7 })
  })

  it('sends the edited tags with the manual query', async () => {
    mockFetchOnce(okJson({ job_id: 8 }))

    await searchByQuery({ q: 'щит', tags: ['баннер', 'дорога'] })

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/search/query')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body)).toEqual({
      q: 'щит',
      tags: ['баннер', 'дорога'],
    })
  })

  it('surfaces the server detail when the media search is rejected', async () => {
    mockFetchOnce(errJson(400, { detail: 'not a decodable image' }))
    const file = new File([new Uint8Array([1])], 'x.jpg', {
      type: 'image/jpeg',
    })

    await expect(searchByMedia(file)).rejects.toThrow('not a decodable image')
  })

  it('reads a media-search job by id', async () => {
    mockFetchOnce(okJson({ status: 'DONE', result: { photo_ids: [] } }))

    const job = await fetchMediaSearchJob(12)

    expect(global.fetch.mock.calls[0][0]).toContain('/v1/jobs/media-search/12')
    expect(job.status).toBe('DONE')
  })

  it('cancels a job by id', async () => {
    mockFetchOnce(okJson({ job_id: 12, status: 'CANCELLED' }))

    await cancelJob(12)

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/jobs/12/cancel')
    expect(options.method).toBe('POST')
  })
})


describe('fingerprint batch and job control', () => {
  it('queues a batch of builds', async () => {
    mockFetchOnce(okJson({ batch_id: 'abc', jobs: [{ job_id: 1 }], errors: [] }))

    const result = await buildFingerprintBatch({
      items: [{ fingerprint_id: '78_v33', folder: '/photos/78' }],
      max_photos: 30,
    })

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/v1/fingerprints/build-batch')
    expect(options.method).toBe('POST')
    expect(JSON.parse(options.body).max_photos).toBe(30)
    expect(result.batch_id).toBe('abc')
  })

  it('reads the batch state', async () => {
    mockFetchOnce(okJson({ total: 2, percent: 50 }))

    const state = await fetchFingerprintBatch('abc')

    expect(global.fetch.mock.calls[0][0]).toContain('/v1/fingerprints/batch/abc')
    expect(state.percent).toBe(50)
  })

  it('pauses and resumes one job', async () => {
    mockFetchOnce(okJson({ job_id: 7, status: 'PAUSED' }))
    await pauseJob(7)
    expect(global.fetch.mock.calls[0][0]).toContain('/v1/jobs/7/pause')

    mockFetchOnce(okJson({ job_id: 7, status: 'RUNNING' }))
    await resumeJob(7)
    expect(global.fetch.mock.calls[0][0]).toContain('/v1/jobs/7/resume')
  })
})
