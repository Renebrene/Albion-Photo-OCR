<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Dark, Notify } from 'quasar'
import { useRouter } from 'vue-router'

import PipelineUpdateButton from './components/PipelineUpdateButton.vue'
import { fetchMediaStatistics, fetchStats } from './api/client'
import { ADDRESS_CLIENT_MODES, useDisplayStore } from './stores/display'
import { usePipelineStore } from './stores/pipeline'
import { usePhotosStore } from './stores/photos'
import { useSessionStore } from './stores/session'

const router = useRouter()

const session = useSessionStore()
const photos = usePhotosStore()
const display = useDisplayStore()
const pipeline = usePipelineStore()

const password = ref('')
const loginName = ref('')

// The interface is drawn only once the user's settings are in place: otherwise
// the grid would flash the default layout and then rearrange itself.
const booted = ref(false)

// Технический раздел — только Администратору. В открытом демо-режиме
// (SCENE_AUTH_REQUIRED=0) ограничений нет.
const canUseTech = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

// «Обновление базы» запускают обе рабочие роли (Администратор и Менеджер).
const canRunPipeline = computed(
  () =>
    !session.authEnabled ||
    ['Администратор', 'Менеджер'].includes(session.user?.role),
)

// Счётчики подвала — только Администратору. Запрос считает по всему корпусу
// (см. docs/roadmap_ui_audit_20261024.md), а Менеджеру и Гостю эти числа
// ничего не решают. Поэтому остальным подвал не запрашивается вовсе, а не
// просто не показывается. В открытом демо-режиме ограничений нет.
//
// Сам подвал при этом остаётся у всех: в нём переключатель ○△□, руководство
// и метка сборки — по ним проверяют свежесть страницы после Ctrl+F5.
const canSeeStats = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

onMounted(async () => {
  await session.load()

  if (needsLogin()) {
    booted.value = true
  } else {
    await afterAuth()
  }

  // Подвал может обернуть содержимое при узком окне — измеряем и при изменении.
  window.addEventListener('resize', measureChrome)
  // Не терять последние 800 мс изменений при закрытии вкладки.
  window.addEventListener('pagehide', flushDisplay)

  await checkBuild()
  buildTimer = window.setInterval(checkBuild, 5 * 60 * 1000)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', measureChrome)
  window.removeEventListener('pagehide', flushDisplay)
  if (statsTimer !== null) window.clearInterval(statsTimer)
  if (buildTimer !== null) window.clearInterval(buildTimer)
  pipeline.stop()
})

function reloadPage() {
  // Именно перезагрузка, а не reload(true): так браузер сам перепроверит
  // index.html (он отдаётся с no-cache) и заберёт новые хешированные бандлы.
  window.location.reload()
}

function flushDisplay() {
  display.flush()
}

async function afterAuth() {
  // Гость только смотрит: его раскладка не сохраняется ни на сервере, ни
  // в localStorage. Рабочие роли получают свой ключ настроек.
  const canPersist = !session.authEnabled || session.user?.role !== 'Гость'
  const userKey = canPersist
    ? (!session.authEnabled
        ? 'local'
        : String(session.user?.user_id || session.user?.name || 'user'))
    : 'guest'

  display.setPersistence(false)
  display.setUserKey(userKey, { migrate: canPersist })
  display.setPersistence(canPersist)
  if (!canPersist) display.reset()

  // Выделения адресов и клиентов не переживают сессию: при входе грид
  // показывает все фото. Настройки отображения при этом по-прежнему
  // сохраняются за рабочими ролями.
  photos.loadSelectionState({ persist: false })
  // The display settings follow the user, not the browser. A Guest always
  // starts from the built-in defaults and never persists them.
  if (canPersist) await display.loadFromServer()

  if (canSeeStats.value) {
    await loadStats()
    if (statsTimer === null) statsTimer = window.setInterval(loadStats, 60_000)
  }
  // Стадию прогона опрашивает шапка: она видна на любой странице. Гостю
  // число совпадений недоступно (нет jobs:read), но стадия показывается.
  pipeline.start(() => ({ withMatched: canRunPipeline.value }))
  booted.value = true

  // Шапка и подвал уже отрисованы: измеряем их и отдаём размер странице фото,
  // чтобы низ грида упирался ровно в подвал (никаких зашитых 85 px).
  await nextTick()
  measureChrome()
}

