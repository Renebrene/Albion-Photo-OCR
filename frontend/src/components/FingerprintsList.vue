<script setup>
// Fingerprint management window (schema/023).
//
// The vectors live on disk; this table mirrors them from
// data/fingerprints/*/metadata.json and adds the human layer: a name, a
// description, the source folder, archiving and a version journal.
import { computed, onMounted, reactive, ref } from 'vue'
import { Notify } from 'quasar'

import AuthImage from './AuthImage.vue'
import {
  browseFolders,
  buildFingerprint,
  buildFingerprintBatch,
  cancelJob,
  deleteFingerprint,
  fetchAddressDirectory,
  fetchFingerprintBatch,
  fetchFingerprintRegistry,
  fetchFingerprintVersions,
  fetchJob,
  fingerprintPreviewUrl,
  pauseJob,
  pickFolderNative,
  resumeJob,
  setFingerprintAddress,
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

// delete dialog (admin only; destroys the registry row and vector files)
const deleteOpen = ref(false)
const deleteTarget = ref(null)
const deleteBusy = ref(false)
const deleteError = ref(null)

function openDelete(item) {
  deleteTarget.value = item
  deleteError.value = null
  deleteOpen.value = true
}

async function doDelete() {
  if (!deleteTarget.value || deleteBusy.value) return

  deleteBusy.value = true
  deleteError.value = null

  try {
    const result = await deleteFingerprint(deleteTarget.value.fingerprint_id)
    deleteOpen.value = false
    Notify.create({
      type: result.error ? 'warning' : 'positive',
      message: result.error
        ? `Реестр очищен, файлы остались: ${result.error}`
        : `Слепок удалён, файлов: ${result.files_removed}`,
    })
    await load()
  } catch (err) {
    deleteError.value = err.message || 'Не удалось удалить слепок'
  } finally {
    deleteBusy.value = false
  }
}

// versions dialog
const versionsOpen = ref(false)
const versionsTarget = ref(null)
const versions = ref([])
const versionsLoading = ref(false)

async function load() {
  loading.value = true
  try {
    items.value = (await fetchFingerprintRegistry()).items || []
    // A rebuilt fingerprint gets a new montage: forget the old failures.
    previewFailed.clear()
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

// Сборка идёт прямо сейчас: показываем паузу/отмену вместо кнопки запуска.
const runningBuild = computed(() =>
  ['PENDING', 'RUNNING', 'PAUSED'].includes(buildJob.value?.status),
)

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

// ---- pause / resume / cancel of a running build --------------------------

async function pauseBuild() {
  if (!buildJob.value?.id) return

  try {
    await pauseJob(buildJob.value.id)
    Notify.create({ type: 'info', message: 'Сборка поставлена на паузу' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function resumeBuild() {
  if (!buildJob.value?.id) return

  try {
    await resumeJob(buildJob.value.id)
    Notify.create({ type: 'info', message: 'Сборка продолжена' })
    await pollBuild(buildJob.value.id)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function cancelBuild() {
  if (!buildJob.value?.id) return

  try {
    await cancelJob(buildJob.value.id)
    Notify.create({ type: 'info', message: 'Сборка отменена' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

// ---- batch: many fingerprints over several workers -----------------------

const batchOpen = ref(false)
const batchBusy = ref(false)
const batchParent = ref('')
const batchParentPath = ref('') // родитель текущего списка, для кнопки «вверх»
const batchDirs = ref([])
const batchSelected = ref([])
// Пользовательский ID на папку; пусто — берётся <имя_папки>_v33.
const batchIds = ref({})
const batchMaxPhotos = ref(30)
const batchState = ref(null) // агрегат от /v1/fingerprints/batch/{id}

function openBatch() {
  batchParent.value = ''
  batchParentPath.value = ''
  batchDirs.value = []
  batchSelected.value = []
  batchIds.value = {}
  batchState.value = null
  batchOpen.value = true
}

function defaultBatchId(path) {
  return `${path.split('/').filter(Boolean).pop()}_v33`
}

function batchIdFor(path) {
  return batchIds.value[path] ?? defaultBatchId(path)
}

function setBatchId(path, value) {
  batchIds.value = { ...batchIds.value, [path]: String(value ?? '') }
}

async function loadBatchDirs(path) {
  batchBusy.value = true

  try {
    const result = await browseFolders(path || null)
    batchParent.value = result.path || ''
    batchParentPath.value = result.parent || ''
    // Every sub-folder is listed: folders without photos in them must stay
    // visible, otherwise there is no way down to data/input/78.
    batchDirs.value = result.dirs || []
    batchSelected.value = []
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    batchBusy.value = false
  }
}

// Folders with photos are the ones worth ticking; the rest are the path.
function selectDirsWithPhotos() {
  batchSelected.value = batchDirs.value
    .filter((dir) => dir.photos > 0)
    .map((dir) => dir.path)
}

async function pickBatchParent() {
  try {
    const result = await pickFolderNative()
    await loadBatchDirs(result.path)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

function toggleBatchDir(path) {
  const index = batchSelected.value.indexOf(path)

  if (index === -1) batchSelected.value.push(path)
  else batchSelected.value.splice(index, 1)
}

async function startBatch() {
  if (!batchSelected.value.length) {
    Notify.create({ type: 'warning', message: 'Отметьте папки' })
    return
  }

  const items = batchSelected.value.map((path) => ({
    fingerprint_id: batchIdFor(path).trim(),
    folder: path,
  }))
  const ids = items.map((item) => item.fingerprint_id)

  if (ids.some((id) => !/^[A-Za-z0-9._-]{1,64}$/.test(id))) {
    Notify.create({
      type: 'warning',
      message: 'ID может содержать буквы, цифры, точку, дефис и подчёркивание',
    })
    return
  }

  if (new Set(ids).size !== ids.length) {
    Notify.create({ type: 'warning', message: 'ID слепков не должны повторяться' })
    return
  }

  batchBusy.value = true

  try {
    const started = await buildFingerprintBatch({
      items,
      max_photos: batchMaxPhotos.value || null,
      replace: true,
    })

    Notify.create({
      type: started.errors.length ? 'warning' : 'positive',
      message:
        `Заданий поставлено: ${started.jobs.length}` +
        (started.errors.length ? `, отклонено: ${started.errors.length}` : ''),
    })

    await pollBatch(started.batch_id)
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    batchBusy.value = false
  }
}

async function pollBatch(batchId) {
  for (let attempt = 0; attempt < 600; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000))
    batchState.value = await fetchFingerprintBatch(batchId)

    const active = (batchState.value.counts.PENDING || 0) +
      (batchState.value.counts.RUNNING || 0) +
      (batchState.value.counts.PAUSED || 0)

    if (!active) break
  }

  await load()
}

async function cancelBatch() {
  if (!batchState.value) return

  for (const job of batchState.value.jobs) {
    if (['PENDING', 'RUNNING', 'PAUSED'].includes(job.status)) {
      try {
        await cancelJob(job.job_id)
      } catch {
        // задание могло уже завершиться — это не ошибка для «отменить все»
      }
    }
  }

  Notify.create({ type: 'info', message: 'Батч отменён' })
}

async function pollBuild(jobId) {
  // DINO over 20-40 photos takes a while; poll a few minutes.
  for (let attempt = 0; attempt < 120; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000))
    const job = await fetchJob(jobId)
    buildJob.value = { id: jobId, status: job.status }

    if (job.status === 'DONE') {
      buildJob.value.result = job.result

      const skipped = job.result?.skipped_images || []

      Notify.create({
        type: skipped.length ? 'warning' : 'positive',
        message: skipped.length
          ? `Слепок собран: ${job.result?.images} фото, пропущено битых файлов: ${skipped.length}`
          : `Слепок собран: ${job.result?.images} фото`,
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

// Адреса для выпадающего списка: берутся из справочника (вкладка «Адреса»).
const addressOptions = ref([])
const editAddressId = ref(null)

async function loadAddressOptions() {
  if (addressOptions.value.length) return

  try {
    const items = (await fetchAddressDirectory()).items || []
    addressOptions.value = items
      .filter((item) => item.active && item.legal_address)
      .map((item) => ({
        label: item.legal_address,
        value: item.address_id,
        caption: item.simple_address || '',
      }))
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function openEdit(item) {
  editTarget.value = { ...item }
  editAddressId.value = item.address?.address_id ?? null
  editOpen.value = true
  await loadAddressOptions()
}

async function saveEdit() {
  const target = editTarget.value

  try {
    const updated = await updateFingerprint(target.fingerprint_id, {
      display_name: target.display_name,
      description: target.description,
      source_folder: target.source_folder,
      active: target.active,
    })

    // Привязка к юридическому адресу из справочника (можно и снять).
    const current = target.address?.address_id ?? null

    if (editAddressId.value !== current) {
      await setFingerprintAddress(target.fingerprint_id, editAddressId.value ?? null)
    }

    editOpen.value = false
    Notify.create({ type: 'positive', message: 'Слепок сохранён' })

    if (updated?.recalc?.job_id) {
      Notify.create({
        type: 'info',
        message: `Запущен пересчёт базы (задание ${updated.recalc.job_id})`,
      })
    }

    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function toggleActive(item, value) {
  try {
    const updated = await updateFingerprint(item.fingerprint_id, { active: value })
    await load()

    if (updated?.recalc?.job_id) {
      Notify.create({
        type: 'info',
        message: `Запущен пересчёт базы (задание ${updated.recalc.job_id})`,
      })
    }
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

// The window shows the legal address (the alias is the fingerprint's name).
function addressLabel(item) {
  const address = item.address
  if (!address) return '—'
  return address.legal_address || address.simple_address || '—'
}

// Previews are written by the builder; a fingerprint built before that has none
// and the request fails, so it is remembered per fingerprint. The set is
// cleared on every reload, so a rebuild picks the new picture up.
const previewFailed = reactive(new Set())

function previewSrc(row) {
  if (!row) return ''

  const version =
    (row.current_version && row.current_version.created_at) || row.updated_at || ''

  return fingerprintPreviewUrl(row.fingerprint_id, version)
}

function markPreviewFailed(fingerprintId) {
  previewFailed.add(fingerprintId)
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
      <q-btn v-if="isAdmin" dense flat icon="library_add" label="Батч-сборка"
        @click="openBatch">
        <q-tooltip>
          Собрать слепки по всем папкам адреса за раз — задания разберут
          параллельные воркеры сборки
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
        { name: 'preview', label: 'Превью', field: 'fingerprint_id', align: 'center' },
        { name: 'name', label: 'Имя', field: 'name', align: 'left', sortable: true },
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
      <template #body-cell-preview="props">
        <q-td :props="props">
          <q-btn dense flat icon="photo_library" size="sm">
            <q-tooltip :delay="200" max-width="600px" class="bg-white text-dark shadow-4">
              <div class="text-caption q-mb-xs">Фото, из которых собран слепок</div>
              <AuthImage
                v-if="!previewFailed.has(props.row.fingerprint_id)"
                :url="previewSrc(props.row)"
                :ratio="16 / 3"
                style="width: 560px; border-radius: 4px"
                @error="markPreviewFailed(props.row.fingerprint_id)"
              />
              <div v-else class="text-caption text-grey-7">
                Превью нет: слепок собран до появления превью, пересоберите его
                из папки — картинка появится.
              </div>
            </q-tooltip>
          </q-btn>
        </q-td>
      </template>

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
          <q-btn
            v-if="isAdmin"
            dense
            flat
            color="negative"
            icon="delete"
            @click="openDelete(props.row)"
          >
            <q-tooltip>Удалить слепок, версии и файлы</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <div class="text-caption text-grey q-mt-sm">
      Векторы слепков лежат в <code>data/fingerprints/&lt;id&gt;</code>; реестр
      только описывает их. Адрес сопоставляется во вкладке «Адреса».
    </div>

    <!-- delete: registry + versions + address link + vector files -->
    <q-dialog v-model="deleteOpen">
      <q-card style="min-width: 420px; max-width: 92vw">
        <q-card-section class="text-subtitle1">
          Удалить слепок {{ deleteTarget?.fingerprint_id }}?
        </q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-banner class="bg-red-1 text-negative text-caption" rounded>
            Будут удалены запись реестра, все версии, привязка к адресу и файлы
            в <code>data/fingerprints/&lt;id&gt;</code>. Восстановить нельзя —
            слепок можно только собрать заново. Прошлые результаты DINO/HYBRID
            останутся в истории и будут ссылаться на удалённый id.
          </q-banner>
          <div v-if="deleteError" class="text-negative text-caption">
            {{ deleteError }}
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup :disable="deleteBusy" />
          <q-btn
            color="negative"
            label="Удалить"
            :loading="deleteBusy"
            @click="doDelete"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

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
            hint="Пусто — слепок называется по алиасу своего адреса (или по своему ID, если адрес не назначен)"
          />
          <q-select
            v-model="editAddressId"
            :options="addressOptions"
            dense
            outlined
            clearable
            emit-value
            map-options
            option-label="label"
            option-value="value"
            label="Юридический адрес (из справочника)"
            hint="Список ведётся во вкладке «Адреса»; можно очистить, чтобы снять привязку"
          >
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.label }}</q-item-label>
                  <q-item-label v-if="scope.opt.caption" caption>
                    {{ scope.opt.caption }}
                  </q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </q-select>

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

          <div>
            <div class="text-caption text-grey-7 q-mb-xs">
              Фото, из которых собран слепок (сохранены вместе со слепком)
            </div>
            <AuthImage
              v-if="editTarget && !previewFailed.has(editTarget.fingerprint_id)"
              :url="previewSrc(editTarget)"
              :ratio="16 / 3"
              style="border-radius: 4px"
              @error="markPreviewFailed(editTarget.fingerprint_id)"
            />
            <div v-else class="text-caption text-grey-7">
              Превью нет: слепок собран до появления превью. Пересоберите его из
              папки — картинка появится.
            </div>
          </div>

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
            />
            <q-btn dense color="secondary" icon="folder_open" label="Выбрать папку"
              @click="openBrowser" />
          </div>
          <!-- Подсказка вне строки: внутри она поднимала кнопку над полем. -->
          <div class="text-caption text-grey-7 q-mt-xs q-mb-sm">
            Папки по умолчанию нет — берутся файлы из выбранной; исходники
            только читаются
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

          <div v-if="buildJob" class="q-mt-md">
            <div class="row items-center q-gutter-sm">
              <div class="text-caption col">
                Задание №{{ buildJob.id }}: {{ buildJob.status }}
                <template v-if="buildJob.progress">
                  · {{ buildJob.progress.stage }}
                  {{ buildJob.progress.done }}/{{ buildJob.progress.total }}
                </template>
              </div>
              <div class="text-caption text-grey">
                {{ buildJob.progress?.percent ?? 0 }} %
              </div>
            </div>

            <q-linear-progress
              :value="(buildJob.progress?.percent ?? 0) / 100"
              :color="buildJob.error ? 'negative' : 'primary'"
              track-color="grey-3"
              size="18px"
              rounded
              class="q-mt-xs"
            />

            <q-banner
              v-if="buildJob.error"
              class="bg-red-1 text-negative q-mt-sm"
            >
              {{ buildJob.error }}
            </q-banner>

            <div
              v-else-if="buildJob.status === 'DONE' && buildJob.result"
              class="q-mt-xs"
            >
              <div class="text-caption text-grey">
                Собрано из {{ buildJob.result.images }} фото
              </div>

              <q-banner
                v-if="buildJob.result.recalc?.job_id"
                dense
                rounded
                class="bg-blue-1 text-primary q-mt-sm"
              >
                Слепок заменён: запущен пересчёт базы
                (задание {{ buildJob.result.recalc.job_id }}, фото:
                {{ buildJob.result.recalc.total }}).
              </q-banner>

              <q-banner
                v-else-if="buildJob.result.recalc_error"
                dense
                rounded
                class="bg-orange-1 text-dark q-mt-sm"
              >
                Слепок заменён, но пересчёт базы не запустился:
                {{ buildJob.result.recalc_error }}. Запустите сортировку вручную.
              </q-banner>

              <q-banner
                v-if="buildJob.result.skipped_images?.length"
                dense
                rounded
                class="bg-orange-1 text-dark q-mt-sm"
              >
                <div class="text-weight-medium">
                  Пропущено битых файлов:
                  {{ buildJob.result.skipped_images.length }}
                </div>
                <div class="text-caption">
                  Эти файлы не включены в слепок:
                </div>
                <ul class="skipped-files">
                  <li
                    v-for="item in buildJob.result.skipped_images"
                    :key="item.name"
                  >
                    {{ item.name }} — {{ item.error }}
                  </li>
                </ul>
              </q-banner>
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <template v-if="runningBuild">
            <q-btn
              v-if="buildJob.status === 'PAUSED'"
              flat
              icon="play_arrow"
              label="Продолжить"
              @click="resumeBuild"
            />
            <q-btn
              v-else
              flat
              icon="pause"
              label="Пауза"
              @click="pauseBuild"
            />
            <q-btn flat color="negative" icon="stop" label="Отменить" @click="cancelBuild" />
          </template>
          <q-btn flat label="Закрыть" v-close-popup />
          <q-btn
            color="primary"
            label="Собрать"
            :loading="buildBusy"
            :disable="runningBuild || !buildForm.fingerprint_id.trim() || !buildForm.folder.trim()"
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
  

    <!-- батч-сборка: папки -> задания, их разбирают воркеры -->
    <q-dialog v-model="batchOpen">
      <q-card style="min-width: 620px; max-width: 94vw; max-height: 90vh">
        <q-card-section class="row items-center">
          <div class="text-subtitle1 col">Батч-сборка слепков</div>
          <q-btn dense flat icon="desktop_windows" label="Системный диалог"
            :loading="batchBusy" @click="pickBatchParent" />
        </q-card-section>
        <q-separator />

        <q-card-section style="max-height: 60vh; overflow: auto">
          <div class="row items-center q-gutter-sm">
            <q-input
              v-model="batchParent"
              dense
              outlined
              class="col"
              label="Папка с подпапками адресов"
              @keyup.enter="loadBatchDirs(batchParent)"
            />
            <q-btn dense label="Показать подпапки" :loading="batchBusy"
              @click="loadBatchDirs(batchParent)" />
            <q-btn
              v-if="batchParentPath"
              dense
              flat
              icon="arrow_upward"
              label="Вверх"
              @click="loadBatchDirs(batchParentPath)"
            />
          </div>
          <!-- Подсказка вне строки: внутри она поднимала кнопки над полем. -->
          <div class="text-caption text-grey-7 q-mt-xs">
            например data/input — вложенные папки станут слепками
          </div>

          <div class="row items-center q-gutter-sm q-mt-sm">
            <q-select
              v-model="batchMaxPhotos"
              :options="PHOTO_CHOICES"
              dense
              outlined
              emit-value
              map-options
              option-label="label"
              option-value="value"
              label="Фото на слепок"
              style="min-width: 220px"
            />
            <q-badge color="grey-7">
              отмечено: {{ batchSelected.length }} из {{ batchDirs.length }}
            </q-badge>
            <q-space />
            <q-btn dense flat label="Отметить все с фото" @click="selectDirsWithPhotos" />
            <q-btn dense flat label="Снять" @click="batchSelected = []" />
          </div>

          <q-list dense separator class="q-mt-sm">
            <q-item
              v-for="dir in batchDirs"
              :key="dir.path"
              clickable
              @click="toggleBatchDir(dir.path)"
            >
              <q-item-section side>
                <q-checkbox
                  :model-value="batchSelected.includes(dir.path)"
                  dense
                  @click.stop
                  @update:model-value="toggleBatchDir(dir.path)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label class="row items-center q-gutter-sm">
                  <span>{{ dir.name }}</span>
                  <q-input
                    :model-value="batchIdFor(dir.path)"
                    dense
                    outlined
                    label="ID слепка"
                    class="batch-id-input"
                    @click.stop
                    @update:model-value="(value) => setBatchId(dir.path, value)"
                  />
                </q-item-label>
                <q-item-label caption>{{ dir.path }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="row items-center q-gutter-xs">
                  <q-badge :color="dir.photos ? 'primary' : 'grey-5'">
                    {{ dir.photos }} фото
                  </q-badge>
                  <q-btn
                    dense
                    flat
                    icon="subdirectory_arrow_right"
                    @click.stop="loadBatchDirs(dir.path)"
                  >
                    <q-tooltip>Войти в папку</q-tooltip>
                  </q-btn>
                </div>
              </q-item-section>
            </q-item>
            <q-item v-if="!batchDirs.length">
              <q-item-section class="text-caption text-grey">
                Пусто. Укажите папку с подпапками адресов (например data/input)
                и нажмите «Показать подпапки», либо откройте системный диалог.
              </q-item-section>
            </q-item>
          </q-list>

          <div v-if="batchState" class="q-mt-md">
            <div class="row items-center q-gutter-sm">
              <div class="text-caption col">
                Итог: {{ batchState.counts.DONE || 0 }}/{{ batchState.total }} готово
                <template v-if="batchState.counts.FAILED">
                  · ошибок {{ batchState.counts.FAILED }}
                </template>
                <template v-if="batchState.counts.PAUSED">
                  · на паузе {{ batchState.counts.PAUSED }}
                </template>
              </div>
              <div class="text-caption text-grey">{{ batchState.percent }} %</div>
            </div>
            <q-linear-progress
              :value="batchState.percent / 100"
              color="primary"
              track-color="grey-3"
              size="18px"
              rounded
              class="q-mt-xs"
            />
            <q-list dense class="q-mt-sm">
              <q-item v-for="job in batchState.jobs" :key="job.job_id">
                <q-item-section>
                  <q-item-label>{{ job.fingerprint_id }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge
                    :color="job.status === 'DONE' ? 'positive' : (job.status === 'FAILED' ? 'negative' : 'grey-7')"
                  >
                    {{ job.status }}
                    <template v-if="job.progress">· {{ job.progress.percent }} %</template>
                  </q-badge>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn v-if="batchState" flat color="negative" icon="stop" label="Отменить все"
            @click="cancelBatch" />
          <q-btn flat label="Закрыть" v-close-popup />
          <q-btn
            color="primary"
            label="Запустить батч"
            :loading="batchBusy"
            :disable="!batchSelected.length"
            @click="startBatch"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.skipped-files {
  margin: 4px 0 0 18px;
  padding: 0;
  max-height: 160px;
  overflow-y: auto;
  font-size: 12px;
}

/* ID слепка в строке папки: не растягивает список и не перехватывает клик. */
.batch-id-input {
  max-width: 240px;
  min-width: 180px;
}
</style>
