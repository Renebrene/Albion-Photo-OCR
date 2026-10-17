<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Dark, Notify } from 'quasar'
import { useRouter } from 'vue-router'

import PipelineUpdateButton from './components/PipelineUpdateButton.vue'
import { fetchMediaStatistics, fetchStats } from './api/client'
import { useDisplayStore } from './stores/display'
import { usePhotosStore } from './stores/photos'
import { useSessionStore } from './stores/session'

const router = useRouter()

const session = useSessionStore()
const photos = usePhotosStore()
const display = useDisplayStore()

const password = ref('')
const loginName = ref('')

// The interface is drawn only once the user's settings are in place: otherwise
// the grid would flash the default layout and then rearrange itself.
const booted = ref(false)

// The technical section is for the staff: Администратор and Менеджер.
const canUseTech = computed(() =>
  ['Администратор', 'Менеджер'].includes(session.user?.role),
)

onMounted(async () => {
  await session.load()

  if (needsLogin()) {
    booted.value = true
  } else {
    await afterAuth()
  }

  // Подвал может обернуть содержимое при узком окне — меряем и при изменении.
  window.addEventListener('resize', measureChrome)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', measureChrome)
  if (statsTimer !== null) window.clearInterval(statsTimer)
})

async function afterAuth() {
  // Гость только смотрит: его выбор/раскладка не сохраняются ни на сервере,
  // ни в localStorage.
  const canPersist = !session.authEnabled || session.user?.role !== 'Гость'
  display.setPersistence(canPersist)
  if (!canPersist) display.reset()

  photos.loadSelectionState({ persist: canPersist })
  // The display settings follow the user, not the browser. A Guest always
  // starts from the built-in defaults and never persists them.
  if (canPersist) await display.loadFromServer()
  await loadStats()
  if (statsTimer === null) statsTimer = window.setInterval(loadStats, 60_000)
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

const stats = ref({ photos: null, videos: null, addresses: null, clients: null, last_photo_at: null, last_video_at: null })
const statsDialogOpen = ref(false)
const mediaStats = ref(null)
const mediaStatsLoading = ref(false)
let statsTimer = null

async function loadStats() {
  try {
    stats.value = await fetchStats()
  } catch {
    // Подвал — вспомогательная информация: без неё окно работает как обычно.
  }
}

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
          v-if="session.user"
          :can-run="canUseTech"
          @finished="loadStats"
        />

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
        <q-tabs v-if="session.user" align="right" shrink class="header-gallery">
          <q-route-tab to="/" icon="photo_library" label="Фотогалерея" exact />
          <q-route-tab to="/videos" icon="movie" label="Видео" exact />
        </q-tabs>

        <!-- Технический раздел: шестерёнка вместо вкладки. Доступен только
             Администратору и Менеджеру — у Гостя его нет вовсе. -->
        <q-btn
          v-if="session.user && canUseTech"
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
            <div class="text-caption text-grey">
              Пароль задаёт администратор. Если вход не срабатывает — обратитесь
              к администратору сервера.
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

        <span class="footer-item">
          Фото: <b>{{ stats.photos === null ? '—' : stats.photos }}</b>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Видео: <b>{{ stats.videos === null || stats.videos === undefined ? '—' : stats.videos }}</b>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Адреса: <b>{{ stats.addresses === null ? '—' : stats.addresses }}</b>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Клиенты: <b>{{ stats.clients === null ? '—' : stats.clients }}</b>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Последнее фото: <b class="footer-last">{{ lastPhoto }}</b>
          <q-tooltip>{{ lastPhotoFull }}</q-tooltip>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Последнее видео: <b class="footer-last">{{ lastVideo }}</b>
          <q-tooltip>{{ lastVideoFull }}</q-tooltip>
        </span>
        <q-btn flat dense no-caps label="Статистика" class="q-ml-sm" @click="openStats" />

        <span class="footer-dot">·</span>
        <span class="footer-item text-grey-6">
          сборка {{ build }}
          <q-tooltip>
            Время сборки интерфейса. Если оно старше последнего обновления —
            страница в браузере старая, обновите её (Ctrl+F5).
          </q-tooltip>
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
.media-stats-dialog { width: min(760px, 94vw); max-width: 94vw; }

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
