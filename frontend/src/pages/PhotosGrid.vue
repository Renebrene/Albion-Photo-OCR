<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Notify } from 'quasar'

import {
  authImageUrl,
  cancelJob,
  enqueueQwen,
  fetchJob,
  describeMediaSearch,
  downloadArchive,
  downloadAuthenticated,
  fetchMediaSearchJob,
  fetchPhotoDetails,
  fetchSearchSuggestions,
  fetchRunActivity,
  savePhotoQwenText,
  fetchAddressDirectory,
  clearPhotoAddressOverride,
  setPhotoAddressOverride,
  fetchQwenHistory,
  fetchQwenSettings,
  originalUrl,
  previewUrl,
  searchByMedia,
  searchByQuery,
} from '../api/client'
import AuthImage from '../components/AuthImage.vue'
import CloudLinkButton from '../components/CloudLinkButton.vue'
import ClientNormalization from '../components/ClientNormalization.vue'
import CollectionsPanel from '../components/CollectionsPanel.vue'
import ResizeHandle from '../components/ResizeHandle.vue'
import DisplaySettings from '../components/DisplaySettings.vue'
import {
  AUTO_TILE_MIN_WIDTH,
  LIST_FIELDS,
  downloadFileName,
  fieldText,
  sortPhotos,
  useDisplayStore,
} from '../stores/display'
import { usePhotosStore } from '../stores/photos'
import { useSessionStore } from '../stores/session'
import { PERIODS, periodRange } from '../utils/periodRange'

const store = usePhotosStore()
const display = useDisplayStore()
const session = useSessionStore()

// Гость (read-only) не работает с подборками и «Избранным»: это писательские
// функции (scopes searches:write / collections:write). В открытом локальном
// режиме ограничивать нечего.
const canUseCollective = computed(() => {
  if (!session.authEnabled) return true
  return ['Администратор', 'Менеджер'].includes(session.user?.role)
})

// Поиск по загруженному фото/видео требует searches:write — у Гостя его нет.
const canSearchMedia = canUseCollective

const { items, error, loading, addresses, clients, savedSearches } =
  storeToRefs(store)

const q = ref('')
const dateMode = ref('upload')

// ---- smart search by an uploaded photo (item 2; photos only for now) ----
const mediaInput = ref(null)
const mediaFile = ref(null) // the chosen File, kept in memory until ПОИСК
const mediaJobId = ref(null)
const mediaStage = ref('')
const mediaBusy = ref(false)
const qwenElapsedSeconds = ref(0)
const manualQwenRunning = ref(false)
let qwenTimer = null

const mediaName = computed(() => (mediaFile.value ? mediaFile.value.name : ''))

function startQwenElapsed() {
  if (qwenTimer !== null) return
  qwenElapsedSeconds.value = 0
  qwenTimer = window.setInterval(() => {
    qwenElapsedSeconds.value += 1
  }, 1000)
}

function stopQwenElapsed() {
  if (qwenTimer !== null) window.clearInterval(qwenTimer)
  qwenTimer = null
  manualQwenRunning.value = false
}

const mediaStageText = computed(() => {
  if (mediaStage.value === 'qwen') {
    return `Распознаётся… ${qwenElapsedSeconds.value} с`
  }
  return ({
    queued: 'в очереди…',
    search: 'поиск по базе…',
  })[mediaStage.value] || 'обработка…'
})

const manualQwenText = computed(() => {
  if (manualStage.value !== 'describing') return ''
  if (manualQwenRunning.value) return `Распознаётся… ${qwenElapsedSeconds.value} с`
  if (qwenElapsedSeconds.value > 0) return `QWEN завершил за ${qwenElapsedSeconds.value} с`
  return 'В очереди QWEN…'
})
// По умолчанию — все фото: грид подгружает их страницами по мере прокрутки.
const period = ref('all')
const customFrom = ref(null)
const customTo = ref(null)

// Grid presentation (mirrors the legacy list/tile toggle + sorting).
const viewMode = ref('tiles')
const sortKey = ref('filename')
const sortDirection = ref('asc')

const sortOptions = [
  { label: 'По имени файла', value: 'filename' },
  { label: 'По адресу', value: 'address' },
  { label: 'По клиенту', value: 'client' },
  { label: 'По дате съёмки', value: 'date' },
]

const sortedItems = computed(() =>
  sortPhotos(items.value, sortKey.value, sortDirection.value),
)

function toggleSortDirection() {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
}

const viewerOpen = ref(false)
const current = ref(null)
const details = ref(null)
const detailsLoading = ref(false)
// Прежние результаты распознавания: что перезаписала новая модель.
const qwenHistory = ref([])

// Разовая пересборка описания одного фото (локально или в облаке).
const rescanBusy = ref(false)
const qwenModels = ref({})

// Пересборка — рабочая задача распознавания (scope jobs:write).
const canRunQwen = computed(() => {
  if (!session.authEnabled) return true
  return ['Администратор', 'Менеджер'].includes(session.user?.role)
})

async function loadQwenModels() {
  try {
    const data = await fetchQwenSettings()
    qwenModels.value = data.models || {}
  } catch {
    qwenModels.value = {}
  }
}

// Ждём завершения задания: воркер берёт его со очереди.
async function waitForQwenJob(jobId, attempts = 60) {
  for (let i = 0; i < attempts; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 1500))
    const job = await fetchJob(jobId)
    if (['DONE', 'FAILED', 'CANCELLED'].includes(job.status)) return job
  }
  return null
}

async function rescanPhoto(provider) {
  if (!current.value || rescanBusy.value) return

  rescanBusy.value = true
  const photoId = current.value.photo_id

  try {
    const result = await enqueueQwen([photoId], false, provider ? { provider } : {})

    if (!result.first_job_id) {
      Notify.create({
        type: 'info',
        message: 'Это фото уже стоит в очереди распознавания',
      })
      return
    }

    Notify.create({
      type: 'info',
      message:
        provider === 'openai'
          ? 'Распознаётся в облаке…'
          : 'Распознаётся локально…',
    })

    const job = await waitForQwenJob(result.first_job_id)

    if (!job) {
      Notify.create({ type: 'warning', message: 'Задание всё ещё выполняется' })
    } else if (job.status === 'DONE') {
      Notify.create({ type: 'positive', message: 'Описание обновлено' })
    } else {
      Notify.create({
        type: 'negative',
        message: `Распознавание: ${job.status}${job.error_message ? ` — ${job.error_message}` : ''}`,
      })
    }

    await loadDetails(current.value)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    rescanBusy.value = false
  }
}

function historyLine(item) {
  const when = item.replaced_at
    ? String(item.replaced_at).replace('T', ' ').slice(0, 16)
    : '—'

  return `${item.qwen_model || 'модель неизвестна'} · ${when}`
}

const qwenHistoryText = computed(() =>
  qwenHistory.value
    .map((item) => {
      const tags = Array.isArray(item.tags)
        ? item.tags.join(', ')
        : (item.tags || '')
      return [
        `${historyLine(item)} · ${item.status || '—'}`,
        `клиент: ${item.client || '—'}, бренд: ${item.brand || '—'}, категория: ${item.category || '—'}`,
        `теги: ${tags || '—'}`,
        item.description || '—',
      ].join('\n')
    })
    .join('\n\n'),
)

// Display settings (tile count / list fields); the same panel also lives in
// the technical section (component DisplaySettings).
const settingsOpen = ref(false)
const gridScrollEl = ref(null)

// Ширина контейнера грида: нужна, чтобы в режиме «Авто» посчитать колонки
// заново при перетаскивании границ панелей.
const gridWidth = ref(0)
let gridObserver = null

