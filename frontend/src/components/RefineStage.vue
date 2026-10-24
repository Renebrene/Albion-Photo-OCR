<script setup>
// Этап «Уточнение»: связывает кадры одной серии и приводит клиента/бренд к
// одному виду. Ручного запуска нет — этап идёт сам после QWEN, поэтому здесь
// только включение и параметры.
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import { fetchRefineSettings, saveRefineSettings } from '../api/client'

const loading = ref(false)
const saving = ref(false)
const settings = ref({
  enabled: false,
  available: true,
  gap_seconds: 30,
  crop_retention_days: 7,
  photos_ready: 0,
})

async function load() {
  loading.value = true
  try {
    settings.value = await fetchRefineSettings()
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
        Связывает кадры одной серии (один экран, короткий интервал, тот же
        кадр по хешу кропа) и приводит клиента и бренда к одному виду:
        дополняет пустые значения и заменяет редкие короткие чтения полными.
        Прежний результат каждого фото сохраняется в истории распознавания.
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
      <div class="text-caption text-grey-7 q-mt-xs">
        Этап работает на процессоре: это группировка по хешу и времени, без
        модели. Видеокарта нужна только QWEN.
      </div>
    </q-card-section>
  </q-card>
</template>
