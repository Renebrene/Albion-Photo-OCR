<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Notify } from 'quasar'

import {
  authImageUrl,
  cancelJob,
  downloadArchive,
  downloadAuthenticated,
  fetchMediaSearchJob,
  fetchPhotoDetails,
  originalUrl,
  previewUrl,
  searchByMedia,
} from '../api/client'
import AuthImage from '../components/AuthImage.vue'
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

const store = usePhotosStore()
const display = useDisplayStore()

const { items, error, loading, addresses, clients, collections, savedSearches } =
  storeToRefs(store)

const q = ref('')
const dateMode = ref('upload')

// ---- smart search by an uploaded photo (item 2; photos only for now) ----
const mediaInput = ref(null)
const mediaFile = ref(null) // the chosen File, kept in memory until ПОИСК
const mediaJobId = ref(null)
const mediaStage = ref('')
const mediaBusy = ref(false)

const mediaName = computed(() => (mediaFile.value ? mediaFile.value.name : ''))

const mediaStageText = computed(
  () =>
    ({
      queued: 'в очереди…',
      qwen: 'QWEN обрабатывает фото…',
      search: 'поиск по базе…',
    })[mediaStage.value] || 'обработка…',
)
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

// "В подборку" dialog
const bucketOpen = ref(false)
const bucketId = ref(null)
const newName = ref('')
const newKind = ref('Моя')
const newClient = ref('')

const dateModes = [
  { label: 'Дата загрузки', value: 'upload' },
  { label: 'Дата съёмки', value: 'capture' },
]

const periods = [
  { label: 'Все даты', value: 'all' },
  { label: 'Текущий месяц', value: 'month' },
  { label: 'Предыдущий месяц', value: 'prev_month' },
  { label: 'Период…', value: 'custom' },
]

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

function iso(date) {
  return date.toISOString().slice(0, 10)
}

function monthRange(offset) {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  const last = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)
  return [iso(first), iso(last)]
}

function currentDates() {
  switch (period.value) {
    case 'month':
      return monthRange(0)
    case 'prev_month':
      return monthRange(-1)
    case 'custom':
      return [customFrom.value || null, customTo.value || null]
    default:
      return [null, null]
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKeydown)
  await store.loadFacets()
  apply()
  await nextTick()

  if (gridScrollEl.value && typeof ResizeObserver !== 'undefined') {
    gridObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) gridWidth.value = entry.contentRect.width
    })
    gridObserver.observe(gridScrollEl.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  stopGridObserver()
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

async function apply() {
  const [dateFrom, dateTo] = currentDates()
  await store.applyFilters({
    q: q.value.trim(),
    addresses: [...store.selectedAddresses],
    clients: [...store.selectedClients],
    dateFrom,
    dateTo,
    dateMode: dateMode.value,
    collectionId: store.collectionId,
  })
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
  store.clearSelection()
  await apply()
}

// ---- smart search by an uploaded photo ----

function pickMedia() {
  mediaInput.value?.click()
}

function onMediaChosen(event) {
  const [file] = Array.from(event.target.files || [])
  event.target.value = '' // allow re-picking the same file

  mediaFile.value = file || null

  if (file) {
    // A media query and a text query are mutually exclusive.
    q.value = ''
  }
}

function clearMedia() {
  mediaFile.value = null
  mediaStage.value = ''
  store.applyNlResults([])
}

async function runMediaSearch() {
  if (!mediaFile.value || mediaBusy.value) return

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

      if (job.status === 'RUNNING') mediaStage.value = 'qwen'
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
    mediaBusy.value = false
    mediaJobId.value = null
    mediaStage.value = ''
  }
}

