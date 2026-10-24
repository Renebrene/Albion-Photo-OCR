<script setup>
// Header control for the resumable pipeline run ("Обновление базы").
//
// It only *observes* the run and asks the backend to start/stop/resume it. The
// heavy work happens in the workers. Until schema/031 is applied the endpoint
// answers 404, so the whole control hides itself instead of showing a broken
// button.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Notify } from 'quasar'

import {
  fetchCurrentPipeline,
  fetchQwenSettings,
  resumePipeline,
  startPipeline,
  stopPipeline,
} from '../api/client'

const props = defineProps({
  // Whether the signed-in user may change the run (needs jobs:write).
  canRun: { type: Boolean, default: false },
})

const emit = defineEmits(['finished'])

const available = ref(false)
const run = ref(null)
const busy = ref(false)
const dialogOpen = ref(false)

let timer = null
let lastStatus = null

const ACTIVE = ['PENDING', 'RUNNING']

const isActive = computed(() => ACTIVE.includes(run.value?.status))
const isStopped = computed(() => run.value?.status === 'STOPPED')
const isDone = computed(() => run.value?.status === 'DONE')
const isIdle = computed(() => !isActive.value && !isStopped.value)

// Skip the QWEN stage and run it later for a chosen period
// (Техраздел → Распознавание → «Дозаполнить за период»).
const skipQwen = ref(false)
// QWEN может быть выключен не на этот раз, а в настройках распознавания:
// тогда и галочка, и сам прогон идут без описаний.
const qwenOffInSettings = ref(false)

function stageRow(stage) {
  return (run.value?.stages || []).find((item) => item.stage === stage) || null
}

function fmt(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

const statusText = computed(() => {
  const current = run.value

  if (!current) return ''

  if (current.status === 'DONE') return `База обновлена ${fmt(current.finished_at)}`

  if (current.status === 'FAILED') {
    return `Ошибка обновления${current.message ? `: ${current.message}` : ''}`
  }

  if (current.status === 'STOPPED') {
    return `Процесс прерван ${fmt(current.finished_at)}`
  }

  const row = stageRow(current.stage)

  switch (current.stage) {
    case 'INGEST': {
      const total = row?.total_count || (current.manifest?.files || []).length
      const done = row?.done_count ?? 0
      return total ? `Обработано медиа ${done}/${total}` : 'Обновление базы…'
    }
    case 'PREVIEW':
      return `Превью: ${row?.done_count ?? 0}/${row?.total_count ?? 0}`
    case 'DINO':
    case 'HYBRID': {
      // Число этой стадии («13686 / 20904») показывает строка прогона рядом
      // (`stores/pipeline.js`), поэтому в кнопке оно не дублируется. Если
      // параллельно идёт QWEN, здесь остаётся только счётчик описаний.
      const qwen = stageRow('QWEN')

      return qwen && (qwen.total_count || qwen.done_count)
        ? `Описаний: ${qwen.done_count ?? 0}`
        : ''
    }
    case 'QWEN':
      return row?.failed_count
        ? `Описаний: ${row?.done_count ?? 0} (ошибок: ${row?.failed_count})`
        : `Описаний: ${row?.done_count ?? 0}`
    default:
      return 'Обновление базы…'
  }
})

async function poll() {
  try {
    const data = await fetchCurrentPipeline()
    available.value = true

    const next = data?.run || null

    // Refresh the footer once a run reaches a terminal state.
    if (next && next.status === 'DONE' && lastStatus && lastStatus !== 'DONE') {
      emit('finished')
    }
    lastStatus = next?.status || null

    run.value = next
  } catch {
    // The endpoint is not deployed yet (404) or unreachable: hide the control.
    available.value = false
    run.value = null
  }
}

watch(dialogOpen, async (open) => {
  if (!open) return

  try {
    const data = await fetchQwenSettings()
    qwenOffInSettings.value = data?.in_pipeline === false
    if (qwenOffInSettings.value) skipQwen.value = true
  } catch {
    // Настройки недоступны — решает сервер, галочка остаётся свободной.
    qwenOffInSettings.value = false
  }
})

async function onClick() {
  if (busy.value) return

  if (isActive.value) {
    dialogOpen.value = true
    return
  }

  dialogOpen.value = true
}

async function startNew() {
  if (!props.canRun) {
    Notify.create({ type: 'warning', message: 'Запуск обновления недоступен этой роли' })
    return
  }

  busy.value = true
  try {
    await startPipeline({ skip_qwen: skipQwen.value })
    dialogOpen.value = false
    Notify.create({ type: 'info', message: 'Обновление базы запущено' })
    await poll()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось запустить' })
  } finally {
    busy.value = false
  }
}

async function doResume() {
  if (busy.value || !run.value) return
  busy.value = true
  try {
    await resumePipeline(run.value.run_id)
    dialogOpen.value = false
    await poll()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось продолжить' })
  } finally {
    busy.value = false
  }
}

async function doRestart() {
  if (busy.value) return
  busy.value = true
  try {
    await startPipeline({ skip_qwen: skipQwen.value })
    dialogOpen.value = false
    await poll()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось запустить' })
  } finally {
    busy.value = false
  }
}

async function doStop() {
  if (busy.value || !run.value) return
  busy.value = true
  try {
    await stopPipeline(run.value.run_id)
    Notify.create({ type: 'info', message: 'Процесс прерван' })
    dialogOpen.value = false
    await poll()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось остановить' })
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  poll()
  timer = window.setInterval(poll, 3000)
})

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer)
})
</script>

