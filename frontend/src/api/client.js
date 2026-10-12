// Thin wrapper around the read-only PhotoBAse API.
// In dev, /api is proxied to the FastAPI backend by Vite.

const BASE = import.meta.env.VITE_API_BASE || '/api'

async function getJson(url) {
  const response = await fetch(url)

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  return response.json()
}

function withCursor(path, { limit, cursor } = {}) {
  const params = new URLSearchParams()

  if (limit) params.set('limit', String(limit))
  if (cursor) params.set('cursor', String(cursor))

  const query = params.toString()

  return query ? `${path}?${query}` : path
}

export function fetchPhotos({ limit = 50, cursor = null, q = null } = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (q) params.set('q', q)

  return getJson(`${BASE}/v1/photos?${params.toString()}`)
}

export function fetchDinoBatches({ limit = 50, cursor = null } = {}) {
  return getJson(withCursor(`${BASE}/v1/batches/dino`, { limit, cursor }))
}

export function fetchDinoBatchRuns(batchId, { limit = 100, cursor = null } = {}) {
  return getJson(
    withCursor(`${BASE}/v1/batches/dino/${batchId}/runs`, { limit, cursor }),
  )
}

export function fetchHybridRuns({ limit = 50, cursor = null } = {}) {
  return getJson(withCursor(`${BASE}/v1/hybrid/runs`, { limit, cursor }))
}

export function previewUrl(photoId, size = 'small') {
  return `${BASE}/v1/photos/${photoId}/previews/${size}`
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let detail = `API error ${response.status}`
    try {
      const payload = await response.json()
      if (payload && payload.detail) detail = payload.detail
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail)
  }

  return response.json()
}

export function createDinoBatch({ run_type = 'NORMAL', photo_ids = null } = {}) {
  return postJson(`${BASE}/v1/jobs/dino-batch`, { run_type, photo_ids })
}

export function createHybridRun(dinoBatchId) {
  return postJson(`${BASE}/v1/jobs/hybrid`, { dino_batch_id: dinoBatchId })
}

export function fetchJobs({ limit = 50, cursor = null } = {}) {
  return getJson(withCursor(`${BASE}/v1/jobs`, { limit, cursor }))
}
