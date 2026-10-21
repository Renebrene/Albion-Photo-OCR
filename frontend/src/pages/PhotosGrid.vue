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
  fetchSortStatus,
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
import { addressEntryForPhoto as findAddressEntry } from '../utils/addressForPhoto'
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
// Точные фильтры, выбранные из подсказок поиска.
const selectedBrand = ref(null)
const selectedTag = ref(null)
const selectedCategory = ref(null)

// ---- smart search by an uploaded photo (item 2; photos only for now) ----
const mediaInput = ref(null)
const mediaFile = ref(null) // the chosen File, kept in memory until ПОИСК
const mediaJobId = ref(null)
const mediaStage = ref('')
const mediaBusy = ref(false)
const qwenElapsedSeconds = ref(0)
const manualQwenRunning = ref(false)
let qwenTimer = null

// Номера запусков ИИ-поиска. Закрытие/очистка/сброс увеличивают номер, и
// поздний ответ старого запуска уже не трогает грид и состояние кнопок.
let mediaRun = 0
let manualRun = 0

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
// По умолчанию — текущий месяц: так переключатель «Дата загрузки / съёмки»
// сразу меняет выдачу, а не показывает один и тот же полный список.
const period = ref('month')
const customFrom = ref(null)
const customTo = ref(null)

// ○ объединение, △ приоритет адресов, □ приоритет клиентов.
const combineMode = computed(() => display.addressClientMode)

watch(
  () => display.addressClientMode,
  async () => {
    // Смена режима меняет смысл выбранных адресов/клиентов — сбрасываем
    // и адресов, и клиентов, и подборки, чтобы грид не показывал старую
    // комбинацию. resetSelectionFilters() также отменяет поздние ответы
    // applyCollection.
    store.resetSelectionFilters()
    addressSearch.value = ''
    clientSearch.value = ''

    // Новый режим меняет и выдачу, и счётчики обеих панелей.
    await store.loadFacets()
    await apply()
  },
)

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
      return
    }

    if (job.status === 'DONE') {
      Notify.create({ type: 'positive', message: 'Описание обновлено' })
    } else {
      Notify.create({
        type: 'negative',
        message: `Распознавание: ${job.status}${job.error_message ? ` — ${job.error_message}` : ''}`,
      })
    }

    // Строка грида обновляется всегда, даже если пользователь успел
    // перелистнуть на другое фото. Детали и историю читаем только для
    // открытого фото; панели пересчитываем из-за client/brand/category.
    if (current.value?.photo_id === photoId) {
      await loadDetails(current.value)

      if (details.value?.photo) {
        store.updateLoadedPhoto(details.value.photo)
      }
    } else {
      const data = await fetchPhotoDetails(photoId).catch(() => null)

      if (data?.photo) store.updateLoadedPhoto(data.photo)
    }

    await store.loadClients()
    await store.loadAddresses()
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

// «За период N фото»: размер всего отфильтрованного набора, а не загруженной
// страницы. `total` приходит с первой страницей; для «Все даты» подпись иная.
const hasFilterSelection = computed(
  () =>
    Boolean(store.query)
    || store.selectedAddresses.length > 0
    || store.selectedClients.length > 0
    || Boolean(store.brand || store.tag || store.category)
    || Boolean(store.collectionId)
    || store.nlIds.length > 0,
)

const periodLabel = computed(() => {
  const count = store.total

  if (hasFilterSelection.value) {
    return count === null || count === undefined
      ? 'В выборке …'
      : `В выборке ${count} фото`
  }

  if (count === null || count === undefined) {
    return period.value === 'all' ? 'Всего фото' : 'За период …'
  }

  return period.value === 'all'
    ? `Всего ${count} фото`
    : `За период ${count} фото`
})

// «Адреса»: сколько адресов реально получили вердикт HYBRID (всего) и
// сколько из них имеют фото в выбранном периоде. Зелёный `*xx` — период.
const recognizedAddressCount = computed(
  () => addresses.value.filter((item) => (item.count || 0) > 0).length,
)
// ---- быстрый поиск по панелям «Адреса» и «Клиент/бренд» ----
// Выпадающего списка нет: ввод фильтрует сам список (автодополнение по
// имеющимся названиям). Enter выбирает первый подходящий адрес/клиента.
const addressSearch = ref('')
const clientSearch = ref('')

const filteredAddresses = computed(() => {
  const term = addressSearch.value.trim().toLowerCase()
  if (!term) return addresses.value

  return addresses.value.filter((item) =>
    [item.name, item.address, item.simple_address, item.legal_address]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(term)),
  )
})

// Поиск в панели идёт по всей базе, а не по показанным 100 клиентам:
// подсказки приходят из /v1/search/suggestions и включают бренды.
const remoteClientItems = ref([])
let clientSuggestTimer = null

watch(clientSearch, (value) => {
  if (clientSuggestTimer !== null) window.clearTimeout(clientSuggestTimer)

  const term = String(value || '').trim()

  if (term.length < 2) {
    remoteClientItems.value = []
    return
  }

  // Старые результаты не должны показываться под новым запросом.
  remoteClientItems.value = []

  clientSuggestTimer = window.setTimeout(async () => {
    try {
      const data = await fetchSearchSuggestions(term, 20)
      const items = (data.items || [])
        .filter((item) => item.kind === 'client' || item.kind === 'brand')
        .map((item) => ({
          value: item.value,
          kind: item.kind,
          count: item.uses,
        }))

      // Пока шёл запрос, текст мог измениться — применяем только актуальный.
      if (String(clientSearch.value || '').trim() === term) {
        remoteClientItems.value = items
      }
    } catch {
      remoteClientItems.value = []
    }
  }, 250)
})

const filteredClients = computed(() => {
  const term = clientSearch.value.trim().toLowerCase()

  const local = clients.value
    .filter((item) => !term || String(item.client).toLowerCase().includes(term))
    .map((item) => ({
      value: item.client,
      kind: 'client',
      count: item.count,
    }))

  if (!term) {
    // Выбранный клиент мог не попасть в топ-100, а также прийти из старого
    // сохранённого поиска/подсказки в другом написании (алиас). Панель должна
    // показывать текущий выбор всегда — иначе заголовок «(1)» противоречит
    // пустому списку.
    const known = new Set(
      local.map((item) => String(item.value).toLowerCase()),
    )
    const selectedExtra = store.selectedClients
      .filter((value) => !known.has(String(value).toLowerCase()))
      .map((value) => ({
        value,
        kind: 'client',
        count: null,
        selectedOnly: true,
      }))

    return [...selectedExtra, ...local]
  }

  const seen = new Set(
    local.map((item) => `client:${String(item.value).toLowerCase()}`),
  )
  const remote = []

  for (const item of remoteClientItems.value) {
    const key = `${item.kind}:${String(item.value).toLowerCase()}`
    if (seen.has(key)) continue
    seen.add(key)
    remote.push(item)
  }

  return [...local, ...remote]
})

