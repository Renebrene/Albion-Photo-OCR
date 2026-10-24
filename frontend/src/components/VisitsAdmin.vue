<script setup>
// Журнал посещений (входов) — вкладка в техразделе только для Администратора.
//
// Панель скрывается только тогда, когда таблицы действительно нет (404: не
// применена миграция 033). Раньше пряталось при любой ошибке, и сетевой сбой
// выглядел как «журнала нет» — теперь в этом случае видно баннер с повтором.
import { onMounted, ref } from 'vue'

import { fetchVisits } from '../api/client'

const items = ref([])
// Пока ответа не было, панель показываем: скрывать её заранее — мигание.
const tableMissing = ref(false)
const error = ref('')
const loading = ref(false)

function fmt(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '—'
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    const data = await fetchVisits(200)
    items.value = data.items || []
    tableMissing.value = false
  } catch (err) {
    items.value = []

    if (err.status === 404) {
      // Таблицы нет — панель просто не нужна.
      tableMissing.value = true
      return
    }

    error.value = err.message || 'Не удалось загрузить журнал посещений'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card v-if="!tableMissing" flat bordered>
    <q-card-section class="row items-center">
      <div class="panel-title col">Посещения (входы)</div>
      <q-btn flat round dense icon="refresh" :loading="loading" @click="load" />
    </q-card-section>
    <q-separator />

    <q-card-section v-if="error" class="row items-center no-wrap q-gutter-sm">
      <q-icon name="error_outline" color="negative" />
      <div class="col text-caption text-negative">{{ error }}</div>
      <q-btn dense flat no-caps size="sm" label="Повторить" :loading="loading" @click="load" />
    </q-card-section>

    <q-card-section>
      <q-markup-table dense flat bordered>
        <thead>
          <tr>
            <th class="text-left">Время</th>
            <th class="text-left">Пользователь</th>
            <th class="text-left">Событие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="visit in items" :key="visit.visit_id">
            <td>{{ fmt(visit.created_at) }}</td>
            <td>{{ visit.user_name }}</td>
            <td>{{ visit.event === 'login' ? 'вход' : 'выход' }}</td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="3" class="text-center text-grey">Пока нет посещений</td>
          </tr>
        </tbody>
      </q-markup-table>
    </q-card-section>
  </q-card>
</template>
