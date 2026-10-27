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

// url -> { objectUrl, refs }. AuthImage releases its reference on unmount, so a
// long browsing session does not accumulate blob URLs for every preview it has
// ever shown. `authImageUrl` keeps one permanent reference for one-off callers
// (the original-image viewer), which is bounded by how many originals the user
// actually opened.
const _imageCache = new Map()
const _imageInflight = new Map()
// Поколение кэша: растёт при смене пользователя (вход/выход). Загрузка,
// начатая под прошлым токеном, не должна попасть в кэш и достаться
// следующему пользователю — иначе Гость мог бы увидеть оригинал, который
// ему не разрешён.
let _imageGeneration = 0
// Недавно освобождённые картинки. Без этого прокрутка вниз-вверх заново
// качала и декодировала всё, что ушло за край экрана: «раньше уже было
// загружено» пропало, как только появилось освобождение blob URL.
// Держим небольшой запас: превью весят ~13 КБ, 400 штук — около 5 МБ.
const _imageRecent = new Map()
const RECENT_IMAGE_LIMIT = 400
// В recent попадают только превью: оригиналы из просмотрщика весят мегабайты,
// и 400 таких blob — это сотни мегабайт несосвобождаемой памяти.
const RECENT_BLOB_MAX_BYTES = 512 * 1024

export async function acquireImageUrl(url) {
  const cached = _imageCache.get(url)
  if (cached && cached.generation === _imageGeneration) {
    cached.refs += 1
    return cached.objectUrl
  }

  // Уже качали и недавно отпустили: blob ещё жив — отдаём без сети и без
  // повторного декодирования.
  const recent = _imageRecent.get(url)
  if (recent && recent.generation === _imageGeneration) {
    _imageRecent.delete(url)
    _imageCache.set(url, {
      objectUrl: recent.objectUrl,
      refs: 1,
      generation: _imageGeneration,
      size: recent.size,
    })
    return recent.objectUrl
  }

  if (_imageInflight.has(url)) {
    const objectUrl = await _imageInflight.get(url)
    const entry = _imageCache.get(url)
    if (entry) entry.refs += 1
    return objectUrl
  }

  const generation = _imageGeneration

  const task = (async () => {
    const response = await fetch(url, { headers: authHeaders() })

    if (!response.ok) {
      throw new Error(`image error ${response.status}`)
    }

    const blob = await response.blob()

    if (generation !== _imageGeneration) {
      // Пока грузили, пользователь сменился: blob принадлежит прошлой сессии
      // и не должен попасть ни в кэш, ни на экран.
      throw new Error('image session changed')
    }

    const objectUrl = URL.createObjectURL(blob)
    _imageCache.set(url, {
      objectUrl,
      refs: 1,
      generation,
      size: blob.size,
    })
    return objectUrl
  })()

  _imageInflight.set(url, task)

  try {
    return await task
  } finally {
    if (_imageInflight.get(url) === task) _imageInflight.delete(url)
  }
}

export function releaseImageUrl(url) {
  const entry = _imageCache.get(url)
  if (!entry) return

  entry.refs -= 1

  if (entry.refs > 0) return

  _imageCache.delete(url)

  // Кэш прошлой сессии или крупный оригинал в recent не держим.
  if (entry.generation !== _imageGeneration || entry.size > RECENT_BLOB_MAX_BYTES) {
    URL.revokeObjectURL(entry.objectUrl)
    return
  }

  _imageRecent.set(url, {
    objectUrl: entry.objectUrl,
    generation: entry.generation,
    size: entry.size,
  })

  // Переполнение — освобождаем самые старые: память остаётся ограниченной.
  while (_imageRecent.size > RECENT_IMAGE_LIMIT) {
    const oldest = _imageRecent.keys().next().value
    const dropped = _imageRecent.get(oldest)
    _imageRecent.delete(oldest)
    if (dropped) URL.revokeObjectURL(dropped.objectUrl)
  }
}