// ---- шапка и подвал: их суммарная высота ----

const headerRef = ref(null)
const footerRef = ref(null)

function measureChrome() {
  const header = headerRef.value?.$el?.getBoundingClientRect().height || 50
  const footer = footerRef.value?.$el?.getBoundingClientRect().height || 35

  document.documentElement.style.setProperty(
    '--app-chrome',
    `${Math.round(header + footer)}px`,
  )
}

// ---- подвал: сводка по базе ----

// Время сборки подставляет Vite (см. define в vite.config.js). typeof здесь не
// для красоты: если подстановка не сработала (сборка другим инструментом,
// тесты), обычное обращение обрушило бы всё приложение, а не подпись в подвале.
const build = typeof __APP_BUILD__ === 'string' ? __APP_BUILD__ : '—'

// Метка сборки на сервере. Открытая вкладка живёт часами и молча показывает
// старый интерфейс — тогда новую кнопку или настройку «не видно», хотя она уже
// развёрнута. Сравниваем свою метку с /build.json (его пишет сборка) и
// предлагаем обновиться.
const serverBuild = ref(null)
const buildStale = computed(
  () => !!serverBuild.value && serverBuild.value !== build,
)
let buildTimer = null

async function checkBuild() {
  try {
    const response = await fetch('/build.json', { cache: 'no-store' })
    if (!response.ok) return
    const data = await response.json()
    serverBuild.value = typeof data?.build === 'string' ? data.build : null
  } catch {
    // Файла нет (старая сборка) — подсказка просто не появляется.
  }
}

const stats = ref({
  photos: null,
  videos: null,
  period_photos: null,
  period_videos: null,
  addresses: null,
  clients: null,
  last_photo_at: null,
  last_video_at: null,
})
const statsDialogOpen = ref(false)
const mediaStats = ref(null)
const mediaStatsLoading = ref(false)
let statsTimer = null

// Счётчик запросов: быстрые смены периода не должны оставлять старые числа.
let statsRequest = 0

async function loadStats() {
  // Счётчики — только Администратору: см. canSeeStats.
  if (!canSeeStats.value) return

  const request = ++statsRequest

  try {
    // «Медиа за период» follows the grid's current date filter.
    const data = await fetchStats({
      dateFrom: photos.dateFrom,
      dateTo: photos.dateTo,
      dateMode: photos.dateMode,
    })

    if (request !== statsRequest) return
    stats.value = data
  } catch {
    // Подвал — вспомогательная информация: без неё окно работает как обычно.
  }
}

// Период меняется в гриде; подвал должен обновиться сразу, не ждать минуту.
watch(
  () => [photos.dateFrom, photos.dateTo, photos.dateMode],
  () => {
    if (session.user && canSeeStats.value) void loadStats()
  },
)

const periodLabel = computed(() => {
  const from = photos.dateFrom
  const to = photos.dateTo

  if (!from && !to) return 'За всё время'

  const fmt = (value) => {
    if (!value) return '…'
    const [year, month, day] = String(value).split('-')
    return year && month && day ? `${day}.${month}.${year}` : String(value)
  }

  if (from && to && from === to) return `За ${fmt(from)}`

  return `За период ${fmt(from)} — ${fmt(to)}`
})

// «14.10.2026» — дата последнего добавления фото.
const lastPhoto = computed(() => {
  const value = stats.value.last_photo_at

  if (!value) return '—'

  const [date] = String(value).split(/[T ]/)

  const [year, month, day] = date.split('-')

  return year && month && day ? `${day}.${month}.${year}` : date
})

const lastPhotoFull = computed(() => {
  const value = stats.value.last_photo_at

  return value ? String(value).replace('T', ' ').slice(0, 19) : 'нет данных'
})

const lastVideo = computed(() => {
  const value = stats.value.last_video_at
  if (!value) return '—'
  const [date] = String(value).split(/[T ]/)
  const [year, month, day] = date.split('-')
  return year && month && day ? `${day}.${month}.${year}` : date
})

