<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Notify } from 'quasar'

import { usePoller } from '../composables/usePoller'

import {
  clearQwenJobs,
  enqueueQwen,
  fetchQwenHistoryLog,
  fetchQwenModels,
  fetchQwenSettings,
  fetchQwenStats,
  rescanQwenPeriod,
  scanQwenPeriod,
  stopQwenJobs,
  unloadQwen,
  updateQwenSettings,
} from '../api/client'
import { useSessionStore } from '../stores/session'
import { useAsyncAction } from '../composables/useAsyncAction'
import { confirmDialog } from '../composables/confirmDialog'

const session = useSessionStore()
const canConfigure = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

// Кнопки с асинхронным действием: защита от двойного клика и индикатор.
// Разбираем на верхнеуровневые ref'ы: вложенные в объект не разворачиваются
// в шаблоне, и `:loading` получил бы объект вместо boolean.
const { busy: runAllBusy, run: runAllRun } = useAsyncAction()
const { busy: retryBusy, run: retryRun } = useAsyncAction()
const { busy: stopQueueBusy, run: stopQueueRun } = useAsyncAction()
const { busy: clearQueueBusy, run: clearQueueRun } = useAsyncAction()
const { busy: unloadBusy, run: unloadRun } = useAsyncAction()
const { busy: clearKeyBusy, run: clearKeyRun } = useAsyncAction()

// provider settings
const provider = ref('ollama')
const baseUrl = ref('')
const apiKey = ref('')
const apiKeyHint = ref(null)
const apiKeySet = ref(false)
const keepAlive = ref('10m')
const unloadOnIdle = ref(true)
const billboardCropEnabled = ref(false)
const billboardCropAvailable = ref(false)
const billboardCropSaving = ref(false)
// Участие QWEN в «Обновлении базы» (главный переключатель описаний).
const qwenInPipeline = ref(true)
const qwenInPipelineSaving = ref(false)
// Промпты: действующий (его можно править) и встроенный (для сброса).
const promptText = ref('')
const cropPromptText = ref('')
const defaultPrompt = ref('')
const defaultCropPrompt = ref('')
const promptsSaving = ref(false)

const model = ref(null)
const available = ref([])
const current = ref(null)
const modelsUnavailable = ref(false)
// Что запомнено для каждого провайдера: { ollama: '…', openai: '…' }.
const savedModels = ref({})
// Пока первичная загрузка не закончилась, наблюдатель за провайдером молчит:
// иначе сохранение сработало бы на присвоении значения из настроек.
const settingsLoaded = ref(false)

const stats = ref(null)
const historyLog = ref({ items: [], text: '' })
const historyLoading = ref(false)
const historyError = ref('')
const rescanOpen = ref(false)
const rescanMode = ref('destructive')
const rescanBusy = ref(false)
const rescanDateMode = ref('upload')
const rescanFrom = ref('')
const rescanTo = ref('')
const rescanError = ref('')
const isDestructiveRescan = computed(() => rescanMode.value === 'destructive')


function sizeLabel(size) {
  if (!size) return ''
  const gb = size / 1024 ** 3
  return `${gb.toFixed(1)} GB`
}

async function loadSettings() {
  try {
    const data = await fetchQwenSettings()
    provider.value = data.provider || 'ollama'
    baseUrl.value = data.base_url || ''
    apiKeyHint.value = data.api_key_hint
    apiKeySet.value = !!data.api_key_set
    keepAlive.value = data.keep_alive || ''
    unloadOnIdle.value = data.unload_on_idle !== false
    billboardCropAvailable.value = data.billboard_crop_available === true
    billboardCropEnabled.value = data.billboard_crop_enabled === true
    qwenInPipeline.value = data.in_pipeline !== false
    promptText.value = data.prompt || ''
    cropPromptText.value = data.crop_prompt || ''
    defaultPrompt.value = data.default_prompt || ''
    defaultCropPrompt.value = data.default_crop_prompt || ''
    model.value = data.model || null
    current.value = data.model || null
    savedModels.value = data.models || {}
    apiKey.value = ''
    settingsLoaded.value = true
  } catch (err) {
    error.value = err.message
  }
}

