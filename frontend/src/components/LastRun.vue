<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchLastRun, fetchRunHistory, fetchRunLog } from '../api/client'
import PipelineRunsPanel from './PipelineRunsPanel.vue'
import RunHistoryPanel from './RunHistoryPanel.vue'

const data = ref(null)
const history = ref([])
const loading = ref(false)
const error = ref(null)

const logOpen = ref(false)
const logTitle = ref('')
const logText = ref('')
const logLoading = ref(false)
const logError = ref(null)

const KIND_LABELS = {
  pipeline: 'Обновление базы',
  ingest: 'Инспектирование',
  sort: 'Сортировка',
  qwen: 'QWEN',
  scheduler: 'Планировщик',
}

const STAGE_LABELS = {
  INGEST: 'Инспектирование',
  PREVIEW: 'Превью',
  DINO: 'DINO',
  HYBRID: 'HYBRID',
  QWEN: 'QWEN',
}

const STATUS_LABELS = {
  PENDING: 'ожидает',
  RUNNING: 'выполняется',
  DONE: 'успешно',
  FAILED: 'ошибка',
  PARTIAL: 'частично',
  STOPPED: 'прервано',
  CANCELLED: 'отменено',
}

const STATUS_COLORS = {
  PENDING: 'grey',
  RUNNING: 'primary',
  DONE: 'positive',
  FAILED: 'negative',
  PARTIAL: 'orange',
  STOPPED: 'orange',
  CANCELLED: 'grey',
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status || '—'
}

function statusColor(status) {
  return STATUS_COLORS[status] || 'grey'
}

