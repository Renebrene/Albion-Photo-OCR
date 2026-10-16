<script setup>
import { onMounted, ref } from 'vue'

import { fetchLastRun } from '../api/client'
import PipelineRunsPanel from './PipelineRunsPanel.vue'
import RunHistoryPanel from './RunHistoryPanel.vue'

const data = ref(null)
const loading = ref(false)
const error = ref(null)

async function load() {
  loading.value = true
  try {
    data.value = await fetchLastRun()
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
      <div class="text-subtitle1 col">Последний запуск</div>
      <q-btn dense flat icon="refresh" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <!-- Прогоны «Обновления базы» идут первыми: это то, за чем следят. -->
    <PipelineRunsPanel class="q-mb-md" />
    <RunHistoryPanel />

    <div v-if="data" class="row q-col-gutter-md">
      <q-card flat bordered class="col-12 col-md-6">
        <q-card-section>
          <div class="text-caption text-grey">DINO batch</div>
          <template v-if="data.dino_batch">
            <div class="text-h6">
              #{{ data.dino_batch.batch_id }}
              <q-badge :label="data.dino_batch.status" class="q-ml-sm" />
            </div>
            <div class="text-caption">
              {{ data.dino_batch.run_type }} ·
              готово {{ data.dino_batch.completed_count }}/{{ data.dino_batch.total_count }}
              · ошибок {{ data.dino_batch.failed_count }}
            </div>
            <div class="text-caption text-grey">{{ data.dino_batch.created_at }}</div>
          </template>
          <div v-else class="text-grey">нет</div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12 col-md-6">
        <q-card-section>
          <div class="text-caption text-grey">HYBRID run</div>
          <template v-if="data.hybrid_run">
            <div class="text-h6">
              #{{ data.hybrid_run.hybrid_run_id }}
              <q-badge :label="data.hybrid_run.status" class="q-ml-sm" />
            </div>
            <div class="text-caption">
              batch {{ data.hybrid_run.dino_batch_id }} ·
              готово {{ data.hybrid_run.completed_count }}/{{ data.hybrid_run.total_count }}
              · ошибок {{ data.hybrid_run.failed_count }}
            </div>
            <div class="text-caption text-grey">{{ data.hybrid_run.created_at }}</div>
          </template>
          <div v-else class="text-grey">нет</div>
        </q-card-section>
      </q-card>

      <q-card flat bordered class="col-12">
        <q-card-section>
          <div class="text-caption text-grey q-mb-xs">Задания в очереди</div>
          <div class="row q-gutter-sm">
            <q-chip
              v-for="(count, status) in data.jobs"
              :key="status"
              dense
            >
              {{ status }}: {{ count }}
            </q-chip>
            <span v-if="!Object.keys(data.jobs).length" class="text-grey">
              пусто
            </span>
          </div>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
