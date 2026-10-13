<script setup>
import { onMounted, ref } from 'vue'
import { Dark, Notify } from 'quasar'

import { usePhotosStore } from './stores/photos'
import { useSessionStore } from './stores/session'

const session = useSessionStore()
const photos = usePhotosStore()

const loginOpen = ref(false)
const selectedName = ref(null)
const password = ref('')

onMounted(async () => {
  await session.load()
  await session.loadUsers()
  if (session.user) await photos.loadSelectionState()
})

function openLogin(name) {
  if (!name) return
  selectedName.value = name
  password.value = ''
  loginOpen.value = true
}

async function doLogin() {
  try {
    const user = await session.login(selectedName.value, password.value)
    Notify.create({ type: 'positive', message: `Вы вошли как ${user.name}` })
    loginOpen.value = false
    await photos.loadSelectionState()
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

        <q-avatar
          v-if="session.user"
          :style="{ background: session.user.color || '#1976d2' }"
          size="28px"
          text-color="white"
          class="q-mr-sm"
        >
          {{ (session.user.name || '?').slice(0, 1) }}
        </q-avatar>

        <q-btn flat round dense icon="dark_mode" @click="toggleDark" />

        <q-select
          :model-value="session.user?.name || null"
          :options="session.users.map((u) => u.name)"
          dense
          borderless
          dark
          options-dark
          label="Менеджер"
          class="q-ml-md"
          style="min-width: 170px"
          @update:model-value="openLogin"
        />

        <q-btn
          v-if="session.user"
          flat
          dense
          icon="logout"
          label="Выйти"
          @click="doLogout"
        />

        <q-tabs align="right" shrink>
          <q-route-tab to="/" label="Фото" exact />
          <q-route-tab to="/technical" label="Технический" exact />
        </q-tabs>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>

    <q-dialog v-model="loginOpen">
      <q-card style="min-width: 320px">
        <q-card-section class="text-subtitle1">
          Вход: {{ selectedName }}
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-input
            v-model="password"
            type="password"
            dense
            outlined
            label="Пароль"
            @keyup.enter="doLogin"
          />
          <div class="text-caption text-grey q-mt-xs">
            Если пароль не задан — оставьте пустым.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Войти" @click="doLogin" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-layout>
</template>
