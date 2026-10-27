<script setup>
// Address directory (schema/022): the human-readable names behind a
// recognition id. The grid shows the same names as soon as an id is mapped
// here, and downloads can use them as file names (see the display settings).
import { computed, onMounted, ref } from 'vue'
import { Notify } from 'quasar'

import {
  createAddress,
  deleteAddress,
  fetchAddressDirectory,
  fetchAddressSides,
  fetchUnassignedFingerprints,
  importAddresses,
  setAddressFingerprints,
  updateAddress,
} from '../api/client'
import { useAsyncAction } from '../composables/useAsyncAction'
import { confirmDialog } from '../composables/confirmDialog'

// Закладки справочника (задание, п. 6а): «Экраны» и «Остальное». У каждой своя
// таблица и своя загрузка XLS; адрес попадает в закладку при создании и
// сохраняет её при последующих импортах.
const scope = ref('screens')

// Поверхности A(1), A(2), A(3) показываются одной строкой — стороной (правило
// «Сайта»: у щита и видеоэкрана A1/A2 остаются разными сторонами). Если у
// стороны несколько поверхностей, действия спрашивают, к какой применить.
const sideByScope = ref({ screens: [], other: [] })
const sideItems = computed(() => sideByScope.value[scope.value] || [])

// В закладках считаем стороны — таблица показывает их же, а не поверхности.
const scopeCounts = computed(() => ({
  screens: (sideByScope.value.screens || []).length,
  other: (sideByScope.value.other || []).length,
}))

const surfacePickerOpen = ref(false)
const surfacePicker = ref({ surfaces: [], action: null, label: '' })

/** Выполнить действие над стороной: над поверхностью или через выбор. */
function runOnSurface(row, action, label) {
  const surfaces = (row.surfaces || []).map((item) => ({
    ...item,
    simple_address: item.simple_address || row.simple || '',
    format: row.format,
    city: row.city,
    scope: row.scope,
  }))

  if (!surfaces.length) return

  if (surfaces.length === 1) {
    action(surfaces[0])
    return
  }

  surfacePicker.value = { surfaces, action, label }
  surfacePickerOpen.value = true
}

function pickSurface(item) {
  const pending = surfacePicker.value
  surfacePickerOpen.value = false

  if (pending && typeof pending.action === 'function') pending.action(item)
}
const unassigned = ref([])
const loading = ref(false)

// "new address" form
const newLegal = ref('')
const newSimple = ref('')

// edit dialog
const editOpen = ref(false)
const editTarget = ref(null)

// fingerprint mapping dialog
const mapOpen = ref(false)
const mapTarget = ref(null)
const mapSelected = ref([])

const busy = computed(() => loading.value)

// import from a spreadsheet
const importInput = ref(null)
const importing = ref(false)
// Выбранный файл можно сначала «примерить»: выгрузка каталога на 1500 строк
// иначе сразу добавляет полторы тысячи адресов.
const importDryRun = ref(false)

function pickImportFile() {
  importDryRun.value = false
  importInput.value?.click()
}

function pickPreviewFile() {
  importDryRun.value = true
  importInput.value?.click()
}

async function onImportFileChosen(event) {
  const [file] = Array.from(event.target.files || [])
  event.target.value = ''

  if (!file) return

  const dryRun = importDryRun.value

  importing.value = true

  try {
    const result = await importAddresses(file, { dryRun, scope: scope.value })
    Notify.create({
      type: dryRun ? 'info' : 'positive',
      message:
        `${dryRun ? 'Предпросмотр (база не изменена)' : 'Импорт'}: ` +
        `строк ${result.rows}, добавлено ${result.created}, ` +
        `обновлено ${result.updated}, без изменений ${result.skipped}` +
        (result.renamed ? `, переименовано слепков ${result.renamed}` : '') +
        (result.errors?.length ? `, ошибок ${result.errors.length}` : ''),
    })

    // Предпросмотр ничего не меняет — перечитывать справочник незачем.
    if (!dryRun) await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    importing.value = false
  }
}

