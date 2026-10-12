<script setup>
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'

import { previewUrl } from '../api/client'
import { usePhotosStore } from '../stores/photos'

const store = usePhotosStore()
const { items, error, loading } = storeToRefs(store)

const search = ref('')
const viewerOpen = ref(false)
const current = ref(null)

onMounted(() => {
  store.refresh()
})

function applySearch() {
  store.applySearch(search.value.trim())
}

async function onLoad(index, done) {
  if (!store.hasMore) {
    done(true)
    return
  }

  await store.loadPage()
  done(!store.hasMore)
}

function open(photo) {
  current.value = photo
  viewerOpen.value = true
}

function viewerUrl() {
  return current.value ? previewUrl(current.value.photo_id, 'middle') : ''
}
</script>

<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-gutter-md q-mb-md">
      <q-input
        v-model="search"
        dense
        outlined
        clearable
        placeholder="Поиск по имени файла"
        class="col-12 col-sm-4"
        @keyup.enter="applySearch"
      >
        <template #append>
          <q-btn icon="search" flat dense @click="applySearch" />
        </template>
      </q-input>

      <q-btn icon="refresh" flat dense @click="store.refresh()" />

      <q-space />

      <div class="text-caption text-grey">{{ items.length }} фото</div>
    </div>

    <div v-if="error" class="q-mb-md">
      <q-banner class="bg-red-1 text-negative">
        Ошибка загрузки: {{ error }}
      </q-banner>
    </div>

    <q-infinite-scroll @load="onLoad" :offset="300">
      <div class="photo-grid">
        <q-card
          v-for="photo in items"
          :key="photo.photo_id"
          class="photo-card cursor-pointer"
          @click="open(photo)"
        >
          <q-img
            :src="previewUrl(photo.photo_id, 'small')"
            :ratio="4 / 3"
            spinner-color="primary"
          />
          <q-card-section class="q-pa-xs">
            <div class="ellipsis text-caption">{{ photo.filename }}</div>
          </q-card-section>
        </q-card>
      </div>

      <template #loading>
        <div class="row justify-center q-my-md">
          <q-spinner-dots color="primary" size="40px" />
        </div>
      </template>
    </q-infinite-scroll>

    <div
      v-if="!loading && !error && items.length === 0"
      class="text-grey q-mt-lg"
    >
      Ничего не найдено.
    </div>

    <q-dialog v-model="viewerOpen">
      <q-card style="max-width: 90vw; max-height: 90vh">
        <q-img :src="viewerUrl()" class="rounded-borders" />
        <q-card-section class="q-pa-sm">
          <div class="text-caption text-grey-8">
            {{ current?.filename }} — {{ current?.photo_id }}
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.photo-card {
  overflow: hidden;
}
</style>