async function loadModels() {
  loading.value = true

  try {
    const data = await fetchQwenModels()
    available.value = (data.available || []).map((m) => ({
      label: `${m.name} ${m.size ? `(${sizeLabel(m.size)})` : ''}`.trim(),
      value: m.name,
    }))
    current.value = data.current
    modelsUnavailable.value = false
  } catch {
    // Облачный провайдер может не отдавать список моделей — это не ошибка
    // настроек: имя модели можно ввести руками, сохранённое значение остаётся.
    modelsUnavailable.value = true
    available.value = current.value ? [{ label: current.value, value: current.value }] : []
  } finally {
    // Показываем именно сохранённую модель этого провайдера.
    model.value = current.value || model.value
    loading.value = false
  }
}

// Модель запоминается сразу при выборе: у каждого провайдера своя модель.
async function setBillboardCropEnabled(value) {
  if (!canConfigure.value || billboardCropSaving.value) return

  const previous = billboardCropEnabled.value
  billboardCropEnabled.value = Boolean(value)
  billboardCropSaving.value = true
  try {
    const data = await updateQwenSettings({ billboard_crop_enabled: billboardCropEnabled.value })
    billboardCropEnabled.value = data?.billboard_crop_enabled === true
    Notify.create({
      type: 'positive',
      message: billboardCropEnabled.value
        ? 'Описание щита и crop для QWEN включены'
        : 'Crop щита выключен; QWEN анализирует полный кадр',
    })
  } catch (err) {
    billboardCropEnabled.value = previous
    Notify.create({ type: 'negative', message: err.message || 'Не удалось сохранить настройку crop' })
  } finally {
    billboardCropSaving.value = false
  }
}

async function setQwenInPipeline(value) {
  if (!canConfigure.value || qwenInPipelineSaving.value) return

  const previous = qwenInPipeline.value
  qwenInPipeline.value = Boolean(value)
  qwenInPipelineSaving.value = true
  try {
    const data = await updateQwenSettings({ in_pipeline: qwenInPipeline.value })
    qwenInPipeline.value = data?.in_pipeline !== false
    Notify.create({
      type: 'positive',
      message: qwenInPipeline.value
        ? 'QWEN участвует в «Обновлении базы»'
        : 'QWEN выключен из прогона; «Уточнение» тоже остановлено',
    })
  } catch (err) {
    qwenInPipeline.value = previous
    Notify.create({ type: 'negative', message: err.message || 'Не удалось сохранить настройку QWEN' })
  } finally {
    qwenInPipelineSaving.value = false
  }
}

