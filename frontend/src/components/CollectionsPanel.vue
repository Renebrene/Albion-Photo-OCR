<script setup>
// Подборки. Слева — подборки адресов, справа — подборки клиентов: подборка
// хранит состояние выбора (какие адреса или клиенты отмечены) и восстанавливает
// его по клику. На фотографии подборка напрямую не влияет: грид фильтруется
// по отмеченным адресам и клиентам.
import { computed } from 'vue'
import { Notify } from 'quasar'

import { usePhotosStore } from '../stores/photos'

const props = defineProps({
  scope: {
    type: String,
    default: 'addresses',
    validator: (value) => ['addresses', 'clients'].includes(value),
  },
})

const emit = defineEmits(['create'])

const store = usePhotosStore()

const items = computed(() => store.collectionsFor(props.scope))

const title = computed(() =>
  props.scope === 'clients' ? 'Подборки клиентов' : 'Подборки адресов',
)

const emptyText = computed(() =>
  props.scope === 'clients'
    ? 'Отметьте клиентов и нажмите «+»'
    : 'Отметьте адреса и нажмите «+»',
)

async function pick(collection) {
  try {
    await store.applyCollection(collection)
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
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
    <q-card-section class="panel-head q-pb-xs row items-center">
      <div class="panel-title col">{{ title }}</div>
      <q-btn dense flat icon="add" size="sm" @click="emit('create', scope)">
        <q-tooltip>Сохранить текущий выбор в подборку</q-tooltip>
      </q-btn>
    </q-card-section>
    <q-separator />
    <q-scroll-area class="col">
      <q-list dense>
        <q-item
          v-for="collection in items"
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
            <div class="text-caption text-grey-7">
              {{
                scope === 'clients' ? 'клиентов' : 'адресов'
              }}: {{ collection.members }}
            </div>
          </q-item-section>
          <q-item-section side>
            <q-btn
              dense
              flat
              size="sm"
              icon="delete"
              @click.stop="remove(collection)"
            >
              <q-tooltip>Удалить подборку</q-tooltip>
            </q-btn>
          </q-item-section>
        </q-item>
        <q-item v-if="!items.length">
          <q-item-section class="text-caption text-grey">
            {{ emptyText }}
          </q-item-section>
        </q-item>
      </q-list>
    </q-scroll-area>
  </q-card>
</template>
