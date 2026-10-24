<script setup>
// Пять полей описания фото: описание, клиент, бренд, категория, теги.
//
// Одни и те же поля показывают две формы — правка описания QWEN в карточке
// фото и ручной режим ИИ-поиска. Раньше это были два независимых набора
// разметки с одинаковыми подписями, поэтому подписи и состав полей могли
// разойтись (второй аудит, 2.5). Отличаются только раскладка и подсказка.
//
// Поля правятся прямо в объекте родителя: копия потребовала бы синхронизации
// в обе стороны, а объект у обоих вызывающих уже реактивный.
defineProps({
  // { description, client, brand, category, tags } — все значения строки.
  fields: { type: Object, required: true },
  // Две колонки (правка в карточке) или один столбец (поиск по полям).
  columns: { type: Boolean, default: false },
  tagsHint: { type: String, default: '' },
})

// Состав и подписи полей — в одном месте, чтобы формы не разошлись снова.
const FIELDS = [
  { key: 'client', label: 'Клиент' },
  { key: 'brand', label: 'Бренд' },
  { key: 'category', label: 'Категория' },
  { key: 'tags', label: 'Теги (через запятую)' },
]
</script>

<template>
  <q-input
    v-model="fields.description"
    type="textarea"
    autogrow
    dense
    outlined
    label="Описание"
    :class="columns ? '' : 'q-mb-sm'"
  />

  <div v-if="columns" class="row q-col-gutter-sm">
    <div v-for="field in FIELDS" :key="field.key" class="col-12 col-md-6">
      <q-input
        v-model="fields[field.key]"
        dense
        outlined
        :label="field.label"
        :hint="field.key === 'tags' ? tagsHint : ''"
      />
    </div>
  </div>

  <template v-else>
    <q-input
      v-for="field in FIELDS"
      :key="field.key"
      v-model="fields[field.key]"
      outlined
      dense
      class="q-mb-sm"
      :label="field.label"
      :hint="field.key === 'tags' ? tagsHint : ''"
    />
  </template>
</template>
