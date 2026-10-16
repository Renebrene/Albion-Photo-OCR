<script setup>
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import { fetchAutomation, runAutomation, updateAutomation } from '../api/client'

const settings = ref(null)
const error = ref(null)
const busy = ref(false)

async function load() {
  try {
    settings.value = await fetchAutomation()
    error.value = null
  } catch (err) {
    error.value = err.message
  }
}

async function save(patch) {
  busy.value = true
  try {
    settings.value = await updateAutomation(patch)
    Notify.create({ type: 'positive', message: 'Настройки сохранены' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    busy.value = false
  }
}

async function runNow() {
  busy.value = true
  try {
    const result = await runAutomation(true)
    Notify.create({
      type: 'info',
      message: `Тик: DINO ${result.dino_batch_id ?? '—'}, QWEN ${result.qwen_jobs ?? 0}`,
    })
    await load()
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
      <div class="text-subtitle1 col">Автоматизация</div>
      <q-btn dense flat icon="refresh" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <template v-if="settings">
      <q-card flat bordered class="q-mb-md">
        <q-card-section>
          <q-toggle
            :model-value="settings.enabled"
            label="Планировщик включён"
            :disable="busy"
            @update:model-value="(v) => save({ enabled: v })"
          />
          <div class="text-caption text-grey q-mt-xs">
            Планировщик только ставит в очередь уже поддержанные операции
            (QWEN для фото без метаданных, DINO для фото без прогонов). Новые
            файлы он не импортирует. Запускается через
            <code>python -m app.jobs.worker --automation</code>.
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="q-mb-md">
        <q-card-section class="q-gutter-sm">
          <q-input
            :model-value="settings.interval_minutes"
            type="number"
            dense
            outlined
            label="Интервал, минут"
            style="max-width: 200px"
            :disable="busy"
            @update:model-value="(v) => save({ interval_minutes: Number(v) })"
          />

          <q-toggle
            :model-value="settings.auto_qwen"
            label="Автоматически запускать QWEN для новых фото"
            :disable="busy"
            @update:model-value="(v) => save({ auto_qwen: v })"
          />

          <div class="text-caption text-grey">
            Фоновый вотчер папки не реализуется; полный прогон запускается
            кнопкой «Обновление базы». Последний тик: {{ settings.last_tick || '—' }}
          </div>
        </q-card-section>
      </q-card>

      <div class="row q-gutter-sm">
        <q-btn
          color="primary"
          icon="play_arrow"
          label="Запустить тик сейчас"
          :loading="busy"
          @click="runNow"
        />
      </div>

      <q-banner class="bg-grey-2 q-mt-md text-caption">
        Watcher-режим (слежение за папкой и автоматический INGEST новых файлов)
        из легаси не реализован: он пишет новые данные и требует отдельного
        согласования.
      </q-banner>
    </template>
  </div>
</template>
