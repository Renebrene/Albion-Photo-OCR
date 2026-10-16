<script setup>
// История прогонов «Обновления базы» для вкладки «Последний запуск»:
// дата, режим, статус, длительность по этапам и сообщение об ошибке.
// Если супервизор не развёрнут (404), блок не показывается.
import { computed, onMounted, ref } from 'vue'

import { fetchPipelineRuns } from '../api/client'

const runs = ref([])
const available = ref(false)
const loading = ref(false)

const STAGE_LABELS = {
  INGEST: 'Загрузка',
  PREVIEW: 'Превью',
  DINO: 'DINO',
  HYBRID: 'HYBRID',
  QWEN: 'Описания',
}

const STATUS_LABELS = {
  PENDING: 'ожидает',
  RUNNING: 'идёт',
  STOPPED: 'прерван',
  DONE: 'завершён',
  FAILED: 'ошибка',
  SUPERSEDED: 'заменён',
}

function fmt(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

function seconds(a, b) {
  if (!a || !b) return null
  const start = Date.parse(String(a).replace(' ', 'T'))
  const end = Date.parse(String(b).replace(' ', 'T'))
  if (Number.isNaN(start) || Number.isNaN(end)) return null
  return Math.max(0, Math.round((end - start) / 1000))
}

function statusColor(status) {
  return {
    DONE: 'positive',
    FAILED: 'negative',
    RUNNING: 'info',
    STOPPED: 'orange',
    PENDING: 'grey',
    SUPERSEDED: 'grey-7',
  }[status] || 'grey'
}

const hasRuns = computed(() => runs.value.length > 0)

async function load() {
  loading.value = true
  try {
    const data = await fetchPipelineRuns(10)
    runs.value = data.items || []
    available.value = true
  } catch {
    available.value = false
    runs.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card v-if="available" flat bordered>
    <q-card-section class="row items-center">
      <div class="panel-title col">Запуски обновления базы</div>
      <q-btn flat round dense icon="refresh" :loading="loading" @click="load" />
    </q-card-section>
    <q-separator />

    <q-card-section>
      <div v-if="!hasRuns" class="text-grey-7 text-caption">
        Пока не было ни одного запуска.
      </div>

      <div v-for="run in runs" :key="run.run_id" class="pipeline-run q-mb-md">
        <div class="row items-center q-gutter-sm">
          <span class="text-weight-medium">#{{ run.run_id }}</span>
          <q-badge :color="statusColor(run.status)" :label="STATUS_LABELS[run.status] || run.status" />
          <span class="text-caption text-grey-7">
            {{ run.mode }} · {{ fmt(run.started_at || run.created_at) }}
          </span>
        </div>

        <div v-if="run.message" class="text-caption" :class="run.status === 'FAILED' ? 'text-negative' : 'text-grey-8'">
          {{ run.message }}
        </div>

        <div class="row q-gutter-md q-mt-xs">
          <span v-for="stage in run.stages" :key="stage.stage" class="stage-chip">
            {{ STAGE_LABELS[stage.stage] || stage.stage }}:
            <b>{{ stage.status === 'SKIPPED' ? '—' : stage.status.toLowerCase() }}</b>
            <span v-if="seconds(stage.started_at, stage.finished_at) !== null" class="text-grey-7">
              ({{ seconds(stage.started_at, stage.finished_at) }} с)
            </span>
            <span v-if="stage.failed_count" class="text-negative"> · ошибок: {{ stage.failed_count }}</span>
          </span>
        </div>
      </div>
    </q-card-section>
  </q-card>
</template>

<style scoped>
.stage-chip {
  font-size: 12px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 6px;
  padding: 2px 8px;
}

body.body--dark .stage-chip {
  background: rgba(255, 255, 255, 0.08);
}
</style>
