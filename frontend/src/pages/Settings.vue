<script setup>
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  enqueueQwen,
  fetchQwenModels,
  fetchQwenStats,
  setQwenModel,
  unloadQwen,
} from '../api/client'

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

const model = ref(null)
const available = ref([])
const current = ref(null)

const stats = ref(null)

function sizeLabel(size) {
  if (!size) return ''
  const gb = size / 1024 ** 3
  return `${gb.toFixed(1)} GB`
}

async function load() {
  loading.value = true
  error.value = null

  try {
    const data = await fetchQwenModels()
    available.value = (data.available || []).map((m) => ({
      label: `${m.name} (${sizeLabel(m.size)})`,
      value: m.name,
    }))
    current.value = data.current
    model.value = data.current
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await fetchQwenStats()
  } catch {
    stats.value = null
  }
}

async function retryFailed() {
  try {
    const result = await enqueueQwen(null, true)
    Notify.create({
      type: 'positive',
      message: `В очередь: ${result.jobs} фото`,
    })
    await loadStats()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function save() {
  if (!model.value) return
  saving.value = true

  try {
    const data = await setQwenModel(model.value)
    current.value = data.model
    Notify.create({ type: 'positive', message: `Модель: ${data.model}` })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    saving.value = false
  }
}

async function unload() {
  try {
    await unloadQwen()
    Notify.create({ type: 'positive', message: 'Модель выгружена из памяти' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

onMounted(() => {
  load()
  loadStats()
})
</script>

<template>
  <div style="max-width: 720px">
    <div class="text-h6 q-mb-md">Модель QWEN</div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">
        {{ error }}
      </q-banner>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Модель QWEN (Ollama)</div>

        <q-select
          v-model="model"
          :options="available"
          :loading="loading"
          dense
          outlined
          emit-value
          map-options
          label="Модель"
          class="q-mb-md"
        />

        <div class="text-caption text-grey q-mb-md">
          Текущая: <b>{{ current || '—' }}</b>. Модель выгружается из памяти
          сразу после обработки каждого фото.
        </div>

        <div class="q-gutter-sm">
          <q-btn color="primary" label="Сохранить" :loading="saving" @click="save" />
          <q-btn flat icon="refresh" label="Обновить список" :loading="loading" @click="load" />
          <q-btn flat color="orange" icon="memory" label="Выгрузить из памяти" @click="unload" />
        </div>
      </q-card-section>
    </q-card>

    <q-card v-if="stats" flat bordered class="q-mt-md">
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Метаданные QWEN</div>

        <div class="row q-gutter-sm q-mb-md">
          <q-chip
            v-for="(count, status) in stats.counts"
            :key="status"
            :color="status === 'FAILED' && count ? 'negative' : 'grey-4'"
            :text-color="status === 'FAILED' && count ? 'white' : 'black'"
            dense
          >
            {{ status }}: {{ count }}
          </q-chip>
        </div>

        <q-btn
          flat
          color="teal"
          icon="replay"
          :label="`Повторить для упавших (${stats.failed_photo_ids.length})`"
          :disable="!stats.failed_photo_ids.length"
          @click="retryFailed"
        />
      </q-card-section>
    </q-card>
  </div>
</template>
