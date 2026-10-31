<script setup>
// Этап «Уточнение»: связывает кадры одной серии и приводит клиента/бренд к
// одному виду. Ручного запуска нет — этап идёт сам после QWEN, поэтому здесь
// только включение и параметры.
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  applyRefinePreview,
  fetchRefineRules,
  fetchRefineSettings,
  previewRefine,
  previewQwenRescan,
  fetchClientAliases,
  saveRefineRules,
  saveRefineSettings,
} from '../api/client'

const loading = ref(false)
const saving = ref(false)
const settings = ref({
  enabled: false,
  available: true,
  gap_seconds: 30,
  crop_retention_days: 7,
  photos_ready: 0,
})
const rulesText = ref('')
const rulesVersion = ref(0)
const rulesSaving = ref(false)
const previewLoading = ref(false)
const dateFrom = ref('2026-09-01')
const dateTo = ref('2026-10-29')
const preview = ref(null)
const applyLoading = ref(false)
const qwenPreviewLoading = ref(false)
const qwenPreview = ref(null)
const aliasSummary = ref({ clients: 0, brands: 0 })
const cropFrequencyEnabled = ref(false)

async function load() {
  loading.value = true
  try {
    settings.value = await fetchRefineSettings()
    const storedRules = await fetchRefineRules()
    rulesVersion.value = storedRules.version
    rulesText.value = JSON.stringify(storedRules.rules, null, 2)
    cropFrequencyEnabled.value = Boolean(storedRules.rules?.crop_frequency_enabled)
    const [clientAliases, brandAliases] = await Promise.all([
      fetchClientAliases('client'),
      fetchClientAliases('brand'),
    ])
    aliasSummary.value = {
      clients: clientAliases.items?.length || 0,
      brands: brandAliases.items?.length || 0,
    }
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    loading.value = false
  }
}

// Тумблер сохраняется сразу: панель вкладки размонтируется при переключении,
// и нажатие, не отправленное на сервер, молча терялось.
const savingEnabled = ref(false)

async function setEnabled(value) {
  if (savingEnabled.value) return

  const previous = settings.value.enabled
  settings.value.enabled = Boolean(value)
  savingEnabled.value = true

  try {
    const updated = await saveRefineSettings({ enabled: settings.value.enabled })
    settings.value = { ...settings.value, ...updated }
  } catch (err) {
    settings.value.enabled = previous
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    savingEnabled.value = false
  }
}

async function saveRules() {
  rulesSaving.value = true
  try {
    const rules = JSON.parse(rulesText.value)
    const saved = await saveRefineRules(rules)
    rulesVersion.value = saved.version
    rulesText.value = JSON.stringify(saved.rules, null, 2)
    preview.value = null
    Notify.create({ type: 'positive', message: `JSON-правила сохранены, версия ${saved.version}` })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message || 'Некорректный JSON' })
  } finally {
    rulesSaving.value = false
  }
}

// Частотное предпочтение хранится в JSON-правилах; тумблер пишет новую
// версию сразу, чтобы настройка не потерялась при переключении вкладки.
async function setCropFrequency(value) {
  const previous = cropFrequencyEnabled.value
  cropFrequencyEnabled.value = Boolean(value)
  rulesSaving.value = true

  try {
    const rules = JSON.parse(rulesText.value)
    rules.crop_frequency_enabled = cropFrequencyEnabled.value
    const saved = await saveRefineRules(rules)
    rulesVersion.value = saved.version
    rulesText.value = JSON.stringify(saved.rules, null, 2)
    preview.value = null
    Notify.create({
      type: 'positive',
      message: `Предпочтение по частоте ${cropFrequencyEnabled.value ? 'включено' : 'выключено'}, версия ${saved.version}`,
    })
  } catch (err) {
    cropFrequencyEnabled.value = previous
    Notify.create({ type: 'negative', message: err.message || 'Не удалось сохранить правило' })
  } finally {
    rulesSaving.value = false
  }
}

function loadRulesFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => { rulesText.value = String(reader.result || '') }
  reader.readAsText(file)
  event.target.value = ''
}

