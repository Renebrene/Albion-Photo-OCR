<script setup>
// Working (source) folder for INGEST: choose the folder on the server (in-app
// browser or the OS dialog), pre-check its composition and start the scan.
// The scan itself is a worker job - the browser only enqueues it.
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  browseFolders,
  fetchIngestFolder,
  pickFolderNative,
  runIngest,
  saveIngestFolder,
  scanIngestFolder,
} from '../api/client'

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
})
const busy = ref(false)
const nativeBusy = ref(false)
const jobId = ref(null)

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
  try {
    const stats = await scanIngestFolder(path.value.trim())
    state.value = { ...state.value, ...stats, configured: path.value.trim(), exists: true }
    checkedPath.value = path.value.trim()
    Notify.create({
      type: stats.problem_count ? 'warning' : 'positive',
      message:
        `Найдено: ${stats.photos} фото, ${stats.videos} видео ` +
        `(${humanBytes(stats.bytes)})` +
        (stats.problem_count ? `, проблем: ${stats.problem_count}` : ''),
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

async function start() {
  busy.value = true
  try {
    const result = await runIngest(path.value.trim() || null)
    jobId.value = result.job_id
    Notify.create({
      type: result.skipped ? 'warning' : 'positive',
      message: result.skipped
        ? 'Обход этой папки уже в очереди'
        : `Задание ingest поставлено в очередь: ${result.job_id}`,
    })
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
        <div class="text-subtitle2 q-mb-sm">Папка с рабочими фотографиями</div>

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
            label="Сканировать"
            :loading="busy"
            :disable="!canScan"
            @click="start"
          >
            <q-tooltip>
              Запустить ingest: файлы проверяются декодером и вносятся в базу
            </q-tooltip>
          </q-btn>
        </div>

        <div class="text-caption text-grey-7 q-mt-sm">
          Фото и видео берутся из этой же папки (обход рекурсивный, включая
          подпапки); исходники только читаются. «Проверить» — предварительная
          оценка состава (размеры и расширения без декодирования). Для папки на
          своём ПК укажите её сетевой/смонтированный путь на сервере.
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
            Такие файлы будут пропущены при сканировании. Можно пересканировать
            папку или всё равно запустить ingest, а затем перейти к этапу
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
              label="Пропустить и сканировать"
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
