<script setup>
// Display settings for the photo grid (item 10 of the UI backlog).
//
// Rendered both in the gear dialog next to the tiles/list toggle and in the
// technical section, so the same controls live in exactly one place.
import { LIST_FIELDS, TILE_COUNTS, useDisplayStore } from '../stores/display'

const display = useDisplayStore()
</script>

<template>
  <div class="column q-gutter-md">
    <div>
      <div class="text-subtitle2">Режим «Плитка»: плиток в ряду</div>
      <q-btn-toggle
        v-model="display.tileColumns"
        :options="TILE_COUNTS.map((count) => ({ label: String(count), value: count }))"
        dense
        unelevated
        no-caps
        toggle-color="primary"
        class="q-mt-xs"
      />
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
      <q-btn
        dense
        flat
        no-caps
        icon="restart_alt"
        label="Сбросить настройки отображения"
        @click="display.reset()"
      />
    </div>
  </div>
</template>
