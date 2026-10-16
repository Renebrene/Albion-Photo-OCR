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

export function authHeaders(extra = {}) {
  const token = getToken()
  return token ? { ...extra, Authorization: `Bearer ${token}` } : { ...extra }
}

// --- authenticated media -----------------------------------------------------
// <img>/window.open cannot attach a bearer token, so media is fetched with
// auth and turned into a blob object URL.

const _imageCache = new Map()
const _imageInflight = new Map()

export async function authImageUrl(url) {
  if (_imageCache.has(url)) return _imageCache.get(url)
  if (_imageInflight.has(url)) return _imageInflight.get(url)

  const task = (async () => {
    const response = await fetch(url, { headers: authHeaders() })

    if (!response.ok) {
      throw new Error(`image error ${response.status}`)
    }

    const objectUrl = URL.createObjectURL(await response.blob())
    _imageCache.set(url, objectUrl)

    return objectUrl
  })()

  _imageInflight.set(url, task)

  try {
    return await task
  } finally {
    _imageInflight.delete(url)
  }
}

export function clearImageCache() {
  for (const objectUrl of _imageCache.values()) {
    URL.revokeObjectURL(objectUrl)
  }
  _imageCache.clear()
}

export async function downloadAuthenticated(url, filename) {
  const response = await fetch(url, { headers: authHeaders() })

  if (!response.ok) {
    throw new Error(`download error ${response.status}`)
  }

  const objectUrl = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename || 'download'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

// ZIP of the selected photos: the server assembles it, the browser saves the
// blob (a plain link could not carry the token).
export async function downloadArchive(items, filename = 'photobase.zip') {
  const response = await fetch(`${BASE}/v1/photos/archive`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ items }),
  })

  if (!response.ok) {
    let detail = `ошибка ${response.status}`

    try {
      const body = await response.json()

      if (body && body.detail) detail = body.detail
    } catch {
      // No body: the status code is all we have.
    }

    throw new Error(detail)
  }

  const objectUrl = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
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

// Counts for the status bar: photos, addresses, clients, last upload.
export function fetchStats() {
  return getJson(`${BASE}/v1/stats`)
}

export function fetchFingerprints() {
  return getJson(`${BASE}/v1/fingerprints`)
}

export function fetchLastRun() {
  return getJson(`${BASE}/v1/runs/last`)
}

// ---- resumable pipeline run ("Обновление базы") ----
// The supervisor only becomes visible once schema/031 is applied; before that
// these return 404 and the header control hides itself.

export function fetchCurrentPipeline() {
  return getJson(`${BASE}/v1/pipeline/current`)
}

export function fetchPipelineRuns(limit = 20) {
  return getJson(`${BASE}/v1/pipeline?limit=${limit}`)
}

export function startPipeline(payload = {}) {
  return postJson(`${BASE}/v1/pipeline/start`, payload)
}

export function stopPipeline(runId) {
  return postJson(`${BASE}/v1/pipeline/${runId}/stop`, {})
}

export function resumePipeline(runId) {
  return postJson(`${BASE}/v1/pipeline/${runId}/resume`, {})
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
  date_mode = null,
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
  // Date filter source: upload date (default) or EXIF capture date.
  if (date_mode) params.set('date_mode', date_mode)
  if (collection_id) params.set('collection_id', String(collection_id))
  if (ids) [].concat(ids).forEach((v) => params.append('ids', v))

  return getJson(`${BASE}/v1/photos?${params.toString()}`)
}

export function fetchPhotoDetails(photoId) {
  return getJson(`${BASE}/v1/photos/${photoId}/details`)
}

// Durable video library (separate from photo-only DINO/HYBRID/QWEN).
export function fetchVideos({ limit = 50, cursor = null, q = null, date_from = null, date_to = null, date_mode = 'upload' } = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  params.set('date_mode', date_mode)
  if (cursor) params.set('cursor', cursor)
  if (q) params.set('q', q)
  if (date_from) params.set('date_from', date_from)
  if (date_to) params.set('date_to', date_to)
  return getJson(`${BASE}/v1/videos?${params.toString()}`)
}

export function fetchVideo(videoId) {
  return getJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}`)
}

export function updateVideoTitle(videoId, display_title) {
  return putJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/title`, { display_title })
}

export function requestVideoPlayback(videoId) {
  return postJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/playback-ticket`, {})
}

export function requestVideoDownload(videoId) {
  return postJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/download-ticket`, {})
}

