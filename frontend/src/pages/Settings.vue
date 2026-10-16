<script setup>
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  enqueueQwen,
  fetchQwenModels,
  fetchQwenSettings,
  fetchQwenStats,
  unloadQwen,
  updateQwenSettings,
} from '../api/client'

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

// provider settings
const provider = ref('ollama')
const baseUrl = ref('')
const apiKey = ref('')
const apiKeyHint = ref(null)
const apiKeySet = ref(false)
const keepAlive = ref('10m')
const unloadOnIdle = ref(true)

const model = ref(null)
const available = ref([])
const current = ref(null)

const stats = ref(null)


function sizeLabel(size) {
  if (!size) return ''
  const gb = size / 1024 ** 3
  return `${gb.toFixed(1)} GB`
}

async function loadSettings() {
  try {
    const data = await fetchQwenSettings()
    provider.value = data.provider || 'ollama'
    baseUrl.value = data.base_url || ''
    apiKeyHint.value = data.api_key_hint
    apiKeySet.value = !!data.api_key_set
    keepAlive.value = data.keep_alive || ''
    unloadOnIdle.value = data.unload_on_idle !== false
    apiKey.value = ''
  } catch (err) {
    error.value = err.message
  }
}

async function loadModels() {
  loading.value = true
  error.value = null

  try {
    const data = await fetchQwenModels()
    available.value = (data.available || []).map((m) => ({
      label: `${m.name} ${m.size ? `(${sizeLabel(m.size)})` : ''}`.trim(),
      value: m.name,
    }))
    current.value = data.current
    if (!model.value) model.value = data.current
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

async function runAll() {
  try {
    const result = await enqueueQwen(null, false)
    Notify.create({ type: 'positive', message: `QWEN заданий: ${result.jobs}` })
    await loadStats()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function save() {
  saving.value = true

  try {
    const payload = {
      provider: provider.value,
      model: model.value || undefined,
      base_url: baseUrl.value,
      keep_alive: keepAlive.value,
      unload_on_idle: unloadOnIdle.value,
    }

    // Only send the key when the user typed a new one (blank = keep as is).
    if (apiKey.value) payload.api_key = apiKey.value

    await updateQwenSettings(payload)
    await loadSettings()
    await loadModels()
    Notify.create({ type: 'positive', message: 'Настройки QWEN сохранены' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    saving.value = false
  }
}

async function clearKey() {
  try {
    await updateQwenSettings({ api_key: '' })
    await loadSettings()
    Notify.create({ type: 'info', message: 'API-ключ очищен' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function unload() {
  try {
    const result = await unloadQwen()
    Notify.create({
      type: 'positive',
      message:
        result.status === 'unloaded'
          ? 'Модель выгружена из памяти'
          : 'Для облачного провайдера выгрузка не требуется',
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

onMounted(async () => {
  await loadSettings()
  await loadModels()
  loadStats()
})
</script>

<template>
  <div style="max-width: 760px">
    <div class="text-h6 q-mb-md">Модель QWEN</div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Провайдер QWEN</div>

        <q-select
          v-model="provider"
          :options="[
            { label: 'Локально (Ollama)', value: 'ollama' },
            { label: 'Облако (OpenAI-совместимый)', value: 'openai' },
          ]"
          dense
          outlined
          emit-value
          map-options
          label="Провайдер"
          class="q-mb-md"
        />

        <q-banner
          v-if="provider === 'openai'"
          class="bg-orange-1 text-orange-10 q-mb-md"
        >
          Облачный провайдер отправляет изображения на внешний сервис.
          Включайте только по согласованию и без персональных данных.
        </q-banner>

        <template v-if="provider === 'openai'">
          <q-input
            v-model="baseUrl"
            dense
            outlined
            label="Base URL (например, https://api.openai.com/v1)"
            class="q-mb-md"
          />
          <q-input
            v-model="apiKey"
            type="password"
            dense
            outlined
            :label="
              apiKeySet
                ? `API-ключ (сохранён ${apiKeyHint || ''}) — пусто = не менять`
                : 'API-ключ'
            "
            class="q-mb-md"
          />
          <q-btn
            v-if="apiKeySet"
            flat
            dense
            color="negative"
            label="Очистить ключ"
            class="q-mb-md"
            @click="clearKey"
          />
        </template>

        <q-select
          v-model="model"
          :options="available"
          :loading="loading"
          dense
          outlined
          emit-value
          map-options
          use-input
          input-debounce="0"
          new-value-mode="add-unique"
          label="Модель"
          class="q-mb-md"
        />

        <div class="row q-gutter-sm items-center q-mb-md">
          <q-input
            v-model="keepAlive"
            dense
            outlined
            label="Keep-alive (0 = выгружать сразу)"
            style="max-width: 220px"
          />
          <q-toggle
            v-model="unloadOnIdle"
            label="Выгружать при простое очереди"
          />
        </div>

        <div class="text-caption text-grey q-mb-md">
          Текущая: <b>{{ current || '—' }}</b>. Keep-alive держит модель в
          памяти между заданиями; при простое очереди воркер выгружает её.
        </div>

        <div class="q-gutter-sm">
          <q-btn color="primary" label="Сохранить" :loading="saving" @click="save" />
          <q-btn flat icon="refresh" label="Обновить список" :loading="loading" @click="loadModels" />
          <q-btn flat color="orange" icon="memory" label="Выгрузить из памяти" @click="unload" />
        </div>
      </q-card-section>
    </q-card>

    <q-card v-if="stats" flat bordered class="q-mt-md">
      <q-card-section>
        <div class="text-subtitle1 q-mb-sm">Метаданные QWEN</div>

        <div class="text-caption text-grey-8 q-mb-sm">
          ВСЕГО: {{ Object.values(stats.counts).reduce((a, b) => a + b, 0) }} ·
          УСПЕШНО: {{ stats.counts.DONE || 0 }} ·
          В ОЧЕРЕДИ: {{ (stats.counts.PENDING || 0) + (stats.counts.RUNNING || 0) }} ·
          С ОШИБКОЙ: {{ stats.counts.FAILED || 0 }}
        </div>

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

        <div class="row q-gutter-sm">
          <q-btn
            color="secondary"
            icon="auto_awesome"
            label="Запустить QWEN (все фото)"
            @click="runAll"
          />
          <q-btn
            flat
            color="teal"
            icon="replay"
            :label="`Повторить для упавших (${stats.failed_photo_ids.length})`"
            :disable="!stats.failed_photo_ids.length"
            @click="retryFailed"
          />
        </div>
      </q-card-section>
    </q-card>

  </div>
</template>
