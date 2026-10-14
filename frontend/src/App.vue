<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Dark, Notify } from 'quasar'
import { useRouter } from 'vue-router'

import { fetchStats } from './api/client'
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
})

async function afterAuth() {
  photos.loadSelectionState()
  // The display settings follow the user, not the browser.
  await display.loadFromServer()
  await loadStats()
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

const stats = ref({ photos: null, addresses: null, clients: null, last_photo_at: null })

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

function toggleDark() {
  Dark.toggle()
}
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header ref="headerRef" elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>АЛЬБИОН: Фотобаза</q-toolbar-title>

        <q-btn flat round dense icon="dark_mode" @click="toggleDark" />

        <!-- Главный экран выделен плашкой, как блок пользователя. -->
        <q-tabs v-if="session.user" align="right" shrink class="header-gallery">
          <q-route-tab to="/" icon="photo_library" label="Фотогалерея" exact />
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
          Адреса: <b>{{ stats.addresses === null ? '—' : stats.addresses }}</b>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Клиенты: <b>{{ stats.clients === null ? '—' : stats.clients }}</b>
        </span>
        <span class="footer-dot">·</span>
        <span class="footer-item">
          Последнее фото добавлено:
          <b class="footer-last">{{ lastPhoto }}</b>
          <q-tooltip>{{ lastPhotoFull }}</q-tooltip>
        </span>

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
  </q-layout>
</template>

<style scoped>
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
