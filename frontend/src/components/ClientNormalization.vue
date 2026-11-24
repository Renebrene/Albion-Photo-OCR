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
  fetchQwenSettings,
  saveClientAlias,
  updateQwenSettings,
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

// «Низкий приоритет при выдаче»: такие названия не показываются как
// клиент/бренд фото, а уходят в теги — чужая реклама рядом с нашим щитом
// не должна забирать карточку (владелец, 21.11.2026).
const lowPriority = ref([])
const lowPriorityDefault = ref([])
const newLowPriority = ref('')
const lowPrioritySaving = ref(false)
const lowPriorityError = ref('')

// Фильтр качества кропа (по умолчанию включён на сервере).
const cropFilterEnabled = ref(true)
const cropFilterSaving = ref(false)
const cropFilterError = ref('')

// «Запрещённые к выдаче слова»: мат и случайные обрывки распознавания не
// попадают в клиента, бренд, теги и описание (владелец, 21.11.2026).
const forbiddenWords = ref([])
const newForbidden = ref('')
const forbiddenSaving = ref(false)
const forbiddenError = ref('')

const titleWord = computed(() => (kind.value === 'brand' ? 'брендов' : 'клиентов'))

// Названия QWEN показываем только для выбранного вида.
const namesForKind = computed(() =>
  qwenNames.value.filter((item) => item.kind === kind.value),
)

// Ошибки загрузок показываем отдельно: раньше все три «глотали» сбой, и пустой
// список был неотличим от неудачного запроса — можно было заново заводить уже
// существующие алиасы, не понимая, почему список пуст.
const errors = ref({ aliases: '', names: '', audit: '' })

async function loadAliases() {
  try {
    aliases.value = (await fetchClientAliases(kind.value)).items || []
    errors.value.aliases = ''
  } catch (err) {
    errors.value.aliases = err.message || 'Не удалось загрузить сопоставления'
  }
}

async function loadQwenNames() {
  try {
    qwenNames.value = (await fetchQwenClientNames()).items || []
    errors.value.names = ''
  } catch (err) {
    errors.value.names = err.message || 'Не удалось загрузить названия QWEN'
  }
}

async function loadDeliveryLists() {
  try {
    const data = await fetchQwenSettings()
    lowPriority.value = data.low_priority_names || []
    lowPriorityDefault.value = data.low_priority_default || []
    forbiddenWords.value = data.forbidden_words || []
    cropFilterEnabled.value = data.crop_filter_enabled !== false
    lowPriorityError.value = ''
    forbiddenError.value = ''
    cropFilterError.value = ''
  } catch (err) {
    lowPriorityError.value = err.message || 'Не удалось загрузить настройку'
    forbiddenError.value = err.message || 'Не удалось загрузить настройку'
  }
}

async function setCropFilter(value) {
  const previous = cropFilterEnabled.value
  cropFilterEnabled.value = Boolean(value)
  cropFilterSaving.value = true

  try {
    const data = await updateQwenSettings({ crop_filter_enabled: Boolean(value) })
    cropFilterEnabled.value = data?.crop_filter_enabled !== false
    cropFilterError.value = ''
  } catch (err) {
    cropFilterEnabled.value = previous
    cropFilterError.value = err.message || 'Не удалось сохранить настройку'
  } finally {
    cropFilterSaving.value = false
  }
}

async function saveLowPriority(next) {
  lowPrioritySaving.value = true
  try {
    const data = await updateQwenSettings({ low_priority_names: next })
    lowPriority.value = data.low_priority_names || next
    lowPriorityError.value = ''
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    lowPrioritySaving.value = false
  }
}

async function addLowPriority() {
  const name = newLowPriority.value.trim()
  if (!name) return

  if (lowPriority.value.some((item) => item.toLowerCase() === name.toLowerCase())) {
    Notify.create({ type: 'warning', message: 'Такое название уже в списке' })
    return
  }

  await saveLowPriority([...lowPriority.value, name])
  newLowPriority.value = ''
}

