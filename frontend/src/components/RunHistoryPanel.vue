<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchRunHistory, fetchRunLog } from '../api/client'

const items = ref([])
const loading = ref(false)
const error = ref(null)
const selectedRun = ref(null)
const logText = ref('')
const logError = ref(null)
const logLoading = ref(false)
const logDialog = ref(false)

const statusLabels = {
  PENDING: 'ожидает',
  RUNNING: 'выполняется',
  DONE: 'завершён',
  FAILED: 'ошибка',
  PARTIAL: 'частично',
  STOPPED: 'остановлен',
  CANCELLED: 'отменён',
}

const modeLabels = {
  manual: 'вручную',
  schedule: 'по расписанию',
  outofqueue: 'вне очереди',
}

const kindLabels = {
  pipeline: 'Обновление базы',
  ingest: 'Загрузка',
  sort: 'Сортировка',
  qwen: 'QWEN',
  scheduler: 'Планировщик',
}

const logTitle = computed(() => selectedRun.value
  ? `Лог запуска #${selectedRun.value.run_id} · ${selectedRun.value.title || kindLabels[selectedRun.value.kind] || selectedRun.value.kind}`
  : 'Лог запуска')

function formatDate(value) {
  if (!value) return '—'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString()
}

function formatCounts(counts = {}) {
  const pieces = []
  const total = Number(counts.total || 0)
  const done = Number(counts.done || 0)
  const failed = Number(counts.failed || 0)
  const jobsTotal = Number(counts.jobs_total || 0)
  const jobsDone = Number(counts.jobs_done || 0)
  const stages = counts.by_stage || {}

  if (total || done || failed) pieces.push(`готово ${done}/${total}`)
  for (const stageName of ['DINO', 'HYBRID']) {
    const stage = stages[stageName]
    if (!stage?.required) continue
    pieces.push(`${stageName} ${Number(stage.done || 0)}/${Number(stage.total || 0)}`)
  }
  if (failed) pieces.push(`ошибок ${failed}`)
  if (jobsTotal) pieces.push(`заданий ${jobsDone}/${jobsTotal}`)
  if (Number(counts.skipped || 0)) pieces.push(`пропущено ${counts.skipped}`)
  return pieces.join(' · ') || 'без счётчиков'
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const result = await fetchRunHistory({ limit: 30 })
    items.value = Array.isArray(result.items) ? result.items : []
  } catch (err) {
    error.value = err?.message || 'Не удалось загрузить историю запусков'
  } finally {
    loading.value = false
  }
}

async function openLog(run) {
  selectedRun.value = run
  logText.value = ''
  logError.value = null
  logDialog.value = true
  logLoading.value = true
  try {
    logText.value = await fetchRunLog(run.run_id)
  } catch (err) {
    if (err?.message === 'API error 404') {
      logError.value = 'Лог для этого запуска отсутствует или уже удалён.'
    } else if (err?.message === 'API error 403') {
      logError.value = 'Недостаточно прав для просмотра логов.'
    } else {
      logError.value = err?.message || 'Не удалось загрузить лог'
    }
  } finally {
    logLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card flat bordered class="q-mb-md">
    <q-card-section class="row items-center q-pb-sm">
      <div class="text-subtitle1 col">История запусков</div>
      <q-btn dense flat icon="refresh" aria-label="Обновить историю" :loading="loading" @click="load" />
    </q-card-section>
    <q-card-section class="q-pt-none">
      <q-banner v-if="error" class="bg-red-1 text-negative q-mb-sm">{{ error }}</q-banner>
      <div v-else-if="loading && !items.length" class="text-grey">Загрузка истории…</div>
      <div v-else-if="!items.length" class="text-grey">Пока нет записей в общей истории.</div>
      <q-list v-else separator>
        <q-item v-for="run in items" :key="run.run_id" class="q-px-none" :data-run-id="run.run_id">
          <q-item-section>
            <q-item-label>
              <span class="text-weight-medium">{{ run.title || kindLabels[run.kind] || run.kind }}</span>
              <span class="text-grey q-ml-xs">#{{ run.run_id }}</span>
              <q-badge class="q-ml-sm" :label="statusLabels[run.status] || run.status" />
            </q-item-label>
            <q-item-label caption>
              {{ kindLabels[run.kind] || run.kind }} · {{ modeLabels[run.mode] || run.mode }}
              · {{ formatDate(run.started_at || run.created_at) }}
            </q-item-label>
            <q-item-label caption>
              {{ formatCounts(run.counts) }}
              <span v-if="run.error_count"> · ошибок в журнале {{ run.error_count }}</span>
            </q-item-label>
            <q-item-label v-if="run.message" caption class="text-grey-8">{{ run.message }}</q-item-label>
            <q-item-label v-if="run.stages?.length" caption>
              <span v-for="(stage, index) in run.stages" :key="`${run.run_id}-${stage.stage}`">
                <span v-if="index"> · </span>{{ stage.stage }}: {{ stage.status }}
                <span v-if="stage.seconds !== null && stage.seconds !== undefined"> ({{ stage.seconds }} с)</span>
              </span>
            </q-item-label>
          </q-item-section>
          <q-item-section side v-if="run.has_log">
            <q-btn dense flat icon="article" label="Открыть лог" :aria-label="`Открыть лог ${run.run_id}`" @click="openLog(run)" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card-section>
  </q-card>

  <q-dialog v-model="logDialog" maximized>
    <q-card class="column">
      <q-card-section class="row items-center">
        <div class="text-subtitle1 col ellipsis">{{ logTitle }}</div>
        <q-btn flat round dense icon="close" aria-label="Закрыть лог" v-close-popup />
      </q-card-section>
      <q-separator />
      <q-card-section class="col scroll">
        <div v-if="logLoading" class="text-grey">Загрузка лога…</div>
        <q-banner v-else-if="logError" class="bg-orange-1 text-dark">{{ logError }}</q-banner>
        <pre v-else class="run-log">{{ logText }}</pre>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<style scoped>
.run-log {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 0.85rem/1.45 monospace;
  margin: 0;
}
</style>
