<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  createDinoBatch,
  createHybridRun,
  fetchDinoBatchRuns,
  fetchDinoBatches,
  fetchHybridRuns,
  fetchJobs,
  fetchRunActivity,
} from '../api/client'

const tab = ref('dino')
const loading = ref(false)
const error = ref(null)
const starting = ref(false)

// Ручной запуск сортировки запрещён, пока идёт любой процесс, меняющий
// состояние распознавания: полный прогон, тик планировщика или другая
// DINO/HYBRID-сортировка.
const activity = ref(null)
const operationActive = computed(() => Boolean(activity.value))
const operationText = computed(() => {
  const current = activity.value
  if (!current) return ''
  if (current.kind === 'pipeline') {
    return current.stage
      ? `«Обновление базы», стадия ${current.stage}`
      : '«Обновление базы»'
  }
  if (current.kind === 'scheduler') return 'тик планировщика'
  if (current.kind === 'sort') return 'сортировка DINO/HYBRID'
  return 'другая операция'
})
let activityTimer = null

const dinoBatches = ref([])
const hybridRuns = ref([])
const jobs = ref([])

const runsDialog = ref(false)
const runsLoading = ref(false)
const currentBatch = ref(null)
const runs = ref([])

const dinoColumns = [
  { name: 'batch_id', label: 'Batch', field: 'batch_id', align: 'left', sortable: true },
  { name: 'run_type', label: 'Тип', field: 'run_type', align: 'left' },
  { name: 'status', label: 'Статус', field: 'status', align: 'left' },
  { name: 'counts', label: 'Готово / Всего', field: 'completed_count', align: 'left' },
  { name: 'failed_count', label: 'Ошибки', field: 'failed_count', align: 'left' },
  { name: 'actions', label: 'Действия', field: 'actions', align: 'left' },
]

const hybridColumns = [
  { name: 'hybrid_run_id', label: 'Run', field: 'hybrid_run_id', align: 'left', sortable: true },
  { name: 'dino_batch_id', label: 'DINO batch', field: 'dino_batch_id', align: 'left' },
  { name: 'status', label: 'Статус', field: 'status', align: 'left' },
  { name: 'counts', label: 'Готово / Всего', field: 'completed_count', align: 'left' },
  { name: 'failed_count', label: 'Ошибки', field: 'failed_count', align: 'left' },
  { name: 'finished_at', label: 'Завершён', field: 'finished_at', align: 'left' },
]

const jobColumns = [
  { name: 'id', label: 'Job', field: 'id', align: 'left', sortable: true },
  { name: 'job_type', label: 'Тип', field: 'job_type', align: 'left' },
  { name: 'status', label: 'Статус', field: 'status', align: 'left' },
  { name: 'attempts', label: 'Попытки', field: 'attempts', align: 'left' },
  { name: 'error_message', label: 'Ошибка', field: 'error_message', align: 'left' },
]

const runColumns = [
  { name: 'run_id', label: 'Run', field: 'run_id', align: 'left' },
  { name: 'photo_id', label: 'photo_id', field: 'photo_id', align: 'left' },
  { name: 'status', label: 'Статус', field: 'status', align: 'left' },
  { name: 'dino_best_id', label: 'Best', field: 'dino_best_id', align: 'left' },
  { name: 'dino_score', label: 'Score', field: 'dino_score', align: 'left' },
  { name: 'dino_status', label: 'DINO', field: 'dino_status', align: 'left' },
]

function statusColor(status) {
  switch (status) {
    case 'DONE':
      return 'positive'
    case 'FAILED':
      return 'negative'
    case 'RUNNING':
      return 'primary'
    default:
      return 'grey'
  }
}