// Колонки объявлены один раз: литерал в шаблоне создавался заново на каждой
// отрисовке, а q-table по нему пересобирает строки.
// Сведённый вид: одна строка — одна сторона со счётчиком поверхностей.
/** Идентификаторы всех поверхностей стороны — без повторов. */
function sideFingerprints(row) {
  return [...new Set((row.surfaces || []).flatMap((item) => item.fingerprints || []))]
}

const columns = [
  { name: 'side', label: 'Сторона', field: 'side', align: 'left' },
  { name: 'base', label: 'Адрес', field: 'base', align: 'left' },
  // Приходит из XLS (колонка «Формат»); на «Экранах» — всегда «Видеоэкран».
  { name: 'format', label: 'Формат', field: 'format', align: 'left' },
  { name: 'city', label: 'Город', field: 'city', align: 'left' },
  { name: 'fp', label: 'Идентификаторы', field: 'surfaces', align: 'left' },
  { name: 'count', label: 'Поверхностей', field: 'count', align: 'right' },
  { name: 'actions', label: '', field: 'side', align: 'right' },
]

async function load() {
  loading.value = true
  try {
    const [screenSides, otherSides, free] = await Promise.all([
      fetchAddressSides('screens'),
      fetchAddressSides('other'),
      fetchUnassignedFingerprints(),
    ])
    sideByScope.value = {
      screens: screenSides.items || [],
      other: otherSides.items || [],
    }
    unassigned.value = free.items || []
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  } finally {
    loading.value = false
  }
}

// Удаление адреса необратимо (на него ссылаются слепки, он даёт юридическое
// имя при скачивании), поэтому спрашиваем подтверждение и блокируем кнопку.
const { busy: editBusy, run: editRun } = useAsyncAction()
const { busy: mapBusy, run: mapRun } = useAsyncAction()
const { busy: removeBusy, run: removeRun } = useAsyncAction()

onMounted(load)

