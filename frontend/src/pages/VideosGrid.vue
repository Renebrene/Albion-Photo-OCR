<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Notify } from 'quasar'

import { usePoller } from '../composables/usePoller'

import AuthImage from '../components/AuthImage.vue'
import CloudLinkButton from '../components/CloudLinkButton.vue'
import {
  cancelJob,
  enqueueVideoStoryboard,
  enqueueVideoTranscode,
  enqueueVideoTrim,
  fetchJob,
  fetchVideoTranscode,
  fetchVideoTrim,
  requestVideoDerivativeDownload,
  requestVideoDerivativeIdDownload,
  requestVideoDownload,
  requestVideoPlayback,
  updateVideoTitle,
  videoPosterUrl,
  videoStoryboardFrameUrl,
} from '../api/client'
import { useDisplayStore } from '../stores/display'
import { useSessionStore } from '../stores/session'
import { useVideosStore } from '../stores/videos'

const display = useDisplayStore()
const store = useVideosStore()
const session = useSessionStore()
// Гость видит грид и метаданные, но не скачивает, не сжимает и не редактирует.
const isStaff = computed(
  () => !session.authEnabled || ['Администратор', 'Менеджер'].includes(session.user?.role),
)
const canPlayVideos = computed(() => isStaff.value)
const canWriteVideos = computed(() => isStaff.value)
const canDownloadVideos = computed(() => isStaff.value)
const MAX_EDIT_VIDEO_BYTES = 1_610_612_736
const MAX_EDIT_VIDEO_DURATION_SECONDS = 600
function editLimitReason(video) {
  if (!video) return ''
  if (Number(video.size_bytes) > MAX_EDIT_VIDEO_BYTES) return 'Редактирование ограничено размером до 1,5 ГиБ'
  if (Number(video.duration_seconds) > MAX_EDIT_VIDEO_DURATION_SECONDS) return 'Редактирование ограничено длительностью до 10 минут'
  return ''
}
const editBlockedReason = computed(() => editLimitReason(selectedVideo.value || currentVideo.value))
const { items, nextCursor, loading, error, query, dateMode, dateFrom, dateTo, selectedVideoId } = storeToRefs(store)
const viewMode = ref('tiles')
const detailsOpen = ref(false)
const currentVideo = ref(null)
const playbackUrl = ref('')
const playbackError = ref('')
const titleDraft = ref('')
const savingTitle = ref(false)
const downloading = ref(false)
const transcodeSubmitting = ref(false)
const transcodeVideoId = ref(null)
const transcodeVideoLabel = ref('')
const transcodeProfile = ref(null)
const transcodeInfo = ref(null)
const transcodeError = ref('')
const trimMode = ref(false)
const trimStart = ref(0)
const trimEnd = ref(0)
const trimSubmitting = ref(false)
const trimInfo = ref(null)
const trimError = ref('')
const trimStoryboardJobId = ref(null)
const trimStoryboardStatus = ref('IDLE')
const trimFrameCount = 8
const trimPlayer = ref(null)
const scrollElement = ref(null)
let scrollListener = null
let searchTimer = null
// Три опроса прогресса: конвертация, раскадровка, обрезка. usePoller даёт
// паузу в скрытой вкладке, запрет наложения тиков и снятие таймера при уходе
// со страницы — раньше это были свои setInterval (второй аудит, 2.6).
const transcodePoller = usePoller(pollTranscode, { intervalMs: 1500 })
const storyboardPoller = usePoller(pollStoryboard, { intervalMs: 1500 })
const trimPoller = usePoller(pollTrim, { intervalMs: 1500 })

