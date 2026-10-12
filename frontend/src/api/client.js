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

export function fetchPhotos({
  limit = 50,
  cursor = null,
  q = null,
  address = null,
  client = null,
  date_from = null,
  date_to = null,
  collection_id = null,
} = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (q) params.set('q', q)
  if (address) params.set('address', address)
  if (client) params.set('client', client)
  if (date_from) params.set('date_from', date_from)
  if (date_to) params.set('date_to', date_to)
  if (collection_id) params.set('collection_id', String(collection_id))

  return getJson(`${BASE}/v1/photos?${params.toString()}`)
}

export function fetchCollections() {
  return getJson(`${BASE}/v1/collections`)
}

export function createCollection(payload) {
  return postJson(`${BASE}/v1/collections`, payload)
}

export function deleteCollection(collectionId) {
  return deleteJson(`${BASE}/v1/collections/${collectionId}`)
}

export function addCollectionMembers(collectionId, payload) {
  return postJson(`${BASE}/v1/collections/${collectionId}/members`, payload)
}

export function removeCollectionMembers(collectionId, payload) {
  return postJson(
    `${BASE}/v1/collections/${collectionId}/members/remove`,
    payload,
  )
}

export function fetchAddresses() {
  return getJson(`${BASE}/v1/addresses`)
}

export function fetchClients() {
  return getJson(`${BASE}/v1/clients`)
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

export function originalUrl(photoId) {
  return `${BASE}/v1/photos/${photoId}/original`
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

export function enqueueQwen(photoIds = null) {
  return postJson(`${BASE}/v1/jobs/qwen`, { photo_ids: photoIds })
}

async function putJson(url, body) {
  const response = await fetch(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    let detail = `API error ${response.status}`
    try {
      const payload = await response.json()
      if (payload && payload.detail) detail = payload.detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return response.json()
}

export function fetchQwenModels() {
  return getJson(`${BASE}/v1/qwen/models`)
}

async function deleteJson(url) {
  const response = await fetch(url, { method: 'DELETE' })

  if (!response.ok) {
    let detail = `API error ${response.status}`
    try {
      const payload = await response.json()
      if (payload && payload.detail) detail = payload.detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return response.json()
}

export function setQwenModel(model) {
  return putJson(`${BASE}/v1/qwen/model`, { model })
}

export function unloadQwen() {
  return postJson(`${BASE}/v1/qwen/unload`, {})
}
