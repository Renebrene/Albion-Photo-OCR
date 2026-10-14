<script setup>
// Working (source) folder for INGEST: choose the folder, see how many photos
// (and how many MB) it holds, and start a scan. The scan itself is a worker
// job - the browser only enqueues it and polls the job status.
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  fetchIngestFolder,
  runIngest,
  saveIngestFolder,
  scanIngestFolder,
} from '../api/client'

const path = ref('')
const state = ref({ configured: '', files: 0, bytes: 0, exists: false })
const busy = ref(false)
const jobId = ref(null)

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
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function save() {
  busy.value = true
  try {
    state.value = await saveIngestFolder(path.value.trim())
    path.value = state.value.configured
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
    Notify.create({
      type: 'info',
      message: `Найдено фото: ${stats.files} (${humanBytes(stats.bytes)})`,
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

onMounted(load)
</script>

<template>
  <q-card flat bordered style="max-width: 760px">
    <q-card-section>
      <div class="text-subtitle2 q-mb-sm">Папка с рабочими фотографиями</div>

      <!-- Подсказка вынесена из строки: внутри неё она добавляла высоту, и
           кнопки вставали выше поля ввода. -->
      <div class="row items-center q-gutter-sm">
        <q-input
          v-model="path"
          dense
          outlined
          class="col"
          label="Путь на сервере"
          @keyup.enter="save"
        />
        <q-btn
          dense
          color="primary"
          label="Сохранить"
          :loading="busy"
          :disable="!path.trim()"
          @click="save"
        />
        <q-btn dense flat label="Проверить" :loading="busy" @click="check" />
      </div>
      <div class="text-caption text-grey-7 q-mt-xs q-mb-sm">
        Обход рекурсивный, включая подпапки; исходники только читаются
      </div>

      <div class="row items-center q-gutter-md q-mt-sm">
        <q-badge v-if="state.exists" color="grey-7">
          фото: {{ state.files }}
        </q-badge>
        <q-badge v-if="state.exists" color="grey-7">
          объём: {{ humanBytes(state.bytes) }}
        </q-badge>
        <q-badge v-if="state.configured && !state.exists" color="orange">
          папка недоступна
        </q-badge>
        <q-space />
        <q-btn
          dense
          color="secondary"
          icon="play_arrow"
          label="Запустить ingest"
          :loading="busy"
          :disable="!state.exists"
          @click="start"
        />
      </div>

      <div v-if="jobId" class="text-caption text-grey-8 q-mt-sm">
        Задание №{{ jobId }} выполняется воркером. Уже зарегистрированные файлы
        (совпадение имени и размера) пропускаются без хеширования.
      </div>

      <div class="text-caption text-grey-7 q-mt-sm">
        Фоновый вотчер ещё не подключён: обход запускается кнопкой или командой
        <code>scene-fingerprint ingest &lt;папка&gt;</code>.
      </div>
    </q-card-section>
  </q-card>
</template>
