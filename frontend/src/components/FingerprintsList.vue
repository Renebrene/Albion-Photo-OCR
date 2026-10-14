<script setup>
// Fingerprint management window (schema/023).
//
// The vectors live on disk; this table mirrors them from
// data/fingerprints/*/metadata.json and adds the human layer: a name, a
// description, the source folder, archiving and a version journal.
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  fetchFingerprintRegistry,
  fetchFingerprintVersions,
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
  </div>
</template>
