<script setup>
// Base (starting) settings: reserve the layout the installation is known to
// work with, come back to it in one click, or keep it as a file.
import { computed, ref } from 'vue'
import { Notify } from 'quasar'

import {
  DOWNLOAD_NAME_MODES,
  LIST_FIELDS,
  TILE_COUNTS,
  useDisplayStore,
} from '../stores/display'

const display = useDisplayStore()

const fileInput = ref(null) // q-file: open the system dialog
const file = ref(null) // the chosen file

function label(options, value) {
  const found = options.find((option) => option.value === value)

  return found ? found.label : String(value)
}

// Short human-readable summary of the current settings.
const current = computed(() => {
  const tiles = label(TILE_COUNTS, display.tileColumns)
  const fields = display.listFields.map((field) => label(LIST_FIELDS, field))

  return [
    { what: 'Плиток в ряду', value: tiles },
    { what: 'Поля списка', value: fields.join(', ') || '—' },
    {
      what: 'Имена файлов при скачивании',
      value: label(DOWNLOAD_NAME_MODES, display.downloadNameMode),
    },
    {
      what: 'Ширина панелей',
      value: `${display.leftPanelWidth} / ${display.rightPanelWidth} px`,
    },
    { what: 'Высота списка адресов и клиентов', value: `${display.sideListHeight} px` },
    {
      what: 'Панели',
      value: [
        display.leftPanelOpen ? 'левая открыта' : 'левая скрыта',
        display.rightPanelOpen ? 'правая открыта' : 'правая скрыта',
      ].join(', '),
    },
  ]
})

const baseSaved = computed(() => Boolean(display.base))

function remember() {
  display.saveAsBase()
  Notify.create({
    type: 'positive',
    message: 'Текущие настройки запомнены как базовые',
  })
}

function restore() {
  display.restoreBase()
  Notify.create({ type: 'info', message: 'Вернулись к базовым настройкам' })
}

// ---- файл ----

function downloadBase() {
  const data = display.base || display.snapshot()

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = 'photobase-settings.json'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

async function loadFile(file) {
  if (!file) return

  try {
    const parsed = JSON.parse(await file.text())

    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('это не файл настроек')
    }

    display.adoptBase(parsed)
    Notify.create({
      type: 'positive',
      message: 'Настройки загружены из файла и стали базовыми',
    })
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }

  file.value = null
}
</script>

<template>
  <div class="row q-col-gutter-md">
    <div class="col-12 col-md-6">
      <q-card flat bordered>
        <q-card-section>
          <div class="panel-title q-mb-sm">Базовые настройки</div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Базовое состояние — та раскладка, которая гарантированно работает
            (100 %). Его можно запомнить и вернуть одной кнопкой, если
            эксперименты с видом зашли не туда.
          </div>

          <q-list dense>
            <q-item v-for="row in current" :key="row.what">
              <q-item-section>
                <q-item-label caption>{{ row.what }}</q-item-label>
              </q-item-section>
              <q-item-section side class="text-body2">{{ row.value }}</q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions>
          <q-btn
            color="primary"
            icon="bookmark_add"
            label="Запомнить текущие как базовые"
            @click="remember"
          />
          <q-btn
            flat
            icon="restore"
            label="Вернуть базовые"
            :disable="!baseSaved"
            @click="restore"
          >
            <q-tooltip v-if="!baseSaved">
              Базовые ещё не сохранены — сначала запомните текущие
            </q-tooltip>
          </q-btn>
        </q-card-actions>
      </q-card>
    </div>

    <div class="col-12 col-md-6">
      <q-card flat bordered>
        <q-card-section>
          <div class="panel-title q-mb-sm">Резервная копия</div>
          <div class="text-caption text-grey-7 q-mb-sm">
            Файл с настройками: пригодится, чтобы перенести рабочую раскладку на
            другую машину или пользователя, либо вернуть её позже.
          </div>

          <q-btn
            dense
            outlined
            icon="download"
            label="Скачать файл настроек"
            @click="downloadBase"
          />
          <q-btn
            dense
            flat
            icon="upload"
            label="Загрузить из файла"
            @click="fileInput.pick()"
          />
          <q-file
            ref="fileInput"
            v-model="file"
            class="hidden"
            accept="application/json,.json"
            @update:model-value="loadFile"
          />
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