const effectiveColumns = computed(() => {
  if (display.tileColumns !== 'auto') return display.tileColumns

  const width = gridWidth.value || 0

  if (!width) return 4

  return Math.max(1, Math.min(8, Math.floor(width / AUTO_TILE_MIN_WIDTH)))
})

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${effectiveColumns.value}, minmax(0, 1fr))`,
}))

function stopGridObserver() {
  if (gridObserver) {
    gridObserver.disconnect()
    gridObserver = null
  }
}

function scrollToTop() {
  if (gridScrollEl.value) gridScrollEl.value.scrollTop = 0
}

// "В подборку" dialog: подборка хранит выбор адресов или клиентов.
const bucketOpen = ref(false)
const bucketId = ref(null)
// Какие подборки показывает диалог: адресные или клиентские.
const bucketScope = ref('addresses')
const newName = ref('')
// Существующие подборки того же вида, что и сохраняемый выбор.
const bucketOptions = computed(() =>
  store.collectionsFor(bucketScope.value).map((collection) => ({
    label: collection.name,
    value: collection.collection_id,
  })),
)
// Имена отмеченных значений для диалога: у адресов в выборе лежит
// технический id (79_v33), а показывать нужно понятное имя.
const bucketValues = computed(() => {
  const values =
    bucketScope.value === 'clients'
      ? store.selectedClients
      : store.selectedAddresses

  if (bucketScope.value === 'clients') return values

  return values.map((value) => {
    const found = addresses.value.find((item) => item.address === value)
    const name = found && (found.name || found.address)

    return name && name !== value ? `${name} (${value})` : value
  })
})

const dateModes = [
  { label: 'Дата загрузки', value: 'upload' },
  { label: 'Дата съёмки', value: 'capture' },
]

const periods = PERIODS

// "Выбрать / снять" is one button: it flips between the two states.
const allLoadedSelected = computed(
  () =>
    items.value.length > 0 &&
    items.value.every((photo) => store.isSelected(photo.photo_id)),
)

function toggleSelectAll() {
  if (allLoadedSelected.value) {
    store.clearSelection()
  } else {
    store.selectAllCurrent()
  }
}

// Диапазоны дат считает общий модуль (локальный календарь, см. его шапку).
function currentDates() {
  return periodRange(period.value, {
    customFrom: customFrom.value,
    customTo: customTo.value,
  })
}

// Пока идёт пайплайн, адреса HYBRID и статусы QWEN меняются на месте:
// обновляем уже показанные строки, не сбрасывая прокрутку.
let pipelineSyncTimer = null
let pipelineSyncTick = 0

async function syncDuringPipeline() {
  try {
    const data = await fetchRunActivity()

    if (!data.active) return

    await store.syncLoaded()
    pipelineSyncTick += 1

    if (pipelineSyncTick % 3 === 0) await store.loadFacets()
  } catch {
    // Фоновое обновление не должно влиять на работу грида.
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)

  // Вход на главную всегда начинает с полного грида: старые выделения
  // адресов/клиентов, строка поиска и период не восстанавливаются.
  store.selectedAddresses = []
  store.selectedClients = []
  store.collectionId = null
  store.addressCollectionId = null
  store.clientCollectionId = null
  store.nlIds = []
  q.value = ''
  period.value = 'all'
  customFrom.value = null
  customTo.value = null
  dateMode.value = 'upload'

  await store.loadFacets()
  loadQwenModels()
  apply()

  if (gridScrollEl.value) gridScrollEl.value.scrollTop = 0
  pipelineSyncTimer = window.setInterval(syncDuringPipeline, 10_000)
  await nextTick()

  if (gridScrollEl.value && typeof ResizeObserver !== 'undefined') {
    gridObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) {
        gridWidth.value = entry.contentRect.width
        // Height-only resizes can turn a previously scrollable grid into an
        // underfilled one; width changes also alter the number of columns.
        if (store.hasMore) void fillGridUntilScrollable()
      }
    })
    gridObserver.observe(gridScrollEl.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  stopGridObserver()
  stopQwenElapsed()

  if (suggestTimer !== null) window.clearTimeout(suggestTimer)
  if (pipelineSyncTimer !== null) window.clearInterval(pipelineSyncTimer)
})

// Arrow keys page through the gallery in the order it is displayed.
function onKeydown(event) {
  if (!viewerOpen.value) return

  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    stepPhoto(-1)
  } else if (event.key === 'ArrowRight') {
    event.preventDefault()
    stepPhoto(1)
  }
}

async function apply(overrideQuery = undefined) {
  // Кнопка очистки Quasar присылает update:modelValue(null) раньше, чем
  // v-model записывает значение в q, поэтому пустой запрос передаётся явно.
  const query = overrideQuery === undefined
    ? String(q.value || '').trim()
    : String(overrideQuery || '').trim()

  const [dateFrom, dateTo] = currentDates()
  await store.applyFilters({
    q: query,
    addresses: [...store.selectedAddresses],
    clients: [...store.selectedClients],
    dateFrom,
    dateTo,
    dateMode: dateMode.value,
    collectionId: store.collectionId,
  })
}

// Пока в строке поиска есть текст, фильтр клиентов/брендов неактивен:
// два фильтра одновременно не смешиваются.
const textSearchActive = computed(
  () => String(q.value || '').trim() !== '',
)

// ---- очистка строки поиска ------------------------------------------------
// Обрабатывается событиями самого поля (не watcher'ом): кнопка × присылает
// @clear, а удаление текста — обычный @update:model-value. Оба пути ведут к
// одному применению фильтра, повторный запрос не отправляется.

let hadSearchTerm = false

function onSearchInput(value) {
  const term = String(value || '').trim()

  scheduleSuggestions(value)

  if (term !== '') {
    hadSearchTerm = true
    return
  }

  if (hadSearchTerm) {
    hadSearchTerm = false
    apply('')
  }
}

function onSearchClear() {
  // Некоторые версии Quasar присылают @clear без @update:model-value —
  // на этот случай грид обновляется здесь. Флаг делает вызов идемпотентным.
  if (!hadSearchTerm) return

  hadSearchTerm = false
  apply('')
}

// ---- подсказки строки поиска и проверка раскладки -------------------------

const suggestItems = ref([])
const suggestLayout = ref(null)
const suggestOpen = ref(false)
let suggestTimer = null
let suggestMuted = false

const SUGGESTION_KINDS = {
  tag: 'тег',
  client: 'клиент',
  brand: 'бренд',
  category: 'категория',
  address: 'адрес',
}

const SUGGESTION_ICONS = {
  tag: 'sell',
  client: 'business',
  brand: 'storefront',
  category: 'category',
  address: 'place',
}

function suggestionKind(kind) {
  return SUGGESTION_KINDS[kind] || kind
}

function suggestionIcon(kind) {
  return SUGGESTION_ICONS[kind] || 'search'
}

function scheduleSuggestions(value) {
  if (suggestTimer !== null) window.clearTimeout(suggestTimer)

  // Выбор подсказки программно меняет q — повторный запрос не нужен.
  if (suggestMuted) {
    suggestMuted = false
    return
  }

  const term = String(value || '').trim()

  if (term.length < 2) {
    suggestItems.value = []
    suggestLayout.value = null
    suggestOpen.value = false
    return
  }

  suggestTimer = window.setTimeout(() => loadSuggestions(term), 250)
}

async function loadSuggestions(term) {
  try {
    const data = await fetchSearchSuggestions(term)

    // Пока шёл запрос, строку уже изменили — старые подсказки не показываем.
    if (String(q.value || '').trim() !== term) return

    suggestItems.value = data.items || []
    suggestLayout.value = data.layout || null
    suggestOpen.value = Boolean(suggestItems.value.length || suggestLayout.value)
  } catch {
    suggestItems.value = []
    suggestLayout.value = null
  }
}

function pickSuggestion(value) {
  if (value !== String(q.value || '')) suggestMuted = true

  q.value = value
  suggestOpen.value = false
  suggestItems.value = []
  suggestLayout.value = null
  apply(value)
}

function toggleValue(list, value) {
  const index = list.indexOf(value)
  if (index === -1) list.push(value)
  else list.splice(index, 1)
}

async function pickAddress(address) {
  toggleValue(store.selectedAddresses, address)
  await apply()
}

async function pickClient(client) {
  toggleValue(store.selectedClients, client)
  await apply()
}

async function selectAllAddresses() {
  store.selectedAddresses = addresses.value.map((item) => item.address)
  await apply()
}

async function clearAddresses() {
  store.selectedAddresses = []
  await apply()
}

async function selectAllClients() {
  store.selectedClients = clients.value.map((item) => item.client)
  await apply()
}

async function clearClients() {
  store.selectedClients = []
  await apply()
}

async function reset() {
  q.value = ''
  period.value = 'all'
  customFrom.value = null
  customTo.value = null
  store.selectedAddresses = []
  store.selectedClients = []
  store.collectionId = null
  store.addressCollectionId = null
  store.clientCollectionId = null
  store.clearSelection()
  await apply()
}

// ---- smart search by an uploaded photo ----

function pickMedia() {
  // Гость не имеет searches:write — поиск по файлу ему недоступен.
  if (!canSearchMedia.value) return

  mediaInput.value?.click()
}

// ---- ручной режим: модалка с превью, метаданными и правкой полей QWEN ----
const autoMode = ref(true) // галочка «Авто» активна по умолчанию
const manualOpen = ref(false)
const manualStage = ref('idle') // idle | describing | ready | searching
const manualJobId = ref(null)
const manualFile = ref(null)
const manualMeta = ref(null)
const manualPreviewUrl = ref(null)
const manualModel = ref('')
const manualFields = ref({ description: '', client: '', brand: '', category: '', tags: '' })
const manualIsVideo = ref(false)
const manualVideoRef = ref(null)
const manualDuration = ref(0)
const manualResolution = ref('')
const manualCodec = ref('')
const manualFrameSec = ref(0)

function onMediaChosen(event) {
  const [file] = Array.from(event.target.files || [])
  event.target.value = '' // allow re-picking the same file

  if (file) {
    // A media query and a text query are mutually exclusive.
    q.value = ''
  }

  if (autoMode.value) {
    mediaFile.value = file || null
  } else if (file) {
    openManual(file)
  }
}

function openManual(file) {
  manualFile.value = file
  manualStage.value = 'idle'
  manualFields.value = { description: '', client: '', brand: '', category: '', tags: '' }
  manualMeta.value = { sizeMb: (file.size / 1048576).toFixed(1), date: new Date(file.lastModified).toLocaleString() }
  manualIsVideo.value = file.type.startsWith('video/')
  manualDuration.value = 0
  manualResolution.value = ''
  manualCodec.value = ''
  manualFrameSec.value = 0
  // И фото, и видео показываются из локального файла (без сервера).
  manualPreviewUrl.value = manualIsVideo.value || file.type.startsWith('image/')
    ? URL.createObjectURL(file)
    : null
  manualOpen.value = true

  fetchQwenSettings()
    .then((data) => { manualModel.value = data?.model || '' })
    .catch(() => { manualModel.value = '' })
}

// Длительность и разрешение берём из локального <video> сразу.
function onVideoMeta(event) {
  manualDuration.value = Math.round(event.target.duration || 0)
  manualResolution.value = `${event.target.videoWidth}×${event.target.videoHeight}`
}

function onVideoSeek(event) {
  // Слайдер двигает сам плеер, чтобы кадр было видно.
  if (manualDuration.value) event.target.currentTime = manualFrameSec.value
}

function seekToFrame() {
  const el = manualVideoRef.value
  if (el) el.currentTime = manualFrameSec.value
}

async function closeManual() {
  // Закрытие во время распознавания отменяет job (если она ещё активна).
  if (manualJobId.value && manualStage.value === 'describing') {
    try { await cancelJob(manualJobId.value) } catch { /* best-effort */ }
  }
  stopQwenElapsed()
  manualJobId.value = null
  manualOpen.value = false
  if (manualPreviewUrl.value) URL.revokeObjectURL(manualPreviewUrl.value)
  manualPreviewUrl.value = null
  manualFile.value = null
}

function onPreviewLoad(event) {
  if (!manualMeta.value) return
  manualMeta.value = { ...manualMeta.value, width: event.target.naturalWidth, height: event.target.naturalHeight }
}

async function runDescribe() {
  if (!manualFile.value || manualStage.value === 'describing') return
  stopQwenElapsed()
  qwenElapsedSeconds.value = 0
  manualStage.value = 'describing'

  try {
    const frameSeconds = manualIsVideo.value ? manualFrameSec.value : null
    const upload = await describeMediaSearch(manualFile.value, frameSeconds)
    const { job_id: jobId } = upload
    manualJobId.value = jobId
    if (upload?.media?.codec) manualCodec.value = upload.media.codec
    let job = null
    for (let i = 0; i < 60; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      job = await fetchMediaSearchJob(jobId)

      if (job.status === 'RUNNING') {
        if (job.progress?.stage === 'готово') {
          stopQwenElapsed()
        } else {
          manualQwenRunning.value = true
          startQwenElapsed()
        }
      }
      if (['DONE', 'FAILED', 'CANCELLED'].includes(job.status)) break
    }
    stopQwenElapsed()
    manualJobId.value = null
    if (!job || job.status !== 'DONE') {
      manualStage.value = 'idle'
      Notify.create({ type: 'negative', message: `Распознавание: ${job ? job.status : 'таймаут'}` })
      return
    }
    const qwen = (job.result && job.result.qwen) || {}
    manualFields.value = {
      description: qwen.description || '',
      client: qwen.client || '',
      brand: qwen.brand || '',
      category: qwen.category || '',
      tags: Array.isArray(qwen.tags) ? qwen.tags.join(', ') : '',
    }
    manualStage.value = 'ready'
  } catch (err) {
    stopQwenElapsed()
    manualStage.value = 'idle'
    Notify.create({ type: 'negative', message: err.message })
  }
}

// Теги вводятся строкой через запятую; пустые/дубли отбрасываются.
const manualTags = computed(() =>
  String(manualFields.value.tags || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag, index, all) => tag && all.indexOf(tag) === index),
)

// Пустой запрос сервер отвергает (422) — не даём нажать «Поиск» зря.
const manualHasTerms = computed(() => Boolean(
  manualFields.value.description?.trim()
  || manualFields.value.client?.trim()
  || manualFields.value.brand?.trim()
  || manualFields.value.category?.trim()
  || manualTags.value.length,
))

async function runManualSearch() {
  if (manualStage.value === 'searching') return
  manualStage.value = 'searching'

  try {
    const fields = manualFields.value
    const tags = manualTags.value
    const { job_id: jobId } = await searchByQuery({
      q: fields.description || null,
      client: fields.client || null,
      brand: fields.brand || null,
      category: fields.category || null,
      tags: tags.length ? tags : null,
    })
    let job = null
    for (let i = 0; i < 40; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      job = await fetchMediaSearchJob(jobId)
      if (['DONE', 'FAILED', 'CANCELLED'].includes(job.status)) break
    }
    if (!job || job.status !== 'DONE') {
      manualStage.value = 'ready'
      Notify.create({ type: 'negative', message: `Поиск: ${job ? job.status : 'таймаут'}` })
      return
    }
    const ids = (job.result && job.result.photo_ids) || []
    Notify.create({ type: 'info', message: `ИИ-поиск: найдено ${ids.length}` })
    await store.applyNlResults(ids)
    closeManual()
  } catch (err) {
    manualStage.value = 'ready'
    Notify.create({ type: 'negative', message: err.message })
  }
}


function clearMedia() {
  stopQwenElapsed()
  mediaFile.value = null
  mediaStage.value = ''
  store.applyNlResults([])
}

async function runMediaSearch() {
  if (!mediaFile.value || mediaBusy.value) return

  stopQwenElapsed()
  mediaBusy.value = true
  mediaStage.value = 'queued'

  try {
    const { job_id: jobId } = await searchByMedia(mediaFile.value)
    mediaJobId.value = jobId

    let job = null

    // QWEN needs a few seconds per image; poll until the worker publishes it.
    for (let i = 0; i < 60; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      job = await fetchMediaSearchJob(jobId)

      if (job.status === 'RUNNING') {
        if (job.progress?.stage === 'готово') {
          mediaStage.value = 'search'
          stopQwenElapsed()
        } else {
          mediaStage.value = 'qwen'
          startQwenElapsed()
        }
      }
      if (['DONE', 'FAILED', 'CANCELLED'].includes(job.status)) break
    }

    if (!job || job.status === 'CANCELLED') {
      Notify.create({ type: 'info', message: 'Поиск остановлен' })
      return
    }

    if (job.status !== 'DONE') {
      Notify.create({
        type: 'negative',
        message: `ИИ-поиск: ${job ? job.status : 'таймаут'}`,
      })
      return
    }

    const result = job.result || {}
    const ids = result.photo_ids || []
    const truncated = result.truncated
    const described = result.qwen && result.qwen.description

    Notify.create({
      type: truncated ? 'warning' : 'info',
      message: truncated
        ? `ИИ-поиск: показаны первые ${ids.length} (есть ещё совпадения)`
        : `ИИ-поиск: найдено ${ids.length}${
            described ? ` — «${described}»` : ''
          }`,
    })

    await store.applyNlResults(ids)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    stopQwenElapsed()
    mediaBusy.value = false
    mediaJobId.value = null
    mediaStage.value = ''
  }
}

async function stopMediaSearch() {
  if (!mediaJobId.value) return

  stopQwenElapsed()
  try {
    await cancelJob(mediaJobId.value)
    Notify.create({ type: 'info', message: 'Поиск остановлен' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

// ---- saved searches ----

const saveSearchOpen = ref(false)
const saveSearchName = ref('')

function openSaveSearch() {
  saveSearchName.value = ''
  saveSearchOpen.value = true
}

async function saveSearch() {
  const name = saveSearchName.value.trim()
  if (!name) {
    Notify.create({ type: 'warning', message: 'Введите название поиска' })
    return
  }
  try {
    await store.saveCurrentSearch(name)
    Notify.create({ type: 'positive', message: 'Поиск сохранён' })
    saveSearchOpen.value = false
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function applySavedSearch(search) {
  const filters = search.filters || {}

  q.value = filters.q || ''
  store.collectionId = filters.collection_id || null

  const from = filters.date_from || null
  const to = filters.date_to || null
  customFrom.value = from
  customTo.value = to
  period.value = from || to ? 'custom' : 'all'
  dateMode.value = filters.date_mode === 'capture' ? 'capture' : 'upload'

  await store.applyFilters({
    q: q.value,
    addresses: filters.addresses || [],
    clients: filters.clients || [],
    dateFrom: from,
    dateTo: to,
    dateMode: dateMode.value,
    collectionId: filters.collection_id || null,
  })
}

async function removeSavedSearch(search) {
  try {
    await store.deleteSavedSearchById(search.search_id)
    Notify.create({ type: 'positive', message: 'Поиск удалён' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function openBucketDialog(scope = 'addresses') {
  const values =
    scope === 'clients' ? store.selectedClients : store.selectedAddresses

  if (!values.length) {
    Notify.create({
      type: 'info',
      message:
        scope === 'clients'
          ? 'Сначала отметьте клиентов в правой панели'
          : 'Сначала отметьте адреса в левой панели',
    })
    return
  }

  bucketScope.value = scope
  await store.loadCollections()
  bucketId.value = null
  newName.value = ''
  bucketOpen.value = true
}

async function saveToBucket() {
  const name = newName.value.trim()

  if (!bucketId.value && !name) {
    Notify.create({ type: 'warning', message: 'Введите название подборки' })
    return
  }

  try {
    await store.saveSelectionAsCollection({
      name,
      scope: bucketScope.value,
      collectionId: bucketId.value || null,
    })

    Notify.create({ type: 'positive', message: 'Подборка сохранена' })
    bucketOpen.value = false
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

// ---- подпись плитки ----

/** Дата съёмки как «17.07.2025» (пустая строка, если её нет). */
function tileDate(photo) {
  const value = photo && photo.taken_at

  if (!value) return ''

  const [date] = String(value).split(/[T ]/)
  const [year, month, day] = date.split('-')

  return year && month && day ? `${day}.${month}.${year}` : date
}

/** Вес файла в мегабайтах, одна цифра после запятой. */
function tileSize(photo) {
  const bytes = Number(photo && photo.size_bytes)

  if (!bytes) return ''

  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

/** «дата · вес» одной строкой; пусто, когда нет ни того, ни другого. */
function tileMeta(photo) {
  return [tileDate(photo), tileSize(photo)].filter(Boolean).join(' · ')
}

/** «клиент · бренд» для карточки; пусто, когда распознавания ещё нет. */
function clientBrand(photo) {
  return [photo?.client, photo?.brand].filter(Boolean).join(', ')
}

// Значок QWEN на плитке/в списке: зелёный — описание есть, оранжевый —
// в очереди/процессе, красный — ошибка, серый — описания ещё нет.
function qwenColor(photo) {
  if (photo?.qwen_status === 'FAILED') return 'negative'
  if (photo?.qwen_status === 'PENDING' || photo?.qwen_status === 'RUNNING') {
    return 'orange'
  }
  if (photo?.qwen_described) return 'positive'
  return 'grey'
}

function qwenHint(photo) {
  if (photo?.qwen_status === 'FAILED') return 'QWEN: ошибка'
  if (photo?.qwen_status === 'PENDING') return 'QWEN: в очереди'
  if (photo?.qwen_status === 'RUNNING') return 'QWEN: распознаётся'
  if (photo?.qwen_described) return 'QWEN: описание есть'
  return 'QWEN: описания нет'
}

// ZIP: one server-built archive instead of a file per photo.
const zipBusy = ref(false)

async function downloadZip() {
  if (!store.selectedCount) return

  zipBusy.value = true

  try {
    // Do not name this local `items`: it would shadow the loaded photo list
    // (`items.value`) used in the initializer and hit its temporal dead zone.
    const archiveItems = [...store.selected].map((photoId) => ({
      photo_id: photoId,
      // The same name the single-file download would use.
      name: downloadFileName(
        items.value.find((photo) => photo.photo_id === photoId) || {
          photo_id: photoId,
        },
        display.downloadNameMode,
      ),
    }))

    await downloadArchive(archiveItems)

    Notify.create({
      type: 'positive',
      message: `Архив собран: ${archiveItems.length} фото`,
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    zipBusy.value = false
  }
}

async function downloadSelected() {
  if (!store.selectedCount) {
    Notify.create({ type: 'info', message: 'Сначала выберите фото' })
    return
  }

  for (const photoId of [...store.selected]) {
    // Use the real file name, not the PH_… id (item 11 of the UI backlog);
    // the address prefix follows the display settings (item 11b).
    const photo = items.value.find((item) => item.photo_id === photoId)
    try {
      await downloadAuthenticated(
        originalUrl(photoId),
        downloadFileName(photo || { photo_id: photoId }, display.downloadNameMode),
      )
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
      break
    }
  }
}

// Постепенная подгрузка: следующий лист запрашивается при прокрутке, а если
// текущие карточки не создали полосу прокрутки — автоматически добираем страницы.
let pageLoadPromise = null
let gridFillPromise = null

async function loadNextPhotoPage() {
  if (pageLoadPromise) return pageLoadPromise
  if (!store.hasMore || store.loading) return false

  const previousCount = items.value.length
  const previousCursor = store.nextCursor

  pageLoadPromise = (async () => {
    await store.loadPage()
    await nextTick()

    return (
      items.value.length > previousCount
      && store.nextCursor !== previousCursor
    )
  })()

  try {
    return await pageLoadPromise
  } finally {
    pageLoadPromise = null
  }
}

async function fillGridUntilScrollable() {
  if (gridFillPromise) return gridFillPromise

  gridFillPromise = (async () => {
    await nextTick()

    while (store.hasMore && !store.loading && !error.value) {
      const el = gridScrollEl.value
      // Hidden/not-yet-laid-out containers have no measurable viewport. Do not
      // drain every page just because both scroll metrics are zero.
      if (!el || el.clientHeight <= 0 || el.scrollHeight > el.clientHeight + 1) break

      const advanced = await loadNextPhotoPage()
      if (!advanced) break
    }
  })().finally(() => {
    gridFillPromise = null
  })

  return gridFillPromise
}

// Pinia exposes page completion as items/cursor plus loading=false. Run after
// DOM patch so scrollHeight reflects the newly rendered cards. This also covers
// initial load and every filter/collection refresh without depending on scroll.
watch(
  () => [items.value.length, store.nextCursor, loading.value],
  ([, , isLoading]) => {
    if (!isLoading && store.hasMore) void fillGridUntilScrollable()
  },
  { flush: 'post' },
)

async function onGridScroll(event) {
  const el = event.target
  if (!(el instanceof HTMLElement)) return

  // When the user reaches the end, keep loading until there is meaningful
  // scroll room; a single appended page may still leave the viewport at bottom.
  while (
    store.hasMore
    && el.scrollTop + el.clientHeight >= el.scrollHeight - 600
  ) {
    const advanced = await loadNextPhotoPage()
    if (!advanced) break
  }
}

async function loadMorePhotos() {
  await loadNextPhotoPage()
  await fillGridUntilScrollable()
}

// ---- ручное исправление юридического адреса -------------------------------

const addressEditOpen = ref(false)
const addressOptions = ref([])
const addressChoice = ref(null)
const addressSaving = ref(false)

function addressLabel(item) {
  const legal = item.legal_address || ''
  const simple = item.simple_address || ''

  if (legal && simple && simple !== legal) return `${legal} · ${simple}`

  return legal || simple || item.address
}

async function openAddressEditor() {
  addressChoice.value = details.value?.address_override?.address_id || null
  addressEditOpen.value = true

  try {
    const data = await fetchAddressDirectory()
    addressOptions.value = (data.items || [])
      .filter((item) => item.active)
      .map((item) => ({ address_id: item.address_id, label: addressLabel(item) }))
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function saveAddressOverride() {
  if (!current.value || !addressChoice.value || addressSaving.value) return

  addressSaving.value = true

  try {
    await setPhotoAddressOverride(current.value.photo_id, addressChoice.value)
    Notify.create({ type: 'positive', message: 'Юридический адрес обновлён' })
    addressEditOpen.value = false
    await loadDetails(current.value)
    await store.refresh()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    addressSaving.value = false
  }
}

async function resetAddressOverride() {
  if (!current.value || addressSaving.value) return

  addressSaving.value = true

  try {
    await clearPhotoAddressOverride(current.value.photo_id)
    Notify.create({ type: 'info', message: 'Исправление снято' })
    addressEditOpen.value = false
    await loadDetails(current.value)
    await store.refresh()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    addressSaving.value = false
  }
}

// ---- ручная правка текстового описания QWEN -------------------------------

const qwenEditOpen = ref(false)
const qwenEditSaving = ref(false)
const qwenEditFields = ref({
  description: '',
  client: '',
  brand: '',
  category: '',
  tags: '',
})

function openQwenEditor() {
  const meta = qwen.value || {}

  qwenEditFields.value = {
    description: meta.description || '',
    client: meta.client || '',
    brand: meta.brand || '',
    category: meta.category || '',
    tags: Array.isArray(meta.tags) ? meta.tags.join(', ') : '',
  }

  qwenEditOpen.value = true
}

async function saveQwenEditor() {
  if (!current.value || qwenEditSaving.value) return

  qwenEditSaving.value = true

  try {
    const fields = qwenEditFields.value
    const tags = fields.tags
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean)

    await savePhotoQwenText(current.value.photo_id, {
      description: fields.description || null,
      client: fields.client || null,
      brand: fields.brand || null,
      category: fields.category || null,
      tags,
    })

    Notify.create({ type: 'positive', message: 'Описание сохранено' })
    qwenEditOpen.value = false
    await loadDetails(current.value)
    await store.syncLoaded()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    qwenEditSaving.value = false
  }
}

async function loadDetails(photo) {
  try {
    details.value = await fetchPhotoDetails(photo.photo_id)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }

  // История — вспомогательный блок: её отсутствие не должно ломать карточку.
  try {
    qwenHistory.value = (await fetchQwenHistory(photo.photo_id, 10)).items || []
  } catch {
    qwenHistory.value = []
  }
}

async function open(photo) {
  current.value = photo
  details.value = null
  qwenHistory.value = []
  viewerOpen.value = true
  detailsLoading.value = true

  try {
    await loadDetails(photo)
  } finally {
    detailsLoading.value = false
  }
}

function viewerUrl() {
  return current.value ? previewUrl(current.value.photo_id, 'middle') : ''
}

// ---- viewer gallery navigation (arrows + left/right keys) ----

const viewerIndex = computed(() =>
  current.value
    ? sortedItems.value.findIndex(
        (photo) => photo.photo_id === current.value.photo_id,
      )
    : -1,
)

const canPrev = computed(() => viewerIndex.value > 0)
const canNext = computed(
  () => viewerIndex.value >= 0 && viewerIndex.value < sortedItems.value.length - 1,
)

async function stepPhoto(delta) {
  const target = sortedItems.value[viewerIndex.value + delta]

  if (target) await open(target)
}

function fieldLabel(key) {
  const option = LIST_FIELDS.find((item) => item.value === key)
  return option ? option.label : key
}

// Поля, которые уже показаны двумя основными строками списка: повторять их
// третьей строкой незачем.
const LIST_CAPTION_FIELDS = ['filename', 'address', 'client', 'brand', 'taken_at']

function extraListFields(photo) {
  return display.listFields
    .filter((field) => !LIST_CAPTION_FIELDS.includes(field))
    .map((field) => `${fieldLabel(field)}: ${fieldText(photo, field)}`)
}


async function openOriginal(photo) {
  try {
    const objectUrl = await authImageUrl(originalUrl(photo.photo_id))
    window.open(objectUrl, '_blank')
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function saveOriginal(photo) {
  try {
    await downloadAuthenticated(
      originalUrl(photo.photo_id),
      downloadFileName(photo, display.downloadNameMode),
    )
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

/** Из меню снимка: сохранить его адрес в подборку адресов. */
async function addOneToBucket(photo) {
  const address = photo.address

  if (!address) {
    Notify.create({
      type: 'info',
      message: 'У снимка нет распознанного адреса',
    })
    return
  }

  if (!store.selectedAddresses.includes(address)) {
    store.selectedAddresses = [...store.selectedAddresses, address]
    await store.refresh()
  }

  await openBucketDialog('addresses')
}

// QWEN metadata for the open photo (may be null when it has not run).
const qwen = computed(() => (details.value ? details.value.qwen : null))


// The open photo: the freshly fetched copy, falling back to the grid row
// (which already carries the same fields, minus the QWEN metadata).
const info = computed(
  () => (details.value && details.value.photo) || current.value || null,
)

// QWEN status shown in the viewer: grey "НЕТ" (no result), red "!!!" (error),
// orange "..." (queued or running) and green "ЕСТЬ" (done).
const QWEN_STATUS = {
  DONE: { label: 'ЕСТЬ', color: 'positive' },
  FAILED: { label: '!!!', color: 'negative' },
  PENDING: { label: '...', color: 'orange' },
  RUNNING: { label: '...', color: 'orange' },
}

function qwenStatus(meta) {
  if (!meta || !meta.status) return { label: 'НЕТ', color: 'grey' }
  return QWEN_STATUS[meta.status] || { label: '...', color: 'orange' }
}

function day(value) {
  return value ? String(value).slice(0, 10) : '—'
}

function pixels(photo) {
  return photo?.width && photo?.height ? `${photo.width}×${photo.height}` : '—'
}

function megabytes(bytes) {
  if (bytes === null || bytes === undefined) return '—'
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

function tagList(meta) {
  const tags = meta?.tags
  return Array.isArray(tags) ? tags : []
}
</script>

<template>
  <q-page class="photos-page q-pa-md">
    <div class="row no-wrap full-height">
      <!-- LEFT: адреса + подборки; складывается кнопкой у края -->
      <div
        v-if="display.leftPanelOpen"
        class="left-panel q-pr-xs"
        :style="{ width: display.leftPanelWidth + 'px', flex: '0 0 auto' }"
      >
        <q-card
          flat bordered
          class="column"
          :style="{ height: display.sideListHeight + 'px' }"
        >
          <q-card-section class="panel-head q-pb-xs row items-center">
            <div class="panel-title col">Адреса</div>
            <!-- Одна кнопка: пока ничего не выбрано — «Все», иначе «Снять». -->
            <q-btn
              dense
              flat
              size="sm"
              :label="store.selectedAddresses.length ? 'Снять' : 'Все'"
              @click="
                store.selectedAddresses.length
                  ? clearAddresses()
                  : selectAllAddresses()
              "
            >
              <q-tooltip>
                {{
                  store.selectedAddresses.length
                    ? 'Снять выделение адресов'
                    : 'Выбрать все адреса'
                }}
              </q-tooltip>
            </q-btn>
          </q-card-section>
          <q-separator />
          <q-scroll-area class="col">
            <q-list dense>
              <q-item
                v-for="item in addresses"
                :key="item.address"
                clickable
                :active="store.selectedAddresses.includes(item.address)"
                active-class="bg-primary text-white"
                @click="pickAddress(item.address)"
              >
                <q-item-section>
                  {{ item.name }}
                  <q-tooltip v-if="item.name !== item.address">
                    {{ item.address }}
                  </q-tooltip>
                </q-item-section>
                <q-item-section side>{{ item.count }}</q-item-section>
              </q-item>
              <q-item v-if="!addresses.length">
                <q-item-section class="text-caption text-grey">
                  Нет адресов
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card>

        <ResizeHandle
          direction="horizontal"
          title="Потяните, чтобы изменить высоту списка адресов"
          @resize="(delta) => display.resizeSideList(delta)"
        />

        <CollectionsPanel
          v-if="canUseCollective"
          scope="addresses"
          @create="openBucketDialog"
        />
      </div>

      <ResizeHandle
        v-if="display.leftPanelOpen"
        direction="vertical"
        title="Потяните, чтобы изменить ширину левой панели"
        @resize="(delta) => display.resizePanel('left', delta)"
      />

      <!-- RIGHT: toolbar + grid with its own vertical scroll -->
      <div class="col column full-height q-px-xs">
        <!-- unified search bar: Enter = Поиск, camera = search by a photo -->
        <div class="row items-center q-gutter-sm q-mb-sm">
          <div class="col relative-position">
            <q-input
              v-model="q"
              dense
              outlined
              clearable
              :disable="!!mediaFile"
              :placeholder="
                mediaFile ? '' : 'Название файла, клиент, бренд, адрес'
              "
              @keyup.enter="apply()"
              @update:model-value="onSearchInput"
              @clear="onSearchClear"
            >
              <template #prepend>
                <q-icon :name="mediaFile ? 'image' : 'search'" />
              </template>
            </q-input>

            <!-- Подсказки по существующим значениям + проверка раскладки -->
            <q-menu
              v-model="suggestOpen"
              anchor="bottom left"
              self="top left"
              :offset="[0, 4]"
              no-focus
            >
              <q-list dense style="min-width: 320px; max-width: 520px">
                <q-item
                  v-if="suggestLayout"
                  clickable
                  @click="pickSuggestion(suggestLayout.query)"
                >
                  <q-item-section avatar>
                    <q-icon name="keyboard" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>
                      Похоже, набрано в другой раскладке
                    </q-item-label>
                    <q-item-label caption>
                      {{ suggestLayout.query }}
                    </q-item-label>
                  </q-item-section>
                </q-item>

                <q-item
                  v-for="item in suggestItems"
                  :key="`${item.kind}:${item.value}`"
                  clickable
                  @click="pickSuggestion(item.value)"
                >
                  <q-item-section avatar>
                    <q-icon :name="suggestionIcon(item.kind)" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ item.value }}</q-item-label>
                    <q-item-label caption>
                      {{ suggestionKind(item.kind) }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </div>

          <!-- the chosen image is named right in the search row -->
          <q-chip
            v-if="canSearchMedia && mediaFile"
            dense
            removable
            color="teal"
            text-color="white"
            icon="photo_camera"
            @remove="clearMedia"
          >
            {{ mediaName }} (фото)
          </q-chip>

          <q-checkbox
            v-if="canSearchMedia"
            v-model="autoMode"
            dense
            size="sm"
            label="Авто"
            :disable="mediaBusy"
          >
            <q-tooltip>
              Авто: выбранный файл сразу распознаётся и ищется. Выкл.: откроется
              окно с превью, метаданными и правкой полей QWEN.
            </q-tooltip>
          </q-checkbox>

          <q-btn
            v-if="canSearchMedia"
            dense
            flat
            icon="photo_camera"
            :disable="mediaBusy"
            @click="pickMedia"
          >
            <q-tooltip>Умный поиск по фото или видео</q-tooltip>
          </q-btn>
          <input
            ref="mediaInput"
            type="file"
            accept="image/jpeg,image/png,video/mp4,video/quicktime,.jpg,.jpeg,.png,.mp4,.m4v,.mov,.mpeg,.mpg"
            class="hidden-input"
            @change="onMediaChosen"
          />

          <!-- ПОИСК turns into ИИ-поиск for an image, and into СТОП while it runs -->
          <q-btn
            v-if="mediaBusy"
            dense
            color="negative"
            icon="stop"
            label="Стоп"
            @click="stopMediaSearch"
          />
          <q-btn
            v-else-if="mediaFile"
            dense
            color="teal"
            icon="auto_awesome"
            label="ИИ-поиск"
            @click="runMediaSearch"
          />
          <q-btn
            v-else
            dense
            color="primary"
            icon="search"
            label="Поиск"
            @click="apply"
          />

          <q-spinner-dots v-if="mediaBusy" color="teal" size="24px" />
          <span v-if="mediaBusy" class="text-caption text-grey">
            {{ mediaStageText }}
          </span>

          <q-btn dense flat icon="refresh" :disable="mediaBusy" @click="store.refresh()">
            <q-tooltip>Обновить</q-tooltip>
          </q-btn>
          <q-btn dense flat icon="restart_alt" :disable="mediaBusy" @click="reset">
            <q-tooltip>Сбросить фильтры и результаты поиска</q-tooltip>
          </q-btn>
        </div>

        <!-- Действия над выбором, сортировка, вид и настройки — одной строкой.
             Выбранные адреса и клиенты здесь не повторяются: их подсвечивают
             боковые панели. -->
        <div class="row items-center q-gutter-xs q-mb-sm">
          <q-btn
            dense
            :icon="allLoadedSelected ? 'deselect' : 'select_all'"
            :label="allLoadedSelected ? 'Снять' : 'Выбрать'"
            :color="allLoadedSelected ? 'grey-7' : 'primary'"
            flat
            @click="toggleSelectAll"
          >
            <q-tooltip>
              Выбрать все загруженные фото или снять выбор
            </q-tooltip>
          </q-btn>
          <q-badge v-if="store.selectedCount" color="primary">
            выбрано: {{ store.selectedCount }}
          </q-badge>
          <q-btn
            v-if="canUseCollective"
            dense
            flat
            icon="download"
            label="Скачать"
            :disable="!store.selectedCount"
            @click="downloadSelected"
          >
            <q-tooltip>Скачать выбранные фото по одному</q-tooltip>
          </q-btn>
          <q-btn
            v-if="canUseCollective"
            dense
            color="secondary"
            icon="folder_zip"
            label="ZIP"
            :disable="!store.selectedCount"
            :loading="zipBusy"
            @click="downloadZip"
          >
            <q-tooltip>Скачать выбранные фото одним архивом</q-tooltip>
          </q-btn>
          <CloudLinkButton
            v-if="canUseCollective"
            :photo-ids="store.selected"
            :disabled="!store.selectedCount"
          />

          <q-space />

          <!-- дата: источник фильтра и периода — выпадающим списком -->
          <q-select
            v-model="dateMode"
            :options="dateModes"
            dense
            outlined
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Дата"
            style="min-width: 140px"
            @update:model-value="apply"
          />

          <!-- период: компактно, свой период — двумя полями в этой же строке -->
          <q-select
            v-model="period"
            :options="periods"
            dense
            outlined
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Период"
            style="min-width: 150px"
            @update:model-value="apply"
          />
          <template v-if="period === 'custom'">
            <q-input
              v-model="customFrom"
              type="date"
              dense
              outlined
              label="С"
              style="width: 130px"
              @blur="apply"
            />
            <q-input
              v-model="customTo"
              type="date"
              dense
              outlined
              label="По"
              style="width: 130px"
              @blur="apply"
            />
          </template>

          <q-select
            v-model="sortKey"
            :options="sortOptions"
            dense
            outlined
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Сортировка"
            style="min-width: 175px"
          />
          <q-btn dense flat @click="toggleSortDirection">
            <q-icon
              :name="sortDirection === 'asc' ? 'arrow_upward' : 'arrow_downward'"
            />
            <q-tooltip>
              {{ sortDirection === 'asc' ? 'По возрастанию' : 'По убыванию' }}
            </q-tooltip>
          </q-btn>

          <q-btn-toggle
            v-model="viewMode"
            dense
            toggle-color="primary"
            :options="[
              { value: 'tiles', slot: 'tiles' },
              { value: 'list', slot: 'list' },
            ]"
          >
            <template #tiles><q-icon name="grid_view" /></template>
            <template #list><q-icon name="view_list" /></template>
          </q-btn-toggle>

          <q-btn dense flat icon="settings" @click="settingsOpen = true">
            <q-tooltip>Настройки отображения</q-tooltip>
          </q-btn>

          <!-- Избранное (бывшие «сохранённые поиски») — тоже принадлежит пользователю -->
          <q-btn v-if="canUseCollective" dense flat icon="bookmarks">
            <q-tooltip>Избранное</q-tooltip>
            <q-menu>
              <q-list dense style="min-width: 240px">
                <q-item clickable v-close-popup @click="openSaveSearch">
                  <q-item-section avatar>
                    <q-icon name="bookmark_add" />
                  </q-item-section>
                  <q-item-section>Добавить текущий поиск в Избранное</q-item-section>
                </q-item>
                <q-separator />
                <q-item
                  v-for="search in savedSearches"
                  :key="search.search_id"
                  clickable
                  v-close-popup
                  @click="applySavedSearch(search)"
                >
                  <q-item-section avatar>
                    <q-icon name="bookmark" size="18px" />
                  </q-item-section>
                  <q-item-section>
                    <div class="ellipsis">{{ search.name }}</div>
                  </q-item-section>
                  <q-item-section side>
                    <q-btn
                      dense
                      flat
                      size="sm"
                      icon="delete"
                      @click.stop="removeSavedSearch(search)"
                    />
                  </q-item-section>
                </q-item>
                <q-item v-if="!savedSearches.length">
                  <q-item-section class="text-caption text-grey">
                    В Избранном пусто
                  </q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </div>

        <div v-if="error" class="q-mb-md">
          <q-banner class="bg-red-1 text-negative">Ошибка: {{ error }}</q-banner>
        </div>

        <!-- Полоса-разделитель: фильтры сверху, сетка фото под ней. -->
        <div class="grid-divider" />

        <div
          ref="gridScrollEl"
          class="col grid-scroll"
          @scroll.passive="onGridScroll"
        >
            <div v-if="viewMode === 'tiles'" class="photo-grid" :style="gridStyle">
              <q-card
                v-for="photo in sortedItems"
                :key="photo.photo_id"
                class="photo-card"
              >
                <q-checkbox
                  :model-value="store.isSelected(photo.photo_id)"
                  class="photo-check"
                  dense
                  color="primary"
                  @update:model-value="store.toggleSelected(photo.photo_id)"
                />
                <AuthImage
                  :url="previewUrl(photo.photo_id, 'small')"
                  :ratio="4 / 3"
                  class="cursor-pointer"
                  @click="open(photo)"
                />
                <q-card-section class="q-pa-xs">
                  <!-- Подпись плитки: алиас адреса жирным, имя файла обычным,
                       дата съёмки и вес — жирным курсивом, клиент и бренд —
                       курсивом (результат распознавания QWEN). -->
                  <div
                    v-if="photo.address"
                    class="ellipsis text-caption text-weight-bold"
                  >
                    {{ photo.simple_address || photo.address }}
                    <q-tooltip v-if="photo.simple_address">
                      {{ photo.address }}
                    </q-tooltip>
                  </div>
                  <div class="ellipsis text-caption">
                    <q-icon
                      name="auto_awesome"
                      size="14px"
                      :color="qwenColor(photo)"
                      class="q-mr-xs"
                    >
                      <q-tooltip>{{ qwenHint(photo) }}</q-tooltip>
                    </q-icon>
                    {{ photo.filename }}
                  </div>
                  <div
                    v-if="tileMeta(photo)"
                    class="ellipsis text-caption text-weight-bold font-italic"
                  >
                    {{ tileMeta(photo) }}
                  </div>
                  <div v-if="photo.source_directory" class="ellipsis text-caption text-grey-7" :title="photo.source_directory">
                    Каталог: {{ photo.source_directory }}
                  </div>
                  <div
                    v-if="clientBrand(photo)"
                    class="ellipsis text-caption font-italic"
                  >
                    {{ clientBrand(photo) }}
                  </div>
                </q-card-section>

                <!-- right-click context menu -->
                <q-menu context-menu touch-position>
                  <q-list dense style="min-width: 180px">
                    <q-item clickable v-close-popup @click="open(photo)">
                      <q-item-section avatar>
                        <q-icon name="visibility" />
                      </q-item-section>
                      <q-item-section>Открыть</q-item-section>
                    </q-item>
                    <q-item
                      v-if="canUseCollective"
                      clickable
                      v-close-popup
                      @click="openOriginal(photo)"
                    >
                      <q-item-section avatar>
                        <q-icon name="open_in_new" />
                      </q-item-section>
                      <q-item-section>Оригинал</q-item-section>
                    </q-item>
                    <q-item
                      v-if="canUseCollective"
                      clickable
                      v-close-popup
                      @click="saveOriginal(photo)"
                    >
                      <q-item-section avatar>
                        <q-icon name="download" />
                      </q-item-section>
                      <q-item-section>Сохранить</q-item-section>
                    </q-item>
                    <q-item
                      v-if="canUseCollective"
                      clickable
                      v-close-popup
                      @click="addOneToBucket(photo)"
                    >
                      <q-item-section avatar>
                        <q-icon name="bookmark_add" />
                      </q-item-section>
                      <q-item-section>В подборку</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </q-card>
            </div>

              <q-list v-else separator bordered class="rounded-borders">
              <q-item
                v-for="photo in sortedItems"
                :key="photo.photo_id"
                clickable
                @click="open(photo)"
              >
                <q-item-section side>
                  <q-checkbox
                    :model-value="store.isSelected(photo.photo_id)"
                    dense
                    color="primary"
                    @click.stop
                    @update:model-value="store.toggleSelected(photo.photo_id)"
                  />
                </q-item-section>
                <q-item-section side>
                  <AuthImage
                    :url="previewUrl(photo.photo_id, 'small')"
                    style="width: 64px; height: 48px"
                    class="rounded-borders"
                  />
                </q-item-section>
                <q-item-section>
                  <!-- Строка 1: адрес (алиас) жирным, затем дата съёмки и вес. -->
                  <q-item-label class="ellipsis">
                    <span
                      v-if="photo.simple_address || photo.address"
                      class="text-weight-bold"
                    >
                      {{ photo.simple_address || photo.address }}
                    </span>
                    <span v-if="tileMeta(photo)" class="text-grey-8">
                      <template v-if="photo.simple_address || photo.address">
                        ·
                      </template>
                      {{ tileMeta(photo) }}
                    </span>
                  </q-item-label>

                  <!-- Строка 2: имя файла и результат распознавания
                       (клиент/бренд), когда он уже есть. -->
                  <q-item-label caption class="ellipsis">
                    <q-icon
                      name="auto_awesome"
                      size="14px"
                      :color="qwenColor(photo)"
                      class="q-mr-xs"
                    >
                      <q-tooltip>{{ qwenHint(photo) }}</q-tooltip>
                    </q-icon>
                    {{ photo.filename }}
                    <span v-if="clientBrand(photo)" class="text-grey-8">
                      · {{ clientBrand(photo) }}
                    </span>
                  </q-item-label>

                  <!-- Остальные поля из настроек списка (размер в пикселях,
                       дата загрузки) — третьей строкой, чтобы настройка не
                       потеряла смысл. -->
                  <q-item-label
                    v-if="extraListFields(photo).length || photo.source_directory"
                    caption
                    class="ellipsis text-grey-7"
                    :title="photo.source_directory"
                  >
                    <template v-if="extraListFields(photo).length">{{ extraListFields(photo).join(' · ') }}</template>
                    <template v-if="photo.source_directory">{{ extraListFields(photo).length ? ' · ' : '' }}{{ photo.source_directory }}</template>
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn dense flat icon="more_vert" @click.stop>
                    <q-menu>
                      <q-list dense style="min-width: 180px">
                        <q-item
                          v-if="canUseCollective"
                          clickable
                          v-close-popup
                          @click="openOriginal(photo)"
                        >
                          <q-item-section avatar><q-icon name="open_in_new" /></q-item-section>
                          <q-item-section>Оригинал</q-item-section>
                        </q-item>
                        <q-item
                          v-if="canUseCollective"
                          clickable
                          v-close-popup
                          @click="saveOriginal(photo)"
                        >
                          <q-item-section avatar><q-icon name="download" /></q-item-section>
                          <q-item-section>Сохранить</q-item-section>
                        </q-item>
                        <q-item
                          v-if="canUseCollective"
                          clickable
                          v-close-popup
                          @click="addOneToBucket(photo)"
                        >
                          <q-item-section avatar><q-icon name="bookmark_add" /></q-item-section>
                          <q-item-section>В подборку</q-item-section>
                        </q-item>
                      </q-list>
                    </q-menu>
                  </q-btn>
                </q-item-section>
              </q-item>
            </q-list>

            <div v-if="loading" class="row justify-center q-my-md">
              <q-spinner-dots color="primary" size="40px" />
            </div>
            <div
              v-else-if="store.hasMore"
              class="row items-center justify-center q-gutter-sm q-my-md text-caption text-grey-7"
            >
              <span>Показано {{ items.length }} фото; есть ещё</span>
              <q-btn
                dense
                flat
                color="primary"
                label="Загрузить ещё"
                :loading="loading"
                :disable="loading"
                @click="loadMorePhotos"
              />
            </div>
            <div
              v-else-if="items.length"
              class="text-center text-grey-6 q-my-md text-caption"
            >
              Показаны все фото
            </div>

          <div
            v-if="!loading && !error && items.length === 0"
            class="text-grey q-mt-lg"
          >
            Ничего не найдено.
          </div>
        </div>
      </div>

      <ResizeHandle
        v-if="display.rightPanelOpen"
        direction="vertical"
        title="Потяните, чтобы изменить ширину правой панели"
        @resize="(delta) => display.resizePanel('right', delta)"
      />

      <!-- RIGHT: клиенты + подборки; складывается кнопкой у края -->
      <div
        v-if="display.rightPanelOpen"
        class="right-panel q-pl-xs"
        :style="{ width: display.rightPanelWidth + 'px', flex: '0 0 auto' }"
      >
        <q-card
          flat
          bordered
          class="column"
          :class="{ 'panel-inactive': textSearchActive }"
          :style="{ height: display.sideListHeight + 'px' }"
        >
          <q-card-section class="panel-head q-pb-xs row items-center">
            <div class="panel-title col">
              Клиент/бренд
              <q-tooltip v-if="textSearchActive">
                Недоступно, пока активен поиск по тексту
              </q-tooltip>
            </div>
            <!-- Одна кнопка: пока ничего не выбрано — «Все», иначе «Снять». -->
            <q-btn
              dense
              flat
              size="sm"
              :disable="textSearchActive"
              :label="store.selectedClients.length ? 'Снять' : 'Все'"
              @click="
                store.selectedClients.length
                  ? clearClients()
                  : selectAllClients()
              "
            >
              <q-tooltip>
                {{
                  store.selectedClients.length
                    ? 'Снять выделение клиентов'
                    : 'Выбрать всех клиентов'
                }}
              </q-tooltip>
            </q-btn>
          </q-card-section>
          <q-separator />
          <q-scroll-area class="col">
            <q-list dense :disable="textSearchActive">
              <q-item
                v-for="item in clients"
                :key="item.client"
                clickable
                :active="store.selectedClients.includes(item.client)"
                active-class="bg-secondary text-white"
                @click="pickClient(item.client)"
              >
                <q-item-section>{{ item.client }}</q-item-section>
                <q-item-section side>{{ item.count }}</q-item-section>
              </q-item>
              <q-item v-if="!clients.length">
                <q-item-section class="text-caption text-grey">
                  Нет клиентов
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card>

        <ResizeHandle
          direction="horizontal"
          title="Потяните, чтобы изменить высоту списка клиентов"
          @resize="(delta) => display.resizeSideList(delta)"
        />

        <CollectionsPanel
          v-if="canUseCollective"
          scope="clients"
          @create="openBucketDialog"
        />
      </div>
    </div>

    <!-- плавающие кнопки у краёв: складывают панели в край -->
    <q-btn
      class="edge-toggle edge-toggle--left"
      round
      dense
      size="sm"
      :icon="display.leftPanelOpen ? 'chevron_left' : 'chevron_right'"
      :color="display.leftPanelOpen ? 'grey-7' : 'primary'"
      @click="display.leftPanelOpen = !display.leftPanelOpen"
    >
      <q-tooltip>
        {{ display.leftPanelOpen ? 'Скрыть' : 'Показать' }} адреса и подборки
      </q-tooltip>
    </q-btn>

    <q-btn
      class="edge-toggle edge-toggle--right"
      round
      dense
      size="sm"
      :icon="display.rightPanelOpen ? 'chevron_right' : 'chevron_left'"
      :color="display.rightPanelOpen ? 'grey-7' : 'primary'"
      @click="display.rightPanelOpen = !display.rightPanelOpen"
    >
      <q-tooltip>
        {{ display.rightPanelOpen ? 'Скрыть' : 'Показать' }} клиентов и подборки
      </q-tooltip>
    </q-btn>

    <q-page-sticky position="bottom-right" :offset="[18, 18]">
      <q-btn fab-mini color="primary" icon="arrow_upward" @click="scrollToTop">
        <q-tooltip>Наверх</q-tooltip>
      </q-btn>
    </q-page-sticky>

    <q-dialog v-model="viewerOpen">
      <q-card style="width: 1100px; max-width: 95vw; max-height: 92vh">
        <q-card-section class="row items-center q-pb-sm">
          <!-- Simplified recognition address, with the position in the gallery. -->
          <div class="col ellipsis">
            <div class="text-subtitle1 ellipsis">
              {{ current?.simple_address || current?.address || 'адрес не определён' }}
            </div>
            <div class="text-caption text-grey-7 ellipsis">
              {{ current?.filename }}
            </div>
          </div>
          <q-btn
            v-if="canUseCollective"
            dense
            flat
            icon="open_in_new"
            @click="openOriginal(current)"
          >
            <q-tooltip>Открыть оригинал</q-tooltip>
          </q-btn>
          <q-btn
            v-if="canUseCollective"
            dense
            flat
            icon="download"
            @click="saveOriginal(current)"
          >
            <q-tooltip>Сохранить оригинал</q-tooltip>
          </q-btn>
          <q-btn dense flat icon="close" v-close-popup />
        </q-card-section>
        <q-separator />

        <div class="row no-wrap" style="max-height: 80vh">
          <div class="col-7 column items-center bg-grey-3 q-pa-sm relative-position">
            <q-btn
              class="viewer-nav viewer-nav--left"
              round
              dense
              icon="chevron_left"
              :disable="!canPrev"
              @click="stepPhoto(-1)"
            >
              <q-tooltip>Предыдущее фото (←)</q-tooltip>
            </q-btn>

            <AuthImage
              :url="viewerUrl()"
              :ratio="4 / 3"
              class="rounded-borders"
              style="max-width: 100%"
            />

            <q-btn
              class="viewer-nav viewer-nav--right"
              round
              dense
              icon="chevron_right"
              :disable="!canNext"
              @click="stepPhoto(1)"
            >
              <q-tooltip>Следующее фото (→)</q-tooltip>
            </q-btn>
          </div>

          <div class="col-5 column" style="overflow: auto">
            <q-card-section class="q-gutter-xs">
              <div v-if="detailsLoading">
                <q-spinner-dots color="primary" size="28px" />
              </div>

              <template v-else>
                <div class="q-mt-sm">
                  <div class="row items-center">
                    <div class="text-caption text-grey col">
                      Юридический адрес
                    </div>
                    <q-btn
                      v-if="canUseCollective"
                      dense
                      flat
                      size="sm"
                      icon="edit"
                      @click="openAddressEditor"
                    >
                      <q-tooltip>Исправить юридический адрес</q-tooltip>
                    </q-btn>
                  </div>
                  <div>{{ info?.legal_address || '—' }}</div>
                  <q-badge
                    v-if="details?.address_override"
                    color="orange"
                    label="исправлено вручную"
                    class="q-mt-xs"
                  />
                  <div
                    v-else-if="!info?.legal_address"
                    class="text-caption text-grey-6"
                  >
                    Справочник адресов ещё не подключён.
                  </div>
                </div>

                <div class="row q-col-gutter-xs q-mt-sm">
                  <div class="col-6">
                    <div class="text-caption text-grey">Дата съёмки</div>
                    <div>{{ day(info?.taken_at) }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-caption text-grey">Дата загрузки</div>
                    <div>{{ day(info?.created_at) }}</div>
                  </div>
                </div>

                <div class="row q-col-gutter-xs q-mt-sm">
                  <div class="col-6">
                    <div class="text-caption text-grey">Размер</div>
                    <div>{{ pixels(info) }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-caption text-grey">Вес</div>
                    <div>{{ megabytes(info?.size_bytes) }}</div>
                  </div>
                </div>

                <!-- QWEN status: grey НЕТ, red !!!, orange ..., green ЕСТЬ -->
                <div class="row items-center q-gutter-xs q-mt-sm">
                  <div class="text-caption text-grey">QWEN</div>
                  <q-badge
                    :color="qwenStatus(qwen).color"
                    :label="qwenStatus(qwen).label"
                  />
                  <q-badge
                    v-if="qwen?.qwen_model === 'manual-edit'"
                    color="orange"
                    label="изменено вручную"
                  />
                  <q-btn
                    v-if="canUseCollective"
                    dense
                    flat
                    size="sm"
                    icon="edit"
                    label="Редактировать"
                    @click="openQwenEditor"
                  />
                  <q-btn
                    v-if="canRunQwen"
                    dense
                    flat
                    size="sm"
                    icon="refresh"
                    label="Пересканировать"
                    :loading="rescanBusy"
                  >
                    <q-menu>
                      <q-list dense style="min-width: 260px">
                        <q-item
                          clickable
                          v-close-popup
                          @click="rescanPhoto('ollama')"
                        >
                          <q-item-section>
                            Локально
                            <span v-if="qwenModels.ollama" class="text-grey-7">
                              ({{ qwenModels.ollama }})
                            </span>
                          </q-item-section>
                        </q-item>
                        <q-item
                          clickable
                          v-close-popup
                          @click="rescanPhoto('openai')"
                        >
                          <q-item-section>
                            В облаке
                            <span v-if="qwenModels.openai" class="text-grey-7">
                              ({{ qwenModels.openai }})
                            </span>
                          </q-item-section>
                        </q-item>
                        <q-separator />
                        <q-item>
                          <q-item-section class="text-caption text-grey-7">
                            Пересканируется только это фото. Прежнее описание
                            сохранится в истории. Облако отправляет кадр на
                            внешний сервис.
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </q-menu>
                  </q-btn>
                  <span v-if="qwen?.qwen_model" class="text-caption text-grey">
                    {{ qwen.qwen_model }}
                    <template v-if="qwen.qwen_time_sec">
                      · {{ qwen.qwen_time_sec.toFixed(1) }} c
                    </template>
                  </span>
                </div>

                <div v-if="qwen?.category" class="q-mt-sm">
                  <div class="text-caption text-grey">Категория</div>
                  <div>{{ qwen.category }}</div>
                </div>

                <div class="row q-col-gutter-sm q-mt-sm">
                  <div class="col-12 col-sm-6">
                    <div class="text-caption text-grey">Клиент</div>
                    <div class="ellipsis" :title="qwen?.client || ''">{{ qwen?.client || '—' }}</div>
                  </div>
                  <div class="col-12 col-sm-6">
                    <div class="text-caption text-grey">Бренд</div>
                    <div class="ellipsis" :title="qwen?.brand || ''">{{ qwen?.brand || '—' }}</div>
                  </div>
                </div>

                <div v-if="qwen?.description" class="q-mt-sm">
                  <div class="text-caption text-grey">Описание</div>
                  <div class="text-body2">{{ qwen.description }}</div>
                </div>

                <div v-if="qwen?.error_message" class="q-mt-sm">
                  <q-banner class="bg-red-1 text-negative text-caption">
                    {{ qwen.error_message }}
                  </q-banner>
                </div>

                <div v-if="tagList(qwen).length" class="q-mt-sm">
                  <div class="text-caption text-grey">Теги</div>
                  <div class="row q-gutter-xs q-mt-xs">
                    <q-chip v-for="tag in tagList(qwen)" :key="tag" dense>
                      {{ tag }}
                    </q-chip>
                  </div>
                </div>

                <q-expansion-item
                  v-if="qwenHistory.length"
                  class="q-mt-md"
                  dense
                  switch-toggle-side
                  :label="`История описаний (${qwenHistory.length})`"
                >
                  <div
                    v-for="item in qwenHistory"
                    :key="item.history_id"
                    class="q-mb-sm"
                  >
                    <div class="text-caption text-grey">
                      {{ historyLine(item) }}
                      <template v-if="item.total_tokens">
                        · {{ item.total_tokens }} токенов
                      </template>
                    </div>
                    <div class="text-body2">
                      {{ item.description || '—' }}
                    </div>
                  </div>
                  <div class="text-caption text-grey q-mt-sm">Текстовый лог</div>
                  <pre class="qwen-history-text">{{ qwenHistoryText }}</pre>
                </q-expansion-item>

                <div v-if="!qwen" class="text-caption text-grey q-mt-md">
                  QWEN-метаданных нет.
                </div>

                <div v-if="current?.source_directory" class="q-mt-md text-caption text-grey-7 ellipsis" :title="current.source_directory">
                  Исходный каталог: {{ current.source_directory }}
                </div>
                <div class="q-mt-xs row items-center no-wrap text-caption">
                  <span class="text-grey q-mr-xs">ID:</span>
                  <span class="ellipsis">{{ current?.photo_id }}</span>
                  <q-space />
                  <span v-if="viewerIndex >= 0" class="text-grey q-ml-sm">№ {{ viewerIndex + 1 }}</span>
                </div>
              </template>
            </q-card-section>
          </div>
        </div>
      </q-card>
    </q-dialog>

    <!-- Ручная правка текстового описания QWEN. -->
    <q-dialog v-model="qwenEditOpen">
      <q-card style="min-width: 560px; max-width: 94vw">
        <q-card-section class="text-subtitle1">
          Редактирование описания
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="qwenEditFields.description"
            type="textarea"
            autogrow
            dense
            outlined
            label="Описание"
          />
          <div class="row q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <q-input
                v-model="qwenEditFields.client"
                dense
                outlined
                label="Клиент"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-input
                v-model="qwenEditFields.brand"
                dense
                outlined
                label="Бренд"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-input
                v-model="qwenEditFields.category"
                dense
                outlined
                label="Категория"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-input
                v-model="qwenEditFields.tags"
                dense
                outlined
                label="Теги (через запятую)"
              />
            </div>
          </div>
          <div class="text-caption text-grey-7">
            Прежнее описание сохранится в истории; запись будет помечена как
            «изменено вручную».
          </div>
          <q-expansion-item
            v-if="qwenHistory.length"
            dense
            switch-toggle-side
            :label="`История описаний (${qwenHistory.length})`"
          >
            <pre class="qwen-history-text">{{ qwenHistoryText }}</pre>
          </q-expansion-item>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn
            color="primary"
            label="Сохранить"
            :loading="qwenEditSaving"
            @click="saveQwenEditor"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Ручное исправление юридического адреса (ошибка распознавания). -->
    <q-dialog v-model="addressEditOpen">
      <q-card style="min-width: 460px; max-width: 92vw">
        <q-card-section class="text-subtitle1">
          Юридический адрес
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-select
            v-model="addressChoice"
            :options="addressOptions"
            option-value="address_id"
            option-label="label"
            emit-value
            map-options
            dense
            outlined
            options-dense
            label="Выберите адрес из справочника"
          />
          <div class="text-caption text-grey-7">
            Текущее распознавание: {{ info?.legal_address || '—' }}
          </div>
          <div class="text-caption text-grey-7">
            Исправление хранится в базе отдельно от результатов распознавания;
            сброс возвращает распознанный адрес.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn
            v-if="details?.address_override"
            flat
            color="negative"
            label="Сбросить"
            :loading="addressSaving"
            @click="resetAddressOverride"
          />
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn
            color="primary"
            label="Сохранить"
            :disable="!addressChoice"
            :loading="addressSaving"
            @click="saveAddressOverride"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Подборка хранит отмеченные адреса или клиентов и восстанавливает
         этот выбор по клику в списке. -->
    <q-dialog v-model="bucketOpen">
      <q-card style="min-width: 400px">
        <q-card-section class="text-subtitle1">
          {{
            bucketScope === 'clients'
              ? 'Подборка клиентов'
              : 'Подборка адресов'
          }}
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <div class="text-body2">
            В подборку войдут отмеченные
            {{ bucketScope === 'clients' ? 'клиенты' : 'адреса' }}:
            <b>{{ bucketValues.length }}</b>
          </div>
          <div class="text-caption text-grey-7">
            {{ bucketValues.join(', ') || '—' }}
          </div>

          <q-select
            v-model="bucketId"
            :options="bucketOptions"
            emit-value
            map-options
            dense
            outlined
            clearable
            label="Обновить существующую подборку"
            hint="или оставьте пустым и введите название новой"
          />
          <q-input
            v-model="newName"
            dense
            outlined
            label="Название новой подборки"
            :disable="!!bucketId"
            @keyup.enter="saveToBucket"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Сохранить" @click="saveToBucket" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="saveSearchOpen">
      <q-card style="min-width: 360px">
        <q-card-section class="text-subtitle1">Сохранить поиск</q-card-section>
        <q-separator />
        <q-card-section>
          <q-input
            v-model="saveSearchName"
            dense
            outlined
            label="Название поиска"
            autofocus
            @keyup.enter="saveSearch"
          />
          <div class="text-caption text-grey q-mt-sm">
            Сохраняются текущие фильтры: запрос, адреса, клиенты, период,
            подборка.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Сохранить" @click="saveSearch" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Display settings; the same panel is duplicated in the technical section -->
    <q-dialog v-model="settingsOpen">
      <q-card style="min-width: 380px; max-width: 92vw">
        <q-card-section class="text-subtitle1">
          Настройки отображения
        </q-card-section>
        <q-separator />
        <q-card-section class="row q-col-gutter-md">
          <div :class="canUseCollective ? 'col-12 col-md-6' : 'col-12'">
            <DisplaySettings />
          </div>
          <!-- Нормализация клиентов и брендов: справа, только форма и список
               имён, без журнала (он остался в техразделе). -->
          <div v-if="canUseCollective" class="col-12 col-md-6">
            <ClientNormalization compact />
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Ручной режим умного поиска: превью, метаданные, правка полей QWEN. -->
    <q-dialog v-model="manualOpen" @hide="closeManual">
      <q-card style="width: min(680px, 94vw)">
        <q-card-section class="panel-title">Поиск по медиа — ручной режим</q-card-section>
        <q-separator />
        <q-card-section class="row q-col-gutter-md">
          <div class="col-12 col-sm-5">
            <video
              v-if="manualIsVideo && manualPreviewUrl"
              ref="manualVideoRef"
              :src="manualPreviewUrl"
              class="manual-preview"
              controls
              @loadedmetadata="onVideoMeta"
              @seeked="onVideoSeek"
            />
            <img
              v-else-if="manualPreviewUrl"
              :src="manualPreviewUrl"
              class="manual-preview"
              @load="onPreviewLoad"
            />
            <div v-else class="manual-preview flex flex-center text-grey">
              (превью недоступно)
            </div>

            <div v-if="manualIsVideo" class="q-mt-sm">
              <q-slider
                v-model="manualFrameSec"
                :min="0"
                :max="Math.max(1, manualDuration)"
                :step="1"
                label
                label-always
                @update:model-value="seekToFrame"
              />
              <div class="text-caption text-grey-8">
                Кадр для распознавания: {{ manualFrameSec }} с
              </div>
            </div>

            <div class="text-caption text-grey-8 q-mt-sm">
              <div>Файл: {{ manualFile?.name }}</div>
              <div v-if="manualMeta">Вес: {{ manualMeta.sizeMb }} МБ</div>
              <div v-if="manualIsVideo && manualResolution">Разрешение: {{ manualResolution }}</div>
              <div v-else-if="manualMeta?.width">Размер: {{ manualMeta.width }}×{{ manualMeta.height }}</div>
              <div v-if="manualIsVideo && manualDuration">Длительность: {{ manualDuration }} с</div>
              <div v-if="manualIsVideo && manualCodec">Кодек: {{ manualCodec }}</div>
              <div v-if="manualMeta?.date">Изменён: {{ manualMeta.date }}</div>
              <div v-if="manualModel">Модель: {{ manualModel }}</div>
            </div>
          </div>

          <div class="col-12 col-sm-7">
            <div v-if="manualStage === 'idle'" class="text-caption text-grey-8">
              Нажмите «Распознать» — QWEN опишет файл, поля ниже можно будет
              поправить перед поиском.
            </div>
            <template v-else>
              <q-input v-model="manualFields.description" type="textarea" autogrow outlined dense label="Описание" class="q-mb-sm" />
              <q-input v-model="manualFields.client" outlined dense label="Клиент" class="q-mb-sm" />
              <q-input v-model="manualFields.brand" outlined dense label="Бренд" class="q-mb-sm" />
              <q-input v-model="manualFields.category" outlined dense label="Категория" class="q-mb-sm" />
              <q-input
                v-model="manualFields.tags"
                outlined
                dense
                label="Теги (через запятую)"
                hint="Теги тоже участвуют в поиске"
              />
            </template>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Отмена" @click="closeManual" />
          <q-btn
            v-if="manualStage === 'idle'"
            color="secondary"
            icon="auto_awesome"
            label="Распознать (QWEN)"
            :loading="false"
            @click="runDescribe"
          />
          <template v-else>
            <q-btn
              color="primary"
              icon="search"
              label="Поиск"
              :loading="manualStage === 'searching'"
              :disable="!manualHasTerms"
              @click="runManualSearch"
            />
            <q-btn flat label="Распознать заново" @click="runDescribe" />
          </template>
        </q-card-actions>
        <div v-if="manualQwenText" class="text-caption text-grey-7 q-px-md q-pb-xs">
          {{ manualQwenText }}
        </div>
        <q-linear-progress v-if="manualStage === 'describing'" indeterminate color="secondary" />
        <q-linear-progress v-if="manualStage === 'searching'" indeterminate color="primary" />
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
/* The page itself does not scroll: the filter column is sticky and the grid
   scrolls inside its own container, so the toolbars stay in place.
   --app-chrome — суммарная высота шапки и подвала, её измеряет App.vue: низ
   грида упирается ровно в подвал без зашитых значений. */
.photos-page {
  height: calc(100vh - var(--app-chrome, 85px));
  overflow: hidden;
}

/* Полоса-разделитель между блоком фильтров и сеткой фотографий. */
.grid-divider {
  height: 3px;
  margin-bottom: 10px;
  border-radius: 2px;
  background: linear-gradient(
    90deg,
    rgba(0, 0, 0, 0.12),
    rgba(0, 0, 0, 0.04)
  );
}

body.body--dark .grid-divider {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.18),
    rgba(255, 255, 255, 0.06)
  );
}

/* Боковая панель — колонка: список адресов/клиентов сверху и «Подборки» снизу.
   Раньше это был обычный блок с прокруткой всей колонки, и карточка подборок
   получала нулевую высоту: её список (`q-scroll-area.col`) требует определённой
   высоты, а `flex: 1` в блочном контейнере ничего не значит. Владелец видел
   только заголовок «Подборки» с плюсом, а сами подборки не отображались. */
.left-panel,
.right-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Список адресов/клиентов задан фиксированной высотой и уступает место
   подборкам, если окно ниже: иначе подборки уехали бы под нижний край. */
.left-panel > .q-card:first-child,
.right-panel > .q-card:first-child {
  flex: 0 1 auto;
  min-height: 120px;
}

/* Прокручиваются сами списки, а не панель целиком. */
.left-panel :deep(.q-scroll-area),
.right-panel :deep(.q-scroll-area) {
  min-height: 0;
}

/* Кнопки у краёв: панель складывается, кнопка остаётся на виду. */
.edge-toggle {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  opacity: 0.9;
}

.edge-toggle--left {
  left: 4px;
}

.edge-toggle--right {
  right: 4px;
}

.grid-scroll {
  min-height: 0;
  overflow-y: auto;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.photo-card {
  position: relative;
  overflow: hidden;
}

.hidden-input {
  display: none;
}

.photo-check {
  position: absolute;
  top: 4px;
  left: 4px;
  z-index: 2;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 4px;
}

/* Панель клиентов/брендов гаснет и не принимает клики, пока активен
   текстовый поиск. */
.panel-inactive {
  opacity: 0.55;
  pointer-events: none;
}

/* Превью выбранного файла в ручном режиме поиска. */
.manual-preview {
  width: 100%;
  max-height: 320px;
  object-fit: contain;
  background: #f4f5f7;
  border-radius: 8px;
  min-height: 120px;
}

/* Transparent arrows over the preview image. */
.viewer-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  background: rgba(255, 255, 255, 0.25);
  color: #212121;
}

.viewer-nav--left {
  left: 6px;
}

.viewer-nav--right {
  right: 6px;
}

.qwen-history-text {
  margin: 6px 0 0;
  max-height: 260px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 0.76rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  color: #455a64;
  background: #f5f6f8;
  border-radius: 6px;
  padding: 8px;
}
</style>
