<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchMediaStatistics } from '../api/client'

const MONTH_NAMES = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
]

const stats = ref(null)
const error = ref(null)
const loading = ref(false)

async function load() {
  loading.value = true

  try {
    stats.value = await fetchMediaStatistics()
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

function part(value, index) {
  const date = String(value).split('T')[0]
  return date.split('-')[index]
}

function day(value) {
  if (!value) return '—'
  return `${part(value, 2)}.${part(value, 1)}.${part(value, 0)}`
}

function stamp(value) {
  if (!value) return '—'
  const [date, time = ''] = String(value).split('T')
  const [y, m, d] = date.split('-')
  const clock = time.slice(0, 5)

  return clock ? `${d}.${m}.${y} ${clock}` : `${d}.${m}.${y}`
}

function monthLabel(value) {
  if (!value) return '—'
  const [year, month] = String(value).split('-')
  return `${MONTH_NAMES[Number(month) - 1] || month} ${year}`
}

function periodLabel() {
  if (!stats.value) return '—'
  const start = stats.value.period_start
  const end = stats.value.period_end

  if (!start || !end) return '—'
  return `${day(start)} — ${day(end)}`
}

const rows = computed(() => {
  const s = stats.value

  if (!s) return []

  return [
    { label: 'Сегодня', photos: s.today_photos, videos: s.today_videos },
    { label: 'Вчера', photos: s.yesterday_photos, videos: s.yesterday_videos },
    { label: 'Позавчера', photos: s.day_before_photos, videos: s.day_before_videos },
    { label: 'За неделю', photos: s.last_7_days_photos, videos: s.last_7_days_videos },
    { label: 'Текущий месяц', photos: s.this_month_photos, videos: s.this_month_videos },
  ]
})

const months = computed(() =>
  (stats.value?.months || []).slice().reverse(),
)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Статистика</div>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load">
        <q-tooltip>Обновить</q-tooltip>
      </q-btn>
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div v-if="!stats && loading" class="row justify-center q-my-lg">
      <q-spinner-dots color="primary" size="40px" />
    </div>

    <template v-if="stats">
      <div class="row q-col-gutter-md q-mb-md">
        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Последняя загрузка фото</div>
              <div class="text-subtitle1">{{ stamp(stats.last_photo_at) }}</div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Последняя загрузка видео</div>
              <div class="text-subtitle1">{{ stamp(stats.last_video_at) }}</div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Всего файлов</div>
              <div class="text-subtitle1">
                {{ stats.photos }} фото · {{ stats.videos }} видео
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Период базы</div>
              <div class="text-subtitle1">{{ periodLabel() }}</div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <div class="row q-col-gutter-md">
        <div class="col-12 col-md-5">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-subtitle2 q-mb-sm">По периодам</div>
              <q-table
                :rows="rows"
                :columns="[
                  { name: 'label', label: 'Период', field: 'label', align: 'left' },
                  { name: 'photos', label: 'Фото', field: 'photos', align: 'right' },
                  { name: 'videos', label: 'Видео', field: 'videos', align: 'right' },
                ]"
                row-key="label"
                dense
                flat
                hide-bottom
                :pagination="{ rowsPerPage: 0 }"
              />
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-md-7">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-subtitle2 q-mb-sm">
                Месяцы ({{ months.length }})
              </div>
              <q-table
                :rows="months"
                :columns="[
                  {
                    name: 'month',
                    label: 'Месяц',
                    field: (row) => monthLabel(row.month),
                    align: 'left',
                    sortable: false,
                  },
                  { name: 'photos', label: 'Фото', field: 'photos', align: 'right' },
                  { name: 'videos', label: 'Видео', field: 'videos', align: 'right' },
                  {
                    name: 'total',
                    label: 'Всего',
                    field: (row) => row.photos + row.videos,
                    align: 'right',
                  },
                ]"
                row-key="month"
                dense
                flat
                hide-bottom
                :pagination="{ rowsPerPage: 0 }"
              />
            </q-card-section>
          </q-card>
        </div>
      </div>
    </template>
  </div>
</template>