const lastVideoFull = computed(() => {
  const value = stats.value.last_video_at
  return value ? String(value).replace('T', ' ').slice(0, 19) : 'нет данных'
})

async function openStats() {
  statsDialogOpen.value = true
  mediaStatsLoading.value = true
  try {
    mediaStats.value = await fetchMediaStatistics()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Не удалось загрузить статистику' })
  } finally {
    mediaStatsLoading.value = false
  }
}

// Auth is required and nobody is logged in: show the login screen.
function needsLogin() {
  return session.authEnabled && !session.user
}

// Сервер не ответил на /auth/me (сеть, 5xx). Пробуем ещё раз: пока ответа нет,
// приложение показывает экран входа с причиной.
async function retryAuth() {
  const ok = await session.load()

  if (ok && !needsLogin()) {
    booted.value = true
    await afterAuth()
  }
}

async function doLogin() {
  try {
    const user = await session.login(loginName.value, password.value)
    Notify.create({ type: 'positive', message: `Вы вошли как ${user.name}` })

    // Restore the settings first, then open the main window (the gallery).
    await afterAuth()
    await router.push('/')
  } catch (err) {
    booted.value = true
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function doLogout() {
  // Успеть сохранить последние изменения настроек до сброса токена.
  await display.flush()
  pipeline.stop()
  await session.logout()
  Notify.create({ type: 'info', message: 'Выход выполнен' })

  // The next user starts from the front page, whatever page this one was on.
  await router.push('/')
}

// Тема: значок отражает текущее состояние (солнце — светлая, месяц — тёмная).
const darkMode = ref(Dark.isActive)

function toggleDark() {
  Dark.toggle()
  darkMode.value = Dark.isActive
}
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header ref="headerRef" elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>АЛЬБИОН: Фотобаза</q-toolbar-title>

        <!-- Обновление базы: запускает/ведёт полный прогон. Виден, только
             когда серверный супервизор уже развёрнут. -->
        <PipelineUpdateButton
          v-if="canRunPipeline"
          :can-run="canRunPipeline"
          :busy="pipeline.qwenBusy"
          @finished="loadStats"
        />

        <!-- Распознавание (QWEN): своя очередь, идёт и вне прогона базы. -->
        <div
          v-if="pipeline.qwenText"
          class="row items-center no-wrap text-caption q-ml-md q-mr-sm header-qwen-live"
        >
          <span v-if="pipeline.qwenBusy" class="blink-dot q-mr-xs" />
          <span>
            {{ pipeline.qwenText }}
            <q-tooltip>
              Обработано / всего в текущей выборке распознавания
              <template v-if="pipeline.qwenTitle"> · {{ pipeline.qwenTitle }}</template>
            </q-tooltip>
          </span>
        </div>

        <!-- Стадия прогона и число совпадений — рядом с кнопкой, которая его
             запускает. Видно с любой страницы, а не только из грида. -->
        <div
          v-if="pipeline.text"
          class="row items-center no-wrap text-caption q-mr-sm header-pipeline-live"
        >
          <q-spinner-dots size="14px" class="q-mr-xs" />
          <span class="ellipsis">{{ pipeline.text }}</span>
        </div>

        <q-btn
          flat
          round
          dense
          :icon="darkMode ? 'dark_mode' : 'light_mode'"
          @click="toggleDark"
        >
          <q-tooltip>{{ darkMode ? 'Тёмная тема' : 'Светлая тема' }}</q-tooltip>
        </q-btn>

        <!-- Главный экран выделен плашкой, как блок пользователя. -->
        <q-tabs
          v-if="session.user || !session.authEnabled"
          align="right"
          shrink
          class="header-gallery"
        >
          <q-route-tab to="/" icon="photo_library" label="Фотогалерея" exact />
          <q-route-tab to="/videos" icon="movie" label="Видео" exact />
        </q-tabs>

        <!-- Технический раздел: шестерёнка вместо вкладки. Доступен только
             Администратору и Менеджеру — у Гостя его нет вовсе. -->
        <q-btn
          v-if="canUseTech"
          flat
          round
          dense
          icon="settings"
          class="q-ml-md"
          to="/technical"
        >
          <q-tooltip>Технический раздел</q-tooltip>
        </q-btn>

        <!-- Пользователь и выход: справа от шестерёнки, выделены плашкой. -->
        <div v-if="session.user" class="header-user row items-center no-wrap q-ml-md">
          <q-avatar
            :style="{ background: session.user.color || '#1976d2' }"
            size="28px"
            text-color="white"
          >
            {{ (session.user.name || '?').slice(0, 1) }}
          </q-avatar>

          <div class="q-ml-sm text-weight-medium">{{ session.user.name }}</div>

          <q-btn
            flat
            dense
            icon="logout"
            label="Выйти"
            class="q-ml-md"
            @click="doLogout"
          />
        </div>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <div
        v-if="needsLogin()"
        class="flex flex-center"
        style="min-height: 70vh"
      >
        <q-card style="width: 360px">
          <q-card-section class="text-subtitle1">Вход</q-card-section>
          <q-separator />
          <q-card-section class="q-gutter-md">
            <q-banner
              v-if="session.authError"
              dense
              class="bg-orange-1 text-orange-10"
            >
              {{ session.authError }}
              <template #action>
                <q-btn
                  flat
                  dense
                  no-caps
                  label="Повторить"
                  @click="retryAuth"
                />
              </template>
            </q-banner>
            <q-input
              v-model="loginName"
              dense
              outlined
              label="Имя пользователя"
              @keyup.enter="doLogin"
            />
            <q-input
              v-model="password"
              type="password"
              dense
              outlined
              label="Пароль"
              @keyup.enter="doLogin"
            />
            <div class="login-hint">
              <div>
                <b>Гостевой доступ:</b> логин <code>гость</code>,
                пароль <code>альбион</code>.
              </div>
              <div>
                Настройки гостя между входами не сохраняются; настройки
                Менеджера и Администратора сохраняются за пользователем.
              </div>
            </div>
            <div class="text-caption text-grey">
              Пароль остальных пользователей задаёт администратор. Если вход не
              срабатывает — обратитесь к администратору сервера.
            </div>
          </q-card-section>
          <q-card-actions align="right">
            <q-btn color="primary" label="Войти" @click="doLogin" />
          </q-card-actions>
        </q-card>
      </div>

      <!-- Пока настройки пользователя не загружены, экран не рисуем: иначе
           грид мелькнёт раскладкой по умолчанию и перестроится. -->
      <div v-else-if="!booted" class="flex flex-center" style="min-height: 70vh">
        <q-spinner-dots color="primary" size="36px" />
      </div>

      <router-view v-else />
    </q-page-container>

    <!-- Подвал-статусбар на всю ширину: грид и боковые панели упираются в него. -->
    <q-footer ref="footerRef" v-if="session.user" class="app-footer">
      <div class="row items-center no-wrap full-width q-px-md">
        <q-btn
          flat
          dense
          no-caps
          icon="help_outline"
          label="Руководство пользователя"
          to="/help"
        />

        <q-space />

        <!-- Режим совместного выбора адресов и клиентов: ○ объединение,
             △ приоритет адресов, □ приоритет клиентов. -->
        <div class="footer-mode row items-center no-wrap q-mr-sm">
          <q-btn
            v-for="mode in ADDRESS_CLIENT_MODES"
            :key="mode.value"
            flat
            dense
            class="mode-btn"
            :class="{ 'mode-btn--active': display.addressClientMode === mode.value }"
            :color="display.addressClientMode === mode.value ? 'primary' : 'grey-7'"
            :label="mode.symbol"
            @click="display.addressClientMode = mode.value"
          >
            <q-tooltip>
              {{ mode.label }}: {{ mode.value === 'union'
                ? 'показываются фото любого из выбранных адресов или клиентов'
                : mode.value === 'address'
                  ? 'выбранные адреса задают набор, клиенты уточняют его'
                  : 'выбранные клиенты задают набор, адреса уточняют его' }}
            </q-tooltip>
          </q-btn>
        </div>
        <span class="footer-dot">·</span>

        <template v-if="canSeeStats">
          <span class="footer-item">
            Всего медиа:
            <q-icon name="photo" size="16px" class="footer-icon" />
            <b>{{ stats.photos === null ? '—' : stats.photos }}</b>
            <span class="footer-sep">/</span>
            <q-icon name="videocam" size="16px" class="footer-icon" />
            <b>{{ stats.videos === null || stats.videos === undefined ? '—' : stats.videos }}</b>
          </span>
          <span class="footer-dot">·</span>
          <span class="footer-item">
            {{ periodLabel }}:
            <q-tooltip>
              Только по дате загрузки/съёмки; фильтры грида здесь не учитываются
            </q-tooltip>
            <q-icon name="photo" size="16px" class="footer-icon" />
            <b>{{ stats.period_photos === null ? '—' : stats.period_photos }}</b>
            <span class="footer-sep">/</span>
            <q-icon name="videocam" size="16px" class="footer-icon" />
            <b>{{ stats.period_videos === null || stats.period_videos === undefined ? '—' : stats.period_videos }}</b>
          </span>
          <span class="footer-dot">·</span>
          <span class="footer-item">
            Адресов: <b>{{ stats.addresses === null ? '—' : stats.addresses }}</b>
          </span>
          <span class="footer-dot">·</span>
          <span class="footer-item">
            Клиентов: <b>{{ stats.clients === null ? '—' : stats.clients }}</b>
          </span>
          <span class="footer-dot">·</span>
          <span class="footer-item">
            Последнее медиа:
            <span class="footer-date">
              <q-icon name="photo" size="16px" class="footer-icon" />
              <b class="footer-last">{{ lastPhoto }}</b>
              <q-tooltip>{{ lastPhotoFull }}</q-tooltip>
            </span>
            <span class="footer-sep">/</span>
            <span class="footer-date">
              <q-icon name="videocam" size="16px" class="footer-icon" />
              <b class="footer-last">{{ lastVideo }}</b>
              <q-tooltip>{{ lastVideoFull }}</q-tooltip>
            </span>
          </span>
          <q-btn flat dense no-caps label="Статистика" class="q-ml-sm" @click="openStats" />

          <span class="footer-dot">·</span>
        </template>

        <span class="footer-item text-grey-6">
          сборка {{ build }}
          <q-tooltip>
            Время сборки интерфейса. Если оно старше последнего обновления —
            страница в браузере старая, обновите её (Ctrl+F5).
          </q-tooltip>
        </span>
        <q-btn
          v-if="buildStale"
          dense
          no-caps
          color="warning"
          text-color="black"
          icon="system_update_alt"
          :label="`Доступна новая сборка (${serverBuild}) — обновить`"
          class="q-ml-sm"
          @click="reloadPage"
        />
        <span v-else-if="serverBuild" class="footer-dot">·</span>
        <span v-if="serverBuild && !buildStale" class="footer-item text-grey-6">
          сборка на сервере: {{ serverBuild }}
        </span>
      </div>
    </q-footer>

    <q-dialog v-model="statsDialogOpen">
      <q-card class="media-stats-dialog">
        <q-card-section class="panel-head row items-center">
          <div class="panel-title col">Статистика медиатеки</div>
          <q-btn flat round dense icon="refresh" :loading="mediaStatsLoading" @click="openStats" />
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-separator />
        <q-card-section v-if="mediaStatsLoading && !mediaStats" class="flex flex-center q-pa-xl">
          <q-spinner-dots size="32px" color="primary" />
        </q-card-section>
        <q-card-section v-else-if="mediaStats" class="q-gutter-md">
          <div class="row q-col-gutter-md">
            <div class="col-6"><b>Всего файлов:</b> {{ mediaStats.photos }} фото / {{ mediaStats.videos }} видео</div>
            <div class="col-6"><b>Период базы:</b> {{ mediaStats.period_start ? String(mediaStats.period_start).slice(0, 10) : '—' }} — {{ mediaStats.period_end ? String(mediaStats.period_end).slice(0, 10) : '—' }}</div>
            <div class="col-6"><b>Этот месяц:</b> {{ mediaStats.this_month_photos }} фото / {{ mediaStats.this_month_videos }} видео</div>
            <div class="col-6"><b>Последние 7 дней:</b> {{ mediaStats.last_7_days_photos }} фото / {{ mediaStats.last_7_days_videos }} видео</div>
            <div class="col-4"><b>Сегодня:</b> {{ mediaStats.today_photos }} / {{ mediaStats.today_videos }}</div>
            <div class="col-4"><b>Вчера:</b> {{ mediaStats.yesterday_photos }} / {{ mediaStats.yesterday_videos }}</div>
            <div class="col-4"><b>Позавчера:</b> {{ mediaStats.day_before_photos }} / {{ mediaStats.day_before_videos }}</div>
          </div>
          <q-separator />
          <div class="text-subtitle2">По месяцам</div>
          <q-scroll-area style="height: 280px">
            <q-markup-table dense flat bordered>
              <thead><tr><th class="text-left">Месяц</th><th class="text-right">Фото</th><th class="text-right">Видео</th></tr></thead>
              <tbody>
                <tr v-for="month in mediaStats.months" :key="month.month">
                  <td>{{ String(month.month).slice(0, 7) }}</td>
                  <td class="text-right">{{ month.photos }}</td>
                  <td class="text-right">{{ month.videos }}</td>
                </tr>
                <tr v-if="!mediaStats.months.length"><td colspan="3" class="text-center text-grey">Нет данных</td></tr>
              </tbody>
            </q-markup-table>
          </q-scroll-area>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-layout>
</template>

<style scoped>

/* Живая строка о ходе прогона в шапке: не должна растягивать панель. */
/* Мигающая точка «процесс идёт» — та же, что у стадий прогона. */
.blink-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ffd166;
  animation: pipeline-pulse 1.2s ease-in-out infinite;
}
@keyframes pipeline-pulse {
  0%, 100% { opacity: 0.25; }
  50% { opacity: 1; }
}
.header-pipeline-live {
  max-width: 42vw;
  overflow: hidden;
  white-space: nowrap;
}
.media-stats-dialog { width: min(760px, 94vw); max-width: 94vw; }

/* Подсказка с демо-доступом на экране входа. */
.login-hint {
  background: #f1f3f5;
  color: #4b5563;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.45;
}

.login-hint code {
  background: #e3e7eb;
  border-radius: 4px;
  padding: 0 4px;
  color: #1f2937;
}

/* Пользователь и выход выделены плашкой справа от шестерёнки. */
.header-user {
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.38);
  border-radius: 999px;
  padding: 2px 14px 2px 6px;
}