async function removeLowPriority(name) {
  await saveLowPriority(lowPriority.value.filter((item) => item !== name))
}

async function saveForbidden(next) {
  forbiddenSaving.value = true
  try {
    const data = await updateQwenSettings({ forbidden_words: next })
    forbiddenWords.value = data.forbidden_words || next
    forbiddenError.value = ''
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    forbiddenSaving.value = false
  }
}

async function addForbidden() {
  const word = newForbidden.value.trim()
  if (!word) return

  if (forbiddenWords.value.some((item) => item.toLowerCase() === word.toLowerCase())) {
    Notify.create({ type: 'warning', message: 'Такое слово уже в списке' })
    return
  }

  await saveForbidden([...forbiddenWords.value, word])
  newForbidden.value = ''
}

async function removeForbidden(word) {
  await saveForbidden(forbiddenWords.value.filter((item) => item !== word))
}

async function loadAudit() {
  try {
    audit.value = (await fetchClientAliasAudit(100, kind.value)).items || []
    errors.value.audit = ''
  } catch (err) {
    errors.value.audit = err.message || 'Не удалось загрузить историю изменений'
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

  // Блок «низкий приоритет» есть только в техразделе; в компактном окне над
  // гридом он лишний — там правят сопоставления, а не глобальные правила.
  if (!props.compact) loadDeliveryLists()
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
    <div v-if="errors.names" class="row items-center no-wrap q-gutter-sm q-mb-xs">
      <q-icon name="error_outline" color="negative" size="16px" />
      <div class="col text-caption text-negative">{{ errors.names }}</div>
      <q-btn dense flat no-caps size="sm" label="Повторить" @click="loadQwenNames" />
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
        <span
          v-if="!namesForKind.length && !errors.names"
          class="text-caption text-grey"
        >
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
    <div v-if="errors.aliases" class="row items-center no-wrap q-gutter-sm">
      <q-icon name="error_outline" color="negative" size="16px" />
      <div class="col text-caption text-negative">{{ errors.aliases }}</div>
      <q-btn dense flat no-caps size="sm" label="Повторить" @click="loadAliases" />
    </div>
    <div v-else-if="!aliases.length" class="text-caption text-grey">
      Алиасов нет
    </div>

    <!-- Низкий приоритет при выдаче (владелец, 21.11.2026): названия, которые
         не выводятся как клиент/бренд фото, а остаются тегами. По умолчанию —
         Sunlight/Санлайт: их щиты часто попадают в кадр рядом с нужным. -->
    <div v-if="!compact" class="q-mt-lg delivery-block delivery-block--low">
      <div class="text-subtitle2">Низкий приоритет при выдаче</div>
      <div class="text-caption text-grey q-mb-sm">
        Такие названия не становятся клиентом или брендом фото — предпочтение
        отдаётся другим кропам, а имя остаётся в тегах. Для фото, где есть
        только такая реклама, поля клиента и бренда останутся пустыми.
      </div>

      <div class="row q-gutter-xs q-mb-sm">
        <q-chip
          v-for="name in lowPriority"
          :key="name"
          dense
          removable
          :disable="lowPrioritySaving"
          @remove="removeLowPriority(name)"
        >
          {{ name }}
        </q-chip>
        <span v-if="!lowPriority.length" class="text-caption text-grey">
          Список пуст — правило выключено
        </span>
      </div>

      <div class="row q-gutter-sm items-center">
        <q-input
          v-model="newLowPriority"
          dense
          outlined
          label="Название клиента или бренда"
          style="min-width: 260px"
          @keyup.enter="addLowPriority"
        />
        <q-btn
          color="primary"
          icon="add"
          label="Добавить"
          :loading="lowPrioritySaving"
          @click="addLowPriority"
        />
        <q-btn
          v-if="lowPriorityDefault.length && lowPriority.length !== lowPriorityDefault.length"
          flat
          no-caps
          label="Вернуть Sunlight/Санлайт"
          :disable="lowPrioritySaving"
          @click="saveLowPriority([...lowPriorityDefault])"
        />
      </div>
      <div v-if="lowPriorityError" class="row items-center no-wrap q-gutter-sm q-mt-xs">
        <q-icon name="error_outline" color="negative" size="16px" />
        <div class="col text-caption text-negative">{{ lowPriorityError }}</div>
        <q-btn dense flat no-caps size="sm" label="Повторить" @click="loadDeliveryLists" />
      </div>
    </div>

    <!-- Фильтр качества кропа: «мусорные» вырезки (дефис, номер дома,
         ложное срабатывание детектора) читаются последними. Замер
         scripts/bench_crop_quality.py: 62 % пустых чтений отсекается,
         1,1 % полезных откладывается (и читается, если остальные пусты). -->
    <div v-if="!compact" class="q-mt-lg delivery-block delivery-block--crop-filter">
      <q-toggle
        :model-value="cropFilterEnabled"
        label="Откладывать чтение «мусорных» кропов"
        color="primary"
        dense
        :disable="cropFilterSaving"
        @update:model-value="setCropFilter"
      />
      <div class="text-caption text-grey q-mt-xs">
        Кроп, не похожий на щит, читается последним — и только если обычные
        кропы не дали описания. Экономит время модели, ничего не теряя.
      </div>
      <div v-if="cropFilterError" class="text-caption text-negative q-mt-xs">
        {{ cropFilterError }}
      </div>
    </div>

    <!-- Запрещённые к выдаче слова: мат и обрывки распознавания не попадают
         в клиента/бренд/теги/описание (владелец, 21.11.2026). -->
    <div v-if="!compact" class="q-mt-lg delivery-block delivery-block--forbidden">
      <div class="text-subtitle2">Запрещённые к выдаче слова</div>
      <div class="text-caption text-grey q-mb-sm">
        Слова, которые не должны появляться в карточке фото: мат и случайные
        обрывки распознавания. Совпадение — по целому слову, без учёта
        регистра: «педо» не тронет «торпедо». Такие значения не попадают в
        клиента, бренд, теги и описание.
      </div>

      <div class="row q-gutter-xs q-mb-sm">
        <q-chip
          v-for="word in forbiddenWords"
          :key="word"
          dense
          removable
          color="grey-3"
          :disable="forbiddenSaving"
          @remove="removeForbidden(word)"
        >
          {{ word }}
        </q-chip>
        <span v-if="!forbiddenWords.length" class="text-caption text-grey">
          Список пуст — фильтр выключен
        </span>
      </div>

      <div class="row q-gutter-sm items-center">
        <q-input
          v-model="newForbidden"
          dense
          outlined
          label="Слово или часть слова"
          style="min-width: 260px"
          @keyup.enter="addForbidden"
        />
        <q-btn
          color="primary"
          icon="add"
          label="Добавить"
          :loading="forbiddenSaving"
          @click="addForbidden"
        />
      </div>
      <div
        v-if="forbiddenError"
        class="row items-center no-wrap q-gutter-sm q-mt-xs"
      >
        <q-icon name="error_outline" color="negative" size="16px" />
        <div class="col text-caption text-negative">{{ forbiddenError }}</div>
        <q-btn dense flat no-caps size="sm" label="Повторить" @click="loadDeliveryLists" />
      </div>
    </div>

    <!-- Журнал правок: кто, что и когда изменил (в компактном режиме скрыт). -->
    <div v-if="(audit.length || errors.audit) && !compact" class="q-mt-lg">
      <div class="row items-center no-wrap q-gutter-sm q-mb-xs">
        <div class="col text-caption text-grey-8">История изменений</div>
        <q-btn
          v-if="errors.audit"
          dense
          flat
          no-caps
          size="sm"
          label="Повторить"
          @click="loadAudit"
        />
      </div>
      <div v-if="errors.audit" class="text-caption text-negative q-mb-xs">
        {{ errors.audit }}
      </div>
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