// Подсказка-автодополнение: первый подходящий вариант под полем. Enter
// выбирает его, клик по списку — тоже.
const addressHint = computed(() => {
  const term = addressSearch.value.trim()
  if (!term) return ''
  const first = filteredAddresses.value[0]
  return first ? `→ ${first.name}` : 'нет совпадений'
})

const clientHint = computed(() => {
  const term = clientSearch.value.trim()
  if (!term) return ''
  const first = filteredClients.value[0]
  return first
    ? `→ ${first.value}${first.kind === 'brand' ? ' (бренд)' : ''}`
    : 'нет совпадений'
})

async function pickFirstAddress() {
  // Пустой Enter не должен выбирать первый адрес из полного списка.
  if (!addressSearch.value.trim()) return

  const first = filteredAddresses.value[0]
  if (first) await pickAddress(first.address)
}

async function pickFirstClient() {
  if (!clientSearch.value.trim()) return

  const first = filteredClients.value[0]
  if (first) await pickClientEntry(first)
}

async function pickClientEntry(item) {
  if (item.kind === 'brand') await pickBrand(item.value)
  else await pickClient(item.value)
}

// ---- строка тегов: адреса, клиенты, бренд, тег, категория ----------------
// Одна строка между поиском и фильтрами: выбранное в панелях видно целиком,
// а при переполнении она прокручивается колесом по горизонтали.
const tagsRowEl = ref(null)

const activeAddressCollections = computed(() =>
  store.addressCollectionIds
    .map((id) => store.collections.find((item) => item.collection_id === id))
    .filter(Boolean),
)

const activeClientCollections = computed(() =>
  store.clientCollectionIds
    .map((id) => store.collections.find((item) => item.collection_id === id))
    .filter(Boolean),
)

function addressTagLabel(item) {
  return item.name || item.simple_address || item.address
}

const addressTags = computed(() => {
  if (activeAddressCollections.value.length) {
    return activeAddressCollections.value.map((collection) => ({
      key: `address-collection:${collection.collection_id}`,
      label: collection.name,
      type: 'address-collection',
      collectionId: collection.collection_id,
      icon: 'bookmark',
    }))
  }

  return store.selectedAddresses.map((value) => {
    const found = addresses.value.find((item) => item.address === value)

    return {
      key: `address:${value}`,
      label: found ? addressTagLabel(found) : value,
      type: 'address',
      value,
    }
  })
})

const clientTags = computed(() => {
  if (activeClientCollections.value.length) {
    return activeClientCollections.value.map((collection) => ({
      key: `client-collection:${collection.collection_id}`,
      label: collection.name,
      type: 'client-collection',
      collectionId: collection.collection_id,
      icon: 'bookmark',
    }))
  }

  return store.selectedClients.map((value) => ({
    key: `client:${value}`,
    label: `Клиент: ${value}`,
    type: 'client',
    value,
  }))
})

const activeTags = computed(() => [
  ...addressTags.value,
  ...clientTags.value,
  ...(selectedBrand.value
    ? [{ key: 'brand', label: `Бренд: ${selectedBrand.value}`, type: 'brand' }]
    : []),
  ...(selectedTag.value
    ? [{ key: 'tag', label: `Тег: ${selectedTag.value}`, type: 'tag' }]
    : []),
  ...(selectedCategory.value
    ? [
        {
          key: 'category',
          label: `Категория: ${selectedCategory.value}`,
          type: 'category',
        },
      ]
    : []),
])

// В заголовке панели клиентов: выбранные в списке + бренд из тега.
const clientSelectionCount = computed(
  () => store.selectedClients.length + (selectedBrand.value ? 1 : 0),
)

function tagColor(type) {
  if (type === 'address' || type === 'address-collection') return 'primary'
  return 'secondary'
}

async function removeTag(tag) {
  switch (tag.type) {
    case 'address':
      toggleValue(store.selectedAddresses, tag.value)
      break
    case 'client':
      toggleValue(store.selectedClients, tag.value)
      break
    case 'brand':
      selectedBrand.value = null
      break
    case 'tag':
      selectedTag.value = null
      break
    case 'category':
      selectedCategory.value = null
      break
    case 'address-collection': {
      const collection = store.collections.find(
        (item) => item.collection_id === tag.collectionId,
      )

      if (collection) {
        await store.applyCollection(collection)
        return
      }

      break
    }
    case 'client-collection': {
      const collection = store.collections.find(
        (item) => item.collection_id === tag.collectionId,
      )

      if (collection) {
        await store.applyCollection(collection)
        return
      }

      break
    }
    default:
      return
  }

  await apply()
}

// Строка тегов: колесо и перетаскивание листают её по горизонтали.
const tagsScrollable = ref(false)
let tagsDrag = null

function measureTags() {
  const el = tagsRowEl.value
  tagsScrollable.value = Boolean(
    el && el.scrollWidth > el.clientWidth + 1,
  )
}

watch(activeTags, () => nextTick(measureTags), { deep: true })

function onWindowResize() {
  measureTags()
  display.fitPanels()
}

function onTagsWheel(event) {
  const el = tagsRowEl.value

  if (!el || el.scrollWidth <= el.clientWidth) return

  // Обычное колесо листает строку влево/вправо; shift+колесо и тачпад
  // присылают deltaX — он тоже учитывается.
  event.preventDefault()
  el.scrollLeft += (event.deltaX || 0) + (event.deltaY || 0)
}

function onTagsPointerDown(event) {
  const el = tagsRowEl.value

  if (!el || event.button !== 0 || el.scrollWidth <= el.clientWidth) return

  // Клик по тегу (и по крестику) — не перетаскивание.
  if (event.target instanceof Element && event.target.closest('.q-chip')) return

  tagsDrag = { x: event.clientX, left: el.scrollLeft }
  el.classList.add('is-dragging')
}

function onTagsPointerMove(event) {
  if (!tagsDrag) return

  const el = tagsRowEl.value
  if (!el) return

  el.scrollLeft = tagsDrag.left - (event.clientX - tagsDrag.x)
}

function onTagsPointerUp() {
  const el = tagsRowEl.value
  if (el) el.classList.remove('is-dragging')
  tagsDrag = null
}

// Диапазоны дат считает общий модуль (локальный календарь, см. его шапку).
function currentDates() {
  return periodRange(period.value, {
    customFrom: customFrom.value,
    customTo: customTo.value,
  })
}

