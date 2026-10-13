<script setup>
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Notify } from 'quasar'

import {
  authImageUrl,
  downloadAuthenticated,
  enqueueNlSearch,
  fetchNlSearchJob,
  fetchPhotoDetails,
  originalUrl,
  previewUrl,
  uploadPhotos,
} from '../api/client'
import AuthImage from '../components/AuthImage.vue'
import { usePhotosStore } from '../stores/photos'

const store = usePhotosStore()
const { items, error, loading, addresses, clients, collections, savedSearches } =
  storeToRefs(store)

const q = ref('')
const nlQuery = ref('')
const nlBusy = ref(false)
const dateMode = ref('upload')
const period = ref('month')
const customFrom = ref(null)
const customTo = ref(null)

// Grid presentation (mirrors the legacy list/tile toggle + sorting).
const viewMode = ref('tiles')
const sortKey = ref('filename')
const sortOptions = [
  { label: 'По имени файла', value: 'filename' },
  { label: 'По адресу', value: 'address' },
  { label: 'По клиенту', value: 'client' },
]

const sortedItems = computed(() => {
  const key = sortKey.value
  return [...items.value].sort((a, b) => {
    const av = (a[key] || '').toString()
    const bv = (b[key] || '').toString()
    return av.localeCompare(bv, 'ru')
  })
})

const viewerOpen = ref(false)
const current = ref(null)
const details = ref(null)
const detailsLoading = ref(false)

// upload (button + drag-and-drop)
const fileInput = ref(null)
const uploading = ref(false)
const dragging = ref(false)

// "В подборку" dialog
const bucketOpen = ref(false)
const bucketId = ref(null)
const newName = ref('')
const newKind = ref('Моя')
const newClient = ref('')

const dateModes = [
  { label: 'Дата загрузки', value: 'upload' },
  { label: 'Дата съёмки', value: 'capture', disable: true },
]

const periods = [
  { label: 'Текущий месяц', value: 'month' },
  { label: 'Предыдущий месяц', value: 'prev_month' },
  { label: 'Все даты', value: 'all' },
  { label: 'Выбрать период', value: 'custom' },
]

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
  await store.loadFacets()
  apply()
})