export function enqueueVideoTranscode(videoId, profile) {
  return postJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/transcodes`, { profile })
}

export function fetchVideoTranscode(videoId, profile) {
  return getJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/transcodes/${encodeURIComponent(profile)}`)
}

export function requestVideoDerivativeIdDownload(videoId, derivativeId) {
  return postJson(
    `${BASE}/v1/videos/${encodeURIComponent(videoId)}/derivatives/${Number(derivativeId)}/download-ticket`,
    {},
  )
}

export function requestVideoDerivativeDownload(videoId, profile) {
  return postJson(
    `${BASE}/v1/videos/${encodeURIComponent(videoId)}/transcodes/${encodeURIComponent(profile)}/download-ticket`,
    {},
  )
}

export function enqueueVideoStoryboard(videoId) {
  return postJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/storyboard`, {})
}

export function videoStoryboardFrameUrl(videoId, index) {
  return `${BASE}/v1/videos/${encodeURIComponent(videoId)}/storyboard/${Number(index)}`
}

export function enqueueVideoTrim(videoId, start_seconds, end_seconds) {
  return postJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/trim`, { start_seconds, end_seconds })
}

export function fetchVideoTrim(videoId, start_seconds, end_seconds) {
  const params = new URLSearchParams({ start_seconds: String(start_seconds), end_seconds: String(end_seconds) })
  return getJson(`${BASE}/v1/videos/${encodeURIComponent(videoId)}/trim?${params}`)
}

export function videoPosterUrl(videoId) {
  return `${BASE}/v1/videos/${encodeURIComponent(videoId)}/poster`
}

