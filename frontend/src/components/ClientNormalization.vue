<script setup>
// Client normalisation: map the different spellings QWEN returns to one
// canonical name. Nothing is rewritten in the stored metadata - the aliases
// only affect grouping and the client filter.
//
// It used to live inside the QWEN settings page; it is shown from the photo
// page (toolbar button) because it belongs to the clients, not to the model.
import { computed, onMounted, ref, watch } from 'vue'
import { Notify } from 'quasar'

import {
  deleteClientAlias,
  fetchClientAliasAudit,
  fetchClientAliases,
  fetchQwenClientNames,
  saveClientAlias,
} from '../api/client'

// Справочник один на клиентов и брендов: колонка kind выбирает, что правим
// (schema/035). QWEN одинаково «изобретает» и клиентов, и бренды.
// compact — для окна над гридом: форма и список имён без журнала изменений
// (журнал остаётся в техразделе).
const props = defineProps({
  compact: { type: Boolean, default: false },
})

const kind = ref('client')

const aliases = ref([])
const newAlias = ref('')
const newCanonical = ref('')
const qwenNames = ref([])
const audit = ref([])

const titleWord = computed(() => (kind.value === 'brand' ? 'брендов' : 'клиентов'))

// Названия QWEN показываем только для выбранного вида.
const namesForKind = computed(() =>
  qwenNames.value.filter((item) => item.kind === kind.value),
)

async function loadAliases() {
  try {
    aliases.value = (await fetchClientAliases(kind.value)).items || []
  } catch {
    aliases.value = []
  }
}

async function loadQwenNames() {
  try {
    qwenNames.value = (await fetchQwenClientNames()).items || []
  } catch {
    qwenNames.value = []
  }
}

async function loadAudit() {
  try {
    audit.value = (await fetchClientAliasAudit(100, kind.value)).items || []
  } catch {
    audit.value = []
  }
}

// Клик по названию QWEN подставляет его в поля: алиас — само значение, а
// каноническое — уже заведённое сопоставление, если оно есть.
function pickName(item) {
  newAlias.value = item.name
  const existing = aliases.value.find((row) => row.alias === item.name)
  newCanonical.value = existing ? existing.canonical : ''
}

function fmt(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '—'
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
    await saveClientAlias(alias, canonical, kind.value)
    newAlias.value = ''
    newCanonical.value = ''
    await loadAliases()
    await loadAudit()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

async function removeAlias(alias) {
  try {
    await deleteClientAlias(alias, kind.value)
    await loadAliases()
    await loadAudit()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

// Смена вида перезагружает и справочник, и журнал: они тоже вид-зависимые.
watch(kind, () => {
  newAlias.value = ''
  newCanonical.value = ''
  loadAliases()
  loadAudit()
})

onMounted(() => {
  loadAliases()
  loadQwenNames()
  loadAudit()
})
</script>

<template>
  <div>
    <div class="text-subtitle1 q-mb-sm">Нормализация клиентов и брендов</div>
    <div class="text-caption text-grey q-mb-md">
      Приведите близкие написания клиента или бренда от QWEN к одному.
      Исходные данные не меняются, только группировка и фильтр.
    </div>

    <q-btn-toggle
      v-model="kind"
      dense
      no-caps
      class="q-mb-md"
      :options="[
        { label: 'Клиенты', value: 'client' },
        { label: 'Бренды', value: 'brand' },
      ]"
    />

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

    <!-- Все названия от QWEN в алфавитном порядке; клик подставляет в поля. -->
    <div class="text-caption text-grey-8 q-mb-xs">
      Названия {{ titleWord }}, распознанные QWEN (клик — подставить в поля):
    </div>
    <q-scroll-area style="height: 180px" class="q-mb-md">
      <div class="row q-gutter-xs">
        <q-chip
          v-for="item in namesForKind"
          :key="`${item.kind}:${item.name}`"
          dense
          clickable
          :icon="item.kind === 'client' ? 'person' : 'sell'"
          @click="pickName(item)"
        >
          {{ item.name }} <span class="text-grey-6">({{ item.count }})</span>
        </q-chip>
        <span v-if="!namesForKind.length" class="text-caption text-grey">
          Пока нет распознанных названий
        </span>
      </div>
    </q-scroll-area>

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

    <!-- Журнал правок: кто, что и когда изменил (в компактном режиме скрыт). -->
    <div v-if="audit.length && !compact" class="q-mt-lg">
      <div class="text-caption text-grey-8 q-mb-xs">История изменений</div>
      <q-markup-table dense flat bordered>
        <thead>
          <tr>
            <th class="text-left">Время</th>
            <th class="text-left">Кто</th>
            <th class="text-left">Вид</th>
            <th class="text-left">Алиас</th>
            <th class="text-left">Было → стало</th>
            <th class="text-left">Действие</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in audit" :key="row.audit_id">
            <td>{{ fmt(row.created_at) }}</td>
            <td>{{ row.actor || '—' }}</td>
            <td>{{ row.kind === 'brand' ? 'бренд' : 'клиент' }}</td>
            <td>{{ row.alias }}</td>
            <td>{{ row.canonical_old || '—' }} → {{ row.canonical_new || '—' }}</td>
            <td>{{ { create: 'добавлено', update: 'изменено', delete: 'удалено' }[row.action] || row.action }}</td>
          </tr>
        </tbody>
      </q-markup-table>
    </div>
  </div>
</template>