// Пока идёт пайплайн, число распознанных фото растёт: грид показывает фото
// только после HYBRID, поэтому одних обновлённых строк мало — нужен полный
// перечит, когда меняется размер выборки. Заодно показываем, сколько
// совпадений уже нашлось (это же число видно на вкладке «Сортировка»).
let pipelineSyncTimer = null
let pipelineSyncTick = 0
let pipelineWasActive = false
const pipelineStatus = ref(null)

const pipelineStatusText = computed(() => {
  const status = pipelineStatus.value
  if (!status) return ''

  const parts = []
  if (status.label) parts.push(status.label)
  if (status.matched !== null && status.total !== null) {
    parts.push(`совпадений ${status.matched} из ${status.total}`)
  }
  return parts.join(' · ')
})

async function pipelineStage() {
  const data = await fetchRunActivity()

  if (!data.active) return null

  // Совпадения считает тот же модуль, что и вкладку «Сортировка»; у Гостя
  // нет jobs:read — для него остаётся только общее сообщение о стадии.
  let matched = null
  let total = null

  if (canUseCollective.value) {
    try {
      const status = await fetchSortStatus()
      const stats = status?.current || status?.last?.stats || null
      matched = stats?.matched ?? null
      total = stats?.total ?? null
    } catch {
      // Сводка — вспомогательная: стадия всё равно покажется.
    }
  }

  return {
    label: data.message || 'идёт обновление базы',
    matched,
    total,
  }
}

async function syncDuringPipeline() {
  // Не трогаем грид, пока он занят загрузкой или открыт просмотрщик:
  // refresh() заменил бы лениво загруженные страницы первой и сломал бы
  // навигацию по открытому фото. Следующий тик повторит попытку.
  if (store.loading || viewerOpen.value) return

  try {
    const status = await pipelineStage()

    if (!status) {
      // Пайплайн только что закончился: перечитываем грид один раз, чтобы
      // последние сработавшие HYBRID-совпадения попали на экран.
      if (pipelineWasActive) {
        pipelineWasActive = false
        pipelineStatus.value = null
        await store.refresh()
        await store.loadFacets()
        Notify.create({
          type: 'positive',
          message: 'Обновление базы завершено — галерея обновлена',
        })
      }
      return
    }

    pipelineWasActive = true
    pipelineStatus.value = status

    const known = store.total
    const total = await store.countFiltered()

    // Пока шёл запрос, пользователь мог сменить фильтр — тогда разница
    // относится к фильтру, а не к пайплайну: следующий тик всё увидит сам.
    if (total === null || store.total !== known) return

    if (total !== known) {
      await store.refresh()

      if (known !== null && total > known) {
        Notify.create({
          type: 'info',
          message: `Распознано новых фото: +${total - known}`,
        })
      }
    } else {
      // Размер набора не изменился — обновляем QWEN-поля на месте, не
      // сбрасывая прокрутку.
      await store.syncLoaded()
    }

    pipelineSyncTick += 1

    if (pipelineSyncTick % 3 === 0) await store.loadAddresses()
  } catch {
    // Фоновое обновление не должно влиять на работу грида.
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  window.addEventListener('resize', onWindowResize)

  // Вход на главную всегда начинает с текущего месяца: старые выделения
  // адресов/клиентов, строка поиска и период не восстанавливаются.
  store.selectedAddresses = []
  store.selectedClients = []
  store.collectionId = null
  store.addressCollectionIds = []
  store.clientCollectionIds = []
  store.addressCollectionId = null
  store.clientCollectionId = null
  store.addressCollectionMembers = {}
  store.clientCollectionMembers = {}
  store.addressCollectionValues = []
  store.clientCollectionValues = []
  store.nlIds = []
  q.value = ''
  period.value = 'month'
  customFrom.value = null
  customTo.value = null
  dateMode.value = 'upload'
  clearStructuredFilters()
  addressSearch.value = ''
  clientSearch.value = ''

  await store.loadFacets()
  display.fitPanels()
  loadQwenModels()
  apply()

  // Если прогон уже идёт, стадия и число совпадений появляются сразу, а не
  // через первый десятисекундный тик.
  void syncDuringPipeline()

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
  window.removeEventListener('resize', onWindowResize)
  stopGridObserver()
  stopQwenElapsed()

  if (suggestTimer !== null) window.clearTimeout(suggestTimer)
  if (clientSuggestTimer !== null) window.clearTimeout(clientSuggestTimer)
  if (pipelineSyncTimer !== null) window.clearInterval(pipelineSyncTimer)
})

// Arrow keys page through the gallery in the order it is displayed.
function onKeydown(event) {
  if (!viewerOpen.value) return
  if (event.defaultPrevented) return

  // Поверх просмотра могут быть открыты редактор описания/адреса, подборка
  // или сохранённый поиск: стрелки не должны листать фото за диалогом.
  if (
    addressEditOpen.value
    || qwenEditOpen.value
    || bucketOpen.value
    || saveSearchOpen.value
    || manualOpen.value
  ) {
    return
  }

  // В поле описания стрелки двигают курсор, а не листают фото. Без этой
  // проверки preventDefault() ниже съедал ArrowLeft/ArrowRight в textarea.
  const target = event.target

  if (
    target instanceof HTMLElement
    && (
      target.isContentEditable
      || target.tagName === 'INPUT'
      || target.tagName === 'TEXTAREA'
      || target.tagName === 'SELECT'
    )
  ) {
    return
  }

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
    brand: selectedBrand.value,
    tag: selectedTag.value,
    category: selectedCategory.value,
    dateFrom,
    dateTo,
    dateMode: dateMode.value,
    combine: combineMode.value,
    collectionId: store.collectionId,
  })
}

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

  // Выбор подсказки программно меняет q. Флаг снимаем, но НЕ выходим:
  // иначе он «съедал» первый символ, набранный после выбора подсказки.
  if (suggestMuted) suggestMuted = false

  const term = String(value || '').trim()

  if (term.length < 2) {
    suggestItems.value = []
    suggestLayout.value = null
    suggestOpen.value = false
    return
  }

  suggestTimer = window.setTimeout(() => loadSuggestions(term), 250)
}

/** Уже выбранный тег не должен повторяться в подсказках. */
function suggestionAlreadySelected(item) {
  const value = String(item.value || '').trim().toLowerCase()

  if (item.kind === 'client') {
    return store.selectedClients.some(
      (client) => String(client).trim().toLowerCase() === value,
    )
  }

  if (item.kind === 'brand') {
    return Boolean(
      selectedBrand.value
      && String(selectedBrand.value).trim().toLowerCase() === value,
    )
  }

  if (item.kind === 'tag') {
    return Boolean(
      selectedTag.value
      && String(selectedTag.value).trim().toLowerCase() === value,
    )
  }

  if (item.kind === 'category') {
    return Boolean(
      selectedCategory.value
      && String(selectedCategory.value).trim().toLowerCase() === value,
    )
  }

  if (item.kind === 'address') {
    const row = addresses.value.find((entry) =>
      [entry.name, entry.simple_address, entry.legal_address]
        .filter(Boolean)
        .some((name) => String(name).trim().toLowerCase() === value),
    )

    return Boolean(row && store.selectedAddresses.includes(row.address))
  }

  return false
}