const selectedVideo = computed(() => store.selectedVideo)
// Задание конвертации: показывается независимо от текущего выделения. Раньше
// блок был привязан к выделенному видео, и стоило выбрать другое — прогресс
// и кнопка «Отмена» пропадали, хотя задание продолжало идти.
const transcodeJob = computed(() => (transcodeVideoId.value ? transcodeInfo.value : null))
// Скачивание готовой копии относится к выделенному видео, поэтому только при
// совпадении: профиль конвертации хранится один на страницу.
const activeTranscode = computed(() =>
  transcodeVideoId.value === selectedVideo.value?.video_id ? transcodeInfo.value : null,
)
const transcodeProfiles = [
  { label: 'Сильно · 720p', value: 'strong_720p' },
  { label: 'Стандартно · 1080p', value: 'standard_1080p' },
  { label: 'Легко · 1440p', value: 'light_1440p' },
]
// Подпись профиля для блока прогресса: сырое «standard_1080p» ничего не
// говорит пользователю.
const transcodeProfileLabel = computed(() => {
  const found = transcodeProfiles.find((item) => item.value === transcodeProfile.value)
  return found ? found.label : transcodeProfile.value || ''
})
// Заголовок блока: чтобы было видно, к какому видео относится задание, когда
// выбрано уже другое.
const transcodeJobTitle = computed(() => {
  const name = transcodeVideoLabel.value || transcodeVideoId.value || ''
  return name ? `Сжатие · ${name}` : 'Сжатие'
})
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
  // Ошибку конвертации здесь не чистим: блок прогресса относится к заданию,
  // а не к выделению, и его подпись говорит, о каком видео речь.
}

