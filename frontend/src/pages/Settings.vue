<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Notify } from 'quasar'

import { usePoller } from '../composables/usePoller'

import {
  clearQwenJobs,
  clearStuckQwenJobs,
  enqueueQwen,
  fetchQwenAddresses,
  fetchQwenHistoryLog,
  fetchQwenModels,
  fetchQwenSettings,
  fetchQwenStats,
  pauseQwenJobs,
  previewQwenSelection,
  rescanQwenPeriod,
  resetQwenResults,
  resumeQwenJobs,
  scanQwenPeriod,
  stopQwenJobs,
  unloadQwen,
  updateQwenSettings,
} from '../api/client'
import { useSessionStore } from '../stores/session'
import { useAsyncAction } from '../composables/useAsyncAction'
import { confirmDialog } from '../composables/confirmDialog'
import { PERIODS, periodRange } from '../utils/periodRange'

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

// ---- Панель запуска описания ----------------------------------------------
// Один блок вместо россыпи кнопок: режим, период и адреса выбираются до
// запуска, пауза/продолжение — по очереди, сбросы — отдельными опасными
// действиями (владелец, 21.11.2026).
const runMode = ref('skip') // 'skip' — дополнить, 'overwrite' — перезаписать
const runPeriod = ref('all')
const runFrom = ref('')
const runTo = ref('')
const runDateMode = ref('capture')
const runNotice = ref('')

const dateModeOptions = [
  { label: 'Дата съёмки', value: 'capture' },
  { label: 'Дата загрузки', value: 'upload' },
]

const addressChoices = ref([])
const addressOptions = ref([])
const selectedAddresses = ref([])
const addressesLoading = ref(false)

const selection = ref(null)
const selectionBusy = ref(false)
let selectionTimer = null

const { busy: runStartBusy, run: runStartRun } = useAsyncAction()
const { busy: pauseBusy, run: pauseRun } = useAsyncAction()
const { busy: resumeBusy, run: resumeRun } = useAsyncAction()
const { busy: stuckBusy, run: stuckRun } = useAsyncAction()
const { busy: resetBusy, run: resetRun } = useAsyncAction()

const runDates = computed(() => {
  const [from, to] = periodRange(runPeriod.value, {
    customFrom: runFrom.value || null,
    customTo: runTo.value || null,
  })

  // «Период…» без границ — незаполненная форма, а не «всё время»: иначе
  // запуск молча пошёл бы по всему корпусу.
  if (runPeriod.value === 'custom') return [from, to]

  // Остальные варианты всегда дают границы; «Все даты» уходит широким
  // интервалом, потому что сервер ждёт даты.
  return [from || '2000-01-01', to || new Date().toISOString().slice(0, 10)]
})

const runDatesValid = computed(
  () => runDates.value[0] && runDates.value[1] && runDates.value[1] >= runDates.value[0],
)

const selectedAddressIds = computed(() =>
  selectedAddresses.value.map((item) => Number(item.address_id ?? item)),
)

const runPayload = computed(() => ({
  date_from: runDates.value[0],
  date_to: runDates.value[1],
  date_mode: runDateMode.value,
  address_ids: selectedAddressIds.value.length
    ? selectedAddressIds.value
    : null,
}))

const timeline = computed(() => stats.value?.timeline || null)
const runPaused = computed(() => Boolean(timeline.value?.paused))
const runStuck = computed(() => Number(timeline.value?.stuck || 0))

// Оценка остатка: среднее по последним описаниям × очередь. Округляем до
// минут — это всё равно «≈».
const etaLabel = computed(() => {
  const seconds = Number(timeline.value?.eta_seconds || 0)

  if (!seconds) return ''

  const minutes = Math.max(1, Math.round(seconds / 60))

  if (minutes < 60) return `${minutes} мин`

  return `${Math.floor(minutes / 60)} ч ${minutes % 60} мин`
})