async function loadSuggestions(term) {
  try {
    const data = await fetchSearchSuggestions(term)

    // Пока шёл запрос, строку уже изменили — старые подсказки не показываем.
    if (String(q.value || '').trim() !== term) return

    suggestItems.value = (data.items || [])
      .filter((item) => !suggestionAlreadySelected(item))
    suggestLayout.value = data.layout || null
    suggestOpen.value = Boolean(suggestItems.value.length || suggestLayout.value)
  } catch {
    suggestItems.value = []
    suggestLayout.value = null
  }
}

function clearStructuredFilters() {
  selectedBrand.value = null
  selectedTag.value = null
  selectedCategory.value = null
}

async function clearStructuredAndApply() {
  clearStructuredFilters()
  await apply()
}

async function clearStructured(kind) {
  if (kind === 'brand') selectedBrand.value = null
  if (kind === 'tag') selectedTag.value = null
  if (kind === 'category') selectedCategory.value = null
  await apply()
}

async function pickSuggestion(item) {
  if (!item) return

  const kind = item.kind
  const value = item.value

  suggestOpen.value = false
  suggestItems.value = []
  suggestLayout.value = null
  suggestMuted = true

  // Подсказка — структурный выбор: свободный текст убираем, иначе «СТС»
  // найдёт ещё и «Ростсельмаш» подстрокой. Прежние теги при этом сохраняются:
  // новый выбор дополняет строку тегов, а не стирает её.
  q.value = ''

  if (kind === 'layout') {
    // The converted layout is still a text search.
    q.value = value
    await apply(value)
    return
  }

  if (kind === 'client') {
    if (!store.selectedClients.includes(value)) {
      store.selectedClients = [...store.selectedClients, value]
    }
  } else if (kind === 'brand') {
    selectedBrand.value = value
  } else if (kind === 'tag') {
    selectedTag.value = value
  } else if (kind === 'category') {
    selectedCategory.value = value
  } else if (kind === 'address') {
    const wanted = String(value || '').trim().toLowerCase()
    const found = addresses.value.find((entry) =>
      [entry.name, entry.address, entry.simple_address, entry.legal_address]
        .filter(Boolean)
        .some((candidate) => String(candidate).trim().toLowerCase() === wanted),
    )

    if (found) {
      // Адрес из поиска — одиночный выбор со сбросом прежнего состояния:
      // выбранный адрес подсвечивается в списке, грид показывает именно его.
      store.selectedAddresses = [found.address]
      store.selectedClients = []
      clearStructuredFilters()
    } else {
      // The panel keeps its own names (aliases/display names); if the exact
      // suggestion is not there, fall back to the text search rather than
      // leaving an empty grid.
      q.value = value
      await apply(value)
      return
    }
  } else {
    // Unknown kind: keep the old substring behaviour.
    q.value = value
    await apply(value)
    return
  }

  await apply()
}

function toggleValue(list, value) {
  const index = list.indexOf(value)
  if (index === -1) list.push(value)
  else list.splice(index, 1)
}

async function pickAddress(address) {
  // Выбор из отфильтрованного поиска заменяет только выбор АДРЕСОВ: клиенты,
  // бренд и тег должны остаться (фильтры складываются по OR).
  if (addressSearch.value.trim()) {
    store.selectedAddresses = [address]
    store.addressCollectionIds = []
    store.addressCollectionMembers = {}
    store.addressCollectionId = null
    store.addressCollectionValues = []
    store._syncCollectionId()
    addressSearch.value = ''
    await apply()
    return
  }

  toggleValue(store.selectedAddresses, address)
  await apply()
}

async function pickClient(client) {
  // Симметрично адресам: выбор клиента не стирает адреса/бренд/тег.
  if (clientSearch.value.trim()) {
    store.selectedClients = [client]
    store.clientCollectionIds = []
    store.clientCollectionMembers = {}
    store.clientCollectionId = null
    store.clientCollectionValues = []
    store._syncCollectionId()
    clientSearch.value = ''
    await apply()
    return
  }

  toggleValue(store.selectedClients, client)
  await apply()
}

// Бренд из панели — точный фильтр (как и подсказка главного поиска), но
// выбранные клиенты он не сбрасывает: в строке тегов видно оба фильтра.
async function pickBrand(brand) {
  const searching = Boolean(clientSearch.value.trim())
  const same = selectedBrand.value
    && String(selectedBrand.value).toLowerCase() === String(brand).toLowerCase()

  if (searching) {
    // Бренд дополняет выбранных клиентов (OR), а не заменяет их.
    selectedBrand.value = brand
    clientSearch.value = ''
    q.value = ''
  } else if (same) {
    selectedBrand.value = null
  } else {
    selectedBrand.value = brand
  }

  await apply()
}

// Подсветка в правом списке: клиенты — по выбору, бренды — по тегу «Бренд».
function isClientActive(item) {
  if (item.kind === 'brand') {
    return (
      Boolean(selectedBrand.value)
      && String(selectedBrand.value).toLowerCase()
        === String(item.value).toLowerCase()
    )
  }

  return store.selectedClients.includes(item.value)
}

async function resetAddressSelection() {
  // Пустой выбор = все адреса: фильтр по адресу просто не отправляется.
  store.selectedAddresses = []
  store.addressCollectionIds = []
  store.addressCollectionId = null
  store.addressCollectionValues = []
  store.addressCollectionMembers = {}
  store._syncCollectionId()
  await apply()
}

async function resetClientSelection() {
  // Пустой выбор = «все клиенты и бренды базы»: фильтр по клиенту/бренду
  // просто не отправляется. Поэтому отдельная кнопка «Все» не нужна.
  store.selectedClients = []
  selectedBrand.value = null
  store.clientCollectionIds = []
  store.clientCollectionId = null
  store.clientCollectionMembers = {}
  store.clientCollectionValues = []
  store._syncCollectionId()
  await apply()
}

