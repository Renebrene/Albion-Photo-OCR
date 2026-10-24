<script setup>
// Настройки файлохранилища Albion: адрес, папка, TTL и машинный токен.
// Токен приходит с сервера только маской; пустое поле при сохранении означает
// «не менять», отдельная кнопка очищает его.
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  fetchCloudSettings,
  saveCloudSettings,
  verifyCloudConnection,
} from '../api/client'
import { useSessionStore } from '../stores/session'

const session = useSessionStore()

// Менять адрес/токен может только Администратор (`settings:write`).
const canConfigure = computed(
  () => !session.authEnabled || session.user?.role === 'Администратор',
)

const baseUrl = ref('')
const folderId = ref('')
const ttlDays = ref(90)
const token = ref('')

const apiKeySet = ref(false)
const apiKeyHint = ref('')
const configured = ref(false)

const loading = ref(false)
const saving = ref(false)
const verifying = ref(false)
const clearing = ref(false)
const error = ref('')
const verifyResult = ref(null)

function apply(data) {
  baseUrl.value = data?.base_url || ''
  folderId.value = data?.folder_id || ''
  ttlDays.value = data?.ttl_days ?? 90
  apiKeySet.value = Boolean(data?.api_key_set)
  apiKeyHint.value = data?.api_key_hint || ''
  configured.value = Boolean(data?.configured)
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    apply(await fetchCloudSettings())
  } catch (err) {
    error.value = err.message || 'Не удалось загрузить настройки Albion'
  } finally {
    loading.value = false
  }
}

// Срок ссылки: сервер принимает 1…3650 дней и так же ограничивает значение.
// Раньше пустое или нулевое поле молча превращалось в 90, а отрицательное
// уходило как есть — теперь показываем ошибку и не даём сохранить.
const TTL_MIN = 1
const TTL_MAX = 3650

function ttlValid(value) {
  const days = Number(value)

  return Number.isFinite(days) && days >= TTL_MIN && days <= TTL_MAX
}

const ttlRules = [
  (value) => ttlValid(value) || `От ${TTL_MIN} до ${TTL_MAX} дней`,
]

const ttlInvalid = computed(() => !ttlValid(ttlDays.value))

function payload() {
  const body = {
    base_url: baseUrl.value.trim(),
    folder_id: folderId.value.trim(),
    ttl_days: Math.max(TTL_MIN, Math.min(Math.round(Number(ttlDays.value)) || TTL_MIN, TTL_MAX)),
  }

  // Пустое поле = «не менять»: сервер отличает его от явной очистки.
  if (token.value) body.api_key = token.value

  return body
}

async function save() {
  saving.value = true
  error.value = ''

  try {
    apply(await saveCloudSettings(payload()))
    token.value = ''
    verifyResult.value = null
    Notify.create({ type: 'positive', message: 'Настройки Albion сохранены' })
  } catch (err) {
    error.value = err.message || 'Не удалось сохранить настройки Albion'
  } finally {
    saving.value = false
  }
}

async function clearToken() {
  clearing.value = true
  error.value = ''

  try {
    apply(await saveCloudSettings({ api_key: '' }))
    token.value = ''
    verifyResult.value = null
    Notify.create({ type: 'info', message: 'Токен Albion очищен' })
  } catch (err) {
    error.value = err.message || 'Не удалось очистить токен'
  } finally {
    clearing.value = false
  }
}

async function verify() {
  verifying.value = true
  error.value = ''
  verifyResult.value = null

  try {
    verifyResult.value = await verifyCloudConnection()
  } catch (err) {
    error.value = err.message || 'Albion не ответил на проверку'
  } finally {
    verifying.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card flat bordered>
    <q-card-section>
      <div class="panel-title q-mb-sm">Файлохранилище Albion</div>

      <div class="text-caption text-grey-7 q-mb-md">
        Внутренние файлы можно хранить на Albion. Ссылки, которые получают
        пользователи, ведёт файлохранилище; Photobase только отправляет файлы.
      </div>

      <q-banner v-if="!configured" dense class="bg-grey-2 q-mb-md">
        Albion не настроен: укажите адрес, папку и машинный токен.
      </q-banner>

      <q-banner v-if="!canConfigure" dense class="bg-grey-2 q-mb-sm">
        Адрес, токен и папку меняет только Администратор.
      </q-banner>

      <q-banner v-if="error" dense class="bg-red-1 text-negative q-mb-sm">
        {{ error }}
      </q-banner>

      <q-input
        v-model="baseUrl"
        dense
        outlined
        label="Адрес файлохранилища (https://…)"
        class="q-mb-sm"
        :disable="!canConfigure"
      />
      <q-input
        v-model="folderId"
        dense
        outlined
        label="Папка (folder_id, выданная Albion)"
        class="q-mb-sm"
        :disable="!canConfigure"
      />
      <div class="row q-col-gutter-sm q-mb-sm">
        <div class="col-12 col-sm-6">
          <q-input
            v-model.number="ttlDays"
            type="number"
            dense
            outlined
            label="Срок ссылки, дней"
            :disable="!canConfigure"
            :rules="ttlRules"
            lazy-rules
          />
        </div>
        <div class="col-12 col-sm-6">
          <q-input
            v-model="token"
            type="password"
            dense
            outlined
            :label="
              apiKeySet
                ? `Токен (сохранён ${apiKeyHint || ''}) — пусто = не менять`
                : 'Машинный токен Albion'
            "
            :disable="!canConfigure"
          />
        </div>
      </div>

      <div class="row items-center q-gutter-sm">
        <q-btn
          color="primary"
          icon="save"
          label="Сохранить"
          :loading="saving"
          :disable="!canConfigure || ttlInvalid"
          @click="save"
        />
        <q-btn
          flat
          icon="wifi_tethering"
          label="Проверить связь"
          :loading="verifying"
          :disable="!configured && !baseUrl"
          @click="verify"
        />
        <q-btn
          v-if="apiKeySet"
          flat
          color="negative"
          icon="key_off"
          label="Очистить токен"
          :loading="clearing"
          :disable="!canConfigure"
          @click="clearToken"
        />
        <q-btn flat icon="refresh" :loading="loading" @click="load" />
      </div>

      <q-banner
        v-if="verifyResult"
        dense
        class="bg-green-1 text-green-10 q-mt-sm"
      >
        Связь есть: {{ verifyResult.name || 'Albion' }}.
        Права: {{ (verifyResult.scopes || []).join(', ') || '—' }}.
      </q-banner>
    </q-card-section>
  </q-card>
</template>
