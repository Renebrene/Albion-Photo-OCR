<script setup>
// Ready Albion links. `all` is used in the technical section (owner shown);
// without it the gear shows only the current user's links.
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import { fetchMediaLinks } from '../api/client'

const props = defineProps({
  all: { type: Boolean, default: false },
})

const items = ref([])
const configured = ref(true)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await fetchMediaLinks({ all: props.all, limit: 100 })
    items.value = data.items || []
    configured.value = data.configured !== false
  } catch (err) {
    error.value = err.message || 'Не удалось загрузить ссылки'
  } finally {
    loading.value = false
  }
}

async function copy(url) {
  try {
    await navigator.clipboard.writeText(url)
    Notify.create({ type: 'positive', message: 'Ссылка скопирована' })
  } catch {
    Notify.create({ type: 'warning', message: 'Скопируйте ссылку вручную' })
  }
}

function fmtDate(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

onMounted(load)
</script>

<template>
  <q-card flat bordered class="q-mt-md">
    <q-card-section class="panel-head row items-center">
      <div class="panel-title col">{{ all ? 'Ссылки Albion' : 'Мои ссылки' }}</div>
      <q-btn dense flat icon="refresh" :loading="loading" @click="load" />
    </q-card-section>
    <q-card-section class="q-pt-none">
      <q-banner v-if="!configured" dense class="bg-orange-1 text-dark q-mb-sm">
        Albion не настроен: задайте ALBION_UPLOAD_URL и ALBION_API_KEY.
      </q-banner>
      <q-banner v-if="error" dense class="bg-red-1 text-negative q-mb-sm">{{ error }}</q-banner>
      <div v-if="!items.length && !error" class="text-grey text-caption">
        Пока нет действующих ссылок.
      </div>
      <q-list v-else separator>
        <q-item v-for="item in items" :key="item.link_id" class="q-px-none">
          <q-item-section>
            <q-item-label class="ellipsis">
              <a :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.url }}</a>
            </q-item-label>
            <q-item-label caption>
              {{ item.media_kind }} · {{ item.media_id }}
              <template v-if="all"> · {{ item.owner_name || item.owner_user_id || '—' }}</template>
              · создано {{ fmtDate(item.created_at) }} · до {{ fmtDate(item.expires_at) }}
            </q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn dense flat icon="content_copy" aria-label="Копировать ссылку" @click="copy(item.url)" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card-section>
  </q-card>
</template>
