<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Notify } from 'quasar'

import AuthImage from '../components/AuthImage.vue'
import {
  requestVideoDownload,
  requestVideoPlayback,
  updateVideoTitle,
  videoPosterUrl,
} from '../api/client'
import { useDisplayStore } from '../stores/display'
import { useVideosStore } from '../stores/videos'

const display = useDisplayStore()
const store = useVideosStore()
const { items, nextCursor, loading, error, query, dateMode, dateFrom, dateTo, selectedVideoId } = storeToRefs(store)
const viewMode = ref('tiles')
const detailsOpen = ref(false)
const currentVideo = ref(null)
const playbackUrl = ref('')
const playbackError = ref('')
const titleDraft = ref('')
const savingTitle = ref(false)
const downloading = ref(false)
const scrollElement = ref(null)
let scrollListener = null
let searchTimer = null

const selectedVideo = computed(() => store.selectedVideo)
const gridStyle = computed(() => {
  if (display.tileColumns === 'auto') {
    return { gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))' }
  }
  return { gridTemplateColumns: `repeat(${Number(display.tileColumns)}, minmax(0, 1fr))` }
})
const dateModes = [
  { label: 'Дата загрузки', value: 'upload' },
  { label: 'Дата съёмки', value: 'capture' },
]

function loadPage(options = {}) {
  return store.loadPage(options)
}

function applyFilters() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadPage({ reset: true }), 250)
}

function selectVideo(video) {
  store.selectVideo(video.video_id)
}

async function openDetails(video) {
  currentVideo.value = video
  titleDraft.value = video.display_title || ''
  playbackUrl.value = ''
  playbackError.value = ''
  detailsOpen.value = true
  try {
    const ticket = await requestVideoPlayback(video.video_id)
    if (detailsOpen.value && currentVideo.value?.video_id === video.video_id) {
      playbackUrl.value = ticket.url
    }
  } catch (err) {
    playbackError.value = err.message || 'Не удалось открыть видео'
    Notify.create({ type: 'negative', message: playbackError.value })
  }
}

function closeDetails() {
  detailsOpen.value = false
  // Drop the source immediately so the browser releases its streaming ticket.
  playbackUrl.value = ''
  currentVideo.value = null
}

