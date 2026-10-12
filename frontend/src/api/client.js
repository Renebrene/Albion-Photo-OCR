// Thin wrapper around the read-only PhotoBAse API.
// In dev, /api is proxied to the FastAPI backend by Vite.

const BASE = import.meta.env.VITE_API_BASE || '/api'
const TOKEN_KEY = 'photobase_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

function authHeaders(extra = {}) {
  const token = getToken()
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra }
}

async function getJson(url) {
  const response = await fetch(url, { headers: authHeaders() })

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  return response.json()
}

export function login(name, password) {
  return postJson(`${BASE}/v1/auth/login`, { name, password })
}

export function logout() {
  return postJson(`${BASE}/v1/auth/logout`, {})
}

export function fetchMe() {
  return getJson(`${BASE}/v1/auth/me`)
}

export function fetchUsers(activeOnly = false) {
  return getJson(`${BASE}/v1/users?active_only=${activeOnly}`)
}

export function fetchSystem() {
  return getJson(`${BASE}/v1/system`)
}

export function fetchFingerprints() {
  return getJson(`${BASE}/v1/fingerprints`)
}

export function fetchLastRun() {
  return getJson(`${BASE}/v1/runs/last`)
}

export function createUser(payload) {
  return postJson(`${BASE}/v1/users`, payload)
}

export function updateUser(userId, payload) {
  return patchJson(`${BASE}/v1/users/${userId}`, payload)
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
  ids = null,
} = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (q) params.set('q', q)
  // `address`/`client` accept a single value or an array (OR semantics).
  if (address) [].concat(address).forEach((v) => params.append('address', v))
  if (client) [].concat(client).forEach((v) => params.append('client', v))
  if (date_from) params.set('date_from', date_from)
  if (date_to) params.set('date_to', date_to)
  if (collection_id) params.set('collection_id', String(collection_id))
  if (ids) [].concat(ids).forEach((v) => params.append('ids', v))

  return getJson(`${BASE}/v1/photos?${params.toString()}`)
}

export function fetchPhotoDetails(photoId) {
  return getJson(`${BASE}/v1/photos/${photoId}/details`)
}

export async function uploadPhotos(files) {
  const form = new FormData()
  for (const file of files) form.append('files', file)

  // No Content-Type header: the browser sets the multipart boundary.
  const response = await fetch(`${BASE}/v1/upload`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
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

export function enqueueNlSearch(query) {
  return postJson(`${BASE}/v1/jobs/nl-search`, { query })
}

export function fetchNlSearchJob(jobId) {
  return getJson(`${BASE}/v1/jobs/nl-search/${jobId}`)
}

export function fetchAutomation() {
  return getJson(`${BASE}/v1/automation`)
}

export function updateAutomation(payload) {
  return putJson(`${BASE}/v1/automation`, payload)
}

export function runAutomation(force = false) {
  return postJson(`${BASE}/v1/automation/run?force=${force}`, {})
}

export function fetchDataStorage() {
  return getJson(`${BASE}/v1/data/storage`)
}

export async function fetchDataExport(format = 'json') {
  const response = await fetch(`${BASE}/v1/data/export?format=${format}`, {
    headers: authHeaders(),
  })

  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }

  return response
}

export function fetchSavedSearches() {
  return getJson(`${BASE}/v1/searches`)
}

export function createSavedSearch(payload) {
  return postJson(`${BASE}/v1/searches`, payload)
}

export function deleteSavedSearch(searchId) {
  return deleteJson(`${BASE}/v1/searches/${searchId}`)
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
    headers: authHeaders({ 'Content-Type': 'application/json' }),
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
    headers: authHeaders({ 'Content-Type': 'application/json' }),
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

async function patchJson(url, body) {
  const response = await fetch(url, {
    method: 'PATCH',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
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

async function deleteJson(url) {
  const response = await fetch(url, {
    method: 'DELETE',
    headers: authHeaders(),
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

export function setQwenModel(model) {
  return putJson(`${BASE}/v1/qwen/model`, { model })
}

export function unloadQwen() {
  return postJson(`${BASE}/v1/qwen/unload`, {})
}
