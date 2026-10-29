<script setup>
// Header control for the resumable pipeline run ("Обновление базы").
//
// It only *observes* the run and asks the backend to start/stop/resume it. The
// heavy work happens in the workers. Until schema/031 is applied the endpoint
// answers 404, so the whole control hides itself instead of showing a broken
// button.
import { computed, onMounted, ref, watch } from 'vue'
import { Notify } from 'quasar'

import { usePoller } from '../composables/usePoller'

import {
  fetchCurrentPipeline,
  fetchQwenSettings,
  resumePipeline,
  startPipeline,
  stopPipeline,
  updateQwenSettings,
} from '../api/client'

const props = defineProps({
  // Whether the signed-in user may change the run (needs jobs:write).
  canRun: { type: Boolean, default: false },
  // Идёт другой процесс (очередь описаний или уточнение): «База обновлена»
  // показывать рано, хотя прогон и завершён.
  busy: { type: Boolean, default: false },
  // Может ли пользователь писать настройки описаний (Администратор): тогда
  // выключатель в окне меняет общую настройку, а не только текущий прогон.
  canWriteSettings: { type: Boolean, default: false },
  // Личные настройки запуска (п. 2в): «Пропустить уточнение» и глубина
  // сканирования запоминаются за менеджером. Хранятся в display-сторе, сюда
  // приходят пропом, наружу уходят событием — компонент остаётся без store.
  runOptions: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['finished', 'update:runOptions'])

const available = ref(false)
const run = ref(null)
// Ошибка опроса: показываем строкой, а не прячем весь контроль.
const pollError = ref('')
const busy = ref(false)
const dialogOpen = ref(false)
// Окно-подсказка для Менеджера и Гостя: кнопка видна, но прогон не запускает.
const infoOpen = ref(false)

// Опрос прогона раз в 3 с: первый запрос сразу (immediate), скрытая вкладка
// молчит, уход со страницы останавливает опрос.
const poller = usePoller(poll, { intervalMs: 3000, immediate: true })
let lastStatus = null

const ACTIVE = ['PENDING', 'RUNNING']

const isActive = computed(() => ACTIVE.includes(run.value?.status))
const isStopped = computed(() => run.value?.status === 'STOPPED')
const isDone = computed(() => run.value?.status === 'DONE')
const isIdle = computed(() => !isActive.value && !isStopped.value)

// Описание (QWEN) — ОДНА настройка с техразделом (владелец, 29.10.2026):
// выключатель здесь и переключатель «QWEN участвует в обновлении базы» в
// Техразделе → Описание — это один и тот же флаг `in_pipeline`. Раньше галочка
// была разовой и не связанной с настройкой: выключенное описание запускалось
// снова, и приходилось останавливать прогон.
const qwenInPipeline = ref(true)
const qwenSaving = ref(false)

// Настройки описаний пишет Администратор (scope settings:write). Менеджеру
// выключатель остаётся разовым: прогон пойдёт без описаний, общая настройка
// не изменится.
const canWriteQwenSettings = computed(() => props.canWriteSettings)

// Пропускать ли описание в этом прогоне — производная от настройки.
const skipQwen = computed(() => !qwenInPipeline.value)

// «Уточнение» — хвост этапа описаний. Выбор запоминается за менеджером
// (п. 2в): следующий запуск начнётся с тем же значением.
const skipRefine = ref(Boolean(props.runOptions?.skipRefine))


// Глубина сканирования новых фото (владелец, 29.10.2026): инспектор смотрит
// файлы, изменённые за этот период. По умолчанию неделя — обходить весь том
// на каждом запуске незачем, уже зарегистрированные файлы он всё равно
// пропускает. «Все даты» нужны, когда в папке появился старый архив.
const SCAN_DEPTHS = [
  { label: '1 неделя', value: 7 },
  { label: '1 месяц', value: 30 },
  { label: '3 месяца', value: 90 },
  { label: 'Все даты', value: 0 },
]
const scanDays = ref(Number(props.runOptions?.scanDays ?? 7))
// Любое изменение этих двух настроек уходит в store — без сохранения
// «по кнопке»: человек не должен помнить, что их надо ещё где-то запомнить.
watch([scanDays, skipRefine], () => {
  emit('update:runOptions', {
    scanDays: scanDays.value,
    skipRefine: skipRefine.value,
  })
})

function stageRow(stage) {
  return (run.value?.stages || []).find((item) => item.stage === stage) || null
}

function fmt(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

// «24.10.2026 18:22» — так дата-время читается без разглядывания.
function fmtHuman(value) {
  if (!value) return ''

  const [date, time = ''] = String(value).replace('T', ' ').split(' ')
  const [year, month, day] = date.split('-')

  if (!year || !month || !day) return fmt(value)

  return `${day}.${month}.${year} ${time.slice(0, 5)}`.trim()
}

const statusText = computed(() => {
  const current = run.value

  if (!current) return ''

  if (current.status === 'DONE') {
    // Прогон закончился — сообщение показываем всегда, с датой и временем.
    // Если очереди описаний и уточнения ещё идут, это сказано прямо: прогон
    // завершён, но работа продолжается.
    return props.busy
      ? `База обновлена ${fmtHuman(current.finished_at)} · описание и уточнение идут`
      : `База обновлена ${fmtHuman(current.finished_at)}`
  }

  if (current.status === 'FAILED') {
    return `Ошибка обновления${current.message ? `: ${current.message}` : ''}`
  }

  if (current.status === 'STOPPED') {
    return `Процесс прерван ${fmt(current.finished_at)}`
  }

  // Числа стадий и этапов показываются строкой рядом с кнопкой
  // (stores/pipeline.js): здесь, в кнопке, они дублировались и расходились.
  const row = stageRow(current.stage)

  if (current.stage === 'QWEN' && row?.failed_count) {
    return `Пропущено описаний: ${row.failed_count}`
  }

  return ''
})

async function poll() {
  try {
    const data = await fetchCurrentPipeline()
    available.value = true
    pollError.value = ''

    const next = data?.run || null

    // Прогон закончился: сообщение с датой и временем. Подвал обновляем там же.
    if (next && next.status === 'DONE' && lastStatus && lastStatus !== 'DONE') {
      emit('finished')
      Notify.create({
        type: 'positive',
        icon: 'check_circle',
        message: props.busy
          ? `База обновлена ${fmtHuman(next.finished_at)} · описание и уточнение продолжаются`
          : `База обновлена ${fmtHuman(next.finished_at)}`,
        timeout: 8000,
      })
    }
    lastStatus = next?.status || null

    run.value = next
  } catch (err) {
    // Скрываем управление только тогда, когда раздела действительно нет
    // (404: супервизор не развёрнут). Одна сетевая заминка раньше прятала и
    // кнопку, и состояние прогона — теперь видно ошибку, а опрос повторяется
    // сам, прогон остаётся на месте.
    if (err?.status === 404) {
      available.value = false
      run.value = null
      return
    }

    // Показываем управление: раз ответ пришёл (пусть и с ошибкой), раздел
    // есть, и пользователю важнее видеть причину, чем пустое место.
    available.value = true
    pollError.value = err?.message || 'Нет связи с сервером'
  }
}

watch(dialogOpen, async (open) => {
  if (!open) return

  try {
    const data = await fetchQwenSettings()
    qwenInPipeline.value = data?.in_pipeline !== false

  } catch {
    // Настройки недоступны — решает сервер, выключатель остаётся включённым.
    qwenInPipeline.value = true
  }
})

async function onClick() {
  if (busy.value) return

  // Менеджеру и Гостю управление недоступно: база обновляется сама. Вместо
  // паузы или запуска показываем объяснение (владелец, 29.10.2026).
  if (!props.canRun) {
    infoOpen.value = true
    return
  }

  // Первый клик — пауза, повторный — продолжение с того же места. Окно
  // открывается отдельной кнопкой: там «Начать заново» и выключатели этапов.
  if (isActive.value) {
    await pauseRun()
    return
  }

  if (isStopped.value) {
    await continueRun()
    return
  }

  dialogOpen.value = true
}

async function pauseRun() {
  if (busy.value || !run.value) return

  busy.value = true
  try {
    await stopPipeline(run.value.run_id)
    await poll()
    Notify.create({
      type: 'info',
      icon: 'pause',
      message: 'Процесс приостановлен. Запуск с главной страницы продолжит с того же места.',
      timeout: 8000,
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось приостановить' })
  } finally {
    busy.value = false
  }
}

async function continueRun() {
  if (busy.value || !run.value) return

  busy.value = true
  try {
    await resumePipeline(run.value.run_id)
    await poll()
    Notify.create({ type: 'info', message: 'Продолжаю с того же места' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось продолжить' })
  } finally {
    busy.value = false
  }
}

/**
 * Переключить описание: меняет общую настройку (как в техразделе).
 *
 * У Администратора это тот же флаг, что в «Техраздел → Описание», поэтому
 * следующее «Обновление базы» уже пойдёт без описаний; у Менеджера настройка
 * не пишется — выключается только текущий запуск.
 */
async function setQwenInPipeline(value) {
  const next = Boolean(value)
  const previous = qwenInPipeline.value
  qwenInPipeline.value = next

  if (!canWriteQwenSettings.value) {
    Notify.create({
      type: 'info',
      message: next
        ? 'Описание пойдёт в этом прогоне; общая настройка — в техническом разделе'
        : 'Этот прогон без описаний; общая настройка — в техническом разделе',
    })
    return
  }

  qwenSaving.value = true

  try {
    const data = await updateQwenSettings({ in_pipeline: next })
    qwenInPipeline.value = data?.in_pipeline !== false
    Notify.create({
      type: 'positive',
      message: qwenInPipeline.value
        ? 'QWEN участвует в «Обновлении базы»'
        : 'QWEN выключен из прогона; «Уточнение» тоже остановлено',
    })
  } catch (err) {
    qwenInPipeline.value = previous
    Notify.create({
      type: 'negative',
      message: err.message || 'Не удалось сохранить настройку QWEN',
    })
  } finally {
    qwenSaving.value = false
  }
}

async function startNew() {
  if (!props.canRun) {
    Notify.create({ type: 'warning', message: 'Запуск обновления недоступен этой роли' })
    return
  }

  busy.value = true
  try {
    await startPipeline({
      skip_qwen: skipQwen.value,
      skip_refine: skipRefine.value,
      scan_days: scanDays.value || null,
    })
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
    await startPipeline({
      skip_qwen: skipQwen.value,
      skip_refine: skipRefine.value,
      scan_days: scanDays.value || null,
    })
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
  // Опрос прогона: первый запрос сразу, далее раз в 3 с. Скрытая вкладка
  // молчит, тики не накладываются, уход со страницы останавливает опрос —
  // раньше это был свой setInterval (второй аудит, 2.6).
  poller.start()
})
</script>

<template>
  <div v-if="available" class="pipeline-control row items-center no-wrap q-mr-sm">
    <!-- Кнопка видна всем ролям, но запускать прогон может только
         Администратор (владелец, 29.10.2026): база обновляется сама несколько
         раз в день. Менеджер и Гость видят неактивный вид и окно-подсказку. -->
    <q-btn
      flat
      dense
      no-caps
      :class="{ 'pipeline-readonly': !canRun }"
      :icon="isActive ? 'pause' : 'cloud_upload'"
      :label="'Обновление базы'"
      :disable="busy"
      :aria-disabled="!canRun ? 'true' : undefined"
      @click="onClick"
    >
      <q-tooltip>
        {{
          !canRun
            ? 'База обновляется автоматически несколько раз в день.'
            : isActive
              ? 'Нажмите, чтобы приостановить. Повторный запуск продолжит с того же места.'
              : isStopped
                ? 'Нажмите, чтобы продолжить с того же места. «Начать заново» — в кнопке с галкой справа.'
                : 'Инспекция → превью → сортировка (Дино, Гибрид) → описание → уточнение.'
        }}
      </q-tooltip>
    </q-btn>

    <q-btn
      v-if="canRun"
      flat
      dense
      round
      size="sm"
      icon="expand_more"
      class="q-ml-xs"
      @click="dialogOpen = true"
    >
      <q-tooltip>Начать заново, выключить описание или уточнение</q-tooltip>
    </q-btn>

    <span
      v-if="pollError"
      class="row items-center no-wrap text-caption text-orange-9 q-mx-xs"
    >
      <q-icon name="cloud_off" size="16px" class="q-mr-xs" />
      {{ pollError }}
    </span>

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
            Инспекция → превью → сортировка (Дино, Гибрид) → описание →
            уточнение. Тяжёлые шаги идут в фоновых воркерах, окно можно
            закрыть.
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

          <!-- Глубина сканирования новых фото: сколько назад смотреть по дате
               изменения файла. По умолчанию неделя (владелец, 29.10.2026). -->
          <q-select
            v-if="!isActive"
            v-model="scanDays"
            :options="SCAN_DEPTHS"
            dense
            outlined
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Сканировать новые фото за"
            style="max-width: 320px"
          />
          <div v-if="!isActive" class="text-caption text-grey-7">
            Инспектор смотрит только файлы, изменённые за этот период;
            зарегистрированные пропускаются. «Все даты» — когда в папке появился
            старый архив.
          </div>

          <!-- Тот же выключатель, что в техразделе («Описание»): один флаг
               in_pipeline на всю систему (владелец, 29.10.2026). -->
          <q-toggle
            v-if="!isActive"
            :model-value="qwenInPipeline"
            label="Описание (QWEN) в обновлении базы"
            dense
            :loading="qwenSaving"
            @update:model-value="setQwenInPipeline"
          />
          <!-- Второй выключатель этапа: «Уточнение» можно не запускать в этом
               прогоне, не меняя постоянную настройку этапа. -->
          <q-toggle
            v-if="!isActive"
            v-model="skipRefine"
            label="Пропустить уточнение"
            dense
          />
          <div v-if="!isActive && skipRefine" class="text-caption text-grey-7">
            «Уточнение» связывает кадры одной серии и приводит чтения к одному
            виду. Постоянный выключатель этапа — в техразделе, вкладка
            «Описание».
          </div>
          <div v-if="!isActive" class="text-caption text-grey-7">
            <template v-if="!qwenInPipeline">
              Описание выключено: прогон пойдёт без описаний и без
              «Уточнения». Дозаполнить позже — Технический раздел → «Описание»
              → «Дозаполнить за период».
              <template v-if="!canWriteQwenSettings">
                Общая настройка меняется Администратором; сейчас выключен
                только этот запуск.
              </template>
            </template>
            <template v-else>
              Без описания прогон завершится быстрее (на вашем корпусе описание
              — около 87 % времени прогона). Выключатель здесь — тот же, что в
              техразделе: следующее «Обновление базы» пойдёт без описаний.
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

    <!-- Менеджер и Гость: кнопка неактивна, по нажатию — объяснение. -->
    <q-dialog v-model="infoOpen">
      <q-card style="width: min(460px, 92vw)">
        <q-card-section class="text-subtitle1">Обновление базы</q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <div>
            База обновляется автоматически несколько раз в день. Для
            специального обновления обратитесь к Администратору.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Понятно" color="primary" v-close-popup />
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

/* Неактивный вид для ролей без права запуска. Кнопка остаётся кликабельной:
   нажатие открывает окно с объяснением, поэтому это не `disabled`. */
.pipeline-readonly {
  opacity: 0.55;
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