<template>
  <div v-if="available" class="pipeline-control row items-center no-wrap q-mr-sm">
    <q-btn
      flat
      dense
      no-caps
      :icon="isActive ? 'sync' : 'cloud_upload'"
      :label="'Обновление базы'"
      :disable="busy || (!canRun && !isActive && !isStopped)"
      @click="onClick"
    >
      <q-tooltip>
        Инспектирование → превью → DINO/HYBRID → описания. Запускает или управляет
        текущим прогоном.
      </q-tooltip>
    </q-btn>

    <span v-if="isActive" class="blink-dot q-mx-xs" />

    <span v-if="statusText" class="pipeline-status">{{ statusText }}</span>

    <q-dialog v-model="dialogOpen">
      <q-card style="width: min(520px, 92vw)">
        <q-card-section class="text-subtitle1">
          {{
            isActive
              ? 'Обновление базы выполняется'
              : isStopped
                ? 'Процесс остановлен'
                : 'Обновление базы'
          }}
        </q-card-section>
        <q-separator />

        <q-card-section class="q-gutter-sm">
          <div v-if="!isIdle">{{ statusText }}</div>
          <div v-if="isIdle" class="text-caption text-grey-7">
            Инспектор → превью → DINO/HYBRID → описания. Тяжёлые шаги идут в
            фоновых воркерах, окно можно закрыть.
          </div>
          <div v-if="isStopped" class="text-caption text-grey-7">
            Продолжить — с того же набора медиа. Начать заново — новый прогон,
            он учтёт появившиеся файлы, а уже обработанные не пересчитывает.
          </div>
          <div v-else-if="isActive" class="text-caption text-grey-7">
            Вы уверены, что хотите остановить? Текущий статус будет запомнен и
            продолжен после повторного запуска. Информацию можно посмотреть в
            Техническом разделе. Остановка произойдёт после текущего шага; уже
            запущенные задачи доиграют, состояние сохранится.
          </div>

          <q-toggle
            v-if="!isActive"
            v-model="skipQwen"
            label="Пропустить QWEN — запущу отдельно за период"
            dense
            :disable="qwenOffInSettings"
          />
          <div v-if="!isActive" class="text-caption text-grey-7">
            <template v-if="qwenOffInSettings">
              QWEN выключен в настройках «Распознавание»: прогон пойдёт без
              описаний и без «Уточнения». Включается там же одним
              переключателем.
            </template>
            <template v-else>
              Без QWEN прогон завершится быстрее. Затем в Техническом разделе →
              «Распознавание» → «Дозаполнить за период» можно поставить в
              очередь только выбранные даты.
            </template>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />

          <template v-if="canRun">
            <template v-if="isStopped">
              <q-btn color="primary" label="Продолжить" :loading="busy" @click="doResume" />
              <q-btn color="secondary" label="Начать заново" :loading="busy" @click="doRestart" />
            </template>
            <q-btn
              v-else-if="isActive"
              color="negative"
              label="Остановить"
              :loading="busy"
              @click="doStop"
            />
            <q-btn
              v-else
              color="primary"
              label="Запустить"
              :loading="busy"
              @click="startNew"
            />
          </template>
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.pipeline-status {
  font-size: 12px;
  white-space: nowrap;
  opacity: 0.9;
}

/* A calm pulse on a single dot instead of blinking text. */
.blink-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ffd166;
  animation: pipeline-pulse 1.2s ease-in-out infinite;
}

@keyframes pipeline-pulse {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .blink-dot { animation: none; opacity: 0.9; }
}
</style>
