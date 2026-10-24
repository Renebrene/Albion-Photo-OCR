<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  createDinoBatch,
  fetchAddresses,
  fetchHybridSettings,
  previewHybridSettings,
  saveHybridSettings,
  createHybridRun,
  fetchDinoBatchRuns,
  fetchDinoBatches,
  fetchHybridRuns,
  fetchJobs,
  fetchRunActivity,
  fetchRunLog,
  fetchSortStatus,
} from '../api/client'
import { useAsyncAction } from '../composables/useAsyncAction'

const tab = ref('dino')

// Порог уверенности распознавания: ниже него фото уходит в «Требуют проверки».
const lowScore = ref(null)
const lowScoreSaved = ref(null)
const minMargin = ref(0)
const minMarginSaved = ref(0)
const lowScoreBusy = ref(false)
const reviewCount = ref(0)
// Предпросмотр: сколько фото попадёт в корзину при введённом значении.
const previewCount = ref(null)
const previewBusy = ref(false)
let previewTimer = null
const loading = ref(false)
const error = ref(null)
const starting = ref(false)

// Ручной запуск сортировки запрещён, пока идёт любой процесс, меняющий
// состояние описаний: полный прогон, тик планировщика или другая
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

async function loadReviewSettings() {
  try {
    const settings = await fetchHybridSettings()
    lowScore.value = settings.low_score
    lowScoreSaved.value = settings.low_score
    minMargin.value = settings.min_margin ?? 0
    minMarginSaved.value = settings.min_margin ?? 0
  } catch (err) {
    // Настройка необязательная: без неё вкладка работает как раньше.
    lowScore.value = null
  }

  try {
    const data = await fetchAddresses()
    const review = (data.items || []).find((item) => item.review)
    reviewCount.value = review ? review.count : 0
  } catch {
    reviewCount.value = 0
  }
}

/**
 * Живой счётчик: пока оператор подбирает порог, показываем размер корзины при
 * введённом значении. Запросы сглаживаются, чтобы не бить по базе на каждый
 * символ.
 */
// Номер запроса предпросмотра: ответ на прошлое значение не должен переписать
// счётчик для нового (пользователь печатает быстрее, чем отвечает сервер).
let previewRequest = 0

function schedulePreview() {
  if (previewTimer !== null) window.clearTimeout(previewTimer)

  previewTimer = window.setTimeout(async () => {
    const value = Number(lowScore.value)
    const request = ++previewRequest

    if (!Number.isFinite(value) || value < 0 || value > 1) {
      previewCount.value = null
      return
    }

    previewBusy.value = true
    try {
      const data = await previewHybridSettings(value, Number(minMargin.value) || 0)

      if (request !== previewRequest) return

      previewCount.value = data.review_count
    } catch {
      if (request === previewRequest) previewCount.value = null
    } finally {
      if (request === previewRequest) previewBusy.value = false
    }
  }, 350)
}

async function saveReviewSettings() {
  if (lowScore.value === null || lowScoreBusy.value) return

  lowScoreBusy.value = true
  try {
    const settings = await saveHybridSettings({
      low_score: Number(lowScore.value),
      min_margin: Number(minMargin.value) || 0,
    })
    lowScoreSaved.value = settings.low_score
    minMarginSaved.value = settings.min_margin ?? 0
    previewCount.value = null
    Notify.create({
      type: 'positive',
      message: `Порог сохранён: ${settings.low_score}`,
    })
    await loadReviewSettings()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    lowScoreBusy.value = false
  }
}

// Сводка последней виртуальной сортировки.
const sortStatus = ref(null)
const sortLogOpen = ref(false)
const sortLogText = ref('')
const sortLogLoading = ref(false)
const sortLogError = ref(null)

const sortState = computed(() => {
  const current = sortStatus.value?.current
  const last = sortStatus.value?.last
  const stats = current || last?.stats || null
  const status = last?.status || null

  if (current) return { label: 'ПРОЦЕСС', color: 'primary', stats }

  if (!last) return { label: 'НЕТ ДАННЫХ', color: 'grey', stats: null }

  if (status === 'DONE') return { label: 'ОК', color: 'positive', stats }
  if (status === 'FAILED') return { label: 'ОШИБКА', color: 'negative', stats }

  return { label: status === 'STOPPED' ? 'ПРЕРВАНО' : status, color: 'orange', stats }
})

const sortSource = computed(() => {
  const last = sortStatus.value?.last
  if (!last) return ''
  if (last.kind === 'pipeline') return 'обновление базы'
  if (last.mode === 'schedule') return 'по расписанию'
  if (last.mode === 'outofqueue') return 'вне очереди'
  return 'вручную'
})

function fmtDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

function modeDate(mode) {
  return fmtDate(sortStatus.value?.modes?.[mode]?.started_at)
}

async function loadSortStatus() {
  try {
    sortStatus.value = await fetchSortStatus()
  } catch {
    sortStatus.value = null
  }
}

async function openSortLog() {
  const run = sortStatus.value?.last
  if (!run?.run_id) return

  sortLogOpen.value = true
  sortLogLoading.value = true
  sortLogText.value = ''
  sortLogError.value = null

  try {
    sortLogText.value = await fetchRunLog(run.run_id)
  } catch (err) {
    sortLogError.value = err.message
  } finally {
    sortLogLoading.value = false
  }
}

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

