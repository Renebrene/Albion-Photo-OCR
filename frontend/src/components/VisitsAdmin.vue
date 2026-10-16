<script setup>
// Журнал посещений (входов) — вкладка в техразделе только для Администратора.
// Скрывается, пока таблица не развёрнута (миграция 033 не применена).
import { onMounted, ref } from 'vue'

import { fetchVisits } from '../api/client'

const items = ref([])
const available = ref(false)
const loading = ref(false)

function fmt(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '—'
}

async function load() {
  loading.value = true
  try {
    const data = await fetchVisits(200)
    items.value = data.items || []
    available.value = true
  } catch {
    available.value = false
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card v-if="available" flat bordered>
    <q-card-section class="row items-center">
      <div class="panel-title col">Посещения (входы)</div>
      <q-btn flat round dense icon="refresh" :loading="loading" @click="load" />
    </q-card-section>
    <q-separator />

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