async function stopMediaSearch() {
  if (!mediaJobId.value) return

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

async function openBucketDialog() {
  if (!store.selectedCount) {
    Notify.create({ type: 'info', message: 'Сначала выберите фото' })
    return
  }
  await store.loadCollections()
  bucketId.value = null
  newName.value = ''
  bucketOpen.value = true
}

async function saveToBucket() {
  try {
    let collectionId = bucketId.value

    if (!collectionId) {
      const name = newName.value.trim()
      if (!name) {
        Notify.create({ type: 'warning', message: 'Введите название подборки' })
        return
      }
      const created = await store.createCollection({
        name,
        kind: newKind.value,
        client: newClient.value.trim() || null,
        scope: 'photos',
      })
      collectionId = created.collection_id
    }

    const added = await store.addSelectedToCollection(collectionId)
    Notify.create({ type: 'positive', message: `Добавлено в подборку: ${added}` })
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

// ZIP: one server-built archive instead of a file per photo.
const zipBusy = ref(false)

async function downloadZip() {
  if (!store.selectedCount) return

  zipBusy.value = true

  try {
    const items = [...store.selected].map((photoId) => ({
      photo_id: photoId,
      // The same name the single-file download would use.
      name: downloadFileName(
        items.value.find((photo) => photo.photo_id === photoId) || {
          photo_id: photoId,
        },
        display.downloadNameMode,
      ),
    }))

    await downloadArchive(items)

    Notify.create({
      type: 'positive',
      message: `Архив собран: ${items.length} фото`,
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

async function onLoad(index, done) {
  if (!store.hasMore) {
    done(true)
    return
  }

  await store.loadPage()
  done(!store.hasMore)
}

async function open(photo) {
  current.value = photo
  details.value = null
  viewerOpen.value = true
  detailsLoading.value = true

  try {
    details.value = await fetchPhotoDetails(photo.photo_id)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
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

async function addOneToBucket(photo) {
  if (!store.isSelected(photo.photo_id)) {
    store.toggleSelected(photo.photo_id)
  }
  await openBucketDialog()
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

        <CollectionsPanel @create="openBucketDialog" />
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
          <q-input
            v-model="q"
            dense
            outlined
            clearable
            :disable="!!mediaFile"
            :placeholder="
              mediaFile ? '' : 'Название файла, клиент, бренд, адрес'
            "
            class="col"
            @keyup.enter="apply"
          >
            <template #prepend>
              <q-icon :name="mediaFile ? 'image' : 'search'" />
            </template>
          </q-input>

          <!-- the chosen image is named right in the search row -->
          <q-chip
            v-if="mediaFile"
            dense
            removable
            color="teal"
            text-color="white"
            icon="photo_camera"
            @remove="clearMedia"
          >
            {{ mediaName }} (фото)
          </q-chip>

          <q-btn dense flat icon="photo_camera" :disable="mediaBusy" @click="pickMedia">
            <q-tooltip>Умный поиск по фото (одно изображение)</q-tooltip>
          </q-btn>
          <input
            ref="mediaInput"
            type="file"
            accept="image/jpeg,image/png,.jpg,.jpeg,.png"
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

          <!-- сохранённые поиски переехали из левой панели в это меню -->
          <q-btn dense flat icon="bookmarks">
            <q-tooltip>Сохранённые поиски</q-tooltip>
            <q-menu>
              <q-list dense style="min-width: 240px">
                <q-item clickable v-close-popup @click="openSaveSearch">
                  <q-item-section avatar>
                    <q-icon name="bookmark_add" />
                  </q-item-section>
                  <q-item-section>Сохранить текущий поиск</q-item-section>
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
                    Нет сохранённых поисков
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

        <div ref="gridScrollEl" class="col grid-scroll">
          <q-infinite-scroll @load="onLoad" :offset="600">
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
                       дата съёмки и вес — жирным курсивом, клиент — курсивом. -->
                  <div
                    v-if="photo.address"
                    class="ellipsis text-caption text-weight-bold"
                  >
                    {{ photo.simple_address || photo.address }}
                    <q-tooltip v-if="photo.simple_address">
                      {{ photo.address }}
                    </q-tooltip>
                  </div>
                  <div class="ellipsis text-caption">{{ photo.filename }}</div>
                  <div
                    v-if="tileMeta(photo)"
                    class="ellipsis text-caption text-weight-bold font-italic"
                  >
                    {{ tileMeta(photo) }}
                  </div>
                  <div
                    v-if="photo.client"
                    class="ellipsis text-caption font-italic"
                  >
                    {{ photo.client }}
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
                    <q-item clickable v-close-popup @click="openOriginal(photo)">
                      <q-item-section avatar>
                        <q-icon name="open_in_new" />
                      </q-item-section>
                      <q-item-section>Оригинал</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="saveOriginal(photo)">
                      <q-item-section avatar>
                        <q-icon name="download" />
                      </q-item-section>
                      <q-item-section>Сохранить</q-item-section>
                    </q-item>
                    <q-item clickable v-close-popup @click="addOneToBucket(photo)">
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

                  <!-- Строка 2: имя файла, клиент и бренд через запятую. -->
                  <q-item-label caption class="ellipsis">
                    {{
                      [photo.filename, photo.client, photo.brand]
                        .filter(Boolean)
                        .join(', ')
                    }}
                  </q-item-label>

                  <!-- Остальные поля из настроек списка (размер в пикселях,
                       дата загрузки) — третьей строкой, чтобы настройка не
                       потеряла смысл. -->
                  <q-item-label
                    v-if="extraListFields(photo).length"
                    caption
                    class="ellipsis text-grey-7"
                  >
                    {{ extraListFields(photo).join(' · ') }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn dense flat icon="more_vert" @click.stop>
                    <q-menu>
                      <q-list dense style="min-width: 180px">
                        <q-item clickable v-close-popup @click="openOriginal(photo)">
                          <q-item-section avatar><q-icon name="open_in_new" /></q-item-section>
                          <q-item-section>Оригинал</q-item-section>
                        </q-item>
                        <q-item clickable v-close-popup @click="saveOriginal(photo)">
                          <q-item-section avatar><q-icon name="download" /></q-item-section>
                          <q-item-section>Сохранить</q-item-section>
                        </q-item>
                        <q-item clickable v-close-popup @click="addOneToBucket(photo)">
                          <q-item-section avatar><q-icon name="bookmark_add" /></q-item-section>
                          <q-item-section>В подборку</q-item-section>
                        </q-item>
                      </q-list>
                    </q-menu>
                  </q-btn>
                </q-item-section>
              </q-item>
            </q-list>

            <template #loading>
              <div class="row justify-center q-my-md">
                <q-spinner-dots color="primary" size="40px" />
              </div>
            </template>
          </q-infinite-scroll>

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
          flat bordered
          class="column"
          :style="{ height: display.sideListHeight + 'px' }"
        >
          <q-card-section class="panel-head q-pb-xs row items-center">
            <div class="panel-title col">Клиенты</div>
            <!-- Одна кнопка: пока ничего не выбрано — «Все», иначе «Снять». -->
            <q-btn
              dense
              flat
              size="sm"
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
            <q-list dense>
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

        <CollectionsPanel @create="openBucketDialog" />
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
              <span v-if="viewerIndex >= 0" class="text-grey-7">
                ({{ viewerIndex + 1 }})
              </span>
            </div>
            <div class="text-caption text-grey-7 ellipsis">
              {{ current?.filename }}
            </div>
          </div>
          <q-btn dense flat icon="open_in_new" @click="openOriginal(current)">
            <q-tooltip>Открыть оригинал</q-tooltip>
          </q-btn>
          <q-btn dense flat icon="download" @click="saveOriginal(current)">
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
              <div class="text-caption text-grey">ID</div>
              <div class="ellipsis">{{ current?.photo_id }}</div>

              <div v-if="detailsLoading">
                <q-spinner-dots color="primary" size="28px" />
              </div>

              <template v-else>
                <div class="q-mt-sm">
                  <div class="text-caption text-grey">Юридический адрес</div>
                  <div>{{ info?.legal_address || '—' }}</div>
                  <div
                    v-if="!info?.legal_address"
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

                <div class="row q-col-gutter-xs q-mt-sm">
                  <div class="col-6">
                    <div class="text-caption text-grey">Клиент</div>
                    <div>{{ current?.client || '—' }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-caption text-grey">Бренд</div>
                    <div>{{ current?.brand || '—' }}</div>
                  </div>
                </div>

                <!-- QWEN status: grey НЕТ, red !!!, orange ..., green ЕСТЬ -->
                <div class="row items-center q-gutter-xs q-mt-sm">
                  <div class="text-caption text-grey">QWEN</div>
                  <q-badge
                    :color="qwenStatus(qwen).color"
                    :label="qwenStatus(qwen).label"
                  />
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

                <div v-if="!qwen" class="text-caption text-grey q-mt-md">
                  QWEN-метаданных нет.
                </div>
              </template>
            </q-card-section>
          </div>
        </div>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bucketOpen">
      <q-card style="min-width: 360px">
        <q-card-section class="text-subtitle1">В подборку</q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-select
            v-model="bucketId"
            :options="collections"
            option-label="name"
            option-value="collection_id"
            emit-value
            map-options
            dense
            outlined
            clearable
            label="Существующая подборка"
          />
          <div class="text-caption text-grey">или создать новую:</div>
          <q-input v-model="newName" dense outlined label="Название" />
          <q-select
            v-model="newKind"
            :options="['Моя', 'Клиентская']"
            dense
            outlined
            label="Тип"
          />
          <q-input
            v-if="newKind === 'Клиентская'"
            v-model="newClient"
            dense
            outlined
            label="Клиент"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Добавить" @click="saveToBucket" />
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
      <q-card style="min-width: 380px; max-width: 90vw">
        <q-card-section class="text-subtitle1">
          Настройки отображения
        </q-card-section>
        <q-separator />
        <q-card-section>
          <DisplaySettings />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
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

.left-panel,
.right-panel {
  height: 100%;
  overflow-y: auto;
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
</style>
