<script setup>
// Логи: где они лежат и сколько занимают (технический раздел → Данные).
//
// Путь раньше нигде не был виден: логи писались в data/logs, а найти их можно
// было только по документации. Каталог берётся из того же состояния, что и
// бэкапы (один запрос на весь раздел «Данные»): это одна и та же картина
// «где что лежит», и разводить два источника значило бы разойтись им при
// первой же правке.
import { onMounted, ref } from 'vue'

import { fetchBackupStatus } from '../api/client'

const logs = ref(null)
const error = ref(null)
const loading = ref(false)

function humanBytes(value) {
  if (value == null) return '—'
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']
  let size = value
  let i = 0
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i += 1
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

async function load() {
  if (loading.value) return
  loading.value = true

  try {
    logs.value = (await fetchBackupStatus()).logs
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle2 col">Логи</div>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div v-if="logs" class="column q-gutter-sm">
      <q-markup-table dense flat bordered>
        <tbody>
          <tr>
            <td>Путь хранения логов</td>
            <td>
              {{ logs.directory }}
              <q-chip
                v-if="!logs.exists"
                dense
                color="orange-2"
                text-color="orange-9"
                label="каталога нет"
              />
            </td>
          </tr>
          <tr>
            <td>Файлов</td>
            <td>{{ logs.files }} · {{ humanBytes(logs.bytes) }}</td>
          </tr>
          <tr>
            <td>Журнал идентичности</td>
            <td>{{ logs.shadow_log }}</td>
          </tr>
        </tbody>
      </q-markup-table>

      <div v-if="logs.newest?.length">
        <div class="text-caption text-grey q-mb-xs">Последние файлы</div>
        <q-markup-table dense flat bordered>
          <tbody>
            <tr v-for="file in logs.newest" :key="file.name">
              <td class="ellipsis" style="max-width: 420px">{{ file.name }}</td>
              <td class="text-right">{{ humanBytes(file.size) }}</td>
              <td class="text-grey">{{ new Date(file.modified).toLocaleString() }}</td>
            </tr>
          </tbody>
        </q-markup-table>
      </div>

      <div class="text-caption text-grey">
        Путь задаётся переменной <code>SCENE_RUN_LOG_ROOT</code> в env-файле
        (по умолчанию <code>data/logs</code>); старые логи удаляются по сроку
        хранения. Логи служб лежат отдельно, в журнале systemd:
        <code>journalctl --user -u scene-api -n 100</code>.
      </div>
    </div>
  </div>
</template>