/** Permanent reference for one-off callers (opening an original in a tab). */
export function authImageUrl(url) {
  return acquireImageUrl(url)
}

export function clearImageCache() {
  // Новое поколение: незавершённые загрузки прошлой сессии не попадут в кэш,
  // а их blob будут освобождены при завершении.
  _imageGeneration += 1

  for (const entry of _imageCache.values()) {
    URL.revokeObjectURL(entry.objectUrl)
  }
  for (const entry of _imageRecent.values()) {
    URL.revokeObjectURL(entry.objectUrl)
  }
  _imageCache.clear()
  _imageRecent.clear()
  _imageInflight.clear()
}

/**
 * Ошибка запроса с причиной от сервера.
 *
 * Сервер отвечает `{"detail": ...}`; раньше GET показывал только код
 * («API error 422»), а обрыв сети уходил наверх английским «Failed to fetch».
 */
async function apiError(response) {
  let detail = `Не удалось выполнить запрос (код ${response.status})`

  try {
    const body = await response.json()

    if (body && typeof body.detail === 'string' && body.detail) {
      detail = body.detail
    } else if (body && Array.isArray(body.detail)) {
      // Ошибки валидации FastAPI приходят массивом объектов.
      const parts = body.detail
        .map((item) => (item && (item.msg || item.detail)) || '')
        .filter(Boolean)

      if (parts.length) detail = parts.join('; ')
    }
  } catch {
    // Тело не JSON — остаётся код состояния.
  }

  const error = new Error(detail)
  // Код состояния нужен вызывающим: «лог удалён» — это 404, а не текст.
  error.status = response.status
  return error
}

// Сколько ждать ответа. Без таймаута зависший сервер оставлял кнопку в
// состоянии «занято» навсегда: `useAsyncAction` снимает флаг в `finally`, а он
// не наступает. Долгие выгрузки (архив, оригинал) идут мимо этой функции, так
// что получаса запаса не требуется — хватает полминуты.
const REQUEST_TIMEOUT_MS = 30_000

function timeoutSignal(timeoutMs) {
  // `AbortSignal.timeout` есть не во всех окружениях: без него запрос идёт
  // как раньше, без таймаута — это лучше, чем падать на каждом запросе.
  return typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
    ? AbortSignal.timeout(timeoutMs)
    : undefined
}

function networkError(err) {
  // `AbortSignal.timeout` отклоняет запрос собственной ошибкой с именем
  // TimeoutError: показывать её как «нет связи» — сбивать с толку.
  if (err && err.name === 'TimeoutError') {
    return new Error(
      `Сервер не отвечает дольше ${Math.round(REQUEST_TIMEOUT_MS / 1000)} с — повторите`,
    )
  }

  if (err instanceof TypeError) {
    return new Error('Нет связи с сервером — проверьте подключение и повторите')
  }

  return err
}

