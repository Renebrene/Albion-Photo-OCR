<script setup>
import { onMounted, ref } from 'vue'

import { fetchFingerprints } from '../api/client'

const items = ref([])
const loading = ref(false)
const error = ref(null)

async function load() {
  loading.value = true
  try {
    items.value = (await fetchFingerprints()).items || []
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle1 col">База слепков ({{ items.length }})</div>
      <q-btn dense flat icon="refresh" @click="load" />
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">{{ error }}</q-banner>
    </div>

    <q-table
      :rows="items"
      :loading="loading"
      row-key="id"
      flat
      bordered
      :columns="[
        { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
        { name: 'images', label: 'Фото', field: 'images', align: 'left', sortable: true },
        { name: 'dimension', label: 'Размерность', field: 'dimension', align: 'left' },
        { name: 'version', label: 'Версия', field: 'version', align: 'left' },
        { name: 'model', label: 'Модель', field: 'model', align: 'left' },
      ]"
      no-data-label="Нет слепков"
    >
      <template #top-row>
        <td colspan="5" class="text-caption text-grey">
          Каталог: data/fingerprints
        </td>
      </template>
    </q-table>
  </div>
</template>