async function apply() {
  const [dateFrom, dateTo] = currentDates()
  await store.applyFilters({
    q: q.value.trim(),
    addresses: [...store.selectedAddresses],
    clients: [...store.selectedClients],
    dateFrom,
    dateTo,
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

async function pickCollection(collection) {
  await store.selectCollection(
    store.collectionId === collection.collection_id
      ? null
      : collection.collection_id,
  )
}

async function removeCollection(collection) {
  try {
    await store.deleteCollectionById(collection.collection_id)
    Notify.create({ type: 'positive', message: 'Подборка удалена' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
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

  await store.applyFilters({
    q: q.value,
    addresses: filters.addresses || [],
    clients: filters.clients || [],
    dateFrom: from,
    dateTo: to,
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

async function downloadSelected() {
  if (!store.selectedCount) {
    Notify.create({ type: 'info', message: 'Сначала выберите фото' })
    return
  }

  for (const photoId of [...store.selected]) {
    try {
      await downloadAuthenticated(originalUrl(photoId), photoId)
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
      break
    }
  }
}

function pickFiles() {
  fileInput.value?.click()
}

async function onFilesChosen(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = '' // allow re-picking the same file
  await doUpload(files)
}

async function onDrop(event) {
  dragging.value = false
  await doUpload(Array.from(event.dataTransfer?.files || []))
}

async function doUpload(files) {
  if (!files.length) return
  uploading.value = true
  try {
    const result = await uploadPhotos(files)
    const accepted = result.accepted ?? 0
    const failed = (result.items || []).filter((item) => item.error).length
    Notify.create({
      type: accepted ? 'positive' : 'warning',
      message: `Загружено: ${accepted}, ошибок: ${failed}`,
    })
    await store.refresh()
    await store.loadFacets()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    uploading.value = false
  }
}

async function runNlSearch() {
  const query = nlQuery.value.trim()
  if (!query) return

  nlBusy.value = true
  try {
    const { job_id: jobId } = await enqueueNlSearch(query)

    let job = null
    for (let i = 0; i < 40; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500))
      job = await fetchNlSearchJob(jobId)
      if (job.status === 'DONE' || job.status === 'FAILED') break
    }

    if (!job || job.status !== 'DONE') {
      Notify.create({
        type: 'negative',
        message: `NL-поиск: ${job ? job.status : 'таймаут'}`,
      })
      return
    }

    const ids = (job.result && job.result.photo_ids) || []
    Notify.create({ type: 'info', message: `NL-поиск: найдено ${ids.length}` })
    await store.applyNlResults(ids)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    nlBusy.value = false
  }
}

async function clearNlSearch() {
  nlQuery.value = ''
  await store.applyNlResults([])
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
    await downloadAuthenticated(originalUrl(photo.photo_id), photo.filename)
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

function tagList(meta) {
  const tags = meta?.tags
  return Array.isArray(tags) ? tags : []
}
</script>

<template>
  <q-page class="q-pa-md">
    <div class="row no-wrap q-col-gutter-md">
      <!-- LEFT: period + addresses + clients + collections -->
      <div class="col-auto" style="width: 360px; min-width: 320px">
        <q-card flat bordered class="q-mb-sm">
          <q-card-section class="q-pb-sm">
            <div class="text-subtitle2 q-mb-sm">Период</div>

            <q-option-group v-model="dateMode" :options="dateModes" inline dense />

            <q-select
              v-model="period"
              :options="periods"
              dense
              outlined
              emit-value
              map-options
              option-label="label"
              option-value="value"
              class="q-mt-sm"
              @update:model-value="apply"
            />

            <div v-if="period === 'custom'" class="row q-col-gutter-xs q-mt-sm">
              <div class="col">
                <q-input v-model="customFrom" type="date" dense outlined label="С" />
              </div>
              <div class="col">
                <q-input v-model="customTo" type="date" dense outlined label="По" />
              </div>
              <div class="col-auto">
                <q-btn dense flat icon="search" @click="apply" />
              </div>
            </div>

            <div class="text-caption text-orange q-mt-xs">
              «Дата съёмки» не сохраняется — фильтр по дате загрузки.
            </div>
          </q-card-section>
        </q-card>

        <div class="row no-wrap q-mb-sm" style="height: 300px">
          <q-card flat bordered class="col q-mr-xs column">
            <q-card-section class="q-pb-xs row items-center">
              <div class="text-subtitle2 col">Адреса</div>
              <q-btn dense flat size="sm" label="Все" @click="selectAllAddresses" />
              <q-btn dense flat size="sm" label="Снять" @click="clearAddresses" />
            </q-card-section>
            <q-separator />
            <q-scroll-area class="col">
              <q-list dense>
                <q-item
                  v-for="item in addresses"
                  :key="item.address"
                  clickable
                  @click="pickAddress(item.address)"
                >
                  <q-item-section side>
                    <q-checkbox
                      :model-value="store.selectedAddresses.includes(item.address)"
                      dense
                      color="primary"
                      @click.stop
                      @update:model-value="pickAddress(item.address)"
                    />
                  </q-item-section>
                  <q-item-section>{{ item.address }}</q-item-section>
                  <q-item-section side>{{ item.count }}</q-item-section>
                </q-item>
              </q-list>
            </q-scroll-area>
          </q-card>

          <q-card flat bordered class="col column">
            <q-card-section class="q-pb-xs row items-center">
              <div class="text-subtitle2 col">Клиенты</div>
              <q-btn dense flat size="sm" label="Все" @click="selectAllClients" />
              <q-btn dense flat size="sm" label="Снять" @click="clearClients" />
            </q-card-section>
            <q-separator />
            <q-scroll-area class="col">
              <q-list dense>
                <q-item
                  v-for="item in clients"
                  :key="item.client"
                  clickable
                  @click="pickClient(item.client)"
                >
                  <q-item-section side>
                    <q-checkbox
                      :model-value="store.selectedClients.includes(item.client)"
                      dense
                      color="primary"
                      @click.stop
                      @update:model-value="pickClient(item.client)"
                    />
                  </q-item-section>
                  <q-item-section>{{ item.client }}</q-item-section>
                  <q-item-section side>{{ item.count }}</q-item-section>
                </q-item>
              </q-list>
            </q-scroll-area>
          </q-card>
        </div>

        <q-card flat bordered class="column" style="height: 240px">
          <q-card-section class="q-pb-xs row items-center">
            <div class="text-subtitle2 col">Подборки</div>
            <q-btn dense flat icon="add" size="sm" @click="openBucketDialog" />
          </q-card-section>
          <q-separator />
          <q-scroll-area class="col">
            <q-list dense>
              <q-item
                v-for="collection in collections"
                :key="collection.collection_id"
                clickable
                :active="store.collectionId === collection.collection_id"
                active-class="bg-secondary text-white"
                @click="pickCollection(collection)"
              >
                <q-item-section avatar>
                  <q-icon name="bookmark" size="18px" />
                </q-item-section>
                <q-item-section>
                  <div class="ellipsis">{{ collection.name }}</div>
                  <div class="text-caption text-grey-7">{{ collection.kind }}</div>
                </q-item-section>
                <q-item-section side>{{ collection.members }}</q-item-section>
                <q-item-section side>
                  <q-btn
                    dense
                    flat
                    size="sm"
                    icon="delete"
                    @click.stop="removeCollection(collection)"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-scroll-area>
        </q-card>

        <q-card flat bordered class="column q-mt-sm" style="height: 200px">
          <q-card-section class="q-pb-xs row items-center">
            <div class="text-subtitle2 col">История поиска</div>
            <q-btn
              dense
              flat
              size="sm"
              icon="bookmark_add"
              label="Сохранить поиск"
              @click="openSaveSearch"
            />
          </q-card-section>
          <q-separator />
          <q-scroll-area class="col">
            <q-list dense>
              <q-item
                v-for="search in savedSearches"
                :key="search.search_id"
                clickable
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
          </q-scroll-area>
        </q-card>
      </div>

      <!-- RIGHT: toolbar + grid -->
      <div class="col">
        <div class="row items-center q-gutter-sm q-mb-sm">
          <q-input
            v-model="q"
            dense
            outlined
            clearable
            placeholder="Файл, клиент, бренд, категория…"
            class="col-12 col-sm-3"
            @keyup.enter="apply"
          />
          <q-btn
            color="primary"
            icon="photo_library"
            label="Показать фотографии"
            @click="apply"
          />
          <q-btn flat icon="refresh" dense @click="store.refresh()" />
          <q-btn flat icon="restart_alt" dense label="Сброс" @click="reset" />

          <q-chip
            v-for="value in store.selectedAddresses"
            :key="`a-${value}`"
            removable
            color="primary"
            text-color="white"
            @remove="pickAddress(value)"
          >
            Адрес: {{ value }}
          </q-chip>
          <q-chip
            v-for="value in store.selectedClients"
            :key="`c-${value}`"
            removable
            color="secondary"
            text-color="white"
            @remove="pickClient(value)"
          >
            Клиент: {{ value }}
          </q-chip>

          <q-space />

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
            style="min-width: 170px"
          />

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

          <div class="text-caption text-grey">{{ items.length }} фото</div>
        </div>

        <div class="row items-center q-gutter-sm q-mb-sm">
          <q-input
            v-model="nlQuery"
            dense
            outlined
            clearable
            placeholder="Спросить: «вывески бренда Luvio»"
            class="col-12 col-sm-6"
            :disable="nlBusy"
            @keyup.enter="runNlSearch"
          />
          <q-btn
            dense
            color="teal"
            icon="auto_awesome"
            label="NL-поиск"
            :loading="nlBusy"
            @click="runNlSearch"
          />
          <q-btn
            v-if="store.nlIds.length"
            dense
            flat
            icon="close"
            label="Сбросить NL"
            @click="clearNlSearch"
          />
          <q-badge v-if="store.nlIds.length" color="teal">
            NL: {{ store.nlIds.length }}
          </q-badge>
        </div>

        <div class="row items-center q-gutter-sm q-mb-sm">
          <q-btn
            flat
            dense
            icon="select_all"
            label="Выбрать все"
            @click="store.selectAllCurrent()"
          />
          <q-btn
            flat
            dense
            icon="deselect"
            label="Снять"
            @click="store.clearSelection()"
          />
          <q-badge v-if="store.selectedCount" color="primary">
            выбрано: {{ store.selectedCount }}
          </q-badge>
          <q-btn
            dense
            color="secondary"
            icon="bookmark_add"
            label="В подборку"
            @click="openBucketDialog"
          />
          <q-btn
            dense
            flat
            icon="download"
            label="Скачать выбранные"
            @click="downloadSelected"
          />
          <q-btn
            dense
            color="primary"
            icon="upload"
            label="Загрузить"
            :loading="uploading"
            @click="pickFiles"
          />
          <input
            ref="fileInput"
            type="file"
            accept="image/jpeg,.jpg,.jpeg"
            multiple
            class="hidden-input"
            @change="onFilesChosen"
          />
        </div>

        <div v-if="error" class="q-mb-md">
          <q-banner class="bg-red-1 text-negative">Ошибка: {{ error }}</q-banner>
        </div>

        <q-infinite-scroll
          @load="onLoad"
          :offset="300"
          class="drop-zone"
          :class="{ 'drop-zone--active': dragging }"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="onDrop"
        >
          <div v-if="viewMode === 'tiles'" class="photo-grid">
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
                <div class="ellipsis text-caption">{{ photo.filename }}</div>
                <div v-if="photo.address" class="ellipsis text-caption text-grey-8">
                  {{ photo.address }}
                </div>
                <div v-if="photo.client" class="ellipsis text-caption text-grey-8">
                  {{ photo.client }}
                </div>
              </q-card-section>

              <!-- right-click context menu -->
              <q-menu context-menu touch-position>
                <q-list dense style="min-width: 180px">
                  <q-item clickable v-close-popup @click="open(photo)">
                    <q-item-section avatar><q-icon name="visibility" /></q-item-section>
                    <q-item-section>Открыть</q-item-section>
                  </q-item>
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
                <q-item-label>{{ photo.filename }}</q-item-label>
                <q-item-label caption>
                  {{ photo.address || '—' }} · {{ photo.client || '—' }}
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

        <div v-if="!loading && !error && items.length === 0" class="text-grey q-mt-lg">
          Ничего не найдено.
        </div>
      </div>
    </div>

    <q-dialog v-model="viewerOpen">
      <q-card style="width: 1100px; max-width: 95vw; max-height: 92vh">
        <q-card-section class="row items-center q-pb-sm">
          <div class="text-subtitle1 col ellipsis">{{ current?.filename }}</div>
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
          <div class="col-7 column items-center bg-grey-3 q-pa-sm">
            <AuthImage
              :url="viewerUrl()"
              :ratio="4 / 3"
              class="rounded-borders"
              style="max-width: 100%"
            />
          </div>

          <div class="col-5 column" style="overflow: auto">
            <q-card-section class="q-gutter-xs">
              <div class="text-caption text-grey">ID: {{ current?.photo_id }}</div>

              <div v-if="detailsLoading">
                <q-spinner-dots color="primary" size="28px" />
              </div>

              <template v-else>
                <div class="row q-col-gutter-xs">
                  <div class="col-6">
                    <div class="text-caption text-grey">Адрес (распознавание)</div>
                    <div>{{ current?.address || '—' }}</div>
                  </div>
                  <div class="col-6">
                    <div class="text-caption text-grey">Клиент</div>
                    <div>{{ current?.client || '—' }}</div>
                  </div>
                </div>

                <template v-if="qwen">
                  <div class="row q-col-gutter-xs q-mt-sm">
                    <div class="col-6">
                      <div class="text-caption text-grey">Бренд</div>
                      <div>{{ qwen.brand || '—' }}</div>
                    </div>
                    <div class="col-6">
                      <div class="text-caption text-grey">Категория</div>
                      <div>{{ qwen.category || '—' }}</div>
                    </div>
                  </div>

                  <div class="row items-center q-gutter-xs q-mt-sm">
                    <q-badge
                      :color="qwen.status === 'DONE' ? 'positive' : (qwen.status === 'FAILED' ? 'negative' : 'grey')"
                      :label="qwen.status"
                    />
                    <span class="text-caption text-grey">
                      {{ qwen.qwen_model }}
                      <template v-if="qwen.qwen_time_sec">
                        · {{ qwen.qwen_time_sec.toFixed(1) }} c
                      </template>
                    </span>
                  </div>

                  <div v-if="qwen.description" class="q-mt-sm">
                    <div class="text-caption text-grey">Описание</div>
                    <div class="text-body2">{{ qwen.description }}</div>
                  </div>

                  <div v-if="qwen.error_message" class="q-mt-sm">
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
                </template>

                <div v-else class="text-caption text-grey q-mt-md">
                  QWEN-метаданных для этого фото нет.
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
  </q-page>
</template>

<style scoped>
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.photo-card {
  position: relative;
  overflow: hidden;
}

.photo-check {
  position: absolute;
  top: 4px;
  left: 4px;
  z-index: 2;
  background: rgba(255, 255, 255, 0.85);
  border-radius: 4px;
}

.hidden-input {
  display: none;
}

.drop-zone--active {
  outline: 2px dashed var(--q-primary);
  outline-offset: 4px;
  border-radius: 6px;
  background: rgba(33, 150, 243, 0.06);
}
</style>
