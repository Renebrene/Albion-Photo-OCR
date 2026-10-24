<script setup>
// Подборки. Слева — подборки адресов, справа — подборки клиентов: подборка
// хранит состояние выбора (какие адреса или клиенты отмечены) и восстанавливает
// его по клику. На фотографии подборка напрямую не влияет: грид фильтруется
// по отмеченным адресам и клиентам.
import { computed } from 'vue'
import { Notify } from 'quasar'

import { usePhotosStore } from '../stores/photos'
import { useAsyncAction } from '../composables/useAsyncAction'
import { confirmDialog } from '../composables/confirmDialog'
import { useSessionStore } from '../stores/session'

const props = defineProps({
  scope: {
    type: String,
    default: 'addresses',
    validator: (value) => ['addresses', 'clients'].includes(value),
  },
})

const emit = defineEmits(['create'])

const store = usePhotosStore()
const session = useSessionStore()

// Создание и удаление подборок требует scope collections:write; у Гостя его
// нет, поэтому ему доступен только просмотр. В открытом локальном режиме
// (аутентификация выключена) ограничивать нечего.
const canEdit = computed(() => {
  if (!session.authEnabled) return true
  return ['Администратор', 'Менеджер'].includes(session.user?.role)
})

const items = computed(() => store.collectionsFor(props.scope))

// Подборка подсвечивается тем же цветом, что и её элементы в панели:
// адреса — primary, клиенты — secondary.
const activeClass = computed(() =>
  props.scope === 'clients' ? 'bg-secondary text-white' : 'bg-primary text-white',
)

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

const { busy: removeBusy, run: removeRun } = useAsyncAction()

async function remove(collection) {
  const name = collection.name || 'без названия'
  const confirmed = await confirmDialog({
    title: 'Удалить подборку?',
    message: `«${name}» · участников: ${collection.members}. Подборка удалится вместе с составом.`,
  })

  if (!confirmed) return

  await removeRun(async () => {
    try {
      await store.deleteCollectionById(collection.collection_id)
      Notify.create({ type: 'positive', message: 'Подборка удалена' })
    } catch (err) {
      Notify.create({ type: 'negative', message: err.message })
    }
  })
}


</script>

<template>
  <q-card flat bordered class="column" style="flex: 1; min-height: 140px">
    <q-card-section class="panel-head q-pb-xs row items-center">
      <div class="panel-title col">{{ title }}</div>
      <q-btn
        v-if="canEdit"
        dense
        flat
        icon="add"
        size="sm"
        @click="emit('create', scope)"
      >
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
          :active="store.isCollectionActive(collection)"
          :active-class="activeClass"
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
          <q-item-section v-if="canEdit" side>
            <q-btn
              dense
              flat
              size="sm"
              icon="delete"
              :loading="removeBusy"
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