/** Один путь для всех JSON-запросов: единый разбор ошибок. */
async function requestJson(url, { method = 'GET', body, keepalive = false, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  const options = {
    method,
    headers: authHeaders(),
    keepalive,
    signal: timeoutSignal(timeoutMs),
  }

  if (body !== undefined) {
    options.headers = authHeaders({ 'Content-Type': 'application/json' })
    options.body = JSON.stringify(body)
  }

  let response

  try {
    response = await fetch(url, options)
  } catch (err) {
    throw networkError(err)
  }

  if (!response.ok) throw await apiError(response)

  return response.json()
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
  return requestJson(url)
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
// Shared `date_from/date_to/date_mode` suffix for the grid-aware endpoints.
function dateQuery({ dateFrom = null, dateTo = null, dateMode = 'upload' } = {}) {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (dateMode) params.set('date_mode', dateMode)
  const text = params.toString()
  return text ? `?${text}` : ''
}

export function fetchStats(options = {}) {
  return getJson(`${BASE}/v1/stats${dateQuery(options)}`)
}

export function fetchLastRun() {
  return getJson(`${BASE}/v1/runs/last`)
}

export function fetchRunActivity() {
  return getJson(`${BASE}/v1/runs/activity`)
}

// Сводка виртуальной сортировки: совпадения, статус, режимы, текущий batch.
export function fetchSortStatus() {
  return getJson(`${BASE}/v1/sort/status`)
}

export function fetchRunHistory({ kind = null, limit = 20 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (kind) params.set('kind', kind)
  return getJson(`${BASE}/v1/runs/history?${params.toString()}`)
}

export async function fetchRunLog(runId) {
  const response = await fetch(
    `${BASE}/v1/runs/history/${encodeURIComponent(runId)}/log`,
    { headers: authHeaders() },
  )

  if (!response.ok) throw await apiError(response)

  return response.text()
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
  brand = null,
  tag = null,
  category = null,
  date_from = null,
  date_to = null,
  date_mode = null,
  combine = null,
  collection_id = null,
  ids = null,
  sort = null,
  order = null,
} = {}) {
  const params = new URLSearchParams()
  params.set('limit', String(limit))
  if (cursor) params.set('cursor', cursor)
  if (q) params.set('q', q)
  // `address`/`client` accept a single value or an array (OR semantics).
  if (address) [].concat(address).forEach((v) => params.append('address', v))
  if (client) [].concat(client).forEach((v) => params.append('client', v))
  // Structured values chosen from search suggestions: exact, not substring.
  if (brand) params.set('brand', brand)
  if (tag) params.set('tag', tag)
  if (category) params.set('category', category)
  if (date_from) params.set('date_from', date_from)
  if (date_to) params.set('date_to', date_to)
  // Date filter source: upload date (default) or EXIF capture date.
  if (date_mode) params.set('date_mode', date_mode)
  // How address and client selections combine (union|address|client).
  if (combine) params.set('combine', combine)
  // Порядок строк задаёт сервер (см. repository.list_photos).
  if (sort) params.set('sort', sort)
  if (order) params.set('order', order)
  if (collection_id) params.set('collection_id', String(collection_id))
  if (ids) [].concat(ids).forEach((v) => params.append('ids', v))

  return getJson(`${BASE}/v1/photos?${params.toString()}`)
}

export function fetchPhotoDetails(photoId) {
  return getJson(`${BASE}/v1/photos/${photoId}/details`)
}

// Ручная правка описания в карточке фото (scope photos:write).
export function savePhotoQwenText(photoId, payload) {
  return putJson(`${BASE}/v1/photos/${photoId}/qwen-text`, payload)
}

// Подсказки строки поиска: существующие теги/клиенты/бренды/категории
// и вариант в другой раскладке клавиатуры.
export function fetchSearchSuggestions(q, limit = 8) {
  const params = new URLSearchParams({ q, limit: String(limit) })
  return getJson(`${BASE}/v1/search/suggestions?${params.toString()}`)
}

// Остановить активные задания QWEN и очистить список завершённых.
export function stopQwenJobs() {
  return postJson(`${BASE}/v1/jobs/qwen/stop`, {})
}

export function clearQwenJobs() {
  return postJson(`${BASE}/v1/jobs/qwen/clear`, {})
}

// Прежние результаты QWEN: их вытеснила новая модель (schema/036).
export function fetchQwenHistory(photoId, limit = 10) {
  return getJson(
    `${BASE}/v1/photos/${photoId}/qwen-history?limit=${limit}`,
  )
}

export function fetchQwenHistoryLog(limit = 200) {
  return getJson(`${BASE}/v1/qwen/history?limit=${limit}`)
}

export function rescanQwenPeriod(payload) {
  return postJson(`${BASE}/v1/jobs/qwen/rescan`, payload)
}

// Non-destructive catch-up: only photos without a successful description.
export function scanQwenPeriod(payload) {
  return postJson(`${BASE}/v1/jobs/qwen/scan`, payload)
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

// Albion cloud links (schema/039): upload selected media and list ready links.
export function createMediaLinks({ photoIds = [], videoIds = [] } = {}) {
  return postJson(`${BASE}/v1/media-links`, {
    photo_ids: photoIds,
    video_ids: videoIds,
  })
}

// Albion storage settings: the token is never returned, only a mask.
export function fetchCloudSettings() {
  return getJson(`${BASE}/v1/cloud/settings`)
}

export function saveCloudSettings(payload) {
  return putJson(`${BASE}/v1/cloud/settings`, payload)
}

export function verifyCloudConnection() {
  return postJson(`${BASE}/v1/cloud/verify`, {})
}

export function fetchMediaLinks({ all = false, limit = 100, includeUnready = false } = {}) {
  const params = new URLSearchParams({
    all: all ? 'true' : 'false',
    limit: String(limit),
    include_unready: includeUnready ? 'true' : 'false',
  })
  return getJson(`${BASE}/v1/media-links?${params.toString()}`)
}

// Обёртка для загрузки фото в инбокс (`POST /v1/upload`). UI загрузки пока не
// сделан (см. §4.3 второго аудита), но контракт multipart проверяется тестом —
// поэтому обёртка остаётся, а не удаляется вместе с остальными неиспользуемыми.
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

// Smart search by one uploaded photo. The file is transient on the server:
// it is deleted once the worker finishes the job.
async function uploadMediaQuery(file, path, extra = {}) {
  const form = new FormData()
  form.append('file', file)

  for (const [key, value] of Object.entries(extra)) {
    if (value !== null && value !== undefined && value !== '') {
      form.append(key, String(value))
    }
  }

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
// frameSeconds — для видео: описать только кадр в эту секунду.
export function describeMediaSearch(file, frameSeconds = null) {
  const extra = frameSeconds === null || frameSeconds === undefined
    ? {}
    : { frame_seconds: frameSeconds }

  return uploadMediaQuery(file, '/v1/search/media/describe', extra)
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

export function deleteFingerprint(fingerprintId) {
  return deleteJson(
    `${BASE}/v1/fingerprints/registry/${encodeURIComponent(fingerprintId)}`,
  )
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

// --- Доступность оригиналов (технический раздел → Данные) --------------------
// Сводка по корням SCENE_ORIGINALS_ROOTS: подключён ли том и сколько записей на
// него ссылается. Только чтение (scope `read`) и без обхода файлов — пофайловая
// проверка живёт в scripts/check_originals.py.

export function fetchOriginalsHealth() {
  return getJson(`${BASE}/v1/originals/health`)
}

// Полная проверка файлов — заданием: 57 тыс. stat не ждут в HTTP-запросе.
export function startOriginalsCheck() {
  return postJson(`${BASE}/v1/originals/check`, {})
}

export function fetchOriginalsCheckLatest() {
  return getJson(`${BASE}/v1/originals/check/latest`)
}

// --- Бэкапы (технический раздел → Данные) ------------------------------------
// Читать может любой вошедший, запускать и восстанавливать — только
// Администратор: это scope settings:write.

export function fetchBackupStatus() {
  return getJson(`${BASE}/v1/backup/status`)
}

export function fetchBackupArchive(name) {
  return getJson(`${BASE}/v1/backup/archive/${encodeURIComponent(name)}`)
}

export function runBackupNow(parts, { allowSameFilesystem = false } = {}) {
  return postJson(`${BASE}/v1/backup/run`, {
    parts,
    allow_same_filesystem: allowSameFilesystem,
  })
}

export function runRestoreNow(payload) {
  return postJson(`${BASE}/v1/backup/restore`, payload)
}

export function saveBackupSettings(payload) {
  return putJson(`${BASE}/v1/backup/settings`, payload)
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

// Справочник алиасов: kind — 'client' (по умолчанию) или 'brand'.
export function fetchClientAliases(kind = 'client') {
  return getJson(`${BASE}/v1/client-aliases?kind=${kind}`)
}

export function saveClientAlias(alias, canonical, kind = 'client') {
  return putJson(
    `${BASE}/v1/client-aliases?kind=${kind}`,
    { alias, canonical },
  )
}

export function deleteClientAlias(alias, kind = 'client') {
  return deleteJson(
    `${BASE}/v1/client-aliases?alias=${encodeURIComponent(alias)}&kind=${kind}`,
  )
}

// Названия клиентов/брендов, распознанные QWEN, и журнал правок алиасов.
export function fetchQwenClientNames() {
  return getJson(`${BASE}/v1/client-aliases/qwen-names`)
}

export function fetchClientAliasAudit(limit = 100, kind = 'client') {
  return getJson(`${BASE}/v1/client-aliases/audit?limit=${limit}&kind=${kind}`)
}

// Журнал посещений (только Администратор).
export function fetchVisits(limit = 100) {
  return getJson(`${BASE}/v1/visits?limit=${limit}`)
}

// Address directory (schema/022): legal/simple names for fingerprint ids.
// Этап «Уточнение»: включение и параметры (ручного запуска нет).
export function fetchRefineSettings() {
  return getJson(`${BASE}/v1/refine/settings`)
}

export function saveRefineSettings(payload) {
  return putJson(`${BASE}/v1/refine/settings`, payload)
}

// Порог уверенности распознавания: ниже него фото уходит в «Требуют проверки».
export function fetchHybridSettings() {
  return getJson(`${BASE}/v1/hybrid/settings`)
}

/**
 * Сколько фото попадёт в «Требуют проверки» при таких порогах
 * (ничего не сохраняет).
 */
export function previewHybridSettings(lowScore, minMargin = 0) {
  const query = new URLSearchParams({
    low_score: String(lowScore),
    min_margin: String(minMargin),
  })

  return getJson(`${BASE}/v1/hybrid/settings/preview?${query.toString()}`)
}

export function saveHybridSettings(payload) {
  return putJson(`${BASE}/v1/hybrid/settings`, payload)
}

// `scope` — закладка справочника: «Экраны» (screens) или «Остальное» (other).
export function fetchAddressDirectory(scope = null) {
  const query = scope ? `?scope=${encodeURIComponent(scope)}` : ''
  return getJson(`${BASE}/v1/addresses/directory${query}`)
}

// Адреса, сведённые к сторонам: A(1), A(2), A(3) — одна строка (правило «Сайта»).
export function fetchAddressSides(scope = null) {
  const query = scope ? `?scope=${encodeURIComponent(scope)}` : ''
  return getJson(`${BASE}/v1/addresses/directory/grouped${query}`)
}

// Ручное исправление юридического адреса одного фото (scope addresses:write).
export function setPhotoAddressOverride(photoId, addressId) {
  return putJson(`${BASE}/v1/photos/${photoId}/address`, {
    address_id: addressId,
  })
}

export function clearPhotoAddressOverride(photoId) {
  return deleteJson(`${BASE}/v1/photos/${photoId}/address`)
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
export async function importAddresses(file, { dryRun = false, scope = 'other' } = {}) {
  const form = new FormData()
  form.append('file', file)

  // dry_run=1 — посчитать, что изменится, и ничего не записать;
  // scope — закладка, в которую попадут новые адреса.
  const params = new URLSearchParams()
  if (dryRun) params.set('dry_run', '1')
  if (scope) params.set('scope', scope)

  const query = params.toString() ? `?${params.toString()}` : ''

  // No Content-Type header: the browser sets the multipart boundary.
  const response = await fetch(`${BASE}/v1/addresses/import${query}`, {
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

export function saveSelection(state, options = {}) {
  return putJson(`${BASE}/v1/selection`, { state }, options)
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

export function fetchAddresses(options = {}) {
  const base = `${BASE}/v1/addresses${dateQuery(options)}`
  const clients = [].concat(options.clients || []).filter(Boolean)

  if (!clients.length) return getJson(base)

  const extra = clients
    .map((value) => `client=${encodeURIComponent(value)}`)
    .join('&')

  return getJson(`${base}${base.includes('?') ? '&' : '?'}${extra}`)
}

export function fetchClients({ addresses = [], cursor = null, limit = 0 } = {}) {
  const base = `${BASE}/v1/clients`
  const values = [].concat(addresses || []).filter(Boolean)
  const parts = values.map((value) => `address=${encodeURIComponent(value)}`)

  // Панель листает список при прокрутке: продолжение задаётся курсором,
  // размер страницы — тем же запросом.
  if (limit) parts.push(`limit=${encodeURIComponent(limit)}`)
  if (cursor) parts.push(`cursor=${encodeURIComponent(cursor)}`)

  if (!parts.length) return getJson(base)

  return getJson(`${base}?${parts.join('&')}`)
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

/**
 * Доступен ли оригинал: проверяется при открытии фото, до нажатия «скачать».
 * Ответ — `{photo_id, available, reason}`; путь наружу не отдаётся.
 */
export function fetchOriginalStatus(photoId) {
  return getJson(`${BASE}/v1/photos/${photoId}/original/status`)
}

/** Пересоздать превью: без списка — по всей базе, со списком — по photo_id. */
export function backfillPreviews({ photoIds = null, limit = 500 } = {}) {
  const query = new URLSearchParams({ limit: String(limit) })

  return postJson(
    `${BASE}/v1/previews/backfill?${query.toString()}`,
    photoIds && photoIds.length ? { photo_ids: photoIds } : {},
  )
}

async function postJson(url, body) {
  return requestJson(url, { method: 'POST', body })
}

export function createDinoBatch({
  run_type = 'NORMAL',
  photo_ids = null,
  auto_hybrid = false,
} = {}) {
  return postJson(`${BASE}/v1/jobs/dino-batch`, {
    run_type,
    photo_ids,
    auto_hybrid,
  })
}

export function createHybridRun(dinoBatchId) {
  return postJson(`${BASE}/v1/jobs/hybrid`, { dino_batch_id: dinoBatchId })
}

export function fetchJobs({ limit = 50, cursor = null } = {}) {
  return getJson(withCursor(`${BASE}/v1/jobs`, { limit, cursor }))
}

export function enqueueQwen(photoIds = null, onlyFailed = false, extra = {}) {
  return postJson(`${BASE}/v1/jobs/qwen`, {
    photo_ids: photoIds,
    only_failed: onlyFailed,
    // Разовая пересборка: конкретный провайдер/модель (кнопка «Пересканировать»).
    ...extra,
  })
}

export function fetchQwenStats() {
  return getJson(`${BASE}/v1/qwen/stats`)
}

async function putJson(url, body, { keepalive = false } = {}) {
  return requestJson(url, { method: 'PUT', body, keepalive })
}

export function fetchQwenModels() {
  return getJson(`${BASE}/v1/qwen/models`)
}

async function patchJson(url, body) {
  return requestJson(url, { method: 'PATCH', body })
}

async function deleteJson(url) {
  return requestJson(url, { method: 'DELETE' })
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

/**
 * Scan depth by time: `date_from`/`date_to` are inclusive YYYY-MM-DD bounds,
 * `date_mode` is 'upload' (the file's own date) or 'capture' (EXIF date).
 * No bounds — the whole folder, which is the pre-period behaviour.
 */
function periodBody(dateFrom = null, dateTo = null, dateMode = null) {
  const body = {}

  if (dateFrom) body.date_from = dateFrom
  if (dateTo) body.date_to = dateTo
  if (dateFrom || dateTo) body.date_mode = dateMode === 'capture' ? 'capture' : 'upload'

  return body
}

export function scanIngestFolder(path, period = {}) {
  return postJson(`${BASE}/v1/ingest/scan`, {
    path,
    ...periodBody(period.dateFrom, period.dateTo, period.dateMode),
  })
}

/** Enqueue an INSPECT run; without a path the configured folder is used. */
export function runIngest(path = null, period = {}) {
  return postJson(`${BASE}/v1/ingest/run`, {
    ...(path ? { path } : {}),
    ...periodBody(period.dateFrom, period.dateTo, period.dateMode),
  })
}
