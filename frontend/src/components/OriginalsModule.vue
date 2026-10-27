<script setup>
// Доступность оригиналов (технический раздел → Данные).
//
// Отвечает на вопрос «почему у половины фото оригинал недоступен», не открывая
// карточки: корень без каталога — это отмонтированный том, а не пропавшие файлы
// (живой случай 27.10.2026: 27 974 фото остались на пути отключённого диска
// Win10, а корпус лежал на TEST). Сводка приходит из /v1/originals/health — это
// is_dir() по корням и по одному счётчику на корень в SQL.
//
// Полная пофайловая проверка (57 тыс. stat) идёт заданием: кнопка ставит
// ORIGINALS_CHECK, прогресс приходит из /v1/jobs/{id}, готовый отчёт ложится в
// data/reports и показывается здесь после перезагрузки страницы.
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  fetchJob,
  fetchOriginalsCheckLatest,
  fetchOriginalsHealth,
  startOriginalsCheck,
} from '../api/client'
import { usePoller } from '../composables/usePoller'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const canManage = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

const health = ref(null)
const error = ref(null)
const loading = ref(false)

const report = ref(null)
const reportError = ref(null)
const checkRunning = ref(false)
const jobProgress = ref(null)
const checkJobId = ref(null)

async function load() {
  loading.value = true
  try {
    health.value = await fetchOriginalsHealth()
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function loadLatestReport() {
  try {
    report.value = (await fetchOriginalsCheckLatest()).report
  } catch (err) {
    reportError.value = err.message
  }
}

onMounted(() => {
  load()
  loadLatestReport()
})

const poller = usePoller(
  async () => {
    if (!checkJobId.value) return

    const job = await fetchJob(checkJobId.value)
    jobProgress.value = job.progress || null

    const finished = ['DONE', 'FAILED', 'CANCELLED'].includes(job.status)
    if (!finished) return

    checkRunning.value = false
    checkJobId.value = null
    poller.stop()

    if (job.status === 'DONE' && job.result) {
      // Задание возвращает тот же отчёт, что записан в файл.
      report.value = job.result
      Notify.create({ type: 'positive', message: 'Проверка оригиналов завершена' })
    } else {
      reportError.value = job.error_message || 'Проверка оригиналов не удалась'
    }
  },
  // Первый тик — сразу после постановки задания, чтобы прогресс появился
  // без двухсекундной паузы.
  { intervalMs: 2000, immediate: true },
)

async function runCheck() {
  if (checkRunning.value) return

  checkRunning.value = true
  reportError.value = null
  jobProgress.value = null

  try {
    const started = await startOriginalsCheck()
    checkJobId.value = started.job_id || null

    if (!started.job_id) {
      // Задание не создалось и активного нет — иначе кнопка навсегда осталась
      // бы в загрузке без единого запроса.
      checkRunning.value = false
      reportError.value = 'Не удалось поставить проверку: задание не создано'
      return
    }

    poller.start()
  } catch (err) {
    checkRunning.value = false
    reportError.value = err.message
  }
}

// Тревожимся только о тех отключённых томах, на которых что-то лежит: пустой
// корень в списке (например, старый диск, оставленный в SCENE_ORIGINALS_ROOTS)
// сам по себе никому не мешает.
const affected = computed(() =>
  (health.value?.roots || []).filter((root) => !root.available && root.photos > 0),
)

const affectedPhotos = computed(() =>
  affected.value.reduce((sum, root) => sum + root.photos, 0),
)

const reportUnavailable = computed(() => {
  if (!report.value) return 0
  return (
    (report.value.missing || 0) +
    (report.value.outside_roots || 0) +
    (report.value.root_unavailable || 0)
  )
})

function shortDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU')
}
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle2 col">Доступность оригиналов</div>
      <q-btn dense flat icon="refresh" :loading="loading" aria-label="Обновить" @click="load" />
    </div>

    <q-banner v-if="error" class="bg-red-1 text-negative">
      {{ error }}
    </q-banner>

    <template v-if="health">
      <q-banner v-if="!health.configured" class="bg-orange-1">
        <code>SCENE_ORIGINALS_ROOTS</code> не задан: оригиналы не отдаются вообще.
      </q-banner>

      <template v-else>
        <q-markup-table dense flat bordered>
          <thead>
            <tr>
              <th class="text-left">Том</th>
              <th class="text-left">Путь</th>
              <th class="text-right">Фото</th>
              <th class="text-left">Состояние</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="root in health.roots" :key="root.path">
              <td>{{ root.label }}</td>
              <td class="text-caption text-grey-7">{{ root.path }}</td>
              <td class="text-right">{{ root.photos }}</td>
              <td>
                <span v-if="root.available" class="text-positive">подключён</span>
                <span v-else class="text-negative">не подключён</span>
              </td>
            </tr>
          </tbody>
        </q-markup-table>

        <div class="text-caption text-grey q-mt-sm">
          Всего записей: {{ health.total_photos }} · вне разрешённых корней:
          {{ health.outside_roots }}
        </div>

        <div v-if="affected.length" class="text-caption text-negative q-mt-xs">
          На отключённом томе {{ affected.map((root) => root.label).join(', ') }} —
          {{ affectedPhotos }} фото: у них оригинал недоступен. Смонтируйте том или
          перенесите пути (<code>scripts/remap_source_root.py</code>).
        </div>

        <div class="row items-center q-gutter-sm q-mt-md">
          <q-btn
            v-if="canManage"
            dense
            color="primary"
            icon="fact_check"
            label="Проверить файлы"
            :loading="checkRunning"
            @click="runCheck"
          />
          <div v-if="checkRunning" class="text-caption text-grey">
            <template v-if="jobProgress?.total">
              проверено {{ jobProgress.done }} из {{ jobProgress.total }}
            </template>
            <template v-else>обход корпуса идёт…</template>
          </div>
        </div>

        <div v-if="report" class="text-caption q-mt-xs" :class="reportUnavailable ? 'text-negative' : 'text-grey'">
          Последняя полная проверка: {{ shortDate(report.generated_at) }} ·
          проверено {{ report.checked }} · недоступно {{ reportUnavailable }}
          (вне корней {{ report.outside_roots }}, корень не подключён
          {{ report.root_unavailable }}, файла нет {{ report.missing }})
        </div>
        <div v-else class="text-caption text-grey q-mt-xs">
          Полная проверка файлов ещё не запускалась.
        </div>

        <q-banner v-if="reportError" class="bg-red-1 text-negative q-mt-xs">
          {{ reportError }}
        </q-banner>
      </template>
    </template>
  </div>
</template>
