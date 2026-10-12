<script setup>
import { onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'

import { previewUrl } from '../api/client'
import { usePhotosStore } from '../stores/photos'

const store = usePhotosStore()
const { items, error, loading, addresses, clients } = storeToRefs(store)

const q = ref('')
const dateMode = ref('upload')
const period = ref('month')
const customFrom = ref(null)
const customTo = ref(null)

const viewerOpen = ref(false)
const current = ref(null)

const dateModes = [
  { label: 'Дата загрузки', value: 'upload' },
  { label: 'Дата съёмки', value: 'capture', disable: true },
]

const periods = [
  { label: 'Текущий месяц', value: 'month' },
  { label: 'Предыдущий месяц', value: 'prev_month' },
  { label: 'Все даты', value: 'all' },
  { label: 'Выбрать период', value: 'custom' },
]

function iso(date) {
  return date.toISOString().slice(0, 10)
}

function monthRange(offset) {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  const last = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)
  return [iso(first), iso(last)]
}

function currentDates() {
  switch (period.value) {
    case 'month':
      return monthRange(0)
    case 'prev_month':
      return monthRange(-1)
    case 'custom':
      return [customFrom.value || null, customTo.value || null]
    default:
      return [null, null]
  }
}

onMounted(async () => {
  await store.loadFacets()
  apply()
})

async function apply() {
  const [dateFrom, dateTo] = currentDates()
  await store.applyFilters({
    q: q.value.trim(),
    address: store.address,
    client: store.client,
    dateFrom,
    dateTo,
  })
}

async function pickAddress(address) {
  store.address = store.address === address ? '' : address
  await apply()
}

async function pickClient(client) {
  store.client = store.client === client ? '' : client
  await apply()
}

async function clearAddress() {
  store.address = ''
  await apply()
}

async function clearClient() {
  store.client = ''
  await apply()
}

async function reset() {
  q.value = ''
  period.value = 'all'
  customFrom.value = null
  customTo.value = null
  store.address = ''
  store.client = ''
  await apply()
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
    <div class="row no-wrap q-col-gutter-md">
      <!-- LEFT: period + addresses + clients (mirrors the legacy NiceGUI UI) -->
      <div class="col-auto" style="width: 360px; min-width: 320px">
        <q-card flat bordered class="q-mb-sm">
          <q-card-section class="q-pb-sm">
            <div class="text-subtitle2 q-mb-sm">Период</div>

            <q-option-group
              v-model="dateMode"
              :options="dateModes"
              inline
              dense
            />

            <q-select
              v-model="period"
              :options="periods"
              dense
              outlined
              emit-value
              map-options
              option-label="label"
              option-value="value"
              class="q-mt-sm"
              @update:model-value="apply"
            />

            <div v-if="period === 'custom'" class="row q-col-gutter-xs q-mt-sm">
              <div class="col">
                <q-input v-model="customFrom" type="date" dense outlined label="С" />
              </div>
              <div class="col">
                <q-input v-model="customTo" type="date" dense outlined label="По" />
              </div>
              <div class="col-auto">
                <q-btn dense flat icon="search" @click="apply" />
              </div>
            </div>

            <div class="text-caption text-orange q-mt-xs">
              «Дата съёмки» не сохраняется — фильтр идёт по дате загрузки.
            </div>
          </q-card-section>
        </q-card>

        <div class="row no-wrap" style="height: 360px">
          <q-card flat bordered class="col q-mr-xs column">
            <q-card-section class="q-pb-xs">
              <div class="text-subtitle2">Адреса</div>
            </q-card-section>
            <q-separator />
            <q-scroll-area class="col">
              <q-list dense>
                <q-item
                  v-for="item in addresses"
                  :key="item.address"
                  clickable
                  :active="store.address === item.address"
                  active-class="bg-primary text-white"
                  @click="pickAddress(item.address)"
                >
                  <q-item-section>{{ item.address }}</q-item-section>
                  <q-item-section side>{{ item.count }}</q-item-section>
                </q-item>
              </q-list>
            </q-scroll-area>
          </q-card>

          <q-card flat bordered class="col column">
            <q-card-section class="q-pb-xs">
              <div class="text-subtitle2">Клиенты</div>
            </q-card-section>
            <q-separator />
            <q-scroll-area class="col">
              <q-list dense>
                <q-item
                  v-for="item in clients"
                  :key="item.client"
                  clickable
                  :active="store.client === item.client"
                  active-class="bg-primary text-white"
                  @click="pickClient(item.client)"
                >
                  <q-item-section>{{ item.client }}</q-item-section>
                  <q-item-section side>{{ item.count }}</q-item-section>
                </q-item>
              </q-list>
            </q-scroll-area>
          </q-card>
        </div>
      </div>

      <!-- RIGHT: grid -->
      <div class="col">
        <div class="row items-center q-gutter-sm q-mb-sm">
          <q-input
            v-model="q"
            dense
            outlined
            clearable
            placeholder="Имя файла"
            class="col-12 col-sm-3"
            @keyup.enter="apply"
          />
          <q-btn
            color="primary"
            icon="photo_library"
            label="Показать фотографии"
            @click="apply"
          />
          <q-btn flat icon="refresh" dense @click="store.refresh()" />
          <q-btn flat icon="restart_alt" dense label="Сброс" @click="reset" />

          <q-chip
            v-if="store.address"
            removable
            color="primary"
            text-color="white"
            @remove="clearAddress"
          >
            Адрес: {{ store.address }}
          </q-chip>
          <q-chip
            v-if="store.client"
            removable
            color="secondary"
            text-color="white"
            @remove="clearClient"
          >
            Клиент: {{ store.client }}
          </q-chip>

          <q-space />
          <div class="text-caption text-grey">{{ items.length }} фото</div>
        </div>

        <div v-if="error" class="q-mb-md">
          <q-banner class="bg-red-1 text-negative">Ошибка: {{ error }}</q-banner>
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
                <div v-if="photo.address" class="ellipsis text-caption text-grey-8">
                  {{ photo.address }}
                </div>
                <div v-if="photo.client" class="ellipsis text-caption text-grey-8">
                  {{ photo.client }}
                </div>
              </q-card-section>
            </q-card>
          </div>

          <template #loading>
            <div class="row justify-center q-my-md">
              <q-spinner-dots color="primary" size="40px" />
            </div>
          </template>
        </q-infinite-scroll>

        <div v-if="!loading && !error && items.length === 0" class="text-grey q-mt-lg">
          Ничего не найдено.
        </div>
      </div>
    </div>

    <q-dialog v-model="viewerOpen">
      <q-card style="max-width: 90vw; max-height: 90vh">
        <q-img :src="viewerUrl()" class="rounded-borders" />
        <q-card-section class="q-pa-sm">
          <div class="text-caption text-grey-8">
            {{ current?.filename }} — {{ current?.photo_id }}
          </div>
          <div v-if="current?.description" class="text-caption q-mt-xs">
            {{ current.description }}
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
