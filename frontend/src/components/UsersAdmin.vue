<script setup>
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import { createUser, fetchUsers, updateUser } from '../api/client'

const users = ref([])
const loading = ref(false)

const dialogOpen = ref(false)
const form = ref({ name: '', role: 'Менеджер', color: '', password: '' })

const passwordOpen = ref(false)
const passwordUser = ref(null)
const newPassword = ref('')

const roles = ['Администратор', 'Менеджер', 'Гость']
const colors = ['#1976d2', '#26a69a', '#9c27b0', '#ef6c00', '#546e7a', '#c2185b']

async function load() {
  loading.value = true
  try {
    users.value = (await fetchUsers(false)).items || []
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    loading.value = false
  }
}

onMounted(load)

function openAdd() {
  form.value = { name: '', role: 'Менеджер', color: '', password: '' }
  dialogOpen.value = true
}

async function save() {
  try {
    await createUser({
      name: form.value.name.trim(),
      role: form.value.role,
      color: form.value.color || null,
      password: form.value.password || null,
    })
    Notify.create({ type: 'positive', message: 'Пользователь создан' })
    dialogOpen.value = false
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function toggleActive(user) {
  try {
    await updateUser(user.user_id, { active: !user.active })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

function openPassword(user) {
  passwordUser.value = user
  newPassword.value = ''
  passwordOpen.value = true
}

async function savePassword() {
  try {
    await updateUser(passwordUser.value.user_id, {
      password: newPassword.value || null,
    })
    Notify.create({ type: 'positive', message: 'Пароль обновлён' })
    passwordOpen.value = false
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">Пользователи</div>
      <q-btn dense color="primary" icon="person_add" label="Добавить" @click="openAdd" />
      <q-btn dense flat icon="refresh" class="q-ml-sm" @click="load" />
    </div>

    <q-table
      :rows="users"
      :loading="loading"
      row-key="user_id"
      flat
      bordered
      :columns="[
        { name: 'name', label: 'Имя', field: 'name', align: 'left' },
        { name: 'role', label: 'Роль', field: 'role', align: 'left' },
        { name: 'active', label: 'Активен', field: 'active', align: 'left' },
        { name: 'actions', label: '', field: 'actions', align: 'right' },
      ]"
      no-data-label="Нет пользователей"
    >
      <template #body-cell-name="props">
        <q-td :props="props">
          <q-icon name="circle" :style="{ color: props.row.color || '#999' }" size="12px" />
          {{ props.row.name }}
        </q-td>
      </template>
      <template #body-cell-active="props">
        <q-td :props="props">{{ props.row.active ? 'да' : 'нет' }}</q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props">
          <q-btn dense flat size="sm" icon="key" @click="openPassword(props.row)" />
          <q-btn
            dense
            flat
            size="sm"
            :icon="props.row.active ? 'archive' : 'unarchive'"
            @click="toggleActive(props.row)"
          />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="dialogOpen">
      <q-card style="min-width: 360px">
        <q-card-section class="text-subtitle1">Новый пользователь</q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input v-model="form.name" dense outlined label="Имя" />
          <q-select v-model="form.role" :options="roles" dense outlined label="Роль" />
          <q-select
            v-model="form.color"
            :options="colors"
            dense
            outlined
            label="Цвет"
            clearable
          >
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section avatar>
                  <q-icon name="circle" :style="{ color: scope.opt }" />
                </q-item-section>
                <q-item-section>{{ scope.opt }}</q-item-section>
              </q-item>
            </template>
          </q-select>
          <q-input
            v-model="form.password"
            type="password"
            dense
            outlined
            label="Пароль (пусто = без пароля)"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Создать" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="passwordOpen">
      <q-card style="min-width: 320px">
        <q-card-section class="text-subtitle1">
          Пароль: {{ passwordUser?.name }}
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-input
            v-model="newPassword"
            type="password"
            dense
            outlined
            label="Новый пароль (пусто = снять пароль)"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Сохранить" @click="savePassword" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>