async function saveModel(value) {
  if (!value) return

  try {
    const data = await updateQwenSettings({ model: value })
    current.value = data?.model || value
    Notify.create({ type: 'positive', message: `Модель сохранена: ${current.value}` })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

// Смена провайдера тоже сохраняется сразу и подтягивает модель этого провайдера.
watch(provider, async (value, previous) => {
  if (!settingsLoaded.value || value === previous) return

  try {
    await updateQwenSettings({ provider: value })
    // Настройки целиком не перечитываем: это стёрло бы несохранённые правки
    // (адрес, промпт, keep-alive). Обновляем только список моделей — он
    // зависит от провайдера.
    await loadModels()
    Notify.create({
      type: 'info',
      message: value === 'openai' ? 'Провайдер: облако' : 'Провайдер: локально (Ollama)',
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
})

async function loadStats() {
  try {
    stats.value = await fetchQwenStats()
  } catch {
    stats.value = null
  }

  // Описание идёт в воркере: пока очередь не пуста, карточка должна
  // обновляться сама, иначе счётчики «застывают» до ручного перезахода.
  if (qwenQueue.value) startStatsPolling()
  else stopStatsPolling()
}

async function loadHistoryLog() {
  historyLoading.value = true
  historyError.value = ''
  try {
    historyLog.value = await fetchQwenHistoryLog(200)
  } catch (err) {
    historyError.value = err.message || 'Не удалось загрузить историю QWEN'
  } finally {
    historyLoading.value = false
  }
}

function canRescan() {
  // Мешает только работающая модель; ждущие задания — не повод (29.10.2026).
  return !qwenRunning.value
    && Boolean(rescanFrom.value)
    && Boolean(rescanTo.value)
    && rescanTo.value >= rescanFrom.value
}

function openRescan(mode = 'destructive') {
  rescanMode.value = mode
  rescanFrom.value = ''
  rescanTo.value = ''
  rescanError.value = ''
  rescanOpen.value = true
}

function openScan() {
  openRescan('scan')
}

async function runRescan() {
  if (!canRescan() || rescanBusy.value) return
  rescanBusy.value = true
  rescanError.value = ''
  try {
    const payload = {
      date_from: rescanFrom.value,
      date_to: rescanTo.value,
      date_mode: rescanDateMode.value,
    }
    const result = isDestructiveRescan.value
      ? await rescanQwenPeriod(payload)
      : await scanQwenPeriod(payload)

    rescanOpen.value = false
    Notify.create({
      type: 'positive',
      message: isDestructiveRescan.value
        ? `В историю сохранено: ${result.archived}; новых заданий: ${result.jobs}`
        : result.photos
          ? `Фото без описания: ${result.photos}; поставлено заданий: ${result.jobs}`
          : 'За выбранный период нет фото без описания',
    })
    await loadStats()
    await loadHistoryLog()
  } catch (err) {
    rescanError.value = err.message || 'Запуск не выполнен'
  } finally {
    rescanBusy.value = false
  }
}

// Показ триггера запуска: он записан в payload задания.
const SOURCE_LABELS = {
  manual: 'ручной',
  automation: 'плановый',
  pipeline: 'внеочередной',
}

function sourceLabel(source) {
  return SOURCE_LABELS[source] || source
}

function fmtDate(value) {
  if (!value) return '—'
  return String(value).replace('T', ' ').slice(0, 16)
}

// Очередь описаний считается по ЗАДАНИЯМ (`queue`), а не по статусам строк
// photo_qwen: остановленный воркер оставляет в них RUNNING, хотя заданий уже
// нет — окно показывало «N в работе» и не давало поставить период
// (29.10.2026). Блокирует только реально работающее задание.
const qwenPending = computed(
  () => (stats.value?.queue?.PENDING || 0) + (stats.value?.queue?.PAUSED || 0),
)
const qwenRunning = computed(() => stats.value?.queue?.RUNNING || 0)
const qwenQueue = computed(() => qwenPending.value + qwenRunning.value)

// Правый модуль «Распознавания»: сводка присвоения описаний.
const assignmentStats = computed(() => {
  const s = stats.value

  if (!s) return []

  const photos = Number(s.photos || 0)
  const processed = Number(s.processed || 0)

  return [
    { label: 'ВСЕГО ФАЙЛОВ', value: photos },
    { label: 'ОБРАБОТАНО', value: processed },
    { label: 'УСПЕШНО', value: Number(s.counts?.DONE || 0) },
    { label: 'ПУСТО ИЛИ С ОШИБКОЙ', value: Math.max(0, photos - processed) },
  ]
})

// Даты последних запусков по источникам: ручной / плановый / внеочередной.
const launchDates = computed(() => {
  const bySource = {}

  for (const run of stats.value?.runs || []) {
    bySource[run.source] = run.last_finished_at
  }

  return [
    { label: 'Вручную', value: bySource.manual },
    { label: 'По расписанию', value: bySource.automation },
    { label: 'Вне очереди', value: bySource.pipeline },
  ]
})

// ref, а не обычная переменная: окно показывает «обновляется автоматически».
const statsPolling = ref(false)

// Опрос очереди описаний: скрытая вкладка молчит, тики не накладываются,
// уход со страницы останавливает опрос (usePoller). Первый тик — через
// интервал, как было: вызывающий код сам обновляет счётчики сразу после
// постановки задач.
const statsPoller = usePoller(
  async () => {
    await loadStats()
    if (!qwenQueue.value) stopStatsPolling()
  },
  { intervalMs: 5000 },
)

function stopStatsPolling() {
  statsPolling.value = false
  statsPoller.stop()
}

function startStatsPolling() {
  if (statsPolling.value) return

  statsPolling.value = true
  statsPoller.start()
}

async function retryFailed() {
  await retryRun(async () => {
    try {
      const result = await enqueueQwen(null, true)
      Notify.create({
        type: 'positive',
        message: `В очередь: ${result.jobs} фото`,
      })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}
async function runAll() {
  await runAllRun(async () => {
    try {
      const result = await enqueueQwen(null, false)
      Notify.create({ type: 'positive', message: `QWEN заданий: ${result.jobs}` })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}
async function stopQueue() {
  await stopQueueRun(async () => {
    try {
      const result = await stopQwenJobs()
      Notify.create({
        type: 'info',
        message: result.cancelled
          ? `Остановлено заданий: ${result.cancelled}`
          : 'Активных заданий нет',
      })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}
async function clearQueue() {
  const confirmed = await confirmDialog({
    title: 'Очистить список заданий?',
    message: 'Записи о выполненных заданиях описаний будут удалены. Очередь и результаты описаний не трогаются.',
    okLabel: 'Очистить',
  })

  if (!confirmed) return

  await clearQueueRun(async () => {
    try {
      const result = await clearQwenJobs()
      Notify.create({
        type: 'positive',
        message: result.deleted
          ? `Убрано записей: ${result.deleted}`
          : 'Список уже пуст',
      })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}
// Неизменённый встроенный промпт не сохраняем как override: пустая строка
// означает «использовать встроенный».
function promptPayload() {
  return {
    prompt:
      promptText.value.trim() === defaultPrompt.value.trim()
        ? ''
        : promptText.value,
    crop_prompt:
      cropPromptText.value.trim() === defaultCropPrompt.value.trim()
        ? ''
        : cropPromptText.value,
  }
}

async function savePrompts() {
  if (!canConfigure.value || promptsSaving.value) return

  promptsSaving.value = true

  try {
    const data = await updateQwenSettings(promptPayload())
    promptText.value = data?.prompt || ''
    cropPromptText.value = data?.crop_prompt || ''
    Notify.create({ type: 'positive', message: 'Промпты сохранены' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    promptsSaving.value = false
  }
}

async function save() {
  saving.value = true

  try {
    const payload = {
      provider: provider.value,
      model: model.value || undefined,
      base_url: baseUrl.value,
      keep_alive: keepAlive.value,
      unload_on_idle: unloadOnIdle.value,
      ...promptPayload(),
    }

    // Only send the key when the user typed a new one (blank = keep as is).
    if (apiKey.value) payload.api_key = apiKey.value

    await updateQwenSettings(payload)
    await loadSettings()
    await loadModels()
    Notify.create({ type: 'positive', message: 'Настройки QWEN сохранены' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    saving.value = false
  }
}

async function clearKey() {
  await clearKeyRun(async () => {
    try {
      await updateQwenSettings({ api_key: '' })
      await loadSettings()
      Notify.create({ type: 'info', message: 'API-ключ очищен' })
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}
async function unload() {
  await unloadRun(async () => {
    try {
      const result = await unloadQwen()

      Notify.create({
        type: 'positive',
        message:
          result.status === 'unloaded'
            ? 'Модель выгружена из памяти'
            : 'Для облачного провайдера выгрузка не требуется',
      })
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}
onMounted(async () => {
  await loadSettings()
  await loadModels()
  loadStats()
  loadHistoryLog()
})

onBeforeUnmount(stopStatsPolling)
</script>

<template>
  <div style="max-width: 1560px">
    <!-- Главный выключатель описаний: снимает QWEN из «Обновления базы»
         целиком. Пока он выключен, прогон идёт инспектор → превью →
         DINO/HYBRID, а «Уточнение» не запускается — сравнивать нечего. -->
    <q-card flat bordered class="q-mb-md">
      <q-card-section>
        <div class="row items-center no-wrap">
          <q-toggle
            :model-value="qwenInPipeline"
            label="Запускать QWEN в «Обновлении базы»"
            color="primary"
            :disable="!canConfigure || qwenInPipelineSaving"
            @update:model-value="setQwenInPipeline"
          />
          <q-badge
            class="q-ml-md"
            :color="qwenInPipeline ? 'green-7' : 'grey-7'"
            :label="qwenInPipeline ? 'включено' : 'выключено'"
          />
        </div>
        <div class="text-caption text-grey-8 q-mt-xs">
          Выключено — кнопка «Обновление базы» идёт без описаний и без
          «Уточнения»: инспектор, превью, DINO и HYBRID отработают как обычно.
          Описания можно дозаполнить позже за нужный период («Дозаполнить за
          период»).
        </div>
      </q-card-section>
    </q-card>
    <div class="row q-col-gutter-md">
      <div class="col-12 col-sm-6 col-lg">
        <div class="text-h6 q-mb-md">Модель QWEN</div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Провайдер QWEN</div>

        <q-banner v-if="!canConfigure" dense class="bg-grey-2 text-caption q-mb-sm">
          Провайдер, Base URL, API-ключ и модель меняет только Администратор.
          Запуск описаний и выгрузка модели из памяти доступны Менеджеру.
        </q-banner>

        <q-select
          v-model="provider"
          :options="[
            { label: 'Локально (Ollama)', value: 'ollama' },
            { label: 'Облако (OpenAI-совместимый)', value: 'openai' },
          ]"
          dense
          outlined
          emit-value
          map-options
          label="Провайдер"
          class="q-mb-sm"
          :disable="!canConfigure"
        />

        <div class="text-caption text-grey-8 q-mb-md">
          Запомнено: локально — {{ savedModels.ollama || '—' }} ·
          облако — {{ savedModels.openai || '—' }}
        </div>

        <q-banner
          v-if="provider === 'openai'"
          class="bg-orange-1 text-orange-10 q-mb-md"
        >
          Облачный провайдер отправляет изображения на внешний сервис.
          Включайте только по согласованию и без персональных данных.
        </q-banner>

        <template v-if="provider === 'openai'">
          <q-input
            v-model="baseUrl"
            dense
            outlined
            label="Base URL (например, https://api.openai.com/v1)"
            class="q-mb-md"
            :disable="!canConfigure"
          />
          <q-input
            v-model="apiKey"
            type="password"
            dense
            outlined
            :label="
              apiKeySet
                ? `API-ключ (сохранён ${apiKeyHint || ''}) — пусто = не менять`
                : 'API-ключ'
            "
            class="q-mb-md"
            :disable="!canConfigure"
          />
          <q-btn
            v-if="apiKeySet && canConfigure"
            flat
            dense
            color="negative"
            label="Очистить ключ"
            class="q-mb-md"
            :loading="clearKeyBusy"
            @click="clearKey"
          />
        </template>

        <q-select
          v-model="model"
          :options="available"
          :loading="loading"
          dense
          outlined
          emit-value
          map-options
          use-input
          input-debounce="0"
          new-value-mode="add-unique"
          :label="`Модель (провайдер: ${provider === 'openai' ? 'облако' : 'локально'})`"
          class="q-mb-sm"
          :disable="!canConfigure"
          @update:model-value="saveModel"
        />
        <div class="text-caption text-grey-8 q-mb-md">
          Сохранено: {{ current || '—' }}
          <template v-if="modelsUnavailable">
            · список моделей провайдера недоступен, введите имя вручную
          </template>
        </div>

        <div class="row q-gutter-sm items-center q-mb-md">
          <q-input
            v-model="keepAlive"
            dense
            outlined
            label="Keep-alive (0 = выгружать сразу)"
            style="max-width: 220px"
            :disable="!canConfigure"
          />
          <q-toggle
            v-model="unloadOnIdle"
            label="Выгружать при простое очереди"
            :disable="!canConfigure"
          />
        </div>

        <div v-if="billboardCropAvailable" class="q-mb-md">
          <q-toggle
            :model-value="billboardCropEnabled"
            label="Использовать crop рекламного щита для QWEN"
            :disable="!canConfigure || billboardCropSaving"
            @update:model-value="setBillboardCropEnabled"
          />
          <div class="text-caption text-grey-8 q-ml-xl">
            Если щит найден, QWEN анализирует его crop; если не найден или опция выключена — полный кадр.
            Не связано с обычным центральным crop.
          </div>
        </div>
        <q-banner v-else dense class="bg-grey-2 text-caption q-mb-md">
          Детектор рекламных щитов не установлен в этой версии сервера.
        </q-banner>

        <div class="text-caption text-grey-8 q-mb-md">
          Промпты модели редактируются в блоке «Промпты QWEN» справа.
        </div>

        <div class="text-caption text-grey q-mb-md">
          Текущая: <b>{{ current || '—' }}</b>. Keep-alive держит модель в
          памяти между заданиями; при простое очереди воркер выгружает её.
        </div>

        <div class="q-gutter-sm">
          <q-btn v-if="canConfigure" color="primary" label="Сохранить" :loading="saving" @click="save" />
          <q-btn flat icon="refresh" label="Обновить список" :loading="loading" @click="loadModels" />
          <q-btn
            flat
            color="orange"
            icon="memory"
            label="Выгрузить из памяти"
            :loading="unloadBusy"
            @click="unload"
          />
        </div>
      </q-card-section>
    </q-card>
      </div>

      <div class="col-12 col-sm-6 col-lg">
    <q-card v-if="stats" flat bordered>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Метаданные QWEN</div>

        <div class="text-caption text-grey-8 q-mb-sm">
          ВСЕГО ФОТО: {{ stats.photos ?? '—' }} ·
          РАСПОЗНАНО: {{ stats.processed ?? 0 }}
          <template v-if="stats.remaining">(осталось {{ stats.remaining }})</template> ·
          В ОЧЕРЕДИ: {{ qwenQueue }} ·
          С ОШИБКОЙ: {{ stats.counts?.FAILED || 0 }}
        </div>

        <div class="row items-center q-gutter-sm q-mb-md">
          <q-chip
            v-for="(count, status) in stats.counts"
            :key="status"
            :color="status === 'FAILED' && count ? 'negative' : 'grey-4'"
            :text-color="status === 'FAILED' && count ? 'white' : 'black'"
            dense
          >
            {{ status }}: {{ count }}
          </q-chip>
          <span v-if="statsPolling" class="text-caption text-grey-7">
            обновляется автоматически…
          </span>
        </div>

        <div v-if="stats.models && stats.models.length" class="q-mb-md">
          <div class="text-caption text-grey-8 q-mb-xs">
            Какая модель дала описания:
          </div>
          <div
            v-for="item in stats.models"
            :key="item.model"
            class="text-caption text-grey-8"
          >
            {{ item.model }} — {{ item.photos }}
          </div>
          <div
            v-if="stats.tokens && stats.tokens.total"
            class="text-caption text-grey-8 q-mt-xs"
          >
            Токенов облака: {{ stats.tokens.total }}
            (запрос {{ stats.tokens.prompt }} / ответ {{ stats.tokens.completion }})
          </div>
          <div v-if="stats.history_rows" class="text-caption text-grey-8">
            Прежних результатов в истории: {{ stats.history_rows }}
          </div>
        </div>

        <div v-if="stats.runs && stats.runs.length" class="q-mb-md">
          <div class="text-caption text-grey-8 q-mb-xs">
            Последние запуски (по источнику):
          </div>
          <div
            v-for="run in stats.runs"
            :key="run.source"
            class="text-caption text-grey-8"
          >
            {{ sourceLabel(run.source) }}: {{ fmtDate(run.last_finished_at) }}
            · заданий {{ run.jobs }}
            <template v-if="run.failed">(ошибок {{ run.failed }})</template>
          </div>
        </div>

        <div class="row q-gutter-sm">
          <q-btn
            color="secondary"
            icon="auto_awesome"
            label="Запустить QWEN (все фото)"
            :loading="runAllBusy"
            @click="runAll"
          />
          <q-btn
            flat
            color="teal"
            icon="replay"
            :label="`Повторить для упавших (${stats.failed_photo_ids.length})`"
            :disable="!stats.failed_photo_ids.length"
            :loading="retryBusy"
            @click="retryFailed"
          />
          <q-btn
            flat
            color="orange"
            icon="stop"
            label="Остановить описание"
            :disable="!qwenQueue"
            :loading="stopQueueBusy"
            @click="stopQueue"
          />
          <q-btn
            flat
            color="grey-8"
            icon="clear_all"
            label="Очистить список заданий"
            :loading="clearQueueBusy"
            @click="clearQueue"
          />
        </div>
      </q-card-section>
    </q-card>
      </div>

      <!-- Справа: статистика присвоения описаний -->
      <div class="col-12 col-sm-6 col-lg">
        <q-card flat bordered class="fit">
          <q-card-section>
            <div class="text-subtitle1 q-mb-sm">Статистика описаний</div>

            <template v-if="stats">
              <div
                v-for="row in assignmentStats"
                :key="row.label"
                class="row items-baseline q-mb-xs"
              >
                <div class="text-caption text-grey col">{{ row.label }}</div>
                <div class="text-subtitle1">{{ row.value }}</div>
              </div>

              <q-separator class="q-my-sm" />

              <div class="text-caption text-grey q-mb-xs">
                Дата последнего запуска
              </div>
              <div
                v-for="row in launchDates"
                :key="row.label"
                class="row items-baseline q-mb-xs"
              >
                <div class="text-caption text-grey col">{{ row.label }}</div>
                <div class="text-caption">{{ fmtDate(row.value) }}</div>
              </div>

              <q-separator class="q-my-sm" />
              <q-btn
                outline
                color="negative"
                icon="restart_alt"
                label="Пересканировать"
                class="full-width"
                :disable="qwenQueue > 0"
                @click="openRescan()"
              />
              <div class="text-caption text-negative q-mt-xs">
                Удалит текущие QWEN-результаты за выбранный период, сохранив их в историю, и запустит описание заново.
              </div>
              <q-btn
                outline
                color="primary"
                icon="playlist_add"
                label="Дозаполнить за период"
                class="full-width q-mt-sm"
                @click="openScan"
              />
              <div class="text-caption text-grey-7 q-mt-xs">
                Поставит в очередь только фото без успешного описания за
                выбранный период. Существующие результаты не меняются.
              </div>
            </template>

            <div v-else class="text-caption text-grey-7">
              Данные статистики ещё не загружены.
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Третья колонка: текстовый лог прежних описаний. -->
      <div class="col-12 col-sm-6 col-lg">
        <q-card flat bordered class="fit">
          <q-card-section>
            <div class="row items-center q-mb-sm">
              <div class="text-subtitle1 col">История описаний</div>
              <q-btn flat dense round icon="refresh" :loading="historyLoading" @click="loadHistoryLog">
                <q-tooltip>Обновить текстовый лог</q-tooltip>
              </q-btn>
            </div>
            <div v-if="historyError" class="text-negative text-caption q-mb-sm">{{ historyError }}</div>
            <div v-else-if="!historyLog.items.length" class="text-caption text-grey-7">
              История пока пуста.
            </div>
            <pre v-else class="qwen-history-text">{{ historyLog.text }}</pre>
          </q-card-section>
        </q-card>
      </div>

      <!-- Пятая колонка: промпты модели -->
      <div class="col-12 col-sm-6 col-lg">
        <q-card flat bordered class="fit">
          <q-card-section>
            <div class="text-subtitle1 q-mb-sm">Промпты QWEN</div>

            <template v-if="billboardCropAvailable">
              <q-input
                v-model="cropPromptText"
                type="textarea"
                autogrow
                dense
                outlined
                label="Промпт для кропа щита"
                class="q-mb-xs"
                :disable="!canConfigure"
              />
              <div class="row items-center no-wrap q-mb-md">
                <div class="text-caption text-grey-8 col">
                  Этот текст получает модель вместе с вырезанным щитом.
                </div>
                <q-btn
                  flat
                  dense
                  size="sm"
                  label="Встроенный"
                  :disable="!canConfigure"
                  @click="cropPromptText = defaultCropPrompt"
                />
              </div>
            </template>

            <q-input
              v-model="promptText"
              type="textarea"
              autogrow
              dense
              outlined
              label="Промпт для полного кадра"
              class="q-mb-xs"
              :disable="!canConfigure"
            />
            <div class="row items-center no-wrap q-mb-md">
              <div class="text-caption text-grey-8 col">
                Используется, когда кроп щита выключен или щит не найден.
              </div>
              <q-btn
                flat
                dense
                size="sm"
                label="Встроенный"
                :disable="!canConfigure"
                @click="promptText = defaultPrompt"
              />
            </div>

            <div class="text-caption text-grey-8 q-mb-md">
              Пустое поле или кнопка «Встроенный» возвращают стандартный
              промпт. Изменения применяются сразу, без перезапуска.
            </div>

            <q-btn
              v-if="canConfigure"
              color="primary"
              label="Сохранить промпты"
              :loading="promptsSaving"
              @click="savePrompts"
            />
            <div v-else class="text-caption text-grey-7">
              Изменять промпты может только Администратор.
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-dialog v-model="rescanOpen">
      <q-card style="width: 520px; max-width: calc(100vw - 32px)">
        <q-card-section class="text-subtitle1">
          {{ isDestructiveRescan ? 'Пересканировать QWEN за период' : 'Дозаполнить QWEN за период' }}
        </q-card-section>
        <q-card-section class="q-gutter-sm">
          <q-banner
            v-if="isDestructiveRescan"
            class="bg-red-1 text-negative text-caption"
            rounded
          >
            ДЕСТРУКТИВНО: текущие результаты QWEN за выбранный период будут удалены.
            Сначала они сохраняются в историю, затем для выбранных фото запускается
            новое описание с текущей моделью <b>{{ current || '—' }}</b>.
          </q-banner>
          <q-banner v-else class="bg-blue-1 text-caption" rounded>
            В очередь попадут только фото без успешного описания за выбранный
            период. Существующие результаты не удаляются и не перезаписываются;
            модель — <b>{{ current || '—' }}</b>.
          </q-banner>
          <q-select
            v-model="rescanDateMode"
            :options="[{ label: 'Дата загрузки', value: 'upload' }, { label: 'Дата съёмки', value: 'capture' }]"
            emit-value
            map-options
            dense
            outlined
            label="Фильтр периода"
          />
          <div class="row q-col-gutter-sm">
            <div class="col-6">
              <q-input v-model="rescanFrom" type="date" dense outlined label="С даты" />
            </div>
            <div class="col-6">
              <q-input v-model="rescanTo" type="date" dense outlined label="По дату" />
            </div>
          </div>
          <div v-if="qwenRunning" class="text-negative text-caption">
            Модель сейчас занята ({{ qwenRunning }} в работе) — дождитесь или
            нажмите «Остановить описание».
          </div>
          <div v-else-if="qwenPending" class="text-caption text-grey-7">
            В очереди уже ждут {{ qwenPending }} заданий описания: они
            обработаются, когда запустится воркер, а в очередь попадут только
            фото из выбранного периода. Снять их — кнопка «Остановить описание».
          </div>
          <div v-if="rescanError" class="text-negative text-caption">{{ rescanError }}</div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup :disable="rescanBusy" />
          <q-btn
            :color="isDestructiveRescan ? 'negative' : 'primary'"
            :label="isDestructiveRescan ? 'Пересканировать' : 'Поставить в очередь'"
            :disable="!canRescan() || rescanBusy"
            :loading="rescanBusy"
            @click="runRescan"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.qwen-history-text {
  margin: 0;
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 0.78rem/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  color: #455a64;
}
</style>
