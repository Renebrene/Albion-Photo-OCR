<script setup>
// Working (source) folder for INGEST: choose the folder on the server (in-app
// browser or the OS dialog), pre-check its composition and start the scan.
// The scan itself is a worker job - the browser only enqueues it.
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  backfillPreviews,
  browseFolders,
  fetchIngestFolder,
  pickFolderNative,
  runIngest,
  saveIngestFolder,
  scanIngestFolder,
} from '../api/client'
import { PERIODS, periodRange } from '../utils/periodRange'

const path = ref('')
const checkedPath = ref('')
const state = ref({
  configured: '',
  files: 0,
  photos: 0,
  videos: 0,
  media_files: 0,
  bytes: 0,
  photo_bytes: 0,
  video_bytes: 0,
  extensions: {},
  problem_count: 0,
  problems: [],
  preliminary: true,
  truncated: false,
  timed_out: false,
  exists: false,
  excluded_by_period: 0,
  in_period: 0,
  period_applied: false,
})
const busy = ref(false)
const nativeBusy = ref(false)
const jobId = ref(null)

// ---- глубина сканирования по времени --------------------------------------
// Тот же выбор периода и режима даты, что и в фильтре Грида («Дата» +
// «Период…» из utils/periodRange). Пустой период — вся папка.
const period = ref('all')
const customFrom = ref('')
const customTo = ref('')
const dateMode = ref('upload')

const dateModes = [
  { label: 'Дата загрузки', value: 'upload' },
  { label: 'Дата съёмки', value: 'capture' },
]
const periods = PERIODS

const periodBounds = computed(() =>
  periodRange(period.value, {
    customFrom: customFrom.value || null,
    customTo: customTo.value || null,
  }),
)
// «Период…» без дат ничего не ограничивает: пока границы не заданы, шлём
// запрос так же, как без периода, — иначе сервер отклонил бы пустой диапазон.
const periodActive = computed(
  () => periodBounds.value[0] !== null || periodBounds.value[1] !== null,
)
const requestPeriod = computed(() =>
  periodActive.value
    ? {
        dateFrom: periodBounds.value[0],
        dateTo: periodBounds.value[1],
        dateMode: dateMode.value,
      }
    : {},
)

// In-app folder browser (server directories only).
const browseOpen = ref(false)
const browseBusy = ref(false)
const browseError = ref('')
const browsed = ref({ path: null, parent: null, dirs: [], photos: 0 })

// Error log dialog.
const logOpen = ref(false)

const currentPathChecked = computed(() => checkedPath.value === path.value.trim())
const showStats = computed(() => Boolean(state.value.exists && currentPathChecked.value))
const canCheck = computed(() => Boolean(path.value.trim()) && !busy.value)
const canScan = computed(() => Boolean(path.value.trim()) && !busy.value)
const hasProblems = computed(() => Number(state.value.problem_count) > 0)
const extensionEntries = computed(() => Object.entries(state.value.extensions || {}))

function humanBytes(bytes) {
  const value = Number(bytes) || 0
  if (value < 1024) return `${value} Б`
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} КБ`
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} МБ`
  return `${(value / 1024 ** 3).toFixed(2)} ГБ`
}

