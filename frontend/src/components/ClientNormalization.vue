<script setup>
// Client normalisation: map the different spellings QWEN returns to one
// canonical name. Nothing is rewritten in the stored metadata - the aliases
// only affect grouping and the client filter.
//
// It used to live inside the QWEN settings page; it is shown from the photo
// page (toolbar button) because it belongs to the clients, not to the model.
import { onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  deleteClientAlias,
  fetchClientAliases,
  saveClientAlias,
} from '../api/client'

const aliases = ref([])
const newAlias = ref('')
const newCanonical = ref('')

async function loadAliases() {
  try {
    aliases.value = (await fetchClientAliases()).items || []
  } catch {
    aliases.value = []
  }
}

async function addAlias() {
  const alias = newAlias.value.trim()
  const canonical = newCanonical.value.trim()

  if (!alias || !canonical) {
    Notify.create({
      type: 'warning',
      message: 'Заполните оба поля: как распознал QWEN и каноническое имя',
    })
    return
  }

  try {
    await saveClientAlias(alias, canonical)
    newAlias.value = ''
    newCanonical.value = ''
    await loadAliases()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function removeAlias(alias) {
  try {
    await deleteClientAlias(alias)
    await loadAliases()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

onMounted(loadAliases)
</script>

<template>
  <div>
    <div class="text-subtitle1 q-mb-sm">Нормализация клиентов</div>
    <div class="text-caption text-grey q-mb-md">
      Приведите близкие написания клиента от QWEN к одному. Исходные данные не
      меняются, только группировка и фильтр.
    </div>

    <div class="row q-gutter-sm items-center q-mb-md">
      <q-input
        v-model="newAlias"
        dense
        outlined
        label="Как распознал QWEN"
        style="min-width: 220px"
      />
      <q-input
        v-model="newCanonical"
        dense
        outlined
        label="Каноническое имя"
        style="min-width: 220px"
      />
      <q-btn color="primary" icon="add" label="Добавить" @click="addAlias" />
    </div>

    <q-markup-table v-if="aliases.length" dense flat bordered>
      <thead>
        <tr>
          <th class="text-left">Алиас</th>
          <th class="text-left">Канонический</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in aliases" :key="item.alias">
          <td>{{ item.alias }}</td>
          <td>{{ item.canonical }}</td>
          <td class="text-right">
            <q-btn
              dense
              flat
              size="sm"
              icon="delete"
              @click="removeAlias(item.alias)"
            />
          </td>
        </tr>
      </tbody>
    </q-markup-table>
    <div v-else class="text-caption text-grey">Алиасов нет</div>
  </div>
</template>