export function fetchMediaStatistics() {
  return getJson(`${BASE}/v1/media/statistics`)
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

// Smart search by one uploaded photo. The file is transient on the server:
// it is deleted once the worker finishes the job.
async function uploadMediaQuery(file, path) {
  const form = new FormData()
  form.append('file', file)

  // No Content-Type header: the browser sets the multipart boundary.
  const response = await fetch(`${BASE}${path}`, {
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

// Авто-режим: описать и сразу искать.
export function searchByMedia(file) {
  return uploadMediaQuery(file, '/v1/search/media')
}

// Ручной режим, шаг 1: только описание QWEN (поля для правки).
export function describeMediaSearch(file) {
  return uploadMediaQuery(file, '/v1/search/media/describe')
}

// Ручной режим, шаг 2: поиск по поправленным фильтрам.
export function searchByQuery(filters) {
  return postJson(`${BASE}/v1/search/query`, filters)
}

export function fetchMediaSearchJob(jobId) {
  return getJson(`${BASE}/v1/jobs/media-search/${jobId}`)
}

export function cancelJob(jobId) {
  return postJson(`${BASE}/v1/jobs/${jobId}/cancel`, {})
}

// Fingerprint registry (schema/023): names, versions, archiving.
export function fetchFingerprintRegistry() {
  return getJson(`${BASE}/v1/fingerprints/registry`)
}

export function syncFingerprints() {
  return postJson(`${BASE}/v1/fingerprints/sync`, {})
}

export function updateFingerprint(fingerprintId, payload) {
  return putJson(
    `${BASE}/v1/fingerprints/registry/${encodeURIComponent(fingerprintId)}`,
    payload,
  )
}

export function buildFingerprint(payload) {
  return postJson(`${BASE}/v1/fingerprints/build`, payload)
}

export function browseFolders(path = null) {
  const suffix = path ? `?path=${encodeURIComponent(path)}` : ''
  return getJson(`${BASE}/v1/fingerprints/browse${suffix}`)
}

export function pickFolderNative() {
  return postJson(`${BASE}/v1/fingerprints/pick-folder`, {})
}

export function pauseJob(jobId) {
  return postJson(`${BASE}/v1/jobs/${jobId}/pause`, {})
}

export function resumeJob(jobId) {
  return postJson(`${BASE}/v1/jobs/${jobId}/resume`, {})
}

export function buildFingerprintBatch(payload) {
  return postJson(`${BASE}/v1/fingerprints/build-batch`, payload)
}

export function fetchFingerprintBatch(batchId) {
  return getJson(`${BASE}/v1/fingerprints/batch/${batchId}`)
}

export function fetchJob(jobId) {
  return getJson(`${BASE}/v1/jobs/${jobId}`)
}

export function fetchFingerprintVersions(fingerprintId) {
  return getJson(
    `${BASE}/v1/fingerprints/registry/${encodeURIComponent(fingerprintId)}/versions`,
  )
}

// Montage of the source photos, saved with the fingerprint at build time.
// Older fingerprints have none until they are rebuilt (the request 404s).
// `version` busts the image cache: a rebuild keeps the id, so without it the
// browser would keep showing the montage of the previous build.
export function fingerprintPreviewUrl(fingerprintId, version = '') {
  const url = `${BASE}/v1/fingerprints/registry/${encodeURIComponent(fingerprintId)}/preview`

  return version ? `${url}?v=${encodeURIComponent(version)}` : url
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

export function fetchClientAliases() {
  return getJson(`${BASE}/v1/client-aliases`)
}

export function saveClientAlias(alias, canonical) {
  return putJson(`${BASE}/v1/client-aliases`, { alias, canonical })
}

export function deleteClientAlias(alias) {
  return deleteJson(
    `${BASE}/v1/client-aliases?alias=${encodeURIComponent(alias)}`,
  )
}

// Названия клиентов/брендов, распознанные QWEN, и журнал правок алиасов.
export function fetchQwenClientNames() {
  return getJson(`${BASE}/v1/client-aliases/qwen-names`)
}

export function fetchClientAliasAudit(limit = 100) {
  return getJson(`${BASE}/v1/client-aliases/audit?limit=${limit}`)
}

// Журнал посещений (только Администратор).
export function fetchVisits(limit = 100) {
  return getJson(`${BASE}/v1/visits?limit=${limit}`)
}

// Address directory (schema/022): legal/simple names for fingerprint ids.
export function fetchAddressDirectory() {
  return getJson(`${BASE}/v1/addresses/directory`)
}

export function fetchUnassignedFingerprints() {
  return getJson(`${BASE}/v1/addresses/unassigned`)
}

export function createAddress(payload) {
  return postJson(`${BASE}/v1/addresses/directory`, payload)
}

export function updateAddress(addressId, payload) {
  return putJson(`${BASE}/v1/addresses/directory/${addressId}`, payload)
}

export function deleteAddress(addressId) {
  return deleteJson(`${BASE}/v1/addresses/directory/${addressId}`)
}

// Import legal addresses from a spreadsheet (.xlsx/.csv) into the directory.
export async function importAddresses(file) {
  const form = new FormData()
  form.append('file', file)

  // No Content-Type header: the browser sets the multipart boundary.
  const response = await fetch(`${BASE}/v1/addresses/import`, {
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

// Map a fingerprint to an address from the directory (null clears it).
export function setFingerprintAddress(fingerprintId, addressId) {
  return putJson(
    `${BASE}/v1/fingerprints/registry/${encodeURIComponent(fingerprintId)}/address`,
    { address_id: addressId },
  )
}

export function setAddressFingerprints(addressId, fingerprints) {
  return putJson(`${BASE}/v1/addresses/directory/${addressId}/fingerprints`, {
    fingerprints,
  })
}

export function fetchSelection() {
  return getJson(`${BASE}/v1/selection`)
}

export function saveSelection(state) {
  return putJson(`${BASE}/v1/selection`, { state })
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

// Состав подборки: адреса, клиенты или фото (по умолчанию — фото).
export function fetchCollectionMembers(collectionId, memberType = 'photo') {
  return getJson(
    `${BASE}/v1/collections/${collectionId}/members` +
      `?member_type=${encodeURIComponent(memberType)}`,
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

export function enqueueQwen(photoIds = null, onlyFailed = false) {
  return postJson(`${BASE}/v1/jobs/qwen`, {
    photo_ids: photoIds,
    only_failed: onlyFailed,
  })
}

export function fetchQwenStats() {
  return getJson(`${BASE}/v1/qwen/stats`)
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

export function fetchQwenSettings() {
  return getJson(`${BASE}/v1/qwen/settings`)
}

export function updateQwenSettings(payload) {
  return putJson(`${BASE}/v1/qwen/settings`, payload)
}

export function unloadQwen() {
  return postJson(`${BASE}/v1/qwen/unload`, {})
}

// ---- working (source) folder for INGEST ----

export function fetchIngestFolder() {
  return getJson(`${BASE}/v1/ingest/folder`)
}

export function saveIngestFolder(path) {
  return putJson(`${BASE}/v1/ingest/folder`, { path })
}

export function scanIngestFolder(path) {
  return postJson(`${BASE}/v1/ingest/scan`, { path })
}

/** Enqueue an INGEST run; without a path the configured folder is used. */
export function runIngest(path = null) {
  return postJson(`${BASE}/v1/ingest/run`, path ? { path } : {})
}