// Одна кнопка на все состояния: пусто — «Запустить», очередь идёт — «Пауза»,
// на паузе — «Продолжить». «Остановить» стоит рядом отдельно.
const runAction = computed(() => {
  if (runPaused.value) {
    return {
      label: 'Продолжить',
      icon: 'play_circle',
      color: 'positive',
      loading: resumeBusy.value,
      action: resumeDescription,
      hint: 'Вернуть приостановленные задания в очередь',
    }
  }

  if (qwenQueue.value) {
    return {
      label: 'Пауза',
      icon: 'pause',
      color: 'orange',
      loading: pauseBusy.value,
      action: pauseDescription,
      hint: 'Текущее фото дочитывается, следующие в работу не берутся',
    }
  }

  return {
    label: 'Запустить описание',
    icon: 'play_arrow',
    color: 'primary',
    loading: runStartBusy.value,
    action: startQwenRun,
    hint:
      'Перезапись сохраняет прежние результаты в историю; дополнение ставит ' +
      'только фото без успешного описания',
  }
})

const runActionDisabled = computed(() =>
  runPaused.value || qwenQueue.value ? false : !runDatesValid.value,
)


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

async function loadAddressChoices() {
  addressesLoading.value = true

  try {
    const data = await fetchQwenAddresses()
    addressChoices.value = data.items || []
    addressOptions.value = addressChoices.value.map((item) => ({
      label: `${item.name} · ${item.photos}`,
      value: item.address_id,
      name: item.name,
      photos: item.photos,
    }))
  } catch {
    // Список адресов — подсказка: без него запуск работает по всем адресам.
    addressChoices.value = []
    addressOptions.value = []
  } finally {
    addressesLoading.value = false
  }
}

function scheduleSelectionRefresh() {
  if (selectionTimer) clearTimeout(selectionTimer)

  selectionTimer = setTimeout(() => {
    selectionTimer = null
    refreshSelection()
  }, 250)
}

async function refreshSelection() {
  if (!runDatesValid.value) {
    selection.value = null
    return
  }

  selectionBusy.value = true

  try {
    selection.value = await previewQwenSelection(runPayload.value)
  } catch {
    selection.value = null
  } finally {
    selectionBusy.value = false
  }
}

const selectionText = computed(() => {
  const data = selection.value

  if (!data) return ''

  const parts = [`фото: ${data.photos}`, `с описанием: ${data.described}`]

  if (runMode.value === 'skip') parts.push(`будет дополнено: ${data.missing}`)
  else parts.push(`будет перезаписано: ${data.photos}`)

  if (data.addresses) parts.push(`адресов: ${data.addresses}`)

  return parts.join(' · ')
})

// Что именно выбрано — до запуска: даты и адреса (имена из справочника).
const selectionScope = computed(() => {
  const [from, to] = runDates.value
  const dates = from && to ? `период ${from} — ${to}` : 'период не задан'
  const names = selectedAddresses.value
    .map((item) => item?.name || addressChoices.value.find(
      (entry) => entry.address_id === Number(item),
    )?.name)
    .filter(Boolean)

  const addresses = names.length
    ? `адреса: ${names.join(', ')}`
    : 'все адреса'

  return `${dates} · ${addresses}`
})

/** Запуск описания: режим выбирает неразрушающий догон или перезапись. */
async function startQwenRun() {
  await runStartRun(async () => {
    if (!runDatesValid.value) {
      Notify.create({ type: 'warning', message: 'Проверьте границы периода' })
      return
    }

    runNotice.value = ''

    try {
      const payload = { ...runPayload.value }

      const result =
        runMode.value === 'overwrite'
          ? await rescanQwenPeriod(payload)
          : await scanQwenPeriod({ ...payload, limit: 5000 })

      Notify.create({
        type: 'positive',
        message:
          runMode.value === 'overwrite'
            ? `В историю сохранено: ${result.archived}; новых заданий: ${result.jobs}`
            : result.photos
              ? `Фото без описания: ${result.photos}; поставлено заданий: ${result.jobs}`
              : 'За выбранный период и адреса нет фото без описания',
      })

      await loadStats()
      await loadHistoryLog()
      scheduleSelectionRefresh()
    } catch (err) {
      runNotice.value = err.message || 'Запуск не выполнен'
    }
  })
}

