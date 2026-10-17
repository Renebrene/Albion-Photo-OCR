<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Notify } from 'quasar'

import {
  clearQwenJobs,
  enqueueQwen,
  fetchQwenModels,
  fetchQwenSettings,
  fetchQwenStats,
  stopQwenJobs,
  unloadQwen,
  updateQwenSettings,
} from '../api/client'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const canConfigure = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

// provider settings
const provider = ref('ollama')
const baseUrl = ref('')
const apiKey = ref('')
const apiKeyHint = ref(null)
const apiKeySet = ref(false)
const keepAlive = ref('10m')
const unloadOnIdle = ref(true)

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
    await loadSettings()
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

  // Распознавание идёт в воркере: пока очередь не пуста, карточка должна
  // обновляться сама, иначе счётчики «застывают» до ручного перезахода.
  if (qwenQueue.value) startStatsPolling()
  else stopStatsPolling()
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

const qwenQueue = computed(
  () => (stats.value?.counts?.PENDING || 0) + (stats.value?.counts?.RUNNING || 0),
)

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
const statsTimer = ref(null)

function stopStatsPolling() {
  if (statsTimer.value !== null) {
    window.clearInterval(statsTimer.value)
    statsTimer.value = null
  }
}

function startStatsPolling() {
  if (statsTimer.value !== null) return

  statsTimer.value = window.setInterval(async () => {
    await loadStats()
    if (!qwenQueue.value) stopStatsPolling()
  }, 5000)
}

async function retryFailed() {
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
}

async function runAll() {
  try {
    const result = await enqueueQwen(null, false)
    Notify.create({ type: 'positive', message: `QWEN заданий: ${result.jobs}` })
    await loadStats()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function stopQueue() {
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
}

async function clearQueue() {
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
  try {
    await updateQwenSettings({ api_key: '' })
    await loadSettings()
    Notify.create({ type: 'info', message: 'API-ключ очищен' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function unload() {
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
}

onMounted(async () => {
  await loadSettings()
  await loadModels()
  loadStats()
})

onBeforeUnmount(stopStatsPolling)
</script>

<template>
  <div style="max-width: 1180px">
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-7">
        <div class="text-h6 q-mb-md">Модель QWEN</div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Провайдер QWEN</div>

        <q-banner v-if="!canConfigure" dense class="bg-grey-2 text-caption q-mb-sm">
          Провайдер, Base URL, API-ключ и модель меняет только Администратор.
          Запуск распознавания и выгрузка модели из памяти доступны Менеджеру.
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

        <div class="text-caption text-grey q-mb-md">
          Текущая: <b>{{ current || '—' }}</b>. Keep-alive держит модель в
          памяти между заданиями; при простое очереди воркер выгружает её.
        </div>

        <div class="q-gutter-sm">
          <q-btn v-if="canConfigure" color="primary" label="Сохранить" :loading="saving" @click="save" />
          <q-btn flat icon="refresh" label="Обновить список" :loading="loading" @click="loadModels" />
          <q-btn flat color="orange" icon="memory" label="Выгрузить из памяти" @click="unload" />
        </div>
      </q-card-section>
    </q-card>

    <q-card v-if="stats" flat bordered class="q-mt-md">
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Метаданные QWEN</div>

        <div class="text-caption text-grey-8 q-mb-sm">
          ВСЕГО ФОТО: {{ stats.photos ?? '—' }} ·
          РАСПОЗНАНО: {{ stats.processed ?? 0 }}
          <template v-if="stats.remaining">(осталось {{ stats.remaining }})</template> ·
          В ОЧЕРЕДИ: {{ qwenQueue }} ·
          С ОШИБКОЙ: {{ stats.counts.FAILED || 0 }}
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
          <span v-if="statsTimer" class="text-caption text-grey-7">
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
            @click="runAll"
          />
          <q-btn
            flat
            color="teal"
            icon="replay"
            :label="`Повторить для упавших (${stats.failed_photo_ids.length})`"
            :disable="!stats.failed_photo_ids.length"
            @click="retryFailed"
          />
          <q-btn
            flat
            color="orange"
            icon="stop"
            label="Остановить распознавание"
            :disable="!qwenQueue"
            @click="stopQueue"
          />
          <q-btn
            flat
            color="grey-8"
            icon="clear_all"
            label="Очистить список заданий"
            @click="clearQueue"
          />
        </div>
      </q-card-section>
    </q-card>
      </div>

      <!-- Справа: статистика присвоения описаний -->
      <div class="col-12 col-md-5">
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
            </template>

            <div v-else class="text-caption text-grey-7">
              Данные статистики ещё не загружены.
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </div>
</template>