async function runPreview() {
  previewLoading.value = true
  try {
    preview.value = await previewRefine({ date_from: dateFrom.value, date_to: dateTo.value })
    Notify.create({ type: 'positive', message: 'Предпросмотр построен без записи данных' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    previewLoading.value = false
  }
}

async function applyPreview() {
  if (!preview.value?.preview_token) return
  applyLoading.value = true
  try {
    const result = await applyRefinePreview({ preview_token: preview.value.preview_token })
    preview.value = null
    Notify.create({
      type: 'positive',
      message: `Применено к фото: ${result.applied_photos}; пропущено устаревших: ${result.stale_skipped}`,
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    applyLoading.value = false
  }
}

async function runQwenPreview() {
  qwenPreviewLoading.value = true
  try {
    qwenPreview.value = await previewQwenRescan({
      date_from: dateFrom.value,
      date_to: dateTo.value,
      date_mode: 'capture',
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    qwenPreviewLoading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const updated = await saveRefineSettings({
      enabled: settings.value.enabled,
      gap_seconds: Number(settings.value.gap_seconds),
      crop_retention_days: Number(settings.value.crop_retention_days),
    })
    settings.value = { ...settings.value, ...updated }
    Notify.create({ type: 'positive', message: 'Настройки «Уточнения» сохранены' })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <q-card flat bordered :loading="loading">
    <q-card-section>
      <div class="text-subtitle2 q-mb-xs">Уточнение</div>
      <div class="text-caption text-grey-8 q-mb-md">
        Связывает кадры одной серии и дополняет только очевидные совпадения.
        Предпросмотр безопасен: он ничего не записывает. Новые правила хранятся
        отдельной версией JSON, чтобы позже повторить уточнение без QWEN.
      </div>

      <div class="row items-center q-gutter-md q-mb-md">
        <q-toggle
          :model-value="settings.enabled"
          label="Включить этап"
          color="primary"
          :disable="settings.available === false || savingEnabled"
          @update:model-value="setEnabled"
        />
        <q-badge color="grey-7" :label="`готово кадров: ${settings.photos_ready ?? 0}`" />
      </div>

      <div class="row items-center q-gutter-md">
        <q-input
          v-model.number="settings.gap_seconds"
          type="number"
          dense
          outlined
          min="0"
          max="600"
          label="Интервал, сек"
          style="max-width: 170px"
        >
          <q-tooltip>
            Максимальная пауза между кадрами одной серии. Ролики обычно
            пятисекундные, по умолчанию 30 секунд.
          </q-tooltip>
        </q-input>
        <q-input
          v-model.number="settings.crop_retention_days"
          type="number"
          dense
          outlined
          min="1"
          max="90"
          label="Хранить кропы, дней"
          style="max-width: 200px"
        >
          <q-tooltip>
            Если этап не успел пройти за этот срок, кропы удаляются — место на
            диске важнее.
          </q-tooltip>
        </q-input>
        <q-btn
          color="primary"
          no-caps
          label="Сохранить"
          :loading="saving"
          @click="save"
        />
      </div>

      <div
        v-if="settings.available === false"
        class="text-caption text-orange-9 q-mt-md"
      >
        Этап недоступен: QWEN выключен из «Обновления базы» и в базе нет его
        описаний. Включите «Запускать QWEN в «Обновлении базы»» или дозаполните
        описания за период — тогда «Уточнение» станет доступным.
      </div>

      <div class="text-caption text-grey-7 q-mt-md">
        Этап запускается автоматически после того, как QWEN обработал все
        кадры: раньше сравнивать нечего. Отдельной кнопки запуска нет — без
        кропов он невозможен, а кропы создаются только вместе с описанием.
      </div>
      <q-separator class="q-my-md" />
      <div class="text-subtitle2 q-mb-sm">Распознавание нескольких щитов на фото</div>
      <div class="text-caption q-mb-sm">
        Если в кадре несколько щитов, для полей client/brand выбирается рекламодатель,
        который чаще встречается во всей базе QWEN. Оба чтения сохраняются в
        описании и тегах; без этой настройки побеждает основной (крупнейший) кроп.
      </div>
      <q-toggle
        :model-value="cropFrequencyEnabled"
        label="Предпочитать частого рекламодателя при нескольких щитах"
        :disable="rulesSaving"
        @update:model-value="setCropFrequency"
      />
      <div class="text-subtitle2 q-mt-md q-mb-sm">Предпочтительные названия рекламодателей</div>
      <div class="text-caption q-mb-sm">
        Используется существующий аудируемый справочник Client/Brand aliases, без копирования данных в JSON.
        Сейчас сопоставлений: клиент {{ aliasSummary.clients }}, бренд {{ aliasSummary.brands }}.
      </div>
      <q-btn
        flat
        dense
        no-caps
        color="primary"
        label="Справочник клиентов и брендов управляется в нормализации алиасов"
        disable
      />
      <div class="text-subtitle2 q-mt-md q-mb-sm">Правила уточнения (JSON, версия {{ rulesVersion }})</div>
      <q-input
        v-model="rulesText"
        type="textarea"
        autogrow
        outlined
        input-style="font-family: monospace; min-height: 120px"
        label="JSON-правила"
        class="q-mb-sm"
      />
      <div class="row items-center q-gutter-sm q-mb-md">
        <q-btn color="primary" no-caps label="Проверить и сохранить версию" :loading="rulesSaving" @click="saveRules" />
        <label class="q-btn q-btn-item non-selectable no-outline q-btn--standard q-btn--rectangle bg-grey-3 text-dark cursor-pointer">
          <span class="q-btn__content">Загрузить JSON</span>
          <input type="file" accept="application/json,.json" hidden @change="loadRulesFile">
        </label>
      </div>
      <div class="row items-center q-gutter-sm q-mb-sm">
        <q-input v-model="dateFrom" type="date" dense outlined label="Съёмка с" />
        <q-input v-model="dateTo" type="date" dense outlined label="по" />
        <q-btn color="secondary" no-caps label="Предпросмотр" :loading="previewLoading" @click="runPreview" />
      </div>
      <div v-if="preview" class="q-mt-md">
        <div class="text-subtitle2">Предпросмотр · версия {{ preview.rules_version }}</div>
        <div class="text-caption">
          Строк: {{ preview.rows_scanned }}; фото с предложениями: {{ preview.proposal_photos }};
          заполнений description: {{ preview.description_fills }}; обновлений tags: {{ preview.tag_updates }};
          групп с разными description (информация): {{ preview.description_variant_groups }}.
        </div>
        <div class="text-caption text-orange-9 q-mt-xs">
          Предпросмотр не записывает данные. Изменения применяются только отдельной кнопкой ниже.
        </div>
        <q-btn
          color="negative"
          no-caps
          label="Применить предложения"
          class="q-mt-sm"
          :loading="applyLoading"
          :disable="!preview.preview_token || preview.rules_version !== rulesVersion"
          @click="applyPreview"
        />
        <q-list dense bordered class="q-mt-sm">
          <q-item v-for="(item, index) in preview.samples" :key="`${item.photo_id}-${index}`">
            <q-item-section>
              <q-item-label>{{ item.photo_id }} · {{ JSON.stringify(item.changes) }}</q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </div>
      <q-separator class="q-my-md" />
      <div class="text-subtitle2 q-mb-sm">Предпросмотр QWEN-пересканирования периода</div>
      <q-btn
        color="warning"
        no-caps
        label="Проверить охват QWEN без запуска"
        :loading="qwenPreviewLoading"
        @click="runQwenPreview"
      />
      <div v-if="qwenPreview" class="text-caption q-mt-sm">
        БД: {{ qwenPreview.database }} · фото периода: {{ qwenPreview.photos_in_period }};
        текущих QWEN-строк: {{ qwenPreview.qwen_rows_in_period }};
        jobs будет примерно: {{ qwenPreview.queued_job_count_estimate }};
        running сейчас: {{ qwenPreview.qwen_queue?.RUNNING ?? 0 }}.
        История сохраняется; очищаются только результаты выбранного периода.
        Preview ничего не очистил и задания не поставил.
      </div>
      <div class="text-caption text-grey-7 q-mt-md">
        Этап работает на процессоре и повторно использует уже сохранённые QWEN-данные; повторный REFINE не запускает QWEN.
      </div>
    </q-card-section>
  </q-card>
</template>