// Переключение вкладки перечитывает данные СВОЕЙ вкладки. Порог уверенности
// (карточка «Требуют проверки») перечитывать нельзя: незасохранённое значение
// стиралось бы при каждом переходе между вкладками.
function reloadTab() {
  if (tab.value === 'dino') loadDino()
  else if (tab.value === 'hybrid') loadHybrid()
  else loadJobs()
}

function reload() {
  reloadTab()
}

async function startNormalBatch() {
  starting.value = true

  try {
    const result = await createDinoBatch({
      run_type: 'NORMAL',
      auto_hybrid: true,
    })

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

const { busy: hybridBusy, run: hybridRun } = useAsyncAction()

async function startHybrid(batch) {
  await hybridRun(async () => {
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
  })
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
  loadReviewSettings()
  loadActivity()
  loadSortStatus()
  activityTimer = window.setInterval(() => {
    loadActivity()
    loadSortStatus()
  }, 3000)
})

onBeforeUnmount(() => {
  // Таймер предпросмотра иначе срабатывал после ухода со страницы и трогал
  // refs уже удалённого компонента.
  if (previewTimer !== null) {
    window.clearTimeout(previewTimer)
    previewTimer = null
  }

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

    <!-- Сводка сортировки: первой, таблицы — ниже. -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="text-subtitle2 q-mb-xs">
          Уверенность распознавания: корзина «Требуют проверки»
        </div>
        <div class="row items-center q-gutter-md">
          <q-input
            v-model.number="lowScore"
            type="number"
            dense
            outlined
            step="0.01"
            min="0"
            max="1"
            label="Нижний порог"
            style="max-width: 180px"
            :disable="lowScore === null"
            @update:model-value="schedulePreview"
          >
            <q-tooltip>
              Сходство выбранного кандидата (0…1). Ниже порога фото адреса не
              получает и попадает в «Требуют проверки». 0 — проверка выключена.
            </q-tooltip>
          </q-input>
          <q-input
            v-model.number="minMargin"
            type="number"
            dense
            outlined
            step="0.005"
            min="0"
            max="1"
            label="Минимальный отрыв"
            style="max-width: 200px"
            @update:model-value="schedulePreview"
          >
            <q-tooltip>
              Насколько лучший адрес должен опережать второй. Меньше значения —
              фото уходит в «Требуют проверки»: выбор был почти равным.
              0 — проверка выключена.
            </q-tooltip>
          </q-input>
          <q-btn
            color="primary"
            no-caps
            label="Сохранить"
            :loading="lowScoreBusy"
            :disable="
              lowScore === null
              || (lowScore === lowScoreSaved && minMargin === minMarginSaved)
            "
            @click="saveReviewSettings"
          />
          <div class="text-caption text-grey-8">
            Требуют проверки сейчас: <b>{{ reviewCount }}</b> фото
            <template v-if="previewCount !== null">
              <br />
              при {{ Number(lowScore).toFixed(2) }} будет:
              <b>{{ previewCount }}</b> фото
            </template>
          </div>
        </div>
        <div class="text-caption text-grey-7 q-mt-xs">
          Порог применяется при чтении: данные не пересчитываются, значение
          можно менять и смотреть, сколько фото требует ручного разбора.
          Переопределение адреса в карточке фото выводит его из корзины.
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="row items-center q-gutter-sm">
          <div class="text-subtitle1 col">Статистика сортировки</div>
          <q-badge :color="sortState.color" :label="sortState.label" />
          <q-btn
            v-if="sortStatus?.last?.has_log"
            dense
            flat
            size="sm"
            icon="receipt_long"
            label="Лог ошибок"
            @click="openSortLog"
          />
        </div>

        <div class="text-body2 q-mt-sm">
          Совпадений:
          <b>{{ sortState.stats?.matched ?? 0 }}</b>
          из
          <b>{{ sortState.stats?.total ?? 0 }}</b>
          <span v-if="sortState.stats?.failed" class="text-negative">
            · ошибок: {{ sortState.stats.failed }}
          </span>
          <span v-if="sortSource" class="text-caption text-grey-7">
            · источник: {{ sortSource }}
          </span>
        </div>

        <div class="text-caption text-grey-7 q-mt-sm">
          Последний запуск: Вручную — {{ modeDate('manual') }} ·
          По расписанию — {{ modeDate('schedule') }} ·
          Вне очереди — {{ modeDate('outofqueue') }} ·
          Обновление базы — {{ modeDate('pipeline') }}
        </div>
      </q-card-section>
    </q-card>

    <q-tabs v-model="tab" dense align="left" class="text-primary q-mb-sm" @update:model-value="reloadTab">
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
                :loading="hybridBusy" @click="startHybrid(props.row)"
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

    <q-dialog v-model="sortLogOpen">
      <q-card style="min-width: 640px; max-width: 94vw">
        <q-card-section class="text-subtitle1">Лог сортировки</q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow: auto">
          <div v-if="sortLogLoading" class="row justify-center">
            <q-spinner-dots color="primary" size="32px" />
          </div>
          <q-banner v-else-if="sortLogError" dense class="bg-red-1 text-negative">
            {{ sortLogError }}
          </q-banner>
          <pre v-else class="sort-log">{{ sortLogText || 'Лог пуст' }}</pre>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.sort-log {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