async function saveTitle() {
  if (!currentVideo.value) return
  savingTitle.value = true
  try {
    const updated = await updateVideoTitle(currentVideo.value.video_id, titleDraft.value)
    const index = items.value.findIndex((item) => item.video_id === updated.video_id)
    if (index >= 0) items.value[index] = updated
    currentVideo.value = updated
    titleDraft.value = updated.display_title || ''
    Notify.create({ type: 'positive', message: 'Название сохранено' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось сохранить название' })
  } finally {
    savingTitle.value = false
  }
}

async function downloadOriginal() {
  if (!selectedVideo.value || downloading.value) return
  downloading.value = true
  try {
    const ticket = await requestVideoDownload(selectedVideo.value.video_id)
    window.location.assign(ticket.url)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось скачать оригинал' })
  } finally {
    downloading.value = false
  }
}

function formatCapture(value) {
  if (!value) return 'Дата съёмки не указана'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(date.getDate())}-${pad(date.getMonth() + 1)}-${String(date.getFullYear()).slice(-2)} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatDuration(value) {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toFixed(1)} с`
}

function formatMegabytes(bytes) {
  if (bytes === null || bytes === undefined) return '—'
  return `${(Number(bytes) / (1024 * 1024)).toFixed(1)} МБ`
}

function onScroll() {
  const el = scrollElement.value
  if (!el || !nextCursor.value || loading.value) return
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 240) loadPage()
}

onMounted(() => {
  loadPage({ reset: true })
  const el = scrollElement.value
  if (el) {
    scrollListener = onScroll
    el.addEventListener('scroll', scrollListener, { passive: true })
  }
})

onBeforeUnmount(() => {
  clearTimeout(searchTimer)
  if (scrollElement.value && scrollListener) {
    scrollElement.value.removeEventListener('scroll', scrollListener)
  }
  playbackUrl.value = ''
})
</script>

<template>
  <q-page class="videos-page q-pa-md">
    <div class="video-toolbar row items-center q-col-gutter-sm q-mb-sm">
      <div class="col-12 col-md-4">
        <q-input
          v-model="query"
          dense
          outlined
          clearable
          label="Поиск видео по имени или названию"
          @update:model-value="applyFilters"
          @keyup.enter="loadPage({ reset: true })"
        >
          <template #append><q-icon name="search" /></template>
        </q-input>
      </div>
      <div class="col-6 col-md-2">
        <q-select v-model="dateMode" :options="dateModes" emit-value map-options dense outlined @update:model-value="loadPage({ reset: true })" />
      </div>
      <div class="col-6 col-md-2">
        <q-input v-model="dateFrom" type="date" dense outlined label="С даты" @update:model-value="loadPage({ reset: true })" />
      </div>
      <div class="col-6 col-md-2">
        <q-input v-model="dateTo" type="date" dense outlined label="По дату" @update:model-value="loadPage({ reset: true })" />
      </div>
      <div class="col-6 col-md-2 row items-center justify-end q-gutter-xs">
        <q-btn-toggle v-model="viewMode" dense unelevated toggle-color="primary" :options="[{label: 'Плитка', value: 'tiles', icon: 'grid_view'}, {label: 'Список', value: 'list', icon: 'view_list'}]" />
        <q-btn flat round dense icon="refresh" :loading="loading" @click="loadPage({ reset: true })"><q-tooltip>Обновить</q-tooltip></q-btn>
      </div>
    </div>

    <div class="video-actions row items-center q-gutter-sm q-mb-sm">
      <span class="text-caption text-grey-7">Видео: {{ items.length }}{{ nextCursor ? '+' : '' }}</span>
      <q-space />
      <span v-if="selectedVideo" class="text-caption ellipsis">Выбрано: {{ selectedVideo.filename }}</span>
      <q-btn color="primary" icon="download" label="Скачать" :disable="!selectedVideo" :loading="downloading" @click="downloadOriginal" />
      <q-btn color="secondary" icon="compress" label="Сжать" :disable="!selectedVideo" disable>
        <q-tooltip>Конвертация появится в следующем этапе</q-tooltip>
      </q-btn>
    </div>

    <div ref="scrollElement" class="video-scroll">
      <q-banner v-if="error" class="bg-negative text-white q-mb-sm" rounded>{{ error }}</q-banner>
      <div v-if="!items.length && !loading && !error" class="text-grey text-center q-pa-xl">Видео не найдено</div>

      <div v-if="viewMode === 'tiles'" class="video-grid" :style="gridStyle">
        <q-card v-for="video in items" :key="video.video_id" flat bordered class="video-card" :class="{'video-card--selected': selectedVideoId === video.video_id}">
          <div class="video-poster" @click="openDetails(video)">
            <AuthImage :url="videoPosterUrl(video.video_id)" ratio="16/9" />
            <q-icon class="video-play-icon" name="play_circle" size="42px" color="white" />
          </div>
          <q-card-section class="q-pa-sm">
            <div class="video-filename ellipsis" :title="video.filename">{{ video.filename }}</div>
            <div class="video-title ellipsis">{{ video.display_title || ' ' }}</div>
            <div class="video-meta">{{ formatCapture(video.taken_at) }}</div>
            <div class="video-meta">{{ formatDuration(video.duration_seconds) }} / {{ formatMegabytes(video.size_bytes) }}</div>
          </q-card-section>
          <q-card-actions align="right" class="q-pt-none">
            <q-checkbox :model-value="selectedVideoId === video.video_id" dense aria-label="Выбрать видео" @update:model-value="selectVideo(video)" />
            <q-btn flat dense round icon="more_horiz" @click="openDetails(video)"><q-tooltip>Просмотр и название</q-tooltip></q-btn>
          </q-card-actions>
        </q-card>
      </div>

      <q-list v-else bordered separator class="video-list">
        <q-item v-for="video in items" :key="video.video_id" class="video-list-item">
          <q-item-section avatar class="video-list-poster" @click="openDetails(video)">
            <AuthImage :url="videoPosterUrl(video.video_id)" ratio="16/9" />
          </q-item-section>
          <q-item-section clickable @click="openDetails(video)">
            <div class="video-list-first">
              <span class="video-filename">{{ video.filename }}</span>
              <i>{{ formatCapture(video.taken_at) }}</i>
              <i>{{ formatDuration(video.duration_seconds) }}</i>
              <i>{{ formatMegabytes(video.size_bytes) }}</i>
            </div>
            <div class="video-list-title">{{ video.display_title || ' ' }}</div>
          </q-item-section>
          <q-item-section side>
            <q-checkbox :model-value="selectedVideoId === video.video_id" dense aria-label="Выбрать видео" @update:model-value="selectVideo(video)" />
          </q-item-section>
        </q-item>
      </q-list>

      <div v-if="loading" class="row justify-center q-pa-md"><q-spinner-dots color="primary" size="32px" /></div>
      <div v-if="nextCursor && !loading" class="row justify-center q-pa-md"><q-btn outline label="Загрузить ещё" @click="loadPage()" /></div>
    </div>

    <q-dialog v-model="detailsOpen" maximized @hide="closeDetails">
      <q-card class="video-details-page">
        <q-toolbar class="bg-primary text-white">
          <q-toolbar-title class="ellipsis">{{ currentVideo?.filename }}</q-toolbar-title>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-toolbar>
        <div class="video-details-layout q-pa-md">
          <div class="video-player-wrap">
            <video v-if="playbackUrl" :src="playbackUrl" controls playsinline preload="metadata" class="video-player" />
            <div v-else class="flex flex-center bg-grey-2 video-player"><q-spinner-dots v-if="!playbackError" size="36px" color="primary" /><span v-else>{{ playbackError }}</span></div>
          </div>
          <q-card flat bordered class="video-detail-card">
            <q-card-section class="panel-head"><div class="panel-title">Сведения о видео</div></q-card-section>
            <q-card-section class="q-gutter-sm">
              <div><b>Файл:</b> {{ currentVideo?.filename }}</div>
              <div><b>Съёмка:</b> {{ formatCapture(currentVideo?.taken_at) }}</div>
              <div><b>Длительность:</b> {{ formatDuration(currentVideo?.duration_seconds) }}</div>
              <div><b>Размер:</b> {{ currentVideo?.width }} × {{ currentVideo?.height }}</div>
              <div><b>Кодек:</b> {{ currentVideo?.video_codec }} / {{ currentVideo?.container_format }}</div>
              <div><b>Вес:</b> {{ formatMegabytes(currentVideo?.size_bytes) }}</div>
              <div><b>Загружено:</b> {{ formatCapture(currentVideo?.created_at) }}</div>
              <q-input v-model="titleDraft" outlined dense maxlength="300" label="Название" />
              <q-btn color="primary" label="Сохранить название" :loading="savingTitle" @click="saveTitle" />
            </q-card-section>
          </q-card>
        </div>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
.videos-page { height: calc(100vh - var(--app-chrome, 85px)); display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.video-scroll { flex: 1 1 auto; min-height: 0; overflow-y: auto; }
.video-grid { display: grid; gap: 10px; align-content: start; }
.video-card { min-width: 0; position: relative; }
.video-card--selected { border-color: var(--q-primary); box-shadow: 0 0 0 2px var(--q-primary); }
.video-poster { position: relative; cursor: pointer; }
.video-play-icon { position: absolute; right: 8px; bottom: 8px; text-shadow: 0 1px 5px #000; pointer-events: none; }
.video-filename { font-weight: 400; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.video-title { font-weight: 700; min-height: 1.3em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.video-meta { font-style: italic; font-size: 0.82em; color: #666; white-space: nowrap; }
.video-list-item { min-height: 92px; }
.video-list-poster { width: 138px; cursor: pointer; }
.video-list-first { display: flex; gap: 16px; align-items: baseline; flex-wrap: wrap; }
.video-list-first i { font-style: italic; white-space: nowrap; }
.video-list-title { font-weight: 700; padding-top: 3px; }
.video-details-page { display: flex; flex-direction: column; min-height: 0; }
.video-details-layout { display: grid; grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr); gap: 16px; min-height: 0; flex: 1; overflow: auto; }
.video-player-wrap { background: #111; min-height: 0; display: flex; align-items: center; justify-content: center; }
.video-player { width: 100%; max-height: calc(100vh - 100px); aspect-ratio: 16 / 9; }
.video-detail-card { align-self: start; }
@media (max-width: 850px) { .video-details-layout { grid-template-columns: 1fr; } .video-list-first { gap: 6px 12px; } }
</style>