async function loadDino() {
  loading.value = true
  error.value = null

  try {
    dinoBatches.value = (await fetchDinoBatches()).items
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadHybrid() {
  loading.value = true
  error.value = null

  try {
    hybridRuns.value = (await fetchHybridRuns()).items
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadJobs() {
  loading.value = true
  error.value = null

  try {
    jobs.value = (await fetchJobs()).items
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function reload() {
  if (tab.value === 'dino') loadDino()
  else if (tab.value === 'hybrid') loadHybrid()
  else loadJobs()
}

async function startNormalBatch() {
  starting.value = true

  try {
    const result = await createDinoBatch({ run_type: 'NORMAL' })

    if (result.job_id) {
      Notify.create({ type: 'positive', message: `Задание ${result.job_id} создано (batch ${result.batch_id})` })
    } else {
      Notify.create({ type: 'info', message: 'Нет фотографий, требующих DINO' })
    }

    await loadDino()
    await loadActivity()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    starting.value = false
  }
}

async function startHybrid(batch) {
  try {
    const result = await createHybridRun(batch.batch_id)

    if (result.job_id) {
      Notify.create({ type: 'positive', message: `HYBRID задание ${result.job_id} создано` })
    } else {
      Notify.create({ type: 'info', message: 'Нет данных для HYBRID' })
    }

    await loadDino()
    await loadActivity()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function openBatch(batch) {
  currentBatch.value = batch
  runs.value = []
  runsDialog.value = true
  runsLoading.value = true

  try {
    runs.value = (await fetchDinoBatchRuns(batch.batch_id)).items
  } catch (err) {
    error.value = err.message
  } finally {
    runsLoading.value = false
  }
}

async function loadActivity() {
  try {
    const data = await fetchRunActivity()
    activity.value = data.active || null
  } catch {
    // Endpoint unavailable: do not block manual work on a status read error.
    activity.value = null
  }
}

onMounted(() => {
  loadDino()
  loadActivity()
  activityTimer = window.setInterval(loadActivity, 3000)
})

onBeforeUnmount(() => {
  if (activityTimer !== null) window.clearInterval(activityTimer)
})
</script>

<template>
  <div>
    <div class="row items-center q-gutter-md q-mb-md">
      <div class="text-h6">Сортировка</div>
      <q-btn
        color="primary"
        icon="play_arrow"
        label="Запустить виртуальную сортировку"
        :loading="starting"
        :disable="starting || operationActive"
        @click="startNormalBatch"
      >
        <q-tooltip>
          Запускает вне очереди процесс виртуальной сортировки / пересчёт
          имеющейся сортировки файлов на основании алгоритмов Dino/Hybrid
          сопоставления адресов слепкам.
          <template v-if="operationActive">
            <br />Недоступно, пока идёт {{ operationText }}.
          </template>
        </q-tooltip>
      </q-btn>
      <q-btn icon="refresh" flat dense @click="reload" />
      <q-space />
    </div>

    <div v-if="operationActive" class="text-caption text-orange-8 q-mb-sm">
      Идёт {{ operationText }}: ручной запуск сортировки временно недоступен.
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">
        Ошибка загрузки: {{ error }}
      </q-banner>
    </div>

    <q-tabs v-model="tab" dense align="left" class="text-primary q-mb-sm" @update:model-value="reload">
      <q-tab name="dino" label="DINO batches" />
      <q-tab name="hybrid" label="HYBRID runs" />
      <q-tab name="jobs" label="Задания" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated>
      <q-tab-panel name="dino" class="q-pa-none">
        <q-table
          :rows="dinoBatches"
          :columns="dinoColumns"
          row-key="batch_id"
          :loading="loading"
          flat
          bordered
          no-data-label="Нет batch-ей"
          @row-click="(evt, row) => openBatch(row)"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.row.status)" :label="props.row.status" />
            </q-td>
          </template>
          <template #body-cell-counts="props">
            <q-td :props="props">
              {{ props.row.completed_count }} / {{ props.row.total_count }}
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" @click.stop>
              <q-btn
                v-if="props.row.status === 'DONE'"
                size="sm"
                flat
                dense
                color="primary"
                label="HYBRID"
                @click="startHybrid(props.row)"
              />
            </q-td>
          </template>
        </q-table>
      </q-tab-panel>

      <q-tab-panel name="hybrid" class="q-pa-none">
        <q-table
          :rows="hybridRuns"
          :columns="hybridColumns"
          row-key="hybrid_run_id"
          :loading="loading"
          flat
          bordered
          no-data-label="Нет HYBRID-запусков"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.row.status)" :label="props.row.status" />
            </q-td>
          </template>
          <template #body-cell-counts="props">
            <q-td :props="props">
              {{ props.row.completed_count }} / {{ props.row.total_count }}
            </q-td>
          </template>
        </q-table>
      </q-tab-panel>

      <q-tab-panel name="jobs" class="q-pa-none">
        <q-table
          :rows="jobs"
          :columns="jobColumns"
          row-key="id"
          :loading="loading"
          flat
          bordered
          no-data-label="Нет заданий"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.row.status)" :label="props.row.status" />
            </q-td>
          </template>
        </q-table>
      </q-tab-panel>
    </q-tab-panels>

    <q-dialog v-model="runsDialog">
      <q-card style="min-width: 720px; max-width: 95vw">
        <q-card-section class="row items-center q-gutter-sm">
          <div class="text-subtitle1">
            Batch {{ currentBatch?.batch_id }} — runs
          </div>
          <q-space />
          <q-badge
            v-if="currentBatch"
            :color="statusColor(currentBatch.status)"
            :label="currentBatch.status"
          />
        </q-card-section>

        <q-separator />

        <q-card-section>
          <q-table
            :rows="runs"
            :columns="runColumns"
            row-key="run_id"
            :loading="runsLoading"
            dense
            flat
            no-data-label="Нет runs"
          >
            <template #body-cell-status="props">
              <q-td :props="props">
                <q-badge :color="statusColor(props.row.status)" :label="props.row.status" />
              </q-td>
            </template>
            <template #body-cell-dino_score="props">
              <q-td :props="props">
                {{ props.row.dino_score != null ? props.row.dino_score.toFixed(4) : '—' }}
              </q-td>
            </template>
          </q-table>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>
