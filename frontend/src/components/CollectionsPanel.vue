<script setup>
// Портфель (подборки). Один и тот же список стоит в левой и правой панели
// страницы фото, поэтому вынесен в компонент: данные общие (store), меняется
// только место показа.
import { storeToRefs } from 'pinia'
import { Notify } from 'quasar'

import { usePhotosStore } from '../stores/photos'

const emit = defineEmits(['create'])

const store = usePhotosStore()
const { collections } = storeToRefs(store)

async function pick(collection) {
  await store.selectCollection(
    store.collectionId === collection.collection_id
      ? null
      : collection.collection_id,
  )
}

async function remove(collection) {
  try {
    await store.deleteCollectionById(collection.collection_id)
    Notify.create({ type: 'positive', message: 'Подборка удалена' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}
</script>

<template>
  <q-card flat bordered class="column" style="flex: 1; min-height: 140px">
    <q-card-section class="q-pb-xs row items-center">
      <div class="panel-title col">Подборки</div>
      <q-btn dense flat icon="add" size="sm" @click="emit('create')">
        <q-tooltip>Сохранить выбранное в подборку</q-tooltip>
      </q-btn>
    </q-card-section>
    <q-separator />
    <q-scroll-area class="col">
      <q-list dense>
        <q-item
          v-for="collection in collections"
          :key="collection.collection_id"
          clickable
          :active="store.collectionId === collection.collection_id"
          active-class="bg-secondary text-white"
          @click="pick(collection)"
        >
          <q-item-section avatar>
            <q-icon name="bookmark" size="18px" />
          </q-item-section>
          <q-item-section>
            <div class="ellipsis">{{ collection.name }}</div>
            <div class="text-caption text-grey-7">{{ collection.kind }}</div>
          </q-item-section>
          <q-item-section side>{{ collection.members }}</q-item-section>
          <q-item-section side>
            <q-btn
              dense
              flat
              size="sm"
              icon="delete"
              @click.stop="remove(collection)"
            />
          </q-item-section>
        </q-item>
        <q-item v-if="!collections.length">
          <q-item-section class="text-caption text-grey">
            Подборок нет
          </q-item-section>
        </q-item>
      </q-list>
    </q-scroll-area>
  </q-card>
</template>