async function load() {
  try {
    state.value = await fetchIngestFolder()
    path.value = state.value.configured || ''
    checkedPath.value = state.value.exists ? state.value.configured : ''
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function save() {
  busy.value = true
  try {
    state.value = await saveIngestFolder(path.value.trim())
    path.value = state.value.configured
    checkedPath.value = state.value.exists ? state.value.configured : ''
    Notify.create({ type: 'positive', message: 'Папка сохранена' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

async function check() {
  busy.value = true
  // Снимок пути: за время запроса пользователь может исправить строку, и тогда
  // статистика относилась бы к проверенной папке, а подписывалась бы новым
  // путём. Проверяем ровно то, что ушло на сервер.
  const target = path.value.trim()
  const period = requestPeriod.value

  try {
    const stats = await scanIngestFolder(target, period)
    state.value = { ...state.value, ...stats, configured: target, exists: true }
    checkedPath.value = target
    Notify.create({
      type: stats.problem_count ? 'warning' : 'positive',
      message:
        `Найдено: ${stats.photos} фото, ${stats.videos} видео ` +
        `(${humanBytes(stats.bytes)})` +
        (stats.problem_count ? `, проблем: ${stats.problem_count}` : '') +
        (stats.period_applied ? `, в периоде: ${stats.in_period}` : ''),
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

async function start() {
  busy.value = true
  // Тот же снимок пути: инспекция должна обойти именно то, что показано в
  // подтверждении, а не то, что успели дописать в поле.
  const target = path.value.trim() || null

  try {
    const result = await runIngest(target, requestPeriod.value)
    jobId.value = result.job_id
    const depth = periodActive.value
      ? ` (${dateMode.value === 'capture' ? 'дата съёмки' : 'дата загрузки'}: ` +
        `${periodBounds.value[0] || '…'} — ${periodBounds.value[1] || '…'})`
      : ''
    Notify.create({
      type: result.skipped ? 'warning' : 'positive',
      message: result.skipped
        ? 'Обход этой папки уже в очереди'
        : `Задание инспектирования поставлено в очередь: ${result.job_id}${depth}`,
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

/**
 * Пересоздать превью для фото, у которых файлов нет.
 *
 * Работает по photo_id (путь к оригиналу берётся из базы), рабочая папка не
 * сканируется. Фото, чей оригинал недоступен, не удаляются и не меняются —
 * сервер сообщает их число отдельно.
 */
async function rebuildPreviews() {
  busy.value = true
  try {
    const result = await backfillPreviews({ limit: 500 })
    const parts = [
      `без файлов превью: ${result.selected}`,
      `заданий: ${result.queued}`,
    ]

    if (result.already_active) parts.push(`уже в очереди: ${result.already_active}`)

    if (result.originals_missing) {
      Notify.create({
        type: 'warning',
        message:
          `${parts.join(', ')}. Оригинал недоступен у ${result.originals_missing} фото — ` +
          'их записи и превью сохранены, файл нужно вернуть на том.',
      })
    } else {
      Notify.create({
        type: result.queued ? 'positive' : 'info',
        message: parts.join(', '),
      })
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

// ---- выбор папки ----------------------------------------------------------

async function openBrowser() {
  browseOpen.value = true
  await loadBrowse(path.value.trim() || null)
}

async function loadBrowse(target) {
  browseBusy.value = true
  browseError.value = ''
  try {
    browsed.value = await browseFolders(target)
  } catch (err) {
    browseError.value = err.message
  } finally {
    browseBusy.value = false
  }
}

async function chooseBrowsed() {
  if (!browsed.value.path) return
  path.value = browsed.value.path
  browseOpen.value = false
  await save()
}

async function pickNative() {
  nativeBusy.value = true
  try {
    const result = await pickFolderNative()
    if (result?.path) {
      path.value = result.path
      await save()
    }
  } catch (err) {
    Notify.create({ type: 'warning', message: err.message })
  } finally {
    nativeBusy.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card flat bordered>
    <q-card-section class="row q-col-gutter-md">
      <!-- Слева: выбор папки и действия -->
      <div class="col-12 col-md-7">
        <div class="text-subtitle2 q-mb-sm">Инспектор: папка с рабочими фотографиями</div>

        <q-input
          v-model="path"
          dense
          outlined
          label="Путь на сервере"
          @keyup.enter="save"
        >
          <template #append>
            <q-btn
              dense
              flat
              icon="save"
              :loading="busy"
              :disable="!path.trim()"
              @click="save"
            >
              <q-tooltip>Сохранить как рабочую папку</q-tooltip>
            </q-btn>
          </template>
        </q-input>

        <div class="row q-gutter-sm q-mt-sm">
          <q-btn
            dense
            outline
            color="primary"
            icon="folder_open"
            label="Выбрать на сервере"
            @click="openBrowser"
          />
          <q-btn
            dense
            outline
            color="primary"
            icon="computer"
            label="Системное окно"
            :loading="nativeBusy"
            @click="pickNative"
          >
            <q-tooltip>
              Открывает диалог на машине сервера (нужен SCENE_NATIVE_PICKER=1)
            </q-tooltip>
          </q-btn>
          <q-btn
            dense
            color="primary"
            icon="fact_check"
            label="Проверить"
            :loading="busy"
            :disable="!canCheck"
            @click="check"
          />
          <q-btn
            dense
            color="secondary"
            icon="play_arrow"
            label="Инспектировать"
            :loading="busy"
            :disable="!canScan"
            @click="start"
          >
            <q-tooltip>
              Запустить инспектирование: файлы проверяются декодером и вносятся в базу
            </q-tooltip>
          </q-btn>
        </div>

        <!-- Глубина сканирования: те же «Дата» и «Период…», что в фильтре Грида -->
        <div class="row q-gutter-sm q-mt-sm items-center">
          <q-select
            v-model="dateMode"
            :options="dateModes"
            dense
            outlined
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Дата"
            style="min-width: 140px"
          >
            <q-tooltip>
              «Дата загрузки» — по дате самого файла (файл вне периода не
              читается). «Дата съёмки» — по EXIF: файл всё равно читается,
              но в базу попадут только снимки за период.
            </q-tooltip>
          </q-select>
          <q-select
            v-model="period"
            :options="periods"
            dense
            outlined
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Период"
            style="min-width: 150px"
          />
          <template v-if="period === 'custom'">
            <q-input
              v-model="customFrom"
              dense
              outlined
              type="date"
              label="с"
              style="max-width: 150px"
            />
            <q-input
              v-model="customTo"
              dense
              outlined
              type="date"
              label="по"
              style="max-width: 150px"
            />
          </template>
        </div>

        <div class="text-caption text-grey-7 q-mt-sm">
          Фото и видео берутся из этой же папки (обход рекурсивный, включая
          подпапки); исходники только читаются. «Проверить» — предварительная
          оценка состава (размеры и расширения без декодирования). Для папки на
          своём ПК укажите её сетевой/смонтированный путь на сервере.
          <span v-if="periodActive">
            Глубина сканирования: {{ dateMode === 'capture' ? 'по дате съёмки' : 'по дате загрузки' }}
            ({{ periodBounds[0] || '…' }} — {{ periodBounds[1] || '…' }}); счёт
            в «Проверить» — по дате файла.
          </span>
        </div>

        <!-- Итог проверки -->
        <q-banner
          v-if="showStats && !hasProblems"
          dense
          rounded
          class="bg-green-1 text-positive q-mt-md"
        >
          <div class="text-weight-medium">Всё ОК</div>
          <div class="text-caption">
            Проверено: {{ state.photos }} фото, {{ state.videos }} видео.
            Переходите к этапу «Сортировка».
          </div>
        </q-banner>

        <q-banner
          v-else-if="showStats && hasProblems"
          dense
          rounded
          class="bg-orange-1 text-dark q-mt-md"
        >
          <div class="text-weight-medium">
            ОК, но есть ошибки: {{ state.problem_count }}
          </div>
          <div class="text-caption q-mb-xs">
            Такие файлы будут пропущены при инспектировании. Можно пересканировать
            папку или всё равно запустить инспектирование, а затем перейти к этапу
            «Сортировка».
          </div>
          <div class="row q-gutter-sm">
            <q-btn
              dense
              flat
              size="sm"
              color="dark"
              icon="receipt_long"
              label="Лог ошибок"
              @click="logOpen = true"
            />
            <q-btn
              dense
              flat
              size="sm"
              color="dark"
              icon="refresh"
              label="Пересканировать"
              :loading="busy"
              @click="check"
            />
            <q-btn
              dense
              color="secondary"
              size="sm"
              icon="skip_next"
              label="Пропустить и инспектировать"
              :loading="busy"
              @click="start"
            />
          </div>
        </q-banner>

        <div v-if="jobId" class="text-caption text-grey-8 q-mt-sm">
          Задание №{{ jobId }} выполняется воркером. Уже зарегистрированные файлы
          (совпадение имени и размера) пропускаются без хеширования.
        </div>

        <div class="text-caption text-grey-7 q-mt-sm">
          Фоновый вотчер не подключён: обход запускается кнопкой или командой
          <code>scene-fingerprint ingest &lt;папка&gt;</code>.
        </div>

        <div class="row q-gutter-sm q-mt-sm items-center">
          <q-btn
            dense
            outline
            color="primary"
            icon="image"
            label="Пересоздать превью"
            :loading="busy"
            @click="rebuildPreviews"
          >
            <q-tooltip>
              Поставить задания PREVIEW для фото, у которых файлы превью
              отсутствуют. Работает по photo_id, папка не сканируется; фото с
              недоступным оригиналом не трогаются.
            </q-tooltip>
          </q-btn>
          <span class="text-caption text-grey-7">
            Пригодится после переноса хранилища или очистки производных файлов.
          </span>
        </div>
      </div>

      <!-- Справа: блок статистики -->
      <div class="col-12 col-md-5">
        <q-card flat bordered class="fit">
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">Статистика папки</div>

            <template v-if="showStats">
              <div class="row q-col-gutter-sm">
                <div class="col-6">
                  <div class="text-caption text-grey">Фото</div>
                  <div class="text-h6">{{ state.photos }}</div>
                </div>
                <div class="col-6">
                  <div class="text-caption text-grey">Видео</div>
                  <div class="text-h6">{{ state.videos }}</div>
                </div>
                <div class="col-6">
                  <div class="text-caption text-grey">Суммарный вес</div>
                  <div>{{ humanBytes(state.bytes) }}</div>
                </div>
                <div class="col-6">
                  <div class="text-caption text-grey">С ошибками</div>
                  <div :class="hasProblems ? 'text-orange-9' : ''">
                    {{ state.problem_count }}
                  </div>
                </div>
                <div v-if="state.period_applied" class="col-6">
                  <div class="text-caption text-grey">В периоде</div>
                  <div>{{ state.in_period }}</div>
                </div>
                <div v-if="state.period_applied" class="col-6">
                  <div class="text-caption text-grey">Вне периода</div>
                  <div class="text-grey-7">{{ state.excluded_by_period }}</div>
                </div>
              </div>

              <div v-if="extensionEntries.length" class="q-mt-sm">
                <div class="text-caption text-grey q-mb-xs">Расширения</div>
                <div class="row q-gutter-xs">
                  <q-chip
                    v-for="[ext, count] in extensionEntries"
                    :key="ext"
                    dense
                    size="sm"
                    color="grey-3"
                    text-color="grey-9"
                  >
                    {{ ext }}: {{ count }}
                  </q-chip>
                </div>
              </div>

              <q-btn
                v-if="hasProblems"
                dense
                flat
                size="sm"
                color="orange-9"
                icon="receipt_long"
                label="Лог ошибок"
                class="q-mt-sm"
                @click="logOpen = true"
              />

              <q-banner
                v-if="state.timed_out"
                dense
                class="bg-orange-1 text-dark q-mt-sm"
              >
                Проверка остановлена по времени — показаны не все файлы.
                Сканирование продолжит полный обход.
              </q-banner>
              <q-banner
                v-else-if="state.truncated"
                dense
                class="bg-orange-1 text-dark q-mt-sm"
              >
                Достигнут лимит предварительного просмотра — показаны не все
                файлы.
              </q-banner>
            </template>

            <div v-else class="text-caption text-grey-7">
              Выберите папку и нажмите «Проверить» — здесь появятся количество
              фото и видео, суммарный вес, расширения и файлы с ошибками.
            </div>
          </q-card-section>
        </q-card>
      </div>
    </q-card-section>

    <!-- Выбор папки на сервере -->
    <q-dialog v-model="browseOpen">
      <q-card style="min-width: 560px; max-width: 92vw">
        <q-card-section class="row items-center">
          <div class="text-subtitle1 col ellipsis">
            {{ browsed.path || 'Корневые папки' }}
          </div>
          <q-btn
            v-if="browsed.parent"
            dense
            flat
            icon="arrow_upward"
            @click="loadBrowse(browsed.parent)"
          >
            <q-tooltip>На уровень выше</q-tooltip>
          </q-btn>
        </q-card-section>
        <q-separator />

        <q-card-section style="max-height: 60vh; overflow: auto">
          <q-banner v-if="browseError" dense class="bg-red-1 text-negative">
            {{ browseError }}
          </q-banner>
          <q-list v-else dense>
            <q-item
              v-for="dir in browsed.dirs"
              :key="dir.path"
              clickable
              @click="loadBrowse(dir.path)"
            >
              <q-item-section avatar>
                <q-icon name="folder" color="amber-8" />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ dir.name }}</q-item-label>
                <q-item-label caption>{{ dir.path }}</q-item-label>
              </q-item-section>
              <q-item-section side class="text-caption text-grey">
                {{ dir.photos }} фото
              </q-item-section>
            </q-item>
            <q-item v-if="!browsed.dirs.length">
              <q-item-section class="text-grey">Подпапок нет</q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn
            color="primary"
            label="Выбрать эту папку"
            :disable="!browsed.path"
            :loading="browseBusy"
            @click="chooseBrowsed"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Лог ошибок проверки -->
    <q-dialog v-model="logOpen">
      <q-card style="min-width: 620px; max-width: 94vw">
        <q-card-section class="text-subtitle1">
          Ошибки проверки ({{ state.problem_count }})
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow: auto">
          <q-markup-table dense flat bordered>
            <thead>
              <tr>
                <th class="text-left">Файл</th>
                <th class="text-left">Причина</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="problem in state.problems" :key="`${problem.filename}-${problem.reason}`">
                <td>{{ problem.filename }}</td>
                <td>{{ problem.reason }}</td>
              </tr>
              <tr v-if="!state.problems?.length">
                <td colspan="2" class="text-center text-grey">Список пуст</td>
              </tr>
            </tbody>
          </q-markup-table>
          <div v-if="state.timed_out || state.truncated" class="text-caption text-grey-7 q-mt-sm">
            Список неполный: проверка ограничена по времени/количеству. Полный
            результат даст сканирование.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-card>
</template>
