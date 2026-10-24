<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchSystem } from '../api/client'
import { usePoller } from '../composables/usePoller'

const info = ref(null)
const error = ref(null)
const loading = ref(false)

const maxLoginIp = computed(() => {
  const entries = Object.entries(info.value?.security?.login_failures_by_ip || {})
  if (!entries.length) return null
  return entries.sort((a, b) => b[1] - a[1])[0]
})

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
  // Ручное обновление не должно наслаиваться на периодический опрос.
  if (loading.value) return

  loading.value = true

  try {
    info.value = await fetchSystem()
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// Опрос раз в две секунды: тики не накладываются, скрытая вкладка молчит,
// при уходе со страницы опрос останавливается сам (usePoller).
const poller = usePoller(load, { intervalMs: 2000, immediate: true })

onMounted(poller.start)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Система</div>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load" />
    </div>
    <div v-if="!info && !error" class="q-gutter-sm">
      <q-skeleton type="text" width="40%" />
      <q-skeleton type="rect" height="120px" />
      <q-skeleton type="rect" height="120px" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div v-if="info && info.alerts && info.alerts.length" class="q-mb-md">
      <q-banner
        v-for="alert in info.alerts"
        :key="alert.code + (alert.ip || '')"
        dense
        rounded
        :class="alert.severity === 'critical'
          ? 'bg-red-2 text-negative q-mb-xs'
          : 'bg-orange-2 text-dark q-mb-xs'"
      >
        <template #avatar>
          <q-icon name="warning" />
        </template>
        {{ alert.message }}
      </q-banner>
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

      <q-card
        v-if="info.network && info.network.bytes_recv !== undefined"
        flat
        bordered
        class="col-12 col-sm-6"
      >
        <q-card-section>
          <div class="text-caption text-grey">Сеть</div>
          <div class="text-body2 q-mt-xs">
            ↓ {{ gb(info.network.bytes_recv) }} ГБ ·
            ↑ {{ gb(info.network.bytes_sent) }} ГБ
            <span v-if="info.network.rate_mbps != null">
              · {{ info.network.rate_mbps }} МБ/с
            </span>
          </div>
          <div
            v-if="info.network.errors || info.network.drops"
            class="text-caption text-negative q-mt-xs"
          >
            ошибки: {{ info.network.errors }} · потери: {{ info.network.drops }}
          </div>
        </q-card-section>
      </q-card>

      <q-card
        v-for="gpu in info.gpus || []"
        :key="gpu.index"
        flat
        bordered
        class="col-12 col-sm-6"
      >
        <q-card-section>
          <div class="text-caption text-grey">GPU {{ gpu.index }}</div>
          <div class="text-h6">{{ gpu.utilization.toFixed(0) }}%</div>
          <q-linear-progress
            :value="gpu.utilization / 100"
            color="deep-purple"
            class="q-mt-sm"
          />
          <div class="text-caption text-grey q-mt-xs">
            {{ gpu.name }} · VRAM {{ gpu.memory_percent.toFixed(0) }}%
            · {{ gpu.temperature }}°C
          </div>
        </q-card-section>
      </q-card>

      <q-card
        v-if="info.security"
        flat
        bordered
        class="col-12 col-sm-6"
      >
        <q-card-section>
          <div class="text-caption text-grey">Безопасность (окно)</div>
          <div class="text-body2 q-mt-xs">
            неудачных входов: {{ info.security.login_failures }}
            <span v-if="maxLoginIp">
              · максимум с IP: {{ maxLoginIp[1] }} ({{ maxLoginIp[0] }})
            </span>
          </div>
          <div class="text-caption text-grey q-mt-xs">
            лимит {{ info.security.login_failure_limit }} за
            {{ Math.round(info.security.login_failure_window_sec / 60) }} мин
          </div>
        </q-card-section>
      </q-card>

      <q-card
        v-if="info.temperatures && info.temperatures.length"
        flat
        bordered
        class="col-12 col-sm-6"
      >
        <q-card-section>
          <div class="text-caption text-grey">Температуры</div>
          <div class="row q-gutter-sm q-mt-xs">
            <q-chip
              v-for="t in info.temperatures"
              :key="`${t.sensor}-${t.label}`"
              dense
              :color="t.current >= 80 ? 'negative' : 'grey-4'"
              :text-color="t.current >= 80 ? 'white' : 'black'"
            >
              {{ t.label }}: {{ t.current }}°C
            </q-chip>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
