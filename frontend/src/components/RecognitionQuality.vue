<script setup>
// «Качество» — сводка распознавания по прогону HYBRID (владелец, 21.11.2026):
// по каждому адресу видно, сколько фото, сколько из них в слепках, процент
// совпадений с подписью файла, что решило адрес (DINO или соседи) и с каким
// адресом чаще путается. Эталон — название фото, если в нём есть адрес.
import { computed, onMounted, ref } from 'vue'

import {
  fetchRecognitionQualityLive,
  fetchRecognitionQualityRuns,
} from '../api/client'

const data = ref(null)
const runs = ref([])
const runId = ref(null)
const loading = ref(false)
const error = ref('')
const addressFilter = ref('')

const INFLUENCE_LABELS = {
  dino: 'DINO (лучший)',
  neighbors: 'соседи',
  no_dino: 'без DINO',
}

const columns = [
  { name: 'name', label: 'Адрес', field: 'name', align: 'left', sortable: true },
  { name: 'photos', label: 'Всего фото', field: 'photos', align: 'right', sortable: true },
  {
    name: 'fingerprint',
    label: 'В слепке',
    field: 'fingerprint_photos',
    align: 'right',
    sortable: true,
  },
  { name: 'accuracy', label: 'Совпадение', field: 'accuracy', align: 'right', sortable: true },
  { name: 'influence', label: 'Решило', field: 'influence', align: 'left' },
  { name: 'confusion', label: 'Чаще путается', field: 'confused_with', align: 'left' },
]

const rows = computed(() => {
  const query = addressFilter.value.trim().toLocaleLowerCase('ru')

  return (data.value?.addresses || []).filter(
    (item) => !query || String(item.name || '').toLocaleLowerCase('ru').includes(query),
  )
})

const totals = computed(() => data.value?.totals || null)
const run = computed(() => data.value?.run || null)

// «Обновление базы» сортирует только новые файлы: в таком прогоне подписанных
// кадров может быть единицы. Тогда предлагаем ближайший полный прогон, чтобы
// проценты по адресам были осмысленными.
const fullRunSuggestion = computed(() => {
  if (!totals.value || Number(totals.value.labelled || 0) >= 50) return null

  const currentId = run.value?.hybrid_run_id
  const candidates = runs.value.filter(
    (item) => item.hybrid_run_id !== currentId && Number(item.photos || 0) > (run.value?.photos || 0),
  )

  if (!candidates.length) return null

  return candidates.reduce((best, item) =>
    Number(item.photos || 0) > Number(best.photos || 0) ? item : best,
  )
})

function useFullRun() {
  if (!fullRunSuggestion.value) return
  runId.value = fullRunSuggestion.value.hybrid_run_id
  load()
}

// Выбор прогона: последний по умолчанию, но маленькая сортировка новых фото
// («Обновление базы») даёт мало подписанных кадров — можно взять предыдущую
// полную.
const runOptions = computed(() =>
  runs.value.map((item) => ({
    label: `${formatDate(item.finished_at)} · ${formatCount(item.photos)} фото`,
    value: item.hybrid_run_id,
  })),
)

function formatPercent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  return `${(Number(value) * 100).toLocaleString('ru-RU', { maximumFractionDigits: 1 })}%`
}

function formatCount(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  return Number(value).toLocaleString('ru-RU')
}

function formatDate(value) {
  if (!value) return '—'
  const [date, time = ''] = String(value).replace('T', ' ').split(' ')
  const [year, month, day] = date.split('-')

  if (!year || !month || !day) return String(value).slice(0, 16)

  return `${day}.${month}.${year} ${time.slice(0, 5)}`.trim()
}

function influenceLabel(item) {
  if (!item) return '—'

  const name = INFLUENCE_LABELS[item.kind] || item.kind
  const share = item.share === null || item.share === undefined
    ? ''
    : ` · ${Math.round(Number(item.share) * 100)}%`

  return `${name}${share}`
}

