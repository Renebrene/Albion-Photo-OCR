<script setup>
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import { fetchDataExport, fetchDataStorage } from '../api/client'

const stats = ref(null)
const error = ref(null)
const busy = ref(false)

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
  try {
    stats.value = await fetchDataStorage()
    error.value = null
  } catch (err) {
    error.value = err.message
  }
}

async function download(format) {
  busy.value = true
  try {
    const response = await fetchDataExport(format)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = format === 'csv' ? 'photos.csv' : 'photos.json'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    Notify.create({ type: 'positive', message: 'Экспорт готов' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Данные</div>
      <q-btn dense flat icon="refresh" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div class="row q-col-gutter-md">
      <q-card flat bordered class="col-12 col-md-6">
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Экспорт метаданных</div>
          <div class="text-caption text-grey q-mb-md">
            Слепки, распознавание и QWEN-метаданные без абсолютных путей.
          </div>
          <q-btn
            color="primary"
            icon="download"
            label="JSON"
            class="q-mr-sm"
            :loading="busy"
            @click="download('json')"
          />
          <q-btn
            outline
            color="primary"
            icon="table_view"
            label="CSV"
            :loading="busy"
            @click="download('csv')"
          />
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12 col-md-6">
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Импорт</div>
          <q-banner class="bg-grey-2 text-caption">
            Импорт из легаси-NiceGUI пока не реализован: он затрагивает INGEST
            и требует отдельного согласования. Используйте штатный ingest.
          </q-banner>
        </q-card-section>
      </q-card>

      <q-card v-if="stats" flat bordered class="col-12">
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Обслуживание хранилища</div>

          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-caption text-grey">Записи в БД</div>
              <q-markup-table dense flat bordered>
                <tbody>
                  <tr
                    v-for="(value, key) in stats.rows"
                    :key="key"
                  >
                    <td>{{ key }}</td>
                    <td class="text-right">{{ value }}</td>
                  </tr>
                  <tr>
                    <td>database_bytes</td>
                    <td class="text-right">
                      {{ humanBytes(stats.database_bytes) }}
                    </td>
                  </tr>
                </tbody>
              </q-markup-table>
            </div>

            <div class="col-12 col-md-6">
              <div class="text-caption text-grey">Файлы</div>
              <q-markup-table dense flat bordered>
                <tbody>
                  <tr>
                    <td>previews</td>
                    <td class="text-right">
                      {{ stats.previews.files }} файлов ·
                      {{ humanBytes(stats.previews.bytes) }}
                    </td>
                  </tr>
                  <tr>
                    <td>fingerprints</td>
                    <td class="text-right">
                      {{ stats.fingerprints.files }} файлов ·
                      {{ humanBytes(stats.fingerprints.bytes) }}
                    </td>
                  </tr>
                </tbody>
              </q-markup-table>
            </div>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
