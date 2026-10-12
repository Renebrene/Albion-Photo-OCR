<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

import { fetchSystem } from '../api/client'

const info = ref(null)
const error = ref(null)
let timer = null

function gb(bytes) {
  return (bytes / 1024 ** 3).toFixed(1)
}

function uptime(seconds) {
  if (!seconds) return '—'
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${d}д ${h}ч ${m}м`
}

async function load() {
  try {
    info.value = await fetchSystem()
    error.value = null
  } catch (err) {
    error.value = err.message
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 2000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Система</div>
      <q-btn dense flat icon="refresh" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div v-if="info" class="row q-col-gutter-md">
      <q-card flat bordered class="col-12 col-sm-6 col-md-3">
        <q-card-section>
          <div class="text-caption text-grey">CPU</div>
          <div class="text-h6">{{ info.cpu_percent.toFixed(0) }}%</div>
          <q-linear-progress
            :value="info.cpu_percent / 100"
            color="primary"
            class="q-mt-sm"
          />
          <div class="text-caption text-grey q-mt-xs">
            ядер: {{ info.cpu_count }}
            <span v-if="info.load_avg">
              · load: {{ info.load_avg.map((v) => v.toFixed(2)).join(' / ') }}
            </span>
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12 col-sm-6 col-md-3">
        <q-card-section>
          <div class="text-caption text-grey">Память</div>
          <div class="text-h6">{{ info.memory.percent.toFixed(0) }}%</div>
          <q-linear-progress
            :value="info.memory.percent / 100"
            color="teal"
            class="q-mt-sm"
          />
          <div class="text-caption text-grey q-mt-xs">
            {{ gb(info.memory.used) }} / {{ gb(info.memory.total) }} ГБ
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12 col-sm-6 col-md-3">
        <q-card-section>
          <div class="text-caption text-grey">Диск</div>
          <div class="text-h6">{{ info.disk.percent.toFixed(0) }}%</div>
          <q-linear-progress
            :value="info.disk.percent / 100"
            color="orange"
            class="q-mt-sm"
          />
          <div class="text-caption text-grey q-mt-xs">
            {{ gb(info.disk.used) }} / {{ gb(info.disk.total) }} ГБ
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12 col-sm-6 col-md-3">
        <q-card-section>
          <div class="text-caption text-grey">Uptime</div>
          <div class="text-h6">{{ uptime(info.uptime_sec) }}</div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
