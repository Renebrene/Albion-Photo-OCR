<script setup>
// Fingerprint management window (schema/023).
//
// The vectors live on disk; this table mirrors them from
// data/fingerprints/*/metadata.json and adds the human layer: a name, a
// description, the source folder, archiving and a version journal.
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  browseFolders,
  buildFingerprint,
  fetchFingerprintRegistry,
  fetchFingerprintVersions,
  fetchJob,
  pickFolderNative,
  syncFingerprints,
  updateFingerprint,
} from '../api/client'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const isAdmin = computed(() => session.user?.role === 'Администратор')

const items = ref([])
const loading = ref(false)
const syncing = ref(false)
const error = ref(null)

// edit dialog
const editOpen = ref(false)
const editTarget = ref(null)

// versions dialog
const versionsOpen = ref(false)
const versionsTarget = ref(null)
const versions = ref([])
const versionsLoading = ref(false)

async function load() {
  loading.value = true
  try {
    items.value = (await fetchFingerprintRegistry()).items || []
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// ---- build / rebuild ------------------------------------------------------

const buildOpen = ref(false)
const buildBusy = ref(false)
const buildJob = ref(null) // { id, status, result, error }
const buildForm = ref({
  fingerprint_id: '',
  folder: '',
  max_photos: 30,
  replace: true,
})

// folder picker
const browseOpen = ref(false)
const browseBusy = ref(false)
const browsed = ref({ path: null, parent: null, dirs: [], photos: 0 })
const browseError = ref('')

const PHOTO_CHOICES = [
  { label: '30 фото (норма 20–30)', value: 30 },
  { label: '20 фото', value: 20 },
  { label: 'все фото в папке', value: 0 },
]

function openBuild(item = null) {
  buildForm.value = {
    fingerprint_id: item?.fingerprint_id || '',
    folder: item?.source_folder || '',
    max_photos: 30,
    replace: true,
  }
  buildJob.value = null
  buildOpen.value = true
}

async function loadBrowse(path) {
  browseBusy.value = true
  browseError.value = ''

  try {
    browsed.value = await browseFolders(path)
  } catch (err) {
    browseError.value = err.message
  } finally {
    browseBusy.value = false
  }
}

function openBrowser() {
  browseOpen.value = true
  loadBrowse(buildForm.value.folder || null)
}

function chooseFolder(path) {
  buildForm.value.folder = path
  browseOpen.value = false
}

async function pickNative() {
  browseBusy.value = true

  try {
    const result = await pickFolderNative()
    buildForm.value.folder = result.path
    browseOpen.value = false
  } catch (err) {
    browseError.value = err.message
  } finally {
    browseBusy.value = false
  }
}

async function startBuild() {
  const form = buildForm.value

  if (!form.fingerprint_id.trim()) {
    Notify.create({ type: 'warning', message: 'Укажите ID слепка' })
    return
  }

  if (!form.folder.trim()) {
    Notify.create({ type: 'warning', message: 'Выберите папку с фотографиями' })
    return
  }

  buildBusy.value = true
  buildJob.value = null

  try {
    const started = await buildFingerprint({
      fingerprint_id: form.fingerprint_id.trim(),
      folder: form.folder.trim(),
      max_photos: form.max_photos || null,
      replace: form.replace,
    })

    buildJob.value = { id: started.job_id, status: 'PENDING' }

    Notify.create({
      type: started.skipped ? 'warning' : 'positive',
      message: started.skipped
        ? 'Сборка этого слепка уже в очереди'
        : `Задание сборки №${started.job_id} (фото в папке: ${started.photos})`,
    })

    if (!started.skipped) {
      await pollBuild(started.job_id)
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    buildBusy.value = false
  }
}

async function pollBuild(jobId) {
  // DINO over 20-40 photos takes a while; poll a few minutes.
  for (let attempt = 0; attempt < 120; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000))
    const job = await fetchJob(jobId)
    buildJob.value = { id: jobId, status: job.status }

    if (job.status === 'DONE') {
      buildJob.value.result = job.result
      Notify.create({
        type: 'positive',
        message: `Слепок собран: ${job.result?.images} фото`,
      })
      await load()
      return
    }

    if (job.status === 'FAILED' || job.status === 'CANCELLED') {
      buildJob.value.error = job.error_message || job.status
      Notify.create({ type: 'negative', message: `Сборка: ${buildJob.value.error}` })
      return
    }
  }
}

onMounted(load)

async function sync() {
  syncing.value = true
  try {
    const result = await syncFingerprints()
    Notify.create({
      type: 'positive',
      message:
        `Синхронизировано: ${result.on_disk} на диске, ` +
        `новых ${result.created.length}, версий +${result.versions_added.length}`,
    })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    syncing.value = false
  }
}

function openEdit(item) {
  editTarget.value = { ...item }
  editOpen.value = true
}

async function saveEdit() {
  const target = editTarget.value

  try {
    await updateFingerprint(target.fingerprint_id, {
      display_name: target.display_name,
      description: target.description,
      source_folder: target.source_folder,
      active: target.active,
    })
    editOpen.value = false
    Notify.create({ type: 'positive', message: 'Слепок сохранён' })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function toggleActive(item, value) {
  try {
    await updateFingerprint(item.fingerprint_id, { active: value })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
    await load()
  }
}

async function openVersions(item) {
  versionsTarget.value = item
  versions.value = []
  versionsOpen.value = true
  versionsLoading.value = true

  try {
    versions.value = (
      await fetchFingerprintVersions(item.fingerprint_id)
    ).items
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    versionsLoading.value = false
  }
}

function addressLabel(item) {
  const address = item.address
  if (!address) return '—'
  return address.simple_address || address.legal_address || '—'
}

function day(value) {
  return value ? String(value).slice(0, 10) : '—'
}
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">
        Слепки ({{ items.length }})
      </div>
      <q-btn v-if="isAdmin" dense color="primary" icon="add" label="Создать слепок"
        @click="openBuild()">
        <q-tooltip>
          Выбрать папку с фотографиями и собрать (или пересобрать) слепок
        </q-tooltip>
      </q-btn>
      <q-btn v-if="isAdmin" dense flat icon="sync" label="Синхронизировать с диском"
        :loading="syncing" @click="sync">
        <q-tooltip>
          Прочитать data/fingerprints/*/metadata.json и обновить реестр
        </q-tooltip>
      </q-btn>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load">
        <q-tooltip>Обновить</q-tooltip>
      </q-btn>
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <q-table
      :rows="items"
      :loading="loading"
      row-key="fingerprint_id"
      flat
      bordered
      dense
      :pagination="{ rowsPerPage: 0 }"
      :columns="[
        { name: 'id', label: 'ID', field: 'fingerprint_id', align: 'left', sortable: true },
        { name: 'name', label: 'Имя', field: 'display_name', align: 'left' },
        { name: 'address', label: 'Адрес', field: (row) => addressLabel(row), align: 'left' },
        { name: 'images', label: 'Фото', field: 'images_count', align: 'right', sortable: true },
        { name: 'version', label: 'Версия', field: 'algorithm_version', align: 'left' },
        { name: 'updated', label: 'Версия обновлена', field: (row) => day(row.current_version && row.current_version.created_at), align: 'left' },
        { name: 'disk', label: 'На диске', field: 'on_disk', align: 'center' },
        { name: 'active', label: 'Активен', field: 'active', align: 'center' },
        { name: 'actions', label: '', field: 'fingerprint_id', align: 'right' },
      ]"
      no-data-label="Реестр пуст — нажмите «Синхронизировать с диском»"
    >
      <template #body-cell-disk="props">
        <q-td :props="props">
          <q-icon
            :name="props.row.on_disk ? 'check_circle' : 'error'"
            :color="props.row.on_disk ? 'positive' : 'negative'"
            size="18px"
          >
            <q-tooltip>
              {{ props.row.on_disk ? 'Векторы найдены' : 'Векторов нет на диске' }}
            </q-tooltip>
          </q-icon>
        </q-td>
      </template>

      <template #body-cell-active="props">
        <q-td :props="props">
          <q-toggle
            :model-value="props.row.active"
            dense
            :disable="!isAdmin"
            @update:model-value="(value) => toggleActive(props.row, value)"
          />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn dense flat icon="history" @click="openVersions(props.row)">
            <q-tooltip>Версии ({{ props.row.images_count }} фото в текущей)</q-tooltip>
          </q-btn>
          <q-btn dense flat icon="edit" :disable="!isAdmin" @click="openEdit(props.row)">
            <q-tooltip>Имя, описание, папка-источник</q-tooltip>
          </q-btn>
          <q-btn v-if="isAdmin" dense flat icon="refresh" @click="openBuild(props.row)">
            <q-tooltip>Пересобрать из папки</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <div class="text-caption text-grey q-mt-sm">
      Векторы слепков лежат в <code>data/fingerprints/&lt;id&gt;</code>; реестр
      только описывает их. Адрес сопоставляется во вкладке «Адреса».
    </div>

    <!-- edit -->
    <q-dialog v-model="editOpen">
      <q-card style="min-width: 420px; max-width: 92vw">
        <q-card-section class="text-subtitle1">
          Слепок {{ editTarget?.fingerprint_id }}
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="editTarget.display_name"
            dense
            outlined
            label="Имя слепка"
          />
          <q-input
            v-model="editTarget.description"
            dense
            outlined
            type="textarea"
            autogrow
            label="Описание"
          />
          <q-input
            v-model="editTarget.source_folder"
            dense
            outlined
            label="Папка-источник эталонных фото"
            hint="например data/input/78"
          />
          <div class="row items-center">
            <q-toggle v-model="editTarget.active" dense label="Активен" />
            <q-space />
            <span class="text-caption text-grey">
              Фото: {{ editTarget?.images_count }} · версия
              {{ editTarget?.algorithm_version }}
            </span>
          </div>
          <div class="text-caption text-grey">
            Размер подборки: 20–30 фото (решение владельца); больше — только для
            адресов, которые путаются с соседними.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Сохранить" @click="saveEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- versions -->
    <q-dialog v-model="versionsOpen">
      <q-card style="min-width: 560px; max-width: 94vw; max-height: 88vh">
        <q-card-section class="text-subtitle1">
          Версии {{ versionsTarget?.fingerprint_id }}
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 65vh; overflow: auto">
          <div v-if="versionsLoading">
            <q-spinner-dots color="primary" size="28px" />
          </div>

          <q-list v-else separator>
            <q-item v-for="version in versions" :key="version.version_id">
              <q-item-section>
                <q-item-label>
                  {{ version.images_count }} фото · версия
                  {{ version.algorithm_version || '—' }}
                  <q-badge v-if="version.is_current" color="positive" class="q-ml-xs">
                    текущая
                  </q-badge>
                </q-item-label>
                <q-item-label caption>
                  Создана: {{ day(version.created_at) }}
                  <template v-if="version.source_folder">
                    · источник: {{ version.source_folder }}
                  </template>
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-expansion-item
                  dense
                  :label="`имена файлов (${version.image_names.length})`"
                  style="max-width: 220px"
                >
                  <div class="text-caption" style="max-height: 200px; overflow: auto">
                    <div v-for="name in version.image_names" :key="name">
                      {{ name }}
                    </div>
                  </div>
                </q-expansion-item>
              </q-item-section>
            </q-item>
            <q-item v-if="!versions.length">
              <q-item-section class="text-caption text-grey">
                Версий нет
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- build / rebuild -->
    <q-dialog v-model="buildOpen">
      <q-card style="min-width: 560px; max-width: 94vw">
        <q-card-section class="text-subtitle1">Создать / пересобрать слепок</q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="buildForm.fingerprint_id"
            dense
            outlined
            label="ID слепка"
            hint="например 78_v33 — пересборка заменит векторы, старая версия останется в журнале"
          />

          <div class="row items-center q-gutter-sm">
            <q-input
              v-model="buildForm.folder"
              dense
              outlined
              class="col"
              label="Папка с фотографиями"
              hint="Папки по умолчанию нет — берутся файлы из выбранной; исходники только читаются"
            />
            <q-btn dense color="secondary" icon="folder_open" label="Выбрать папку"
              @click="openBrowser" />
          </div>

          <div class="row items-center q-gutter-sm">
            <q-select
              v-model="buildForm.max_photos"
              :options="PHOTO_CHOICES"
              dense
              outlined
              emit-value
              map-options
              option-label="label"
              option-value="value"
              label="Сколько фото взять"
              style="min-width: 230px"
            />
            <q-toggle v-model="buildForm.replace" dense
              label="Пересобрать, если слепок уже есть" />
          </div>

          <div class="text-caption text-grey">
            Норма — 20–30 фото (замер: `docs/fingerprint_size_experiment.md`).
            Подвыборка берётся шагом по списку, файлы не копируются. После
            сборки оригиналы не нужны: сохраняются векторы, а в базе — имена
            фото и даты съёмок.
          </div>

          <div v-if="buildJob" class="q-mt-sm">
            <q-banner :class="buildJob.status === 'DONE' ? 'bg-green-1' : (buildJob.error ? 'bg-red-1 text-negative' : 'bg-blue-1')">
              Задание №{{ buildJob.id }}: {{ buildJob.status }}
              <template v-if="buildJob.result">
                · собрано из {{ buildJob.result.images }} фото
              </template>
              <template v-if="buildJob.error"> · {{ buildJob.error }}</template>
            </q-banner>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Закрыть" v-close-popup />
          <q-btn
            color="primary"
            label="Собрать"
            :loading="buildBusy"
            :disable="!buildForm.fingerprint_id.trim() || !buildForm.folder.trim()"
            @click="startBuild"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- folder browser (server side) -->
    <q-dialog v-model="browseOpen">
      <q-card style="min-width: 620px; max-width: 94vw; max-height: 88vh">
        <q-card-section class="row items-center">
          <div class="text-subtitle1 col">
            Выбор папки на сервере
          </div>
          <q-btn dense flat icon="desktop_windows" label="Системный диалог"
            :loading="browseBusy" @click="pickNative">
            <q-tooltip>
              Открыть окно выбора папки на машине сервера
              (нужен включённый SCENE_NATIVE_PICKER)
            </q-tooltip>
          </q-btn>
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 60vh; overflow: auto">
          <div v-if="browseError" class="text-negative text-caption q-mb-sm">
            {{ browseError }}
          </div>

          <div class="row items-center q-gutter-sm q-mb-sm">
            <q-btn dense flat icon="arrow_upward" :disable="!browsed.parent"
              @click="loadBrowse(browsed.parent)">
              <q-tooltip>Наверх</q-tooltip>
            </q-btn>
            <span class="text-caption ellipsis">{{ browsed.path || 'разрешённые корни' }}</span>
            <q-badge color="grey-7">фото здесь: {{ browsed.photos }}</q-badge>
            <q-space />
            <q-btn v-if="browsed.path" dense color="primary" label="Взять эту папку"
              @click="chooseFolder(browsed.path)" />
          </div>

          <q-list dense separator>
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
                <div class="ellipsis">{{ dir.name }}</div>
              </q-item-section>
              <q-item-section side>
                <span class="text-caption text-grey">{{ dir.photos }} фото</span>
                <q-btn dense flat icon="check" @click.stop="chooseFolder(dir.path)">
                  <q-tooltip>Взять эту папку</q-tooltip>
                </q-btn>
              </q-item-section>
            </q-item>
            <q-item v-if="!browsed.dirs.length">
              <q-item-section class="text-caption text-grey">
                Подпапок нет
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>