async function openDetails(video) {
  currentVideo.value = video
  titleDraft.value = video.display_title || ''
  playbackUrl.value = ''
  playbackError.value = ''
  detailsOpen.value = true

  if (!canPlayVideos.value) {
    playbackError.value = 'Просмотр доступен сотрудникам'
    return
  }

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
  stopTrimTimers()
  trimMode.value = false
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

function stopTranscodePolling() {
  transcodePoller.stop()
}

async function pollTranscode() {
  if (!transcodeVideoId.value || !transcodeProfile.value) return
  try {
    transcodeInfo.value = await fetchVideoTranscode(transcodeVideoId.value, transcodeProfile.value)
    if (['DONE', 'FAILED', 'CANCELLED'].includes(transcodeInfo.value.status)) {
      stopTranscodePolling()
      if (transcodeInfo.value.status === 'DONE') {
        Notify.create({ type: 'positive', message: 'Копия добавлена в видеогалерею' })
        await store.refreshLoaded()
      } else if (transcodeInfo.value.status === 'FAILED') {
        transcodeError.value = transcodeInfo.value.error_message || 'Конвертация завершилась ошибкой'
      }
    }
  } catch (err) {
    transcodeError.value = err.message || 'Не удалось проверить конвертацию'
    stopTranscodePolling()
  }
}

async function startTranscode(profile) {
  if (!selectedVideo.value || transcodeSubmitting.value) return
  transcodeSubmitting.value = true
  transcodeError.value = ''
  transcodeInfo.value = null
  transcodeVideoId.value = selectedVideo.value.video_id
  transcodeVideoLabel.value =
    selectedVideo.value.filename || selectedVideo.value.display_title || ''
  transcodeProfile.value = profile
  try {
    const result = await enqueueVideoTranscode(selectedVideo.value.video_id, profile)
    transcodeInfo.value = await fetchVideoTranscode(selectedVideo.value.video_id, profile)
    if (result.status === 'DONE' || transcodeInfo.value.status === 'DONE') {
      Notify.create({ type: 'positive', message: 'Сжатая копия уже готова' })
    } else {
      stopTranscodePolling()
      transcodePoller.start()
      await pollTranscode()
    }
  } catch (err) {
    transcodeError.value = err.message || 'Не удалось поставить видео на конвертацию'
    Notify.create({ type: 'negative', message: transcodeError.value })
  } finally {
    transcodeSubmitting.value = false
  }
}

async function cancelTranscode() {
  if (!transcodeInfo.value?.job_id) return
  try {
    await cancelJob(transcodeInfo.value.job_id)
    await pollTranscode()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось отменить конвертацию' })
  }
}

async function downloadTranscoded() {
  if (!selectedVideo.value || !transcodeProfile.value || activeTranscode.value?.status !== 'DONE') return
  try {
    const ticket = await requestVideoDerivativeDownload(selectedVideo.value.video_id, transcodeProfile.value)
    window.location.assign(ticket.url)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось скачать сжатую копию' })
  }
}

function stopTrimTimers() {
  trimPoller.stop()
  storyboardPoller.stop()
}

async function enterTrimMode() {
  if (!currentVideo.value) return
  stopTrimTimers()
  trimMode.value = true
  trimStart.value = 0
  trimEnd.value = Number(currentVideo.value.duration_seconds || 0)
  trimInfo.value = null
  trimError.value = ''
  trimStoryboardStatus.value = 'PENDING'
  try {
    const result = await enqueueVideoStoryboard(currentVideo.value.video_id)
    trimStoryboardJobId.value = result.job_id
    if (result.status === 'DONE') {
      trimStoryboardStatus.value = 'DONE'
    } else {
      await pollStoryboard()
      if (trimStoryboardStatus.value === 'PENDING' || trimStoryboardStatus.value === 'RUNNING') {
        storyboardPoller.start()
      }
    }
  } catch (err) {
    trimStoryboardStatus.value = 'FAILED'
    trimError.value = err.message || 'Не удалось подготовить ленту кадров'
  }
}

async function pollStoryboard() {
  if (!trimStoryboardJobId.value) return
  try {
    const job = await fetchJob(trimStoryboardJobId.value)
    trimStoryboardStatus.value = job.status
    if (['DONE', 'FAILED', 'CANCELLED'].includes(job.status)) {
      storyboardPoller.stop()
      if (job.status === 'FAILED') trimError.value = job.error_message || 'Не удалось построить ленту кадров'
    }
  } catch (err) {
    trimStoryboardStatus.value = 'FAILED'
    trimError.value = err.message || 'Не удалось проверить ленту кадров'
    storyboardPoller.stop()
  }
}

function onTrimLoaded() {
  if (trimPlayer.value) trimPlayer.value.currentTime = Number(trimStart.value)
}

async function startTrimPreview() {
  if (!trimPlayer.value) return
  trimPlayer.value.currentTime = Number(trimStart.value)
  try { await trimPlayer.value.play() } catch { /* user can press play in controls */ }
}

function trimTimeUpdate() {
  if (!trimMode.value || !trimPlayer.value) return
  if (trimPlayer.value.currentTime >= Number(trimEnd.value)) trimPlayer.value.pause()
}

function setTrimStartFromPlayer() {
  if (!trimPlayer.value) return
  trimStart.value = Math.max(0, Math.min(Number(trimPlayer.value.currentTime.toFixed(3)), Number(trimEnd.value) - 0.25))
}

function setTrimEndFromPlayer() {
  if (!trimPlayer.value) return
  trimEnd.value = Math.min(Number(currentVideo.value?.duration_seconds || 0), Math.max(Number(trimPlayer.value.currentTime.toFixed(3)), Number(trimStart.value) + 0.25))
}

async function submitTrim() {
  const video = currentVideo.value
  const start = Number(trimStart.value)
  const end = Number(trimEnd.value)
  if (!video || trimSubmitting.value || !Number.isFinite(start) || !Number.isFinite(end) || end - start < 0.25) {
    trimError.value = 'Выберите интервал не короче 0,25 секунды'
    return
  }
  trimSubmitting.value = true
  trimError.value = ''
  stopTrimTimers()
  try {
    const result = await enqueueVideoTrim(video.video_id, start, end)
    trimInfo.value = await fetchVideoTrim(video.video_id, start, end)
    if (result.status !== 'DONE' && trimInfo.value.status !== 'DONE') {
      trimPoller.start()
      await pollTrim()
    }
  } catch (err) {
    trimError.value = err.message || 'Не удалось поставить обрезку в очередь'
  } finally {
    trimSubmitting.value = false
  }
}

async function pollTrim() {
  if (!currentVideo.value) return
  try {
    trimInfo.value = await fetchVideoTrim(currentVideo.value.video_id, Number(trimStart.value), Number(trimEnd.value))
    if (['DONE', 'FAILED', 'CANCELLED'].includes(trimInfo.value.status)) {
      trimPoller.stop()
      if (trimInfo.value.status === 'DONE') {
        Notify.create({ type: 'positive', message: 'Копия добавлена в видеогалерею' })
        // Не сбрасываем список к первой странице: иначе прокрутка прыгала
        // в начало и место работы терялось.
        await store.refreshLoaded()
      }
      if (trimInfo.value.status === 'FAILED') trimError.value = trimInfo.value.error_message || 'Обрезка завершилась ошибкой'
    }
  } catch (err) {
    trimError.value = err.message || 'Не удалось проверить обрезку'
    trimPoller.stop()
  }
}

async function cancelTrim() {
  if (!trimInfo.value?.job_id) return
  try {
    await cancelJob(trimInfo.value.job_id)
    await pollTrim()
  } catch (err) {
    trimError.value = err.message || 'Не удалось отменить обрезку'
  }
}

async function downloadTrim() {
  if (!currentVideo.value || trimInfo.value?.status !== 'DONE') return
  try {
    const ticket = await requestVideoDerivativeIdDownload(currentVideo.value.video_id, trimInfo.value.derivative_id)
    window.location.assign(ticket.url)
  } catch (err) {
    trimError.value = err.message || 'Не удалось скачать обрезанный клип'
  }
}

function leaveTrimMode() {
  stopTrimTimers()
  trimMode.value = false
  if (trimPlayer.value) trimPlayer.value.pause()
}

function formatSeconds(value) {
  const seconds = Math.max(0, Number(value) || 0)
  const mins = Math.floor(seconds / 60)
  return `${mins}:${(seconds % 60).toFixed(1).padStart(4, '0')}`
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
  // Опросы прогресса останавливает сам usePoller при размонтировании.
  clearTimeout(searchTimer)
  if (scrollElement.value && scrollListener) {
    scrollElement.value.removeEventListener('scroll', scrollListener)
  }
  playbackUrl.value = ''
})
</script>