/** Пауза: текущее фото доигрывает, следующие не берутся. */
async function pauseDescription() {
  await pauseRun(async () => {
    try {
      const result = await pauseQwenJobs()
      Notify.create({
        type: result.paused ? 'info' : 'warning',
        message: result.paused
          ? `На паузу поставлено заданий: ${result.paused}. Текущее фото дочитывается.`
          : 'Ждущих заданий нет — пауза не нужна',
      })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}

async function resumeDescription() {
  await resumeRun(async () => {
    try {
      const result = await resumeQwenJobs()
      Notify.create({
        type: result.resumed ? 'positive' : 'info',
        message: result.resumed
          ? `Возвращено в очередь: ${result.resumed}`
          : 'Приостановленных заданий нет',
      })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}

/** Зависшие задания: RUNNING дольше получаса (обычно после убитого воркера). */
async function clearStuck() {
  if (!runStuck.value) return

  const ok = await confirmDialog({
    title: 'Снять зависшие задания?',
    message:
      `Заданий в RUNNING дольше 30 минут: ${runStuck.value}. ` +
      'Они перейдут в CANCELLED; сделанные описания не затрагиваются.',
    okLabel: 'Снять',
    color: 'warning',
  })

  if (!ok) return

  await stuckRun(async () => {
    try {
      const result = await clearStuckQwenJobs(30)
      Notify.create({
        type: result.cancelled ? 'positive' : 'info',
        message: result.cancelled
          ? `Снято зависших заданий: ${result.cancelled}`
          : 'Зависших заданий не найдено',
      })
      await loadStats()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}

/** Жёсткий сброс: описания, история и архивы. Фото и распознавание целы. */
async function hardReset() {
  if (!canConfigure.value) return

  const ok = await confirmDialog({
    title: 'Жёсткий сброс описаний',
    message:
      'Будут удалены ВСЕ описания QWEN, история и архивы, разбор кропов ' +
      'и задания описаний. Фото, превью, кропы и распознавание остаются. ' +
      'Отменить это нельзя — перед удалением пишется отчёт.',
    okLabel: 'Удалить всё',
  })

  if (!ok) return

  await resetRun(async () => {
    try {
      const result = await resetQwenResults()
      Notify.create({
        type: 'positive',
        message:
          `Сброшено: карточки ${result.deleted.photo_qwen ?? 0}, ` +
          `история ${result.deleted.photo_qwen_history ?? 0}. ` +
          'Фото и распознавание не тронуты.',
      })
      await loadStats()
      await loadHistoryLog()
      scheduleSelectionRefresh()
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
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

// Карточка «Метаданные QWEN»: крупные числа вместо строки капсом. Плитки не
// пересекаются и в сумме дают базу: successful + done_empty = DONE, remaining —
// остальные фото; «в очереди» (задания) и «с ошибкой» (статус FAILED) живут
// отдельно, это не часть разбиения (владелец, 20.11.2026).
const qwenMetrics = computed(() => {
  const s = stats.value

  if (!s) return []

  const failed = Number(s.counts?.FAILED || 0)
  const queued = qwenQueue.value

  return [
    { label: 'Фото в базе', value: Number(s.photos || 0), tone: '' },
    { label: 'С описанием', value: Number(s.successful || 0), tone: 'positive' },
    { label: 'Пустой ответ', value: Number(s.done_empty || 0), tone: '' },
    { label: 'Без описания', value: Number(s.remaining || 0), tone: '' },
    { label: 'В очереди', value: queued, tone: queued ? 'info' : '' },
    { label: 'С ошибкой', value: failed, tone: failed ? 'negative' : '' },
  ]
})

// Полоса покрытия: обработанные фото к размеру базы (0..1).
const qwenCoverage = computed(() => {
  const photos = Number(stats.value?.photos || 0)

  if (!photos) return 0

  return Math.min(1, Number(stats.value?.processed || 0) / photos)
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
  loadAddressChoices()
  refreshSelection()
})

// Период, режим и адреса влияют на счётчик «сколько фото попадёт».
watch(
  [runMode, runPeriod, runFrom, runTo, runDateMode, selectedAddresses],
  scheduleSelectionRefresh,
  { deep: true },
)

onBeforeUnmount(() => {
  stopStatsPolling()

  if (selectionTimer) clearTimeout(selectionTimer)
})
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
    <q-card v-if="stats" flat bordered class="fit">
      <q-card-section>
        <div class="row items-center q-mb-sm">
          <div class="text-subtitle1 col">Метаданные QWEN</div>
          <span v-if="statsPolling" class="text-caption text-grey-7">
            обновляется автоматически…
          </span>
        </div>

        <!-- Крупные числа вместо строки капсом: состояние описаний видно с
             первого взгляда, а не читается как абзац (владелец, 20.11.2026). -->
        <div class="qwen-metrics q-mb-sm">
          <div v-for="tile in qwenMetrics" :key="tile.label" class="qwen-metric">
            <div class="qwen-metric__value" :class="tile.tone">{{ tile.value }}</div>
            <div class="qwen-metric__label">{{ tile.label }}</div>
          </div>
        </div>

        <div class="row items-center no-wrap q-mb-md">
          <q-linear-progress
            :value="qwenCoverage"
            color="primary"
            track-color="grey-3"
            rounded
            class="col"
          />
          <div class="text-caption text-grey-8 q-ml-sm">
            {{ stats.processed ?? 0 }} из {{ stats.photos ?? 0 }}
          </div>
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
        </div>

        <div v-if="stats.models && stats.models.length" class="q-mb-md">
          <div class="text-caption text-grey-8 q-mb-xs">
            Какая модель дала описания
          </div>
          <div
            v-for="item in stats.models"
            :key="item.model"
            class="qwen-row"
          >
            <span class="qwen-row__label ellipsis">{{ item.model }}</span>
            <span class="qwen-row__value">{{ item.photos }}</span>
          </div>
          <div v-if="stats.tokens && stats.tokens.total" class="qwen-row">
            <span class="qwen-row__label">Токенов облака</span>
            <span class="qwen-row__value">
              {{ stats.tokens.total }}
              <span class="text-grey-6">
                ({{ stats.tokens.prompt }} / {{ stats.tokens.completion }})
              </span>
            </span>
          </div>
          <div v-if="stats.history_rows" class="qwen-row">
            <span class="qwen-row__label">Прежних результатов в истории</span>
            <span class="qwen-row__value">{{ stats.history_rows }}</span>
          </div>
        </div>

        <div v-if="stats.runs && stats.runs.length" class="q-mb-md">
          <div class="text-caption text-grey-8 q-mb-xs">
            Последние запуски
          </div>
          <div
            v-for="run in stats.runs"
            :key="run.source"
            class="qwen-row"
          >
            <span class="qwen-row__label">
              {{ sourceLabel(run.source) }}
              <span class="text-grey-6">· заданий {{ run.jobs }}</span>
              <span v-if="run.failed" class="text-negative">
                · ошибок {{ run.failed }}
              </span>
            </span>
            <span class="qwen-row__value">{{ fmtDate(run.last_finished_at) }}</span>
          </div>
        </div>

        <!-- Панель запуска описания: режим, период и адреса выбираются до
             запуска; пауза действует со следующего фото (владелец, 21.11.2026). -->
        <q-separator class="q-my-sm" />
        <div class="text-subtitle2 q-mb-sm">Запуск описания</div>

        <!-- Поля — в столбик и во всю ширину блока: длинные названия адресов
             не обрезаются, выбирать проще. -->
        <div class="column q-gutter-sm" style="max-width: 640px">
          <q-select
            v-model="runMode"
            :options="[
              { label: 'Дополнять — только фото без описания', value: 'skip' },
              { label: 'Перезаписывать — старое уйдёт в историю', value: 'overwrite' },
            ]"
            emit-value
            map-options
            dense
            outlined
            label="Режим"
            :disable="runStartBusy"
          />

          <q-select
            v-model="runDateMode"
            :options="dateModeOptions"
            emit-value
            map-options
            dense
            outlined
            label="Дата"
            :disable="runStartBusy"
          />

          <q-select
            v-model="runPeriod"
            :options="PERIODS"
            emit-value
            map-options
            dense
            outlined
            label="Период"
            :disable="runStartBusy"
          />

          <template v-if="runPeriod === 'custom'">
            <q-input
              v-model="runFrom"
              type="date"
              dense
              outlined
              label="С даты"
              :disable="runStartBusy"
            />
            <q-input
              v-model="runTo"
              type="date"
              dense
              outlined
              label="По дату"
              :disable="runStartBusy"
            />
          </template>

          <q-select
            v-model="selectedAddresses"
            :options="addressOptions"
            multiple
            use-chips
            emit-value
            map-options
            dense
            outlined
            input-debounce="200"
            :loading="addressesLoading"
            label="Адреса (пусто — все)"
            :disable="runStartBusy"
          >
            <q-tooltip>
              Адреса после HYBRID: список и число фото в нём. Пусто — запуск
              по всем адресам выбранного периода.
            </q-tooltip>
          </q-select>
        </div>

        <div class="text-caption text-grey-8 q-mt-xs">{{ selectionScope }}</div>
        <div class="text-caption text-grey-7 q-mt-xs">
          <template v-if="runNotice">{{ runNotice }}</template>
          <template v-else-if="selection">{{ selectionText }}</template>
          <template v-else-if="selectionBusy">Считаю, сколько фото попадёт…</template>
          <template v-else>Выберите период и адреса — покажу, сколько фото попадёт.</template>
        </div>

        <div class="row q-gutter-sm q-mt-sm items-center">
          <!-- Одна кнопка на запуск/паузу/продолжение; «Остановить» рядом. -->
          <q-btn
            :color="runAction.color"
            :icon="runAction.icon"
            :label="runAction.label"
            :loading="runAction.loading"
            :disable="runActionDisabled"
            @click="runAction.action"
          >
            <q-tooltip>{{ runAction.hint }}</q-tooltip>
          </q-btn>
          <q-btn
            flat
            color="orange"
            icon="stop"
            label="Остановить"
            :disable="!qwenQueue"
            :loading="stopQueueBusy"
            @click="stopQueue"
          />
          <q-btn
            v-if="stats.failed_photo_ids.length"
            flat
            color="teal"
            icon="replay"
            :label="`Повторить упавшие (${stats.failed_photo_ids.length})`"
            :loading="retryBusy"
            @click="retryFailed"
          />
        </div>

        <div v-if="timeline" class="text-caption text-grey-8 q-mt-xs">
          <span v-if="timeline.started_at">старт {{ fmtDate(timeline.started_at) }}</span>
          <span v-if="timeline.paused"> · пауза {{ fmtDate(timeline.paused_at) }}</span>
          <span v-if="timeline.pending || timeline.running">
            · в очереди {{ timeline.pending + timeline.running }}
          </span>
          <span v-if="timeline.eta_seconds"> · осталось ≈ {{ etaLabel }}</span>
          <span v-else-if="!timeline.pending && !timeline.running"> · очередь пуста</span>
        </div>

        <div class="row q-gutter-sm q-mt-sm items-center">
          <q-btn
            v-if="runStuck"
            flat
            color="warning"
            icon="build"
            :label="`Снять зависшие (${runStuck})`"
            :loading="stuckBusy"
            @click="clearStuck"
          >
            <q-tooltip>
              Задания в RUNNING дольше 30 минут — обычно после убитого воркера.
              Переводим в CANCELLED, описания не трогаем.
            </q-tooltip>
          </q-btn>
          <q-btn
            flat
            color="grey-8"
            icon="clear_all"
            label="Очистить список заданий"
            :loading="clearQueueBusy"
            @click="clearQueue"
          />
          <q-btn
            v-if="canConfigure"
            flat
            color="negative"
            icon="delete_forever"
            label="Жёсткий сброс описаний"
            :loading="resetBusy"
            @click="hardReset"
          >
            <q-tooltip>
              Удаляет все описания, историю, архивы и разбор кропов. Фото и
              распознавание остаются.
            </q-tooltip>
          </q-btn>
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

  </div>
</template>

<style scoped>
/* Плитки «Метаданных QWEN»: число крупно, подпись мелкая — состояние видно
   с первого взгляда, без чтения строки капсом. */
.qwen-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));
  gap: 6px;
}

.qwen-metric {
  padding: 6px 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: #fafafa;
}

.qwen-metric__value {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.1;
  color: #37474f;
}

.qwen-metric__value.positive {
  color: #2e7d32;
}

.qwen-metric__value.info {
  color: #1565c0;
}

.qwen-metric__value.negative {
  color: #c62828;
}

.qwen-metric__label {
  margin-top: 2px;
  font-size: 10.5px;
  line-height: 1.2;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: #78909c;
}

/* Строка «ключ — значение»: модель, токены, запуски. */
.qwen-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 3px 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
  font-size: 12.5px;
  color: #455a64;
}

.qwen-row:last-child {
  border-bottom: 0;
}

.qwen-row__label {
  min-width: 0;
}

.qwen-row__value {
  flex: none;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

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