async function addAddress() {
  const legal = newLegal.value.trim()
  const simple = newSimple.value.trim()

  if (!legal && !simple) {
    Notify.create({
      type: 'warning',
      message: 'Заполните юридическое или упрощённое название',
    })
    return
  }

  try {
    await createAddress({
      legal_address: legal || null,
      simple_address: simple || null,
      // Новый адрес попадает в открытую закладку.
      scope: scope.value,
    })
    newLegal.value = ''
    newSimple.value = ''
    Notify.create({ type: 'positive', message: 'Адрес добавлен' })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
}

function openEdit(item) {
  editTarget.value = { ...item }
  editOpen.value = true
}

async function saveEdit() {
  const target = editTarget.value

  await editRun(async () => {
  try {
    await updateAddress(target.address_id, {
      legal_address: target.legal_address,
      simple_address: target.simple_address,
      active: target.active,
    })
    editOpen.value = false
    Notify.create({ type: 'positive', message: 'Адрес сохранён' })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
  })
}
async function removeAddress(item) {
  const confirmed = await confirmDialog({
    title: 'Удалить адрес?',
    message: `«${item.simple_address || item.legal_address}» · привязано слепков: ${(item.fingerprints || []).length}`
      + ' — привязка будет снята, а имена файлов вернутся к исходным.',
  })

  if (!confirmed) return

  await removeRun(async () => {
  try {
    await deleteAddress(item.address_id)
    Notify.create({ type: 'positive', message: 'Адрес удалён' })
    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
  })
}
function openMap(item) {
  mapTarget.value = item
  mapSelected.value = [...item.fingerprints]
  mapOpen.value = true
}

// Every id that can be assigned: the ones already here plus the free ones.
const mapOptions = computed(() => {
  const options = new Set([...(mapTarget.value?.fingerprints || []), ...unassigned.value])
  return [...options].sort()
})

async function saveMap() {
  await mapRun(async () => {
    try {
    // Сохраняем НАМЕРЕНИЕ пользователя, а не снимок списка: пока окно было
    // открыто, к адресу могли привязать ещё слепки (вкладка «Слепки»,
    // другой пользователь). Отвязываем только те, что сняли здесь, а
    // появившиеся за это время сохраняем — иначе у слепка пропадал адрес.
    const data = await fetchAddressDirectory()
    const fresh = (data.items || []).find(
      (row) => row.address_id === mapTarget.value.address_id,
    )
    const freshIds = fresh?.fingerprints || []
    const opened = new Set(mapTarget.value.fingerprints || [])
    const selected = new Set(mapSelected.value)
    const unchecked = [...opened].filter((id) => !selected.has(id))
    const merged = [
      ...new Set([
        ...freshIds.filter((id) => !unchecked.includes(id)),
        ...selected,
      ]),
    ].sort()

    await setAddressFingerprints(mapTarget.value.address_id, merged)
    mapOpen.value = false

    if (freshIds.some((id) => !opened.has(id))) {
      Notify.create({
        type: 'info',
        message: 'К адресу добавились новые идентификаторы — список обновлён',
      })
    } else {
      Notify.create({ type: 'positive', message: 'Идентификаторы сохранены' })
    }

    await load()
  } catch (err) {
    Notify.create({ type: 'negative', message: err.message })
  }
  })
}</script>

<template>
  <div class="column q-gutter-md" style="max-width: 900px">
    <!-- Две закладки справочника (задание, п. 6а): у каждой своя таблица и своя
         загрузка XLS. Новый адрес и импорт попадают в открытую закладку. -->
    <q-tabs
      v-model="scope"
      dense
      align="left"
      class="text-primary"
      active-color="primary"
      indicator-color="primary"
    >
      <q-tab name="screens" :label="`Экраны (${scopeCounts.screens})`" />
      <q-tab name="other" :label="`Остальное (${scopeCounts.other})`" />
    </q-tabs>

    <q-card flat bordered>
      <q-card-section>
        <div class="text-subtitle2 q-mb-sm">Новый адрес</div>
        <div class="row q-col-gutter-sm">
          <div class="col-12 col-sm-5">
            <q-input
              v-model="newLegal"
              dense
              outlined
              label="Юридическое название"
              @keyup.enter="addAddress"
            />
          </div>
          <div class="col-12 col-sm-4">
            <q-input
              v-model="newSimple"
              dense
              outlined
              label="Упрощённое (alias)"
              @keyup.enter="addAddress"
            />
          </div>
          <div class="col-12 col-sm-3">
            <q-btn
              color="primary"
              icon="add"
              label="Добавить"
              :disable="busy"
              @click="addAddress"
            />
          </div>
        </div>
        <div class="text-caption text-grey q-mt-sm">
          Хотя бы одно из двух названий обязательно; юридическое — уникально.
          Существующий адрес можно загрузить файлом .xlsx/.csv — сопоставление
          идёт по юридическому названию, id адреса сохраняется.
        </div>

        <div class="row q-mt-sm">
          <q-btn
            dense
            flat
            icon="upload_file"
            label="Импорт из XLSX / CSV"
            :loading="importing"
            @click="pickImportFile"
          />
          <q-btn
            dense
            flat
            icon="visibility"
            label="Предпросмотр"
            :loading="importing"
            @click="pickPreviewFile"
          >
            <q-tooltip>Посчитать, что изменится, и ничего не записать</q-tooltip>
          </q-btn>
          <input
            ref="importInput"
            type="file"
            accept=".xlsx,.xlsm,.csv,.tsv"
            class="hidden-input"
            @change="onImportFileChosen"
          />
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered>
      <q-card-section class="row items-center q-pb-xs">
        <div class="panel-title col">Адреса ({{ sideItems.length }})</div>
        <q-btn dense flat icon="refresh" :loading="busy" @click="load">
          <q-tooltip>Обновить</q-tooltip>
        </q-btn>
      </q-card-section>
      <q-separator />

      <!-- Одна строка — одна сторона: A(1), A(2), A(3) сведены в A (правило
           «Сайта»); у щита и видеоэкрана A1/A2 остаются разными сторонами. -->
      <q-table
        :rows="sideItems"
        :columns="columns"
        :row-key="(row) => `${row.base}|${row.format}|${row.side}`"
        dense
        flat
        :pagination="{ rowsPerPage: 0 }"
        :loading="busy"
        no-data-label="Сторон нет"
      >
        <!-- На закладке «Экраны» формат всегда «Видеоэкран» (задание, п. 6б);
             на «Остальном» — тот, что пришёл из XLS по юридическому адресу. -->
        <template #body-cell-format="props">
          <q-td :props="props">
            {{ scope === 'screens' ? 'Видеоэкран' : (props.row.format || '—') }}
          </q-td>
        </template>
        <template #body-cell-base="props">
          <q-td :props="props">
            {{ props.row.base }}
            <div v-if="props.row.simple" class="text-caption text-grey">
              {{ props.row.simple }}
            </div>
          </q-td>
        </template>
        <template #body-cell-fp="props">
          <q-td :props="props">
            <q-chip
              v-for="id in sideFingerprints(props.row)"
              :key="id"
              dense
              size="sm"
              color="primary"
              text-color="white"
            >
              {{ id }}
            </q-chip>
            <span v-if="!sideFingerprints(props.row).length" class="text-caption text-grey">
              не сопоставлено
            </span>
          </q-td>
        </template>
        <template #body-cell-count="props">
          <q-td :props="props">
            {{ props.row.count }}
            <q-tooltip>
              поверхности: {{ props.row.surfaces.map((item) => item.side).join(', ') }}
            </q-tooltip>
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn dense flat icon="link" @click="runOnSurface(props.row, openMap, 'Идентификаторы')">
              <q-tooltip>Идентификаторы распознавания</q-tooltip>
            </q-btn>
            <q-btn dense flat icon="edit" @click="runOnSurface(props.row, openEdit, 'Изменить названия')">
              <q-tooltip>Изменить названия</q-tooltip>
            </q-btn>
            <q-btn
              dense
              flat
              icon="delete"
              :loading="removeBusy"
              @click="runOnSurface(props.row, removeAddress, 'Удалить адрес')"
            >
              <q-tooltip>Удалить адрес</q-tooltip>
            </q-btn>
          </q-td>
        </template>
      </q-table>
    </q-card>

    <!-- У стороны несколько поверхностей — спрашиваем, к какой применить действие. -->
    <q-dialog v-model="surfacePickerOpen">
      <q-card style="min-width: 420px">
        <q-card-section class="text-subtitle1">
          {{ surfacePicker.label }} — выберите поверхность
        </q-card-section>
        <q-separator />
        <q-list dense separator>
          <q-item
            v-for="surface in surfacePicker.surfaces"
            :key="surface.address_id"
            clickable
            @click="pickSurface(surface)"
          >
            <q-item-section>
              <q-item-label>{{ surface.legal_address }}</q-item-label>
              <q-item-label caption>
                сторона {{ surface.side || '—' }}
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </q-dialog>

    <!-- edit names -->
    <q-dialog v-model="editOpen">
      <q-card style="min-width: 380px">
        <q-card-section class="text-subtitle1">Адрес</q-card-section>
        <q-separator />
        <q-card-section class="q-gutter-sm">
          <q-input
            v-model="editTarget.legal_address"
            dense
            outlined
            label="Юридическое название"
          />
          <q-input
            v-model="editTarget.simple_address"
            dense
            outlined
            label="Упрощённое (alias)"
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Сохранить" :loading="editBusy" @click="saveEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- fingerprint mapping -->
    <q-dialog v-model="mapOpen">
      <q-card style="min-width: 420px; max-width: 90vw">
        <q-card-section class="text-subtitle1">
          Идентификаторы: {{ mapTarget?.simple_address || mapTarget?.legal_address }}
        </q-card-section>
        <q-separator />
        <q-card-section style="max-height: 55vh; overflow: auto">
          <q-option-group
            v-model="mapSelected"
            :options="mapOptions.map((id) => ({ label: id, value: id }))"
            type="checkbox"
            dense
          />
          <div v-if="!mapOptions.length" class="text-caption text-grey">
            Свободных идентификаторов нет — все уже сопоставлены.
          </div>
          <div class="text-caption text-grey q-mt-sm">
            Идентификатор принадлежит одному адресу: отмеченный здесь будет
            перенесён с прежнего.
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Отмена" v-close-popup />
          <q-btn color="primary" label="Сохранить" :loading="mapBusy" @click="saveMap" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<style scoped>
.hidden-input {
  display: none;
}
</style>
