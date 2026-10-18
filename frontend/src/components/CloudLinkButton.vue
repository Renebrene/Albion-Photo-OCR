<script setup>
// «Сохранить → Облако»: queue an Albion upload and show the expiring link.
import { computed, onBeforeUnmount, ref } from 'vue'
import { Notify } from 'quasar'

import { createMediaLinks, fetchMediaLinks } from '../api/client'

const props = defineProps({
  photoIds: { type: Array, default: () => [] },
  videoIds: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
})

const busy = ref(false)
const dialog = ref(false)
const items = ref([])
const error = ref('')
let timer = null
let attempts = 0

const total = computed(() => props.photoIds.length + props.videoIds.length)
const hasPending = computed(() => items.value.some((item) => item.status === 'PENDING'))

function stopPolling() {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
}

function mergeLinks(rows) {
  const byId = new Map(rows.map((row) => [row.link_id, row]))
  items.value = items.value.map((item) => byId.get(item.link_id) || item)
}

async function poll() {
  attempts += 1
  try {
    const data = await fetchMediaLinks({ limit: 200, includeUnready: true })
    mergeLinks(data.items || [])
    if (!hasPending.value || attempts >= 150) stopPolling()
  } catch (err) {
    error.value = err.message || 'Не удалось проверить статус загрузки'
    stopPolling()
  }
}

async function start() {
  if (busy.value || total.value === 0) return

  busy.value = true
  error.value = ''
  items.value = []
  stopPolling()
  attempts = 0

  try {
    const data = await createMediaLinks({
      photoIds: props.photoIds,
      videoIds: props.videoIds,
    })
    items.value = data.items || []
    dialog.value = true

    if (hasPending.value) {
      timer = setInterval(poll, 2000)
      await poll()
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось отправить в облако' })
  } finally {
    busy.value = false
  }
}

async function copy(url) {
  try {
    await navigator.clipboard.writeText(url)
    Notify.create({ type: 'positive', message: 'Ссылка скопирована' })
  } catch {
    Notify.create({ type: 'warning', message: 'Скопируйте ссылку вручную' })
  }
}

function fmtDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

onBeforeUnmount(stopPolling)
</script>

<template>
  <q-btn
    dense
    flat
    color="secondary"
    icon="cloud_upload"
    label="Облако"
    :loading="busy"
    :disable="disabled || !total"
    @click="start"
  >
    <q-tooltip>Загрузить выбранное в Albion и получить ссылку на 90 дней</q-tooltip>
  </q-btn>

  <q-dialog v-model="dialog">
    <q-card style="width: min(720px, 94vw)">
      <q-card-section class="panel-head row items-center">
        <div class="panel-title col">Ссылки Albion</div>
        <q-btn flat round dense icon="close" v-close-popup />
      </q-card-section>
      <q-separator />
      <q-card-section class="q-gutter-sm">
        <q-banner v-if="error" dense class="bg-red-1 text-negative">{{ error }}</q-banner>
        <div class="text-caption text-grey-8">
          Ссылка действует 90 дней. Просроченные и удалённые ссылки исчезают из
          списка «Мои ссылки».
        </div>

        <div v-for="item in items" :key="item.link_id" class="cloud-link-row">
          <div class="row items-center q-gutter-sm">
            <q-badge :color="item.status === 'READY' ? 'positive' : item.status === 'FAILED' ? 'negative' : 'grey'">
              {{ item.status }}
            </q-badge>
            <span class="text-caption text-grey-8">{{ item.media_kind }} · {{ item.media_id }}</span>
            <q-space />
            <span v-if="item.expires_at" class="text-caption text-grey-7">
              до {{ fmtDate(item.expires_at) }}
            </span>
          </div>

          <div v-if="item.status === 'READY' && item.url" class="row items-center q-gutter-sm q-mt-xs">
            <q-input :model-value="item.url" dense outlined readonly class="col" />
            <q-btn dense flat icon="content_copy" label="Копировать" @click="copy(item.url)" />
          </div>
          <div v-else-if="item.status === 'FAILED'" class="text-negative text-caption q-mt-xs">
            {{ item.error_message || 'Загрузка не удалась' }}
          </div>
          <div v-else class="row items-center q-gutter-sm text-caption text-grey-8 q-mt-xs">
            <q-spinner-dots size="18px" /> загрузка…
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<style scoped>
.cloud-link-row {
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  padding: 8px 10px;
}
</style>
