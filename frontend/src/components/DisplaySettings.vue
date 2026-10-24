<script setup>
// Display settings for the photo grid (item 10 of the UI backlog) plus the
// download file-name mode (item 11b).
//
// Rendered both in the gear dialog next to the tiles/list toggle and in the
// technical section, so the same controls live in exactly one place.
import {
  DOWNLOAD_NAME_MODES,
  LIST_FIELDS,
  TILE_COUNTS,
  useDisplayStore,
} from '../stores/display'

const display = useDisplayStore()

async function resetDisplay() {
  const confirmed = await confirmDialog({
    title: 'Сбросить настройки отображения?',
    message: 'Колонки, поля списка, ширины панелей и режим адресов вернутся к значениям по умолчанию.',
    okLabel: 'Сбросить',
  })

  if (confirmed) display.reset()
}
</script>

<template>
  <div class="column q-gutter-md">
    <div>
      <div class="text-subtitle2">Режим «Плитка»: плиток в ряду</div>
      <q-btn-toggle
        v-model="display.tileColumns"
        :options="TILE_COUNTS"
        dense
        unelevated
        no-caps
        emit-value
        map-options
        toggle-color="primary"
        class="q-mt-xs"
      />
      <div class="text-caption text-grey">
        «Авто» — колонки считаются по ширине грида: при перетаскивании границ
        панелей плитки перестраиваются сами.
      </div>
    </div>

    <div>
      <q-toggle
        v-model="display.tileShowFilename"
        dense
        label="Показывать исходное имя файла в плитке"
      />
      <div class="text-caption text-grey">
        Если выключить, в плитке останутся адрес, дата и клиент. Значок
        распознавания QWEN стоит перед адресом.
      </div>
    </div>

    <div>
      <div class="text-subtitle2">Дата для фильтра периода</div>
      <q-select
        v-model="display.dateFilterMode"
        :options="[
          { label: 'Дата съёмки', value: 'capture' },
          { label: 'Дата загрузки', value: 'upload' },
        ]"
        dense
        outlined
        emit-value
        map-options
        class="q-mt-xs"
        style="max-width: 260px"
      />
      <div class="text-caption text-grey">
        По умолчанию фильтр и сортировка используют дату съёмки. Переключатель
        убран из панели фильтров.
      </div>
    </div>

    <div>
      <div class="text-subtitle2">Режим «Список»: отображаемые поля</div>
      <q-option-group
        v-model="display.listFields"
        :options="LIST_FIELDS"
        type="checkbox"
        dense
        class="q-mt-xs"
      />
      <div v-if="!display.listFields.length" class="text-caption text-orange">
        Ни одно поле не выбрано — в списке будут только миниатюры.
      </div>
    </div>

    <div>
      <div class="text-subtitle2">Имена файлов при скачивании</div>
      <q-select
        v-model="display.downloadNameMode"
        :options="DOWNLOAD_NAME_MODES"
        dense
        outlined
        emit-value
        map-options
        option-label="label"
        option-value="value"
        class="q-mt-xs"
        style="max-width: 340px"
      />
      <div class="text-caption text-grey">
        «Имя файла» — ровно как в папке, откуда шла инспекция. «Юридическое
        имя» — «1-й Конной Армии ул. 32, A (10).JPG»: адрес из справочника и
        номер (из имени файла, а если его нет — порядковый в выгрузке). У фото
        без сопоставленного адреса имя остаётся исходным. Справочник адресов —
        раздел «Адреса» в техническом разделе.
      </div>
    </div>

    <div>
      <q-btn
        dense
        flat
        no-caps
        icon="restart_alt"
        label="Сбросить настройки отображения"
        @click="resetDisplay"
      />
    </div>
  </div>
</template>