function accuracyColor(value) {
  if (value === null || value === undefined) return 'grey-7'
  if (value >= 0.9) return 'positive'
  if (value >= 0.75) return 'orange-9'
  return 'negative'
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    // Список прогонов нужен один раз; данные — по выбранному (null = последний).
    if (!runs.value.length) {
      const response = await fetchRecognitionQualityRuns()
      runs.value = response.items || []
    }

    data.value = await fetchRecognitionQualityLive(runId.value)
  } catch (err) {
    error.value = err.message || 'Не удалось загрузить сводку'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="recognition-quality">
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Качество распознавания</div>
      <q-btn flat dense round icon="refresh" :loading="loading" @click="load">
        <q-tooltip>Обновить сводку</q-tooltip>
      </q-btn>
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div class="row q-col-gutter-md q-mb-md">
      <!-- Прогон: последний завершённый HYBRID и даты сортировки. -->
      <div class="col-12 col-md-5">
        <q-card flat bordered class="fit">
          <q-card-section>
            <div class="text-caption text-grey">Прогон для оценки</div>
            <q-select
              v-model="runId"
              :options="runOptions"
              dense
              outlined
              emit-value
              map-options
              :display-value="runOptions.find((item) => item.value === runId)?.label || 'Последний прогон'"
              label="Сортировка и гибрид"
              class="q-mt-xs"
              @update:model-value="load"
            >
              <template #option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>{{ scope.opt.label }}</q-item-section>
                </q-item>
              </template>
            </q-select>

            <div class="text-caption text-grey-8 q-mt-sm">
              Последняя сортировка: <b>{{ formatDate(run?.last_sort_at) }}</b><br />
              Последний гибрид: <b>{{ formatDate(run?.last_hybrid_at) }}</b>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- Общий результат точности. -->
      <div class="col-12 col-md-7">
        <q-card flat bordered class="fit">
          <q-card-section>
            <div class="row items-end no-wrap">
              <div class="col">
                <div class="text-caption text-grey">Точность по подписанным фото</div>
                <div
                  class="text-h4"
                  :class="`text-${accuracyColor(totals?.accuracy)}`"
                >
                  {{ formatPercent(totals?.accuracy) }}
                </div>
                <div class="text-caption text-grey-8">
                  Верно {{ formatCount(totals?.correct) }}
                  из {{ formatCount(totals?.labelled) }} подписанных
                  <template v-if="totals?.wrong">
                    · ошибок {{ formatCount(totals.wrong) }}
                  </template>
                </div>
              </div>
              <div class="col-auto q-ml-md text-right">
                <div class="text-caption text-grey">Фото в прогоне</div>
                <div class="text-subtitle1">{{ formatCount(totals?.photos) }}</div>
                <div class="text-caption text-grey">
                  без адреса в имени: {{ formatCount(totals?.no_label) }}
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-banner
      v-if="fullRunSuggestion"
      dense
      rounded
      class="bg-blue-1 text-dark q-mb-md"
    >
      В этом прогоне мало подписанных кадров ({{ formatCount(totals?.labelled) }}) —
      проценты по адресам почти не на чем считать.
      <template v-if="fullRunSuggestion">
        <q-btn
          dense
          flat
          no-caps
          color="primary"
          :label="`Взять полный прогон (${formatCount(fullRunSuggestion.photos)} фото)`"
          @click="useFullRun"
        />
      </template>
    </q-banner>

    <q-card flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-sm">
          <div class="text-subtitle2 col">
            Совпадение по адресам
            <span class="text-caption text-grey-7">
              — эталон берётся из названия фото, поэтому в расчёт входят только
              подписанные кадры
            </span>
          </div>
          <q-input
            v-model="addressFilter"
            dense
            outlined
            clearable
            debounce="200"
            label="Поиск адреса"
            style="max-width: 260px"
          />
        </div>

        <div class="quality-table-scroll">
          <q-table
            :rows="rows"
            :columns="columns"
            :loading="loading"
            row-key="address_id"
            :pagination="{ rowsPerPage: 0 }"
            hide-bottom
            flat
            dense
            no-data-label="Нет данных за выбранный прогон"
          >
            <template #body-cell-name="props">
              <q-td :props="props">
                <span class="ellipsis">{{ props.row.name }}</span>
              </q-td>
            </template>

            <template #body-cell-fingerprint="props">
              <q-td :props="props">
                {{ formatCount(props.row.fingerprint_photos) }}
              </q-td>
            </template>

            <template #body-cell-accuracy="props">
              <q-td :props="props">
                <span :class="`text-${accuracyColor(props.row.accuracy)}`">
                  {{ formatPercent(props.row.accuracy) }}
                </span>
                <q-tooltip v-if="props.row.labelled">
                  Верно {{ props.row.correct }} из {{ props.row.labelled }}
                  подписанных; ошибок {{ props.row.wrong }}
                </q-tooltip>
              </q-td>
            </template>

            <template #body-cell-influence="props">
              <q-td :props="props">
                {{ influenceLabel(props.row.influence) }}
                <q-tooltip v-if="props.row.influence">
                  <template
                    v-for="(count, kind) in props.row.influence.counts"
                    :key="kind"
                  >
                    {{ INFLUENCE_LABELS[kind] || kind }}: {{ count }}<br />
                  </template>
                </q-tooltip>
              </q-td>
            </template>

            <template #body-cell-confusion="props">
              <q-td :props="props">
                <template v-if="props.row.confused_with">
                  {{ props.row.confused_with.name }}
                  <span class="text-grey-7">· {{ props.row.confused_with.count }}</span>
                </template>
                <span v-else class="text-grey-6">—</span>
                <q-tooltip v-if="props.row.confused_with">
                  {{ props.row.confused_with.count }}
                  {{ props.row.confused_with.count === 1 ? 'кадр' : 'кадров' }}
                  подписаны этим адресом, но отнесены к другому
                </q-tooltip>
              </q-td>
            </template>
          </q-table>
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<style scoped>
.quality-table-scroll {
  max-height: min(70vh, 640px);
  overflow-y: auto;
  overscroll-behavior: contain;
}
</style>