function fmt(value) {
  if (!value) return '—'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)

  const pad = (n) => String(n).padStart(2, '0')

  return (
    `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

function duration(run) {
  if (!run?.started_at || !run?.finished_at) return '—'

  const start = new Date(run.started_at).getTime()
  const end = new Date(run.finished_at).getTime()

  if (Number.isNaN(start) || Number.isNaN(end)) return '—'

  const seconds = Math.max(0, Math.round((end - start) / 1000))

  if (seconds < 60) return `${seconds} с`

  const minutes = Math.floor(seconds / 60)

  if (minutes < 60) return `${minutes} мин ${seconds % 60} с`

  return `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`
}

function stoppedStage(run) {
  if (!run || !['STOPPED', 'FAILED'].includes(run.status)) return null

  const stages = run.stages || []

  // Последний этап, который начался, но не завершился успешно.
  for (let index = stages.length - 1; index >= 0; index -= 1) {
    const stage = stages[index]

    if (stage.status && !['DONE', 'SKIPPED'].includes(stage.status)) {
      return stage
    }
  }

  return stages.length ? stages[stages.length - 1] : null
}

function stageDurations(run) {
  const parts = []

  for (const stage of run?.stages || []) {
    if (stage.seconds === null || stage.seconds === undefined) continue

    parts.push(
      `${STAGE_LABELS[stage.stage] || stage.stage}: ${Math.round(stage.seconds)} с`,
    )
  }

  return parts.join(' · ')
}

const latestByKind = computed(() => {
  const byKind = {}

  for (const run of history.value) {
    if (!byKind[run.kind]) byKind[run.kind] = run
  }

  return ['pipeline', 'ingest', 'sort', 'qwen', 'scheduler'].map((kind) => ({
    kind,
    label: KIND_LABELS[kind],
    run: byKind[kind] || null,
  }))
})

async function load() {
  loading.value = true
  error.value = null

  try {
    const [last, runs] = await Promise.all([
      fetchLastRun(),
      fetchRunHistory({ limit: 50 }),
    ])

    data.value = last
    history.value = runs.items || []
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function openLog(run) {
  logOpen.value = true
  logTitle.value = `${KIND_LABELS[run.kind] || run.kind} · ${fmt(run.started_at)}`
  logText.value = ''
  logError.value = null
  logLoading.value = true

  try {
    logText.value = await fetchRunLog(run.run_id)
  } catch (err) {
    logError.value = err.message
  } finally {
    logLoading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Последний запуск</div>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <!-- Сводка по последним запускам: первой, остальные модули ниже. -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="panel-title q-mb-sm">Последние запуски</div>

        <div
          v-for="item in latestByKind"
          :key="item.kind"
          class="run-summary q-py-xs"
        >
          <div class="row items-center q-gutter-sm">
            <div class="text-weight-medium" style="min-width: 150px">
              {{ item.label }}
            </div>

            <template v-if="item.run">
              <q-badge
                :color="statusColor(item.run.status)"
                :label="statusLabel(item.run.status)"
              />
              <span class="text-caption text-grey-8">
                {{ fmt(item.run.started_at) }}
              </span>
              <span
                v-if="item.run.status !== 'RUNNING' && item.run.status !== 'PENDING'"
                class="text-caption text-grey-7"
              >
                · {{ duration(item.run) }}
              </span>
              <q-btn
                v-if="item.run.has_log"
                dense
                flat
                size="sm"
                icon="receipt_long"
                label="Лог"
                @click="openLog(item.run)"
              />
            </template>

            <span v-else class="text-caption text-grey-6">нет запусков</span>
          </div>

          <template v-if="item.run">
            <div
              v-if="item.kind === 'pipeline' && stoppedStage(item.run)"
              class="text-caption text-orange-9 q-ml-md"
            >
              Остановлено на этапе
              «{{ STAGE_LABELS[stoppedStage(item.run).stage] || stoppedStage(item.run).stage }}»
              {{ fmt(item.run.finished_at) }}
              <template v-if="item.run.status === 'STOPPED'"> — кнопкой «Стоп»</template>
              <template v-else-if="item.run.message"> — {{ item.run.message }}</template>
            </div>

            <div
              v-if="item.kind === 'pipeline' && stageDurations(item.run)"
              class="text-caption text-grey-7 q-ml-md"
            >
              Этапы: {{ stageDurations(item.run) }}
            </div>

            <div
              v-if="item.run.message && item.kind !== 'pipeline'"
              class="text-caption text-grey-7 q-ml-md"
            >
              {{ item.run.message }}
            </div>
          </template>
        </div>
      </q-card-section>
    </q-card>

    <!-- Ниже — прежние модули истории и последних batch/run. -->
    <PipelineRunsPanel class="q-mb-md" />
    <RunHistoryPanel />

    <div v-if="data" class="row q-col-gutter-md q-mt-md">
      <q-card flat bordered class="col-12 col-md-6">
        <q-card-section>
          <div class="text-caption text-grey">DINO batch</div>
          <template v-if="data.dino_batch">
            <div class="text-h6">
              #{{ data.dino_batch.batch_id }}
              <q-badge :label="data.dino_batch.status" class="q-ml-sm" />
            </div>
            <div class="text-caption">
              {{ data.dino_batch.run_type }} ·
              готово {{ data.dino_batch.completed_count }}/{{ data.dino_batch.total_count }}
              · ошибок {{ data.dino_batch.failed_count }}
            </div>
            <div class="text-caption text-grey">{{ data.dino_batch.created_at }}</div>
          </template>
          <div v-else class="text-grey">нет</div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12 col-md-6">
        <q-card-section>
          <div class="text-caption text-grey">HYBRID run</div>
          <template v-if="data.hybrid_run">
            <div class="text-h6">
              #{{ data.hybrid_run.hybrid_run_id }}
              <q-badge :label="data.hybrid_run.status" class="q-ml-sm" />
            </div>
            <div class="text-caption">
              batch {{ data.hybrid_run.dino_batch_id }} ·
              готово {{ data.hybrid_run.completed_count }}/{{ data.hybrid_run.total_count }}
              · ошибок {{ data.hybrid_run.failed_count }}
            </div>
            <div class="text-caption text-grey">{{ data.hybrid_run.created_at }}</div>
          </template>
          <div v-else class="text-grey">нет</div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12">
        <q-card-section>
          <div class="text-caption text-grey q-mb-xs">Задания в очереди</div>
          <div class="row q-gutter-sm">
            <q-chip v-for="(count, status) in data.jobs" :key="status" dense>
              {{ status }}: {{ count }}
            </q-chip>
            <span v-if="!Object.keys(data.jobs).length" class="text-grey">
              пусто
            </span>
          </div>
        </q-card-section>
      </q-card>
    </div>

    <q-dialog v-model="logOpen">
      <q-card style="min-width: 680px; max-width: 94vw">
        <q-card-section class="text-subtitle1">{{ logTitle }}</q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow: auto">
          <div v-if="logLoading" class="row justify-center">
            <q-spinner-dots color="primary" size="32px" />
          </div>
          <q-banner v-else-if="logError" dense class="bg-red-1 text-negative">
            {{ logError }}
          </q-banner>
          <pre v-else class="run-log">{{ logText || 'Лог пуст' }}</pre>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.run-summary + .run-summary {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.run-log {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
