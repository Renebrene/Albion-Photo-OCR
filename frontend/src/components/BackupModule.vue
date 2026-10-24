<script setup>
// Бэкапы и восстановление (технический раздел → Данные).
//
// Раздел ничего не решает сам: пути, расписание и опись приходят из
// /v1/backup/status, а сами бэкап и восстановление идут работой в очереди —
// дамп на 50 МБ и архив на 360 МБ не должны ждать HTTP-запрос. Поэтому здесь
// есть опрос работы и честный прогресс, а не «крутилка» на кнопке.
//
// Восстановление поверх рабочей установки требует ввести имя базы (или слово
// «на место»): это защита от промаха мышью, а не от недоверия к администратору.
import { computed, onMounted, ref } from 'vue'
import { Dialog, Notify } from 'quasar'

import {
  fetchBackupArchive,
  fetchBackupStatus,
  fetchJob,
  runBackupNow,
  runRestoreNow,
  saveBackupSettings,
} from '../api/client'
import { usePoller } from '../composables/usePoller'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()
const canManage = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

const status = ref(null)
const error = ref(null)
const loading = ref(false)

const parts = ref({ database: true, data: true, models: false })
const running = ref(false)
const job = ref(null)
const jobKind = ref(null)
const progress = ref(null)

const dirDraft = ref('')
const retentionDraft = ref({ keep_daily: 14, keep_weekly: 8, keep_monthly: 6 })
const savingSettings = ref(false)

const archiveOpen = ref(false)
const archiveName = ref('')
const archiveMembers = ref([])
const archiveSelected = ref([])
const archiveLoading = ref(false)
const archiveError = ref(null)

