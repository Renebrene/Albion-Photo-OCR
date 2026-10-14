<script setup>
import { onMounted, ref } from 'vue'
import { Dark, Notify } from 'quasar'

import { useDisplayStore } from './stores/display'
import { usePhotosStore } from './stores/photos'
import { useSessionStore } from './stores/session'

const session = useSessionStore()
const photos = usePhotosStore()
const display = useDisplayStore()

const password = ref('')
const loginName = ref('')

onMounted(async () => {
  await session.load()

  if (!needsLogin.value) {
    await afterAuth()
  }
})

async function afterAuth() {
  photos.loadSelectionState()
  // The display settings follow the user, not the browser.
  await display.loadFromServer()
}

// Auth is required and nobody is logged in: show the login screen.
function needsLogin() {
  return session.authEnabled && !session.user
}

async function doLogin() {
  try {
    const user = await session.login(loginName.value, password.value)
    Notify.create({ type: 'positive', message: `Вы вошли как ${user.name}` })
    await afterAuth()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function doLogout() {
  await session.logout()
  Notify.create({ type: 'info', message: 'Выход выполнен' })
}

function toggleDark() {
  Dark.toggle()
}
</script>

<template>
  <q-layout view="hHh lpR fFf">
    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>АЛЬБИОН: Фотобаза</q-toolbar-title>

        <q-btn flat round dense icon="dark_mode" @click="toggleDark" />

        <q-tabs v-if="session.user" align="right" shrink>
          <q-route-tab to="/" label="Фото" exact />
        </q-tabs>

        <!-- Технический раздел: шестерёнка вместо вкладки. -->
        <q-btn
          v-if="session.user"
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

      <router-view v-else />
    </q-page-container>
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
</style>