async function reset() {
  const mediaJob = mediaJobId.value
  const manualJob = manualJobId.value

  // Сброс отменяет и незавершённые ИИ-поиски: их поздние результаты не
  // должны снова отфильтровать грид.
  mediaRun += 1
  manualRun += 1
  mediaJobId.value = null
  manualJobId.value = null
  mediaBusy.value = false
  mediaStage.value = ''
  stopQwenElapsed()

  if (mediaJob) cancelJob(mediaJob).catch(() => {})
  if (manualJob) cancelJob(manualJob).catch(() => {})
  if (manualOpen.value) await closeManual({ cancel: false })

  q.value = ''
  period.value = 'month'
  dateMode.value = 'upload'
  customFrom.value = null
  customTo.value = null
  store.resetSelectionFilters()
  clearStructuredFilters()
  addressSearch.value = ''
  clientSearch.value = ''
  suggestOpen.value = false
  suggestItems.value = []
  suggestLayout.value = null
  suggestMuted = false
  hadSearchTerm = false
  mediaFile.value = null
  // «Сбросить фильтры» не трогает корзину выделенных фото: она живёт
  // отдельно от фильтров. Снять выделение можно кнопкой «Обновить».
  await apply()
}

async function refreshGrid() {
  // Обновление — это и есть явный сброс выделения в гриде.
  store.clearSelection()
  await store.refresh()
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
    // A media query and a text query are mutually exclusive: убираем и уже
    // применённый текстовый фильтр, иначе поиск по файлу молча сузится им.
    q.value = ''
    apply('')
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

async function closeManual({ cancel = true } = {}) {
  // @hide срабатывает и после программного закрытия — второй раз не работаем.
  if (!manualOpen.value && !manualJobId.value && !manualPreviewUrl.value) {
    return
  }

  // Закрытие во время распознавания ИЛИ поиска отменяет job и делает
  // поздний ответ недействительным.
  const jobId = manualJobId.value
  manualRun += 1

  if (cancel && jobId) {
    try { await cancelJob(jobId) } catch { /* best-effort */ }
  }

  stopQwenElapsed()
  manualJobId.value = null
  manualStage.value = 'idle'
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
  const run = ++manualRun
  stopQwenElapsed()
  qwenElapsedSeconds.value = 0
  manualStage.value = 'describing'

  try {
    const frameSeconds = manualIsVideo.value ? manualFrameSec.value : null
    const upload = await describeMediaSearch(manualFile.value, frameSeconds)

    if (run !== manualRun) {
      if (upload?.job_id) cancelJob(upload.job_id).catch(() => {})
      return
    }

    const { job_id: jobId } = upload
    manualJobId.value = jobId
    if (upload?.media?.codec) manualCodec.value = upload.media.codec
    let job = null
    for (let i = 0; i < 60; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      if (run !== manualRun) return
      job = await fetchMediaSearchJob(jobId)
      if (run !== manualRun) return

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
    if (run !== manualRun) return
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
    if (run !== manualRun) return
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
  const run = ++manualRun
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
    manualJobId.value = jobId

    if (run !== manualRun) {
      cancelJob(jobId).catch(() => {})
      manualJobId.value = null
      return
    }

    let job = null
    for (let i = 0; i < 40; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      if (run !== manualRun) return
      job = await fetchMediaSearchJob(jobId)
      if (run !== manualRun) return
      if (['DONE', 'FAILED', 'CANCELLED'].includes(job.status)) break
    }

    if (!job || job.status !== 'DONE') {
      if (run !== manualRun) return
      manualStage.value = 'ready'
      Notify.create({ type: 'negative', message: `Поиск: ${job ? job.status : 'таймаут'}` })
      return
    }

    if (run !== manualRun) return
    const ids = (job.result && job.result.photo_ids) || []
    const shown = Math.min(ids.length, 200)
    Notify.create({
      type: 'info',
      message:
        ids.length > shown
          ? `ИИ-поиск: найдено ${ids.length}, показаны первые ${shown}`
          : `ИИ-поиск: найдено ${ids.length}`,
    })
    await store.applyNlResults(ids)
    closeManual({ cancel: false })
  } catch (err) {
    if (run !== manualRun) return
    manualStage.value = 'ready'
    Notify.create({ type: 'negative', message: err.message })
  }
}


async function clearMedia() {
  const jobId = mediaJobId.value

  // Убираем файл вместе с его поиском: поздний ответ не должен вернуть ids.
  mediaRun += 1
  mediaJobId.value = null
  mediaBusy.value = false
  mediaStage.value = ''
  mediaFile.value = null
  stopQwenElapsed()

  if (jobId) {
    try { await cancelJob(jobId) } catch { /* best-effort */ }
  }

  await store.applyNlResults([])
}

async function runMediaSearch() {
  if (!mediaFile.value || mediaBusy.value) return
  const run = ++mediaRun

  stopQwenElapsed()
  mediaBusy.value = true
  mediaStage.value = 'queued'

  try {
    const { job_id: jobId } = await searchByMedia(mediaFile.value)

    if (run !== mediaRun) {
      cancelJob(jobId).catch(() => {})
      return
    }

    mediaJobId.value = jobId

    let job = null

    // QWEN needs a few seconds per image; poll until the worker publishes it.
    for (let i = 0; i < 60; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      if (run !== mediaRun) return
      job = await fetchMediaSearchJob(jobId)
      if (run !== mediaRun) return

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

    if (run !== mediaRun) return

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

    const shown = Math.min(ids.length, 200)

    Notify.create({
      type: truncated || ids.length > shown ? 'warning' : 'info',
      message:
        truncated || ids.length > shown
          ? `ИИ-поиск: показаны первые ${shown} (есть ещё совпадения)`
          : `ИИ-поиск: найдено ${ids.length}${
              described ? ` — «${described}»` : ''
            }`,
    })

    await store.applyNlResults(ids)
  } catch (err) {
    if (run === mediaRun) {
      Notify.create({ type: 'negative', message: err.message })
    }
  } finally {
    // Новый запуск/очистка уже сменили состояние — не трогаем его.
    if (run === mediaRun) {
      stopQwenElapsed()
      mediaBusy.value = false
      mediaJobId.value = null
      mediaStage.value = ''
    }
  }
}

async function stopMediaSearch() {
  const jobId = mediaJobId.value

  // Останавливаем и текущий опрос сразу, не дожидаясь статуса CANCELLED.
  mediaRun += 1
  stopQwenElapsed()
  mediaBusy.value = false
  mediaJobId.value = null
  mediaStage.value = ''

  if (!jobId) return

  try {
    await cancelJob(jobId)
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
  // Программно восстановленный запрос тоже должен корректно очищаться.
  hadSearchTerm = Boolean(q.value)

  addressSearch.value = ''
  clientSearch.value = ''

  selectedBrand.value = filters.brand || null
  selectedTag.value = filters.tag || null
  selectedCategory.value = filters.category || null

  // Сохранённый поиск заменяет подборки, а не смешивается с ними.
  store.addressCollectionIds = []
  store.clientCollectionIds = []
  store.addressCollectionId = null
  store.clientCollectionId = null
  store.addressCollectionMembers = {}
  store.clientCollectionMembers = {}
  store.addressCollectionValues = []
  store.clientCollectionValues = []

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
    brand: selectedBrand.value,
    tag: selectedTag.value,
    category: selectedCategory.value,
    dateFrom: from,
    dateTo: to,
    dateMode: dateMode.value,
    combine: combineMode.value,
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

/**
 * Bring the grid row and both facets up to date after an address change.
 *
 * A full refresh is needed only when the address is part of the active
 * filter (the photo may leave/enter the filtered set). Otherwise the loaded
 * row is updated in place, so lazily loaded pages and scroll survive.
 */
async function applyAddressChange(photoId) {
  if (current.value?.photo_id === photoId) {
    await loadDetails(current.value)

    if (details.value?.photo) {
      store.updateLoadedPhoto(details.value.photo)
    }
  } else {
    const data = await fetchPhotoDetails(photoId).catch(() => null)

    if (data?.photo) store.updateLoadedPhoto(data.photo)
  }

  await store.loadAddresses()
  await store.loadClients()

  if (store.selectedAddresses.length) {
    await store.refresh()
    await store.loadAddresses()
  }
}

async function saveAddressOverride() {
  if (!current.value || !addressChoice.value || addressSaving.value) return

  addressSaving.value = true
  const photoId = current.value.photo_id

  try {
    await setPhotoAddressOverride(photoId, addressChoice.value)
    Notify.create({ type: 'positive', message: 'Юридический адрес обновлён' })
    addressEditOpen.value = false
    await applyAddressChange(photoId)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    addressSaving.value = false
  }
}

async function resetAddressOverride() {
  if (!current.value || addressSaving.value) return

  addressSaving.value = true
  const photoId = current.value.photo_id

  try {
    await clearPhotoAddressOverride(photoId)
    Notify.create({ type: 'info', message: 'Исправление снято' })
    addressEditOpen.value = false
    await applyAddressChange(photoId)
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

// Каждый open() получает номер: поздний ответ от предыдущего фото не должен
// перезаписать details уже открытого (иначе редактор сохранит чужие поля).
let detailsRequest = 0

async function loadDetails(photo) {
  const request = ++detailsRequest
  const photoId = photo.photo_id

  try {
    const data = await fetchPhotoDetails(photoId)

    if (request !== detailsRequest || current.value?.photo_id !== photoId) return
    details.value = data
  } catch (err) {
    if (request === detailsRequest && current.value?.photo_id === photoId) {
      Notify.create({ type: 'negative', message: err.message })
    }
  }

  // История — вспомогательный блок: её отсутствие не должно ломать карточку.
  try {
    const items = (await fetchQwenHistory(photoId, 10)).items || []

    if (request !== detailsRequest || current.value?.photo_id !== photoId) return
    qwenHistory.value = items
  } catch {
    if (request === detailsRequest && current.value?.photo_id === photoId) {
      qwenHistory.value = []
    }
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
    if (current.value?.photo_id === photo.photo_id) detailsLoading.value = false
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
  // После фонового обновления текущего фото может не быть в загруженной
  // странице (индекс −1): стрелка не должна открывать первое фото.
  if (viewerIndex.value < 0) return

  const target = sortedItems.value[viewerIndex.value + delta]

  if (target) await open(target)
}

function fieldLabel(key) {
  const option = LIST_FIELDS.find((item) => item.value === key)
  return option ? option.label : key
}

// Настройка «поля в списке» реально управляет списком: основные поля идут
// первой строкой, текстовые — второй, остальные (дата загрузки и т.п.) —
// третьей.
const LIST_MAIN_FIELDS = ['address', 'taken_at', 'size']
const LIST_SECOND_FIELDS = ['filename', 'client', 'brand', 'category']

const listFieldSet = computed(() => new Set(display.listFields))

function listMainParts(photo) {
  const parts = []

  if (listFieldSet.value.has('address')) {
    const address = photo?.simple_address || photo?.address
    if (address) parts.push({ key: 'address', text: address, bold: true })
  }

  if (listFieldSet.value.has('taken_at') && tileDate(photo)) {
    parts.push({ key: 'taken_at', text: tileDate(photo), bold: false })
  }

  if (listFieldSet.value.has('size') && tileSize(photo)) {
    parts.push({ key: 'size', text: tileSize(photo), bold: false })
  }

  return parts
}

function listSecondParts(photo) {
  const parts = []

  if (listFieldSet.value.has('filename') && photo?.filename) {
    parts.push({ key: 'filename', text: photo.filename })
  }
  if (listFieldSet.value.has('client') && photo?.client) {
    parts.push({ key: 'client', text: photo.client })
  }
  if (listFieldSet.value.has('brand') && photo?.brand) {
    parts.push({ key: 'brand', text: photo.brand })
  }
  if (listFieldSet.value.has('category') && photo?.category) {
    parts.push({ key: 'category', text: photo.category })
  }

  return parts
}

function listExtraFields(photo) {
  return display.listFields
    .filter(
      (field) =>
        !LIST_MAIN_FIELDS.includes(field)
        && !LIST_SECOND_FIELDS.includes(field),
    )
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

/**
 * Юридический адрес фото: ручное исправление важнее распознанного слепка.
 *
 * `photo.legal_address`/`simple_address` уже собраны сервером через
 * COALESCE(override, directory), поэтому по ним находится именно тот адрес,
 * под которым фото показано в панели. Слепок — только запасной путь.
 */
function addressEntryForPhoto(photo) {
  return findAddressEntry(addresses.value, photo)
}

/** Из меню снимка: сохранить его адрес в подборку адресов. */
async function addOneToBucket(photo) {
  const entry = addressEntryForPhoto(photo)

  if (!entry) {
    Notify.create({
      type: 'info',
      message: 'У снимка нет распознанного адреса',
    })
    return
  }

  const value = entry.address

  if (!store.selectedAddresses.includes(value)) {
    store.selectedAddresses = [...store.selectedAddresses, value]
    // Через apply(), чтобы активная подборка снялась и счётчики обновились.
    await apply()
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
        :style="{ width: display.leftPanelWidthEffective + 'px', flex: '0 0 auto' }"
      >
        <q-card
          flat bordered
          class="column"
          :style="{ height: display.sideListHeight + 'px' }"
        >
          <q-card-section class="panel-head q-pb-xs row items-center">
            <div class="panel-title col">
              <span v-if="combineMode === 'union'" class="mode-symbol">○</span>
              <span v-else-if="combineMode === 'address'" class="mode-symbol">△</span>
              <span
                class="mode-label"
                :class="{ 'mode-label--lead': combineMode !== 'client' }"
              >Адреса</span>
              <span class="address-summary">
                <span class="period-count">({{ store.selectedAddresses.length || '' }})</span>
                {{ recognizedAddressCount }}
              </span>
            </div>
            <!-- Пустой выбор = все адреса; кнопка только снимает выделение. -->
            <q-btn
              class="address-reset"
              dense
              flat
              no-caps
              size="sm"
              label="Очистить"
              :disable="!store.selectedAddresses.length"
              @click="resetAddressSelection()"
            >
              <q-tooltip>
                {{
                  store.selectedAddresses.length
                    ? 'Очистить выбор адресов — будут учтены все'
                    : 'Ничего не выбрано: учитываются все адреса'
                }}
              </q-tooltip>
            </q-btn>
          </q-card-section>
          <q-card-section class="q-pt-none q-pb-xs">
            <q-input
              v-model="addressSearch"
              dense
              outlined
              clearable
              placeholder="Поиск адреса"
              class="panel-search"
              @keyup.enter="pickFirstAddress"
            >
              <template #prepend>
                <q-icon name="search" />
              </template>
            </q-input>
            <div v-if="addressHint" class="text-caption text-grey-7 q-mt-xs">
              {{ addressHint }}
            </div>
          </q-card-section>
          <q-separator />
          <q-scroll-area class="col">
            <q-list dense>
              <q-item
                v-for="item in filteredAddresses"
                :key="item.address"
                clickable
                :active="store.selectedAddresses.includes(item.address)"
                active-class="bg-primary text-white"
                @click="pickAddress(item.address)"
              >
                <q-item-section>
                  <div class="address-line">
                    <span class="address-name">
                      {{ item.name }}
                      <q-tooltip v-if="item.name !== item.address">
                        {{ item.address }}
                      </q-tooltip>
                    </span>
                    <span class="address-count">
                      <span class="period-count">({{ item.period_count || '' }})</span>
                      {{ item.count || '' }}
                    </span>
                  </div>
                </q-item-section>
              </q-item>
              <q-item v-if="!filteredAddresses.length">
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
      <div class="col column full-height q-px-xs grid-main">
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
                  @click="pickSuggestion({ kind: 'layout', value: suggestLayout.query })"
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
                  @click="pickSuggestion(item)"
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
            class="apply-search"
            dense
            color="primary"
            icon="search"
            label="Поиск"
            @click="apply()"
          />

          <q-spinner-dots v-if="mediaBusy" color="teal" size="24px" />
          <span v-if="mediaBusy" class="text-caption text-grey">
            {{ mediaStageText }}
          </span>

          <q-btn class="grid-refresh" dense flat icon="refresh" :disable="mediaBusy" @click="refreshGrid()">
            <q-tooltip>Обновить и снять выделение фото</q-tooltip>
          </q-btn>
          <q-btn class="grid-reset" dense flat icon="restart_alt" :disable="mediaBusy" @click="reset">
            <q-tooltip>Сбросить фильтры и результаты поиска</q-tooltip>
          </q-btn>
        </div>

        <!-- Строка тегов: выбранные адреса, клиенты, бренд, тег, категория.
             Одна строка между поиском и фильтрами; при переполнении
             прокручивается колесом, полоса прокрутки скрыта. -->
        <div
          v-if="activeTags.length"
          ref="tagsRowEl"
          class="tags-row q-mb-sm"
          :class="{ 'is-scrollable': tagsScrollable }"
          @wheel="onTagsWheel"
          @pointerdown="onTagsPointerDown"
          @pointermove="onTagsPointerMove"
          @pointerup="onTagsPointerUp"
          @pointerleave="onTagsPointerUp"
          @pointercancel="onTagsPointerUp"
        >
          <q-chip
            v-for="tag in activeTags"
            :key="tag.key"
            dense
            removable
            :icon="tag.icon"
            :color="tagColor(tag.type)"
            text-color="white"
            class="tag-chip"
            @remove="removeTag(tag)"
          >
            {{ tag.label }}
          </q-chip>
        </div>

        <!-- Действия над выбором, сортировка, вид и настройки — одной строкой.
             Выбранные адреса и клиенты здесь не повторяются: их подсвечивают
             боковые панели. -->
        <div class="row items-center q-gutter-xs q-mb-sm">
          <span class="text-caption text-grey-8">{{ periodLabel }}</span>
          <!-- Пока идёт DINO/HYBRID: стадия и число совпадений; грид
               перечитывается сам, когда появляются распознанные фото. -->
          <span
            v-if="pipelineStatusText"
            class="row items-center no-wrap text-caption text-primary pipeline-live"
          >
            <q-spinner-dots size="14px" class="q-mr-xs" />
            {{ pipelineStatusText }}
          </span>
          <!-- Выделение — «корзина»: оно может содержать фото не из текущего
               фильтра. Клик по счётчику снимает выделение целиком. -->
          <q-badge
            v-if="store.selectedCount"
            color="primary"
            class="selection-badge"
            @click="store.clearSelection()"
          >
            выбрано: {{ store.selectedCount }}
            <q-tooltip>Снять выделение</q-tooltip>
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
            @update:model-value="apply()"
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
            @update:model-value="apply()"
          />
          <template v-if="period === 'custom'">
            <q-input
              v-model="customFrom"
              type="date"
              dense
              outlined
              label="С"
              style="width: 130px"
              @blur="apply()"
            />
            <q-input
              v-model="customTo"
              type="date"
              dense
              outlined
              label="По"
              style="width: 130px"
              @blur="apply()"
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
                  lazy
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
                  <!-- Строка 1: поля, выбранные в настройках списка. -->
                  <q-item-label v-if="listMainParts(photo).length" class="ellipsis">
                    <template
                      v-for="(part, index) in listMainParts(photo)"
                      :key="part.key"
                    >
                      <span :class="part.bold ? 'text-weight-bold' : 'text-grey-8'">
                        {{ part.text }}
                      </span>
                      <span v-if="index < listMainParts(photo).length - 1"> · </span>
                    </template>
                  </q-item-label>

                  <!-- Строка 2: имя файла и результат распознавания. -->
                  <q-item-label
                    v-if="listSecondParts(photo).length"
                    caption
                    class="ellipsis"
                  >
                    <q-icon
                      name="auto_awesome"
                      size="14px"
                      :color="qwenColor(photo)"
                      class="q-mr-xs"
                    >
                      <q-tooltip>{{ qwenHint(photo) }}</q-tooltip>
                    </q-icon>
                    <template
                      v-for="(part, index) in listSecondParts(photo)"
                      :key="part.key"
                    >
                      <span>{{ part.text }}</span>
                      <span v-if="index < listSecondParts(photo).length - 1"> · </span>
                    </template>
                  </q-item-label>

                  <!-- Остальные выбранные поля — третьей строкой. -->
                  <q-item-label
                    v-if="listExtraFields(photo).length || photo.source_directory"
                    caption
                    class="ellipsis text-grey-7"
                    :title="photo.source_directory"
                  >
                    <template v-if="listExtraFields(photo).length">{{ listExtraFields(photo).join(' · ') }}</template>
                    <template v-if="photo.source_directory">{{ listExtraFields(photo).length ? ' · ' : '' }}{{ photo.source_directory }}</template>
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
            <div>Ничего не найдено.</div>
            <div
              v-if="activeTags.length"
              class="text-caption text-grey-7 q-mt-xs"
            >
              Активные фильтры: {{ activeTags.map((tag) => tag.label).join(' · ') }}
            </div>
            <div class="row q-gutter-sm q-mt-sm">
              <q-btn
                v-if="selectedBrand || selectedTag || selectedCategory"
                dense
                flat
                color="primary"
                label="Снять бренд и тег"
                @click="clearStructuredAndApply"
              />
              <q-btn
                dense
                flat
                color="primary"
                label="Сбросить все фильтры"
                @click="reset"
              />
            </div>
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
        :style="{ width: display.rightPanelWidthEffective + 'px', flex: '0 0 auto' }"
      >
        <q-card
          flat
          bordered
          class="column"
          :style="{ height: display.sideListHeight + 'px' }"
        >
          <q-card-section class="panel-head q-pb-xs row items-center">
            <div class="panel-title col row items-center no-wrap">
              <span v-if="combineMode === 'union'" class="mode-symbol">○</span>
              <span v-else-if="combineMode === 'client'" class="mode-symbol">□</span>
              <span>
                <span
                  class="mode-label"
                  :class="{ 'mode-label--lead': combineMode !== 'address' }"
                >Клиент/бренд</span>
                <span class="client-summary">({{ clientSelectionCount || '' }})</span>
              </span>
              <q-icon name="help_outline" size="16px" class="client-help q-ml-xs">
                <q-tooltip>
                  Отображается не более 100 клиентов; выбранные показываются
                  всегда. Без выделения учитываются все клиенты и бренды базы.
                  Счётчик — за всё время. Полный список доступен в поиске
                </q-tooltip>
              </q-icon>
            </div>
            <!-- Пустой выбор означает «все клиенты и бренды»; кнопка только
                 снимает конкретное выделение. -->
            <q-btn
              class="client-reset"
              dense
              flat
              no-caps
              size="sm"
              label="Очистить"
              :disable="!clientSelectionCount"
              @click="resetClientSelection()"
            >
              <q-tooltip>
                {{
                  clientSelectionCount
                    ? 'Очистить выбор клиентов и брендов — будут учтены все'
                    : 'Ничего не выбрано: учитываются все клиенты и бренды'
                }}
              </q-tooltip>
            </q-btn>
          </q-card-section>
          <q-card-section class="q-pt-none q-pb-xs">
            <q-input
              v-model="clientSearch"
              dense
              outlined
              clearable
              placeholder="Поиск клиента или бренда"
              class="panel-search"
              @keyup.enter="pickFirstClient"
            >
              <template #prepend>
                <q-icon name="search" />
              </template>
            </q-input>
            <div v-if="clientHint" class="text-caption text-grey-7 q-mt-xs">
              {{ clientHint }}
            </div>
          </q-card-section>
          <q-separator />
          <q-scroll-area class="col">
            <q-list dense>
              <q-item
                v-for="item in filteredClients"
                :key="`${item.kind}:${item.value}`"
                clickable
                :active="isClientActive(item)"
                active-class="bg-secondary text-white"
                @click="pickClientEntry(item)"
              >
                <q-item-section>
                  <div class="ellipsis">{{ item.value }}</div>
                  <div
                    v-if="item.kind === 'brand'"
                    class="text-caption text-grey-7"
                  >
                    бренд
                  </div>
                  <div
                    v-else-if="item.selectedOnly"
                    class="text-caption text-grey-7"
                  >
                    выбран
                  </div>
                </q-item-section>
                <q-item-section side>
                  {{ item.count === null ? '' : item.count }}
                </q-item-section>
              </q-item>
              <q-item v-if="!filteredClients.length">
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
              fit="contain"
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
    <q-dialog v-model="manualOpen" @hide="closeManual()">
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
          <q-btn flat label="Отмена" @click="closeManual()" />
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

/* Строка тегов: одна линия без рамки; полоса прокрутки скрыта, колесо
   мыши прокручивает её по горизонтали (см. onTagsWheel). */
/* Правая колонка — flex-элемент: без min-width: 0 она растягивается под
   содержимое (длинную строку тегов), и та не получает прокрутку. */
.grid-main {
  min-width: 0;
}

.tags-row {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 0;
  background: transparent;
  overflow-x: auto;
  overflow-y: hidden;
  white-space: nowrap;
  min-width: 0;
  max-width: 100%;
  scrollbar-width: none;      /* Firefox */
  -ms-overflow-style: none;   /* старый Edge */
}

/* Курсор-подсказка: строку можно листать колесом или потянуть мышью. */
.tags-row.is-scrollable {
  cursor: grab;
}

.tags-row.is-dragging {
  cursor: grabbing;
  user-select: none;
}

/* У тегов остаётся обычный курсор: крестик должен читаться как кнопка. */
.tags-row .q-chip {
  cursor: default;
}

.tags-row::-webkit-scrollbar {
  display: none;
  height: 0;
}

.tag-chip {
  flex: 0 0 auto;
}

.client-summary {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 300;
  white-space: nowrap;
  color: #455a64;
}

body.body--dark .client-summary {
  color: #b0bec5;
}

.client-help {
  color: #78909c;
  cursor: help;
}

/* Живая строка о ходе DINO/HYBRID: не должна растягивать панель фильтров. */
.pipeline-live {
  max-width: 40vw;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Счётчик выделения — кликабельный: снимает весь выбор. */
.selection-badge {
  cursor: pointer;
}

/* Символ режима у заголовка панели и подчёркивание ведущего фильтра. */
.mode-symbol {
  margin-right: 4px;
  font-weight: 600;
}

.mode-label--lead {
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Счётчик адресов за выбранный период: зелёный тонкий шрифт перед общим. */
.period-count {
  color: #2e7d32;
  font-weight: 300;
  font-size: 12px;
  margin-right: 10px;
}

body.body--dark .period-count {
  color: #81c784;
}

/* Строка адреса: имя и числа всегда на одной линии. */
.address-line {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.address-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.address-count {
  flex: 0 0 auto;
  white-space: nowrap;
}

.address-summary {
  margin-left: 8px;
  text-transform: none;
  letter-spacing: 0;
  white-space: nowrap;
  color: #455a64;
  font-weight: 500;
}

body.body--dark .address-summary {
  color: #cfd8dc;
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
  /* Один тон с шапками боковых панелей: сетка отделяется от белой страницы. */
  background: #eef0f3;
  border-radius: 10px;
  padding: 10px;
}

body.body--dark .grid-scroll {
  background: rgba(255, 255, 255, 0.05);
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