<template>
  <q-page class="videos-page q-pa-md">
    <div class="video-toolbar row items-center no-wrap q-gutter-sm q-mb-sm">
      <div class="col" style="min-width: 220px">
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
      <div class="col-auto" style="width: 170px">
        <q-select v-model="dateMode" :options="dateModes" emit-value map-options dense outlined @update:model-value="loadPage({ reset: true })" />
      </div>
      <div class="col-auto" style="width: 160px">
        <q-input v-model="dateFrom" type="date" dense outlined label="С даты" @update:model-value="loadPage({ reset: true })" />
      </div>
      <div class="col-auto" style="width: 160px">
        <q-input v-model="dateTo" type="date" dense outlined label="По дату" @update:model-value="loadPage({ reset: true })" />
      </div>
      <div class="col-auto row items-center q-gutter-xs">
        <q-btn-toggle v-model="viewMode" dense unelevated toggle-color="primary" :options="[{label: 'Плитка', value: 'tiles', icon: 'grid_view'}, {label: 'Список', value: 'list', icon: 'view_list'}]" />
        <q-btn flat round dense icon="refresh" :loading="loading" @click="loadPage({ reset: true })"><q-tooltip>Обновить</q-tooltip></q-btn>
      </div>
    </div>

    <div class="video-actions row items-center q-gutter-sm q-mb-sm">
      <span class="text-caption text-grey-7">Видео: {{ items.length }}{{ nextCursor ? '+' : '' }}</span>
      <q-space />
      <span v-if="selectedVideo && canDownloadVideos" class="text-caption ellipsis">Выбрано: {{ selectedVideo.filename }}</span>
      <q-btn v-if="canDownloadVideos" color="primary" icon="download" label="Скачать" :disable="!selectedVideo" :loading="downloading" @click="downloadOriginal" />
      <q-btn v-if="canWriteVideos" color="secondary" icon="compress" label="Сжать" :disable="!selectedVideo || Boolean(editLimitReason(selectedVideo))" :loading="transcodeSubmitting">
        <q-menu anchor="bottom right" self="top right">
          <q-list dense style="min-width: 210px">
            <q-item v-for="profile in transcodeProfiles" :key="profile.value" clickable v-close-popup @click="startTranscode(profile.value)">
              <q-item-section>{{ profile.label }}</q-item-section>
            </q-item>
          </q-list>
        </q-menu>
        <q-tooltip>{{ editLimitReason(selectedVideo) || 'Сделать H.264/MP4 копию, оригинал останется без изменений' }}</q-tooltip>
      </q-btn>
      <q-btn v-if="canDownloadVideos && activeTranscode?.status === 'DONE'" outline color="positive" icon="download" label="Скачать сжатое" @click="downloadTranscoded" />
      <CloudLinkButton
        v-if="canWriteVideos"
        :video-ids="selectedVideo ? [selectedVideo.video_id] : []"
        :disabled="!selectedVideo"
      />
    </div>
    <div v-if="transcodeJob || transcodeError" class="video-transcode-status row items-center q-gutter-sm q-mb-sm">
      <span class="text-caption ellipsis">{{ transcodeJobTitle }}</span>
      <span v-if="transcodeJob" class="text-caption text-grey-7">· {{ transcodeProfileLabel }}: {{ transcodeJob.status }}</span>
      <q-linear-progress v-if="transcodeJob && ['PENDING', 'RUNNING'].includes(transcodeJob.status)" class="col" :value="Number(transcodeJob.progress?.percent || 0) / 100" />
      <span v-if="transcodeJob?.status === 'FAILED'" class="text-negative text-caption">{{ transcodeJob.error_message || 'Ошибка конвертации' }}</span>
      <span v-if="transcodeError" class="text-negative text-caption">{{ transcodeError }}</span>
      <q-btn v-if="canWriteVideos && transcodeJob && ['PENDING', 'RUNNING'].includes(transcodeJob.status)" dense flat color="negative" label="Отмена" @click="cancelTranscode" />
    </div>

    <div ref="scrollElement" class="video-scroll">
      <q-banner v-if="error" class="bg-negative text-white q-mb-sm" rounded>{{ error }}</q-banner>
      <div v-if="!items.length && !loading && !error" class="text-grey text-center q-pa-xl">Видео не найдено</div>

      <div v-if="viewMode === 'tiles'" class="video-grid" :style="gridStyle">
        <q-card v-for="video in items" :key="video.video_id" flat bordered class="video-card" :class="{'video-card--selected': selectedVideoId === video.video_id}">
          <div class="video-poster" @click="openDetails(video)">
            <!-- Постеры у всех видео одинакового соотношения: показываем
                 картинку целиком по ширине карточки, без обрезки. -->
            <AuthImage :url="videoPosterUrl(video.video_id)" :ratio="16 / 9" fit="contain" />
            <q-icon class="video-play-icon" name="play_circle" size="42px" color="white" />
          </div>
          <q-card-section class="q-pa-xs">
            <div class="video-filename ellipsis" :title="`${video.filename} — ${video.source_directory || ''}`">
              {{ video.filename }}
            </div>
            <div v-if="video.display_title" class="video-title ellipsis">
              {{ video.display_title }}
            </div>
            <!-- Дата, хроно, вес, выбор и меню — одной компактной строкой. -->
            <div class="video-line row items-center no-wrap">
              <span class="video-meta ellipsis">
                {{ formatCapture(video.taken_at) }} · {{ formatDuration(video.duration_seconds) }} · {{ formatMegabytes(video.size_bytes) }}
              </span>
              <q-space />
              <q-checkbox v-if="canDownloadVideos" :model-value="selectedVideoId === video.video_id" dense aria-label="Выбрать видео" @update:model-value="selectVideo(video)" />
              <q-btn flat dense round icon="more_horiz" @click="openDetails(video)">
                <q-tooltip>Просмотр и название</q-tooltip>
              </q-btn>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <q-list v-else bordered separator class="video-list">
        <q-item v-for="video in items" :key="video.video_id" class="video-list-item">
          <q-item-section avatar class="video-list-poster" @click="openDetails(video)">
            <AuthImage :url="videoPosterUrl(video.video_id)" :ratio="16 / 9" />
          </q-item-section>
          <q-item-section clickable @click="openDetails(video)">
            <div class="video-list-first">
              <span class="video-filename">{{ video.filename }}</span>
              <i class="video-directory">{{ video.source_directory || 'Каталог не указан' }}</i>
              <i>{{ formatCapture(video.taken_at) }}</i>
              <i>{{ formatDuration(video.duration_seconds) }}</i>
              <i>{{ formatMegabytes(video.size_bytes) }}</i>
            </div>
            <div class="video-list-title">{{ video.display_title || ' ' }}</div>
          </q-item-section>
          <q-item-section side>
            <q-checkbox v-if="canDownloadVideos" :model-value="selectedVideoId === video.video_id" dense aria-label="Выбрать видео" @update:model-value="selectVideo(video)" />
          </q-item-section>
        </q-item>
      </q-list>

      <div v-if="loading" class="row justify-center q-pa-md"><q-spinner-dots color="primary" size="32px" /></div>
      <div v-if="nextCursor && !loading" class="row justify-center q-pa-md"><q-btn outline label="Загрузить ещё" @click="loadPage()" /></div>
    </div>

    <q-dialog v-model="detailsOpen" :maximized="false" @hide="closeDetails">
      <q-card
        class="video-details-page"
        style="width: 900px; max-width: calc(100vw - 32px); max-height: min(820px, calc(100vh - 48px))"
      >
        <q-toolbar class="bg-primary text-white">
          <q-toolbar-title class="ellipsis">{{ currentVideo?.filename }}</q-toolbar-title>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-toolbar>
        <div v-if="!trimMode" class="video-details-layout q-pa-md">
          <div class="video-player-wrap">
            <video v-if="playbackUrl" :src="playbackUrl" controls playsinline preload="metadata" class="video-player" />
            <div v-else class="flex flex-center bg-grey-2 video-player">
              <span v-if="!canPlayVideos">Просмотр доступен сотрудникам</span>
              <q-spinner-dots v-else-if="!playbackError" size="36px" color="primary" />
              <span v-else>{{ playbackError }}</span>
            </div>
          </div>
          <q-card flat bordered class="video-detail-card">
            <q-card-section class="panel-head"><div class="panel-title">Сведения о видео</div></q-card-section>
            <q-card-section class="q-gutter-sm">
              <div><b>Файл:</b> {{ currentVideo?.filename }}</div>
              <div><b>Каталог:</b> {{ currentVideo?.source_directory || '—' }}</div>
              <div><b>Съёмка:</b> {{ formatCapture(currentVideo?.taken_at) }}</div>
              <div><b>Длительность:</b> {{ formatDuration(currentVideo?.duration_seconds) }}</div>
              <div><b>Размер:</b> {{ currentVideo?.width }} × {{ currentVideo?.height }}</div>
              <div><b>Кодек:</b> {{ currentVideo?.video_codec }} / {{ currentVideo?.container_format }}</div>
              <div><b>Вес:</b> {{ formatMegabytes(currentVideo?.size_bytes) }}</div>
              <div><b>Загружено:</b> {{ formatCapture(currentVideo?.created_at) }}</div>
              <template v-if="canWriteVideos">
                <q-input v-model="titleDraft" outlined dense maxlength="300" label="Название" />
                <q-btn color="primary" label="Сохранить название" :loading="savingTitle" @click="saveTitle" />
              </template>
              <div v-else><b>Название:</b> {{ currentVideo?.display_title || '—' }}</div>
              <template v-if="canWriteVideos">
                <q-separator />
                <q-btn outline color="secondary" icon="content_cut" label="Обрезать фрагмент" :disable="Boolean(editLimitReason(currentVideo))" @click="enterTrimMode"><q-tooltip v-if="editLimitReason(currentVideo)">{{ editLimitReason(currentVideo) }}</q-tooltip></q-btn>
              </template>
            </q-card-section>
          </q-card>
        </div>
        <div v-else class="trim-editor q-pa-md">
          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-btn flat icon="arrow_back" label="К сведениям" @click="leaveTrimMode" />
            <div class="text-subtitle1">Обрезать фрагмент</div>
            <q-space />
            <span class="text-caption">Оригинал не изменяется</span>
          </div>
          <div class="trim-editor-layout">
            <div class="trim-main">
              <div class="video-player-wrap trim-player-wrap">
                <video
                  v-if="playbackUrl"
                  ref="trimPlayer"
                  :src="playbackUrl"
                  controls
                  playsinline
                  preload="metadata"
                  class="video-player trim-player"
                  @loadedmetadata="onTrimLoaded"
                  @timeupdate="trimTimeUpdate"
                />
              </div>
              <div class="trim-controls q-mt-md">
                <div class="row items-center q-gutter-sm">
                  <q-input v-model.number="trimStart" type="number" min="0" :max="trimEnd - 0.25" step="0.1" dense outlined label="Начало, с" class="col" :disable="trimSubmitting || ['PENDING','RUNNING'].includes(trimInfo?.status)" />
                  <q-btn dense outline label="Текущая → начало" @click="setTrimStartFromPlayer" />
                  <q-input v-model.number="trimEnd" type="number" :min="trimStart + 0.25" :max="currentVideo?.duration_seconds" step="0.1" dense outlined label="Конец, с" class="col" :disable="trimSubmitting || ['PENDING','RUNNING'].includes(trimInfo?.status)" />
                  <q-btn dense outline label="Текущая → конец" @click="setTrimEndFromPlayer" />
                </div>
                <div class="row q-col-gutter-md q-mt-xs">
                  <div class="col-12 col-md-6">
                    <div class="text-caption">Начало: {{ formatSeconds(trimStart) }}</div>
                    <q-slider v-model="trimStart" :min="0" :max="Math.max(0, Number(trimEnd) - 0.25)" :step="0.1" label color="primary" :disable="trimSubmitting || ['PENDING','RUNNING'].includes(trimInfo?.status)" />
                  </div>
                  <div class="col-12 col-md-6">
                    <div class="text-caption">Конец: {{ formatSeconds(trimEnd) }} / {{ formatSeconds(currentVideo?.duration_seconds) }}</div>
                    <q-slider v-model="trimEnd" :min="Number(trimStart) + 0.25" :max="Number(currentVideo?.duration_seconds || 0)" :step="0.1" label color="primary" :disable="trimSubmitting || ['PENDING','RUNNING'].includes(trimInfo?.status)" />
                  </div>
                </div>
                <div class="row items-center q-gutter-sm q-mt-sm">
                  <q-btn outline color="primary" icon="play_arrow" label="Предпросмотр фрагмента" @click="startTrimPreview" />
                  <q-btn color="primary" icon="save" label="Сохранить как новый клип" :loading="trimSubmitting" :disable="['PENDING','RUNNING'].includes(trimInfo?.status)" @click="submitTrim" />
                  <q-btn v-if="canDownloadVideos && trimInfo?.status === 'DONE'" color="positive" icon="download" label="Скачать клип" @click="downloadTrim" />
                  <q-btn v-if="canWriteVideos && ['PENDING','RUNNING'].includes(trimInfo?.status)" flat color="negative" label="Отмена" @click="cancelTrim" />
                  <span v-if="trimInfo" class="text-caption">{{ trimInfo.status }} · {{ trimInfo.progress?.percent ?? 0 }}%</span>
                </div>
                <q-linear-progress v-if="['PENDING','RUNNING'].includes(trimInfo?.status)" class="q-mt-sm" :value="Number(trimInfo.progress?.percent || 0) / 100" />
                <div v-if="trimError" class="text-negative q-mt-sm">{{ trimError }}</div>
              </div>
            </div>
            <q-card flat bordered class="storyboard-card">
              <q-card-section class="panel-head"><div class="panel-title">Ключевые кадры</div></q-card-section>
              <q-card-section>
                <div v-if="['PENDING','RUNNING'].includes(trimStoryboardStatus)" class="text-caption row items-center q-gutter-sm"><q-spinner-dots /> Подготавливаю кадры…</div>
                <div v-else-if="trimStoryboardStatus === 'FAILED'" class="text-negative text-caption">{{ trimError || 'Кадры недоступны' }}</div>
                <div v-else class="storyboard-grid">
                  <button v-for="index in trimFrameCount" :key="index - 1" class="storyboard-frame" type="button" @click="trimPlayer && (trimPlayer.currentTime = (Number(currentVideo?.duration_seconds || 0) * (index - 0.5) / trimFrameCount))">
                    <AuthImage :url="videoStoryboardFrameUrl(currentVideo.video_id, index - 1)" :ratio="16 / 9" />
                    <span>{{ formatSeconds(Number(currentVideo?.duration_seconds || 0) * (index - 0.5) / trimFrameCount) }}</span>
                  </button>
                </div>
              </q-card-section>
            </q-card>
          </div>
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
.video-line { gap: 4px; min-height: 28px; }
.video-line .q-checkbox, .video-line .q-btn { flex: 0 0 auto; }
.video-list-item { min-height: 92px; }
.video-list-poster { width: 138px; cursor: pointer; }
.video-list-first { display: flex; gap: 16px; align-items: baseline; flex-wrap: wrap; }
.video-list-first i { font-style: italic; white-space: nowrap; }
.video-list-title { font-weight: 700; padding-top: 3px; }
.video-details-page { width: 900px; max-width: calc(100vw - 32px); max-height: calc(100vh - 48px); display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.video-details-layout { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.9fr); gap: 12px; min-height: 0; flex: 1; overflow: auto; align-items: start; }
.trim-editor { min-height: 0; flex: 1; overflow: auto; }
.trim-editor-layout { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-height: 0; align-items: start; }
.trim-main { min-width: 0; }
.trim-player-wrap { min-height: 0; }
.trim-player { background: #111; max-height: 42vh; }
.storyboard-card { align-self: start; min-height: 0; }
.storyboard-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; max-height: calc(100vh - 230px); overflow: auto; }
.storyboard-frame { border: 0; padding: 0; background: transparent; cursor: pointer; text-align: left; min-width: 0; }
.storyboard-frame span { display: block; padding: 2px 4px; color: #666; font-size: 0.75rem; }
.video-player-wrap { background: #111; min-height: 0; display: flex; align-items: center; justify-content: center; }
.video-player { width: 100%; max-height: 50vh; aspect-ratio: 16 / 9; object-fit: contain; }
.video-detail-card { align-self: start; min-width: 0; }
@media (max-width: 850px) { .video-details-page { width: calc(100vw - 24px); max-height: calc(100vh - 24px); } .video-details-layout, .trim-editor-layout { grid-template-columns: minmax(0, 1fr); } .video-details-layout { overflow: auto; } .video-list-first { gap: 6px 12px; } .storyboard-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); max-height: none; } .video-player { max-height: 42vh; } }
@media (max-height: 760px) { .video-details-page { max-height: calc(100vh - 24px); } .video-player { max-height: 40vh; } .trim-player { max-height: 34vh; } .storyboard-grid { max-height: calc(100vh - 270px); } }
</style>