/* Главный экран («Фотогалерея») выделен той же плашкой. */
.header-gallery :deep(.q-tab) {
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.38);
  border-radius: 999px;
  min-height: 32px;
  padding: 0 14px;
}

.header-gallery :deep(.q-tab--active) {
  background: rgba(255, 255, 255, 0.34);
  border-color: rgba(255, 255, 255, 0.6);
}

/* Подвал-статусбар. */
.app-footer {
  min-height: 34px;
  background: #f4f5f7;
  color: #4b5563;
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.footer-item {
  font-size: 12px;
  white-space: nowrap;
}

/* Переключатель режима адреса/клиенты: один тёмный блок с тремя
   одинаковыми квадратными кнопками-символами. */
.footer-mode {
  background: rgba(0, 0, 0, 0.10);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
}

.mode-btn {
  width: 26px;
  height: 26px;
  min-width: 26px;
  min-height: 26px;
  padding: 0;
  font-size: 14px;
  line-height: 1;
  border-radius: 6px;
}

.mode-btn :deep(.q-btn__content) {
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.mode-btn--active {
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.14);
}

.footer-icon {
  vertical-align: -3px;
  margin: 0 2px 0 4px;
}

.footer-sep {
  color: #9e9e9e;
  margin: 0 2px;
}

.footer-date {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

body.body--dark .footer-icon,
body.body--dark .footer-sep {
  color: #b0bec5;
}

.footer-dot {
  margin: 0 8px;
  color: #9ca3af;
}

/* Дата последнего добавления — то, за чем следят: выделена. */
.footer-last {
  color: #92400e;
  background: #fef3c7;
  border-radius: 6px;
  padding: 0 6px;
}

body.body--dark .app-footer {
  background: #1d1d1f;
  color: #cbd0d6;
  border-top-color: rgba(255, 255, 255, 0.12);
}

body.body--dark .footer-last {
  color: #fde68a;
  background: rgba(253, 230, 138, 0.16);
}
</style>