function humanBytes(value) {
  if (value == null) return '—'
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']
  let size = value
  let i = 0
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i += 1
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function humanDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

const KIND_LABELS = { database: 'база данных', data: 'данные и слепки' }

async function load() {
  if (loading.value) return
  loading.value = true

  try {
    status.value = await fetchBackupStatus()
    dirDraft.value = status.value.backup_dir
    retentionDraft.value = { ...status.value.retention }
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// Опрос работы: пока она идёт, обновления раз в две секунды; скрытая вкладка
// молчит (usePoller), а размонтирование останавливает опрос.
const poller = usePoller(
  async () => {
    if (!job.value) return
    const fresh = await fetchJob(job.value.id)
    job.value = fresh
    progress.value = fresh.progress || null
    if (['DONE', 'FAILED', 'CANCELLED'].includes(fresh.status)) {
      poller.stop()
      running.value = false
      if (fresh.status === 'DONE') {
        Notify.create({ type: 'positive', message: `${jobKind.value} — готово` })
      } else {
        Notify.create({
          type: 'negative',
          message: `${jobKind.value}: ${fresh.error_message || 'ошибка'}`,
        })
      }
      await load()
    }
  },
  // Первый опрос сразу: работа могла быть поставлена только что, и ждать
  // два секунды, чтобы показать «в очереди», незачем.
  { intervalMs: 2000, immediate: true },
)

function watchJob(response, kind) {
  job.value = { id: response.job_id, status: 'PENDING' }
  jobKind.value = kind
  progress.value = { done: 0, total: 1, stage: 'в очереди', percent: 0 }
  running.value = true
  poller.start()
}

async function startBackup() {
  const chosen = Object.entries(parts.value)
    .filter(([, on]) => on)
    .map(([name]) => name)

  if (!chosen.length) {
    Notify.create({ type: 'warning', message: 'Отметьте, что копировать' })
    return
  }

  try {
    watchJob(await runBackupNow(chosen), 'Бэкап')
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

function askPrompt({ title, message, label, okLabel, okColor = 'negative' }) {
  return new Promise((resolve) => {
    Dialog.create({
      title,
      message,
      prompt: { model: '', label, filled: true },
      ok: { label: okLabel, color: okColor, noCaps: true },
      cancel: { label: 'Отмена', flat: true, noCaps: true },
      persistent: true,
    })
      .onOk((value) => resolve(String(value ?? '')))
      .onCancel(() => resolve(null))
      .onDismiss(() => resolve(null))
  })
}

async function restoreDatabase(backup) {
  if (!canManage.value) return

  const working = status.value.working_database
  const typed = await askPrompt({
    title: 'Восстановление базы данных',
    message:
      `Файл: ${backup.name}. ` +
      `Введите имя базы, в которую восстанавливать. Рабочая база — ${working}: ` +
      'восстановление в неё перезапишет текущие данные (их придётся вводить снова).',
    label: 'Имя базы данных',
    okLabel: 'Восстановить',
  })

  if (typed === null) return
  const target = typed.trim()

  if (!target) {
    Notify.create({ type: 'warning', message: 'Имя базы не введено' })
    return
  }

  try {
    const payload = { file: backup.name, target: 'database', target_db: target }

    if (target === working) {
      payload.confirm = target
      payload.allow_production = true
    }

    watchJob(await runRestoreNow(payload), 'Восстановление базы')
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function restoreAll(backup) {
  await restoreFiles(backup, { inPlace: false, members: null })
}

async function restoreFiles(backup, { inPlace, members }) {
  if (!canManage.value) return

  let targetDir = null
  let confirm = null

  if (inPlace) {
    confirm = await askPrompt({
      title: 'Восстановление «на место»',
      message:
        'Файлы будут записаны поверх рабочих: слепки, логи, отчёты, env-файл ' +
        `и модели. Текущие файлы будут перезаписаны. Чтобы продолжить, введите слово «на место».`,
      label: 'Подтверждение',
      okLabel: 'Перезаписать',
    })

    if (confirm === null) return

    if (confirm.trim().toLowerCase() !== 'на место') {
      Notify.create({ type: 'warning', message: 'Слово подтверждения введено неверно' })
      return
    }
  } else {
    const typed = await askPrompt({
      title: 'Восстановление в отдельную папку',
      message:
        'Файлы будут распакованы в отдельную папку, рабочие данные не изменятся. ' +
        'Оставьте поле пустым для папки по умолчанию (data/restored), или укажите свой путь.',
      label: 'Каталог (необязательно)',
      okLabel: 'Восстановить',
      okColor: 'primary',
    })

    if (typed === null) return
    targetDir = typed.trim() || null
  }

  try {
    watchJob(
      await runRestoreNow({
        file: backup.name,
        target: 'files',
        members,
        target_dir: targetDir,
        in_place: inPlace,
        overwrite: inPlace,
        confirm,
      }),
      'Восстановление файлов',
    )
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function openArchive(backup) {
  archiveOpen.value = true
  archiveName.value = backup.name
  archiveMembers.value = []
  archiveSelected.value = []
  archiveError.value = null
  archiveLoading.value = true

  try {
    const response = await fetchBackupArchive(backup.name)
    archiveMembers.value = response.members
    // Слепки и модель — то, ради чего сюда обычно и заходят.
    archiveSelected.value = response.members.filter(
      (name) => name.startsWith('data/fingerprints/') || name.startsWith('models/'),
    )
  } catch (err) {
    archiveError.value = err.message
  } finally {
    archiveLoading.value = false
  }
}

async function restoreSelected() {
  const backup = { name: archiveName.value }
  const members = [...archiveSelected.value]
  archiveOpen.value = false

  if (!members.length) {
    Notify.create({ type: 'warning', message: 'Ничего не выбрано' })
    return
  }

  await restoreFiles(backup, { inPlace: false, members })
}

async function saveSettings() {
  savingSettings.value = true

  try {
    status.value = await saveBackupSettings({
      backup_dir: dirDraft.value.trim(),
      retention: { ...retentionDraft.value },
    })
    Notify.create({ type: 'positive', message: 'Настройки бэкапов сохранены' })
    error.value = null
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    savingSettings.value = false
  }
}

const groupedBackups = computed(() => {
  const rows = status.value?.backups || []
  const groups = new Map()

  for (const item of rows) {
    const group = groups.get(item.stamp) || { stamp: item.stamp, created: item.created, items: [] }
    group.items.push(item)
    groups.set(item.stamp, group)
  }

  return [...groups.values()]
})

onMounted(load)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle2 col">Бэкапы</div>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <div v-if="status" class="column q-gutter-md">
      <!-- Работа в очереди: бэкап и восстановление идут ей, а не запросу. -->
      <q-banner v-if="running" class="bg-blue-1">
        <div class="row items-center">
          <q-spinner-dots size="20px" color="primary" class="q-mr-sm" />
          <div class="col">
            {{ jobKind }}:
            {{ progress?.stage || job?.status }}
            <span v-if="progress?.total">
              — {{ progress.done }} / {{ progress.total }} ({{ Math.round(progress.percent || 0) }} %)
            </span>
          </div>
        </div>
      </q-banner>

      <q-banner v-else-if="job && job.status === 'FAILED'" class="bg-red-1 text-negative">
        {{ jobKind }}: {{ job.error_message }}
      </q-banner>

      <!-- Пути -->
      <q-card flat bordered>
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Пути</div>

          <q-markup-table dense flat bordered>
            <tbody>
              <tr>
                <td>Каталог бэкапов</td>
                <td>
                  {{ status.backup_dir }}
                  <q-chip
                    v-if="status.directory.same_filesystem_as_project"
                    dense
                    color="orange-2"
                    text-color="orange-9"
                    label="тот же том, что и проект"
                  />
                  <q-chip
                    v-else
                    dense
                    color="green-2"
                    text-color="green-9"
                    label="отдельный том"
                  />
                  <q-chip
                    v-if="!status.directory.mounted"
                    dense
                    color="red-2"
                    text-color="red-9"
                    label="диск не смонтирован"
                  />
                </td>
              </tr>
              <tr>
                <td>Свободно на диске</td>
                <td>
                  {{ humanBytes(status.disk.free) }} из {{ humanBytes(status.disk.total) }}
                  <span class="text-grey">(занято {{ status.disk.used_pct }} %)</span>
                </td>
              </tr>
              <tr>
                <td>Данные проекта</td>
                <td>{{ status.data_dir }}</td>
              </tr>
              <tr>
                <td>Рабочая база</td>
                <td>{{ status.working_database }}</td>
              </tr>
            </tbody>
          </q-markup-table>

          <div v-if="canManage" class="row q-col-gutter-sm items-end q-mt-sm">
            <q-input
              v-model="dirDraft"
              dense
              outlined
              class="col-12 col-md-6"
              label="Каталог бэкапов"
              hint="Создаётся только под смонтированным диском; том проекта отклоняется"
            />
            <q-input
              v-model.number="retentionDraft.keep_daily"
              dense
              outlined
              type="number"
              class="col-4 col-md-2"
              label="Дней"
            />
            <q-input
              v-model.number="retentionDraft.keep_weekly"
              dense
              outlined
              type="number"
              class="col-4 col-md-2"
              label="Недель"
            />
            <q-input
              v-model.number="retentionDraft.keep_monthly"
              dense
              outlined
              type="number"
              class="col-4 col-md-2"
              label="Месяцев"
            />
            <q-btn
              color="primary"
              label="Сохранить"
              :loading="savingSettings"
              @click="saveSettings"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Расписание -->
      <q-card flat bordered>
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Расписание</div>

          <q-markup-table dense flat bordered>
            <tbody>
              <tr>
                <td>Юнит</td>
                <td>
                  {{ status.schedule.unit }}
                  <q-chip
                    dense
                    :color="status.schedule.active ? 'green-2' : 'grey-3'"
                    :text-color="status.schedule.active ? 'green-9' : 'grey-8'"
                    :label="status.schedule.active ? 'активен' : 'не активен'"
                  />
                </td>
              </tr>
              <tr>
                <td>Расписание</td>
                <td>{{ status.schedule.on_calendar || '—' }}</td>
              </tr>
              <tr>
                <td>Следующий запуск</td>
                <td>{{ status.schedule.next_human || '—' }}</td>
              </tr>
              <tr>
                <td>Последний запуск</td>
                <td>{{ status.schedule.last_human || '—' }}</td>
              </tr>
            </tbody>
          </q-markup-table>

          <div class="text-caption text-grey q-mt-sm">
            Время запуска и сроки хранения задаются в юните
            <code>~/.config/systemd/user/scene-backup.timer</code>; здесь их видно,
            а каталог и retention правятся выше (сохраняются в настройках приложения).
          </div>
        </q-card-section>
      </q-card>

      <!-- Ручной бэкап -->
      <q-card flat bordered>
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">Ручной бэкап</div>

          <div class="row q-col-gutter-md items-center">
            <q-checkbox v-model="parts.database" label="База данных" />
            <q-checkbox v-model="parts.data" label="Данные и слепки" />
            <q-checkbox v-model="parts.models" label="Модели (DINOv2 + детектор)" />
            <q-space />
            <q-btn
              color="primary"
              icon="backup"
              label="Создать бэкап"
              :disable="!canManage || running"
              :loading="running"
              @click="startBackup"
            />
          </div>

          <div class="text-caption text-grey q-mt-sm">
            Слепки (38 штук, 23 МБ) всегда едут в архиве данных — пересборка занимает
            часы. Модели — это ещё ~350 МБ, они меняются раз в полгода: без них
            восстановленные слепки нельзя использовать, но ежедневный бэкап они
            утяжеляют, поэтому по умолчанию выключены.
            <span v-if="!canManage"> Запуск доступен только Администратору.</span>
          </div>
        </q-card-section>
      </q-card>

      <!-- Список бэкапов и восстановление -->
      <q-card flat bordered>
        <q-card-section>
          <div class="text-subtitle2 q-mb-sm">
            Бэкапы в каталоге ({{ status.backups.length }})
          </div>

          <div v-if="!status.backups.length" class="text-caption text-grey">
            В каталоге пока нет ни дампов, ни архивов данных.
          </div>

          <div v-for="group in groupedBackups" :key="group.stamp" class="q-mb-md">
            <div class="text-caption text-grey">
              {{ humanDate(group.created) }}
            </div>

            <q-markup-table dense flat bordered>
              <thead>
                <tr>
                  <th class="text-left">Файл</th>
                  <th class="text-left">Тип</th>
                  <th class="text-right">Размер</th>
                  <th class="text-left">sha256</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                <tr v-for="backup in group.items" :key="backup.name">
                  <td class="ellipsis" style="max-width: 320px">{{ backup.name }}</td>
                  <td>{{ KIND_LABELS[backup.kind] || backup.kind }}</td>
                  <td class="text-right">{{ humanBytes(backup.size) }}</td>
                  <td class="text-grey">
                    {{ backup.sha256 ? backup.sha256.slice(0, 12) + '…' : '—' }}
                  </td>
                  <td class="text-right">
                    <template v-if="canManage">
                      <q-btn
                        v-if="backup.kind === 'database'"
                        dense
                        flat
                        color="primary"
                        icon="settings_backup_restore"
                        label="В базу"
                        :disable="running"
                        @click="restoreDatabase(backup)"
                      />
                      <template v-else>
                        <q-btn
                          dense
                          flat
                          color="primary"
                          icon="restore"
                          label="В папку"
                          :disable="running"
                          @click="restoreAll(backup)"
                        />
                        <q-btn
                          dense
                          flat
                          icon="checklist"
                          label="Выбрать файлы"
                          :disable="running"
                          @click="openArchive(backup)"
                        />
                        <q-btn
                          dense
                          flat
                          color="negative"
                          icon="warning"
                          label="На место"
                          :disable="running"
                          @click="restoreFiles(backup, { inPlace: true, members: null })"
                        />
                      </template>
                    </template>
                  </td>
                </tr>
              </tbody>
            </q-markup-table>
          </div>

          <div class="text-caption text-grey">
            «В папку» распаковывает архив в data/restored (или в указанный каталог) и
            ничего не перезаписывает. «На место» пишет поверх рабочих файлов и требует
            подтверждения. Восстановление базы в отдельную БД требует, чтобы она уже
            существовала:
            <code>sudo -u postgres createdb -O lora_ingest имя_базы</code>.
          </div>
        </q-card-section>
      </q-card>
    </div>

    <!-- Выбор файлов внутри архива -->
    <q-dialog v-model="archiveOpen">
      <q-card style="min-width: 640px; max-width: 90vw">
        <q-card-section class="text-subtitle2">
          Файлы архива
          <div class="text-caption text-grey">{{ archiveName }}</div>
        </q-card-section>

        <q-card-section v-if="archiveLoading" class="text-center">
          <q-spinner-dots size="32px" color="primary" />
        </q-card-section>

        <q-card-section v-else-if="archiveError" class="text-negative">
          {{ archiveError }}
        </q-card-section>

        <q-card-section v-else style="max-height: 50vh; overflow: auto">
          <div class="text-caption text-grey q-mb-sm">
            Отмечено {{ archiveSelected.length }} из {{ archiveMembers.length }}
          </div>
          <q-option-group
            v-model="archiveSelected"
            :options="archiveMembers.map((name) => ({ label: name, value: name }))"
            type="checkbox"
            dense
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn
            color="primary"
            label="Восстановить выбранные в папку"
            :disable="!archiveSelected.length"
            @click="restoreSelected"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>
