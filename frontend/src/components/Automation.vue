<script setup>
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  fetchAutomation,
  fetchRunLog,
  runAutomation,
  updateAutomation,
} from '../api/client'

const settings = ref(null)
const error = ref(null)
const busy = ref(false)

const logOpen = ref(false)
const logText = ref('')
const logLoading = ref(false)
const logError = ref(null)

const STATUS_LABELS = {
  DONE: 'успешно',
  STOPPED: 'прервано',
  FAILED: 'ошибка',
  PARTIAL: 'частично',
  RUNNING: 'выполняется',
  PENDING: 'ожидает',
}

const STATUS_COLORS = {
  DONE: 'positive',
  STOPPED: 'orange',
  FAILED: 'negative',
  PARTIAL: 'orange',
  RUNNING: 'primary',
  PENDING: 'grey',
}

const lastRun = computed(() => settings.value?.last_run || null)

function statusLabel(status) {
  return STATUS_LABELS[status] || status || '—'
}

function statusColor(status) {
  return STATUS_COLORS[status] || 'grey'
}

function fmtDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

function runSummary(run) {
  const counts = run?.counts || {}
  const pieces = []

  if (Number(counts.jobs_done || counts.done || 0)) {
    pieces.push(`заданий ${counts.jobs_done ?? counts.done}`)
  }
  if (Number(counts.jobs_failed || counts.failed || 0)) {
    pieces.push(`ошибок ${counts.jobs_failed ?? counts.failed}`)
  }
  if (Number(counts.skipped || 0)) pieces.push(`пропущено ${counts.skipped}`)

  return pieces.join(' · ')
}

async function load() {
  try {
    settings.value = await fetchAutomation()
    error.value = null
  } catch (err) {
    error.value = err.message
  }
}

async function save(patch) {
  busy.value = true
  try {
    settings.value = await updateAutomation(patch)
    Notify.create({ type: 'positive', message: 'Настройки сохранены' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

async function runNow() {
  busy.value = true
  try {
    const result = await runAutomation(true)
    Notify.create({
      type: 'info',
      message: `Тик выполнен: QWEN заданий ${result.qwen_jobs ?? 0}`,
    })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

async function openLog() {
  if (!lastRun.value?.run_id) return

  logOpen.value = true
  logLoading.value = true
  logText.value = ''
  logError.value = null

  try {
    logText.value = await fetchRunLog(lastRun.value.run_id)
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
      <div class="text-subtitle1 col">Планировщик</div>
      <q-btn dense flat icon="refresh" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <template v-if="settings">
      <q-card flat bordered class="q-mb-md">
        <q-card-section>
          <q-toggle
            :model-value="settings.enabled"
            label="Планировщик включён"
            :disable="busy"
            @update:model-value="(v) => save({ enabled: v })"
          />
          <div class="text-caption text-grey q-mt-xs">
            Планировщик только ставит в очередь уже поддержанные операции.
            Новые файлы он не импортирует; watcher папки не реализуется.
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="q-mb-md">
        <q-card-section class="q-gutter-sm">
          <div class="text-subtitle2">Когда запускать</div>

          <q-btn-toggle
            :model-value="settings.mode || 'interval'"
            :options="[
              { label: 'По интервалу', value: 'interval' },
              { label: 'В определённое время', value: 'daily' },
            ]"
            dense
            unelevated
            no-caps
            toggle-color="primary"
            :disable="busy"
            @update:model-value="(v) => save({ mode: v })"
          />

          <q-input
            v-if="(settings.mode || 'interval') === 'interval'"
            :model-value="settings.interval_minutes"
            type="number"
            dense
            outlined
            label="Интервал, минут"
            style="max-width: 220px"
            :disable="busy"
            @update:model-value="(v) => save({ interval_minutes: Number(v) })"
          />

          <q-input
            v-else
            :model-value="settings.daily_time || '09:00'"
            type="time"
            dense
            outlined
            label="Время запуска"
            style="max-width: 220px"
            :disable="busy"
            @update:model-value="(v) => save({ daily_time: v })"
          />

          <q-toggle
            :model-value="settings.auto_qwen"
            label="Запускать QWEN автоматически"
            :disable="busy"
            @update:model-value="(v) => save({ auto_qwen: v })"
          />
          <div class="text-caption text-grey">
            По умолчанию выключено. Если включено, QWEN запускается сразу после
            Инспектирование (после получения ID) и идёт параллельно DINO/HYBRID.
          </div>

          <div class="text-caption text-grey">
            Последний тик: {{ fmtDate(settings.last_tick) }}
          </div>
        </q-card-section>
      </q-card>

      <q-card v-if="lastRun" flat bordered class="q-mb-md">
        <q-card-section>
          <div class="row items-center q-gutter-sm">
            <div class="text-subtitle2 col">Последний запуск</div>
            <q-badge
              :color="statusColor(lastRun.status)"
              :label="statusLabel(lastRun.status)"
            />
            <q-btn
              v-if="lastRun.has_log"
              dense
              flat
              size="sm"
              icon="receipt_long"
              label="Лог"
              @click="openLog"
            />
          </div>
          <div class="text-caption text-grey-8 q-mt-xs">
            {{ fmtDate(lastRun.started_at) }} — {{ fmtDate(lastRun.finished_at) }}
            <template v-if="runSummary(lastRun)"> · {{ runSummary(lastRun) }}</template>
          </div>
          <div v-if="lastRun.message" class="text-caption text-grey-8 q-mt-xs">
            {{ lastRun.message }}
          </div>
        </q-card-section>
      </q-card>

      <div class="row q-gutter-sm">
        <q-btn
          color="primary"
          icon="play_arrow"
          label="Запустить тик сейчас"
          :loading="busy"
          @click="runNow"
        />
      </div>
    </template>

    <q-dialog v-model="logOpen">
      <q-card style="min-width: 640px; max-width: 94vw">
        <q-card-section class="text-subtitle1">Лог планировщика</q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow: auto">
          <div v-if="logLoading" class="row justify-center">
            <q-spinner-dots color="primary" size="32px" />
          </div>
          <q-banner v-else-if="logError" dense class="bg-red-1 text-negative">
            {{ logError }}
          </q-banner>
          <pre v-else class="automation-log">{{ logText || 'Лог пуст' }}</pre>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.automation-log {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
