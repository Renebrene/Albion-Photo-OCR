<script setup>
// Доступность оригиналов (технический раздел → Данные).
//
// Отвечает на вопрос «почему у половины фото оригинал недоступен», не открывая
// карточки: корень без каталога — это отмонтированный том, а не пропавшие файлы
// (живой случай 27.10.2026: 27 974 фото остались на пути отключённого диска
// Win10, а корпус лежал на TEST). Сводка приходит из /v1/originals/health — это
// is_dir() по корням и по одному счётчику на корень в SQL.
//
// Полная пофайловая проверка сюда не тащится: 57 тыс. stat на сетевом томе —
// дело скрипта scripts/check_originals.py, а не HTTP-запроса.
import { computed, onMounted, ref } from 'vue'

import { fetchOriginalsHealth } from '../api/client'

const health = ref(null)
const error = ref(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    health.value = await fetchOriginalsHealth()
    error.value = null
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(load)

// Тревожимся только о тех отключённых томах, на которых что-то лежит: пустой
// корень в списке (например, старый диск, оставленный в SCENE_ORIGINALS_ROOTS)
// сам по себе никому не мешает.
const affected = computed(() =>
  (health.value?.roots || []).filter((root) => !root.available && root.photos > 0),
)

const affectedPhotos = computed(() =>
  affected.value.reduce((sum, root) => sum + root.photos, 0),
)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="text-subtitle2 col">Доступность оригиналов</div>
      <q-btn dense flat icon="refresh" :loading="loading" aria-label="Обновить" @click="load" />
    </div>

    <q-banner v-if="error" class="bg-red-1 text-negative">
      {{ error }}
    </q-banner>

    <template v-if="health">
      <q-banner v-if="!health.configured" class="bg-orange-1">
        <code>SCENE_ORIGINALS_ROOTS</code> не задан: оригиналы не отдаются вообще.
      </q-banner>

      <template v-else>
        <q-markup-table dense flat bordered>
          <thead>
            <tr>
              <th class="text-left">Том</th>
              <th class="text-left">Путь</th>
              <th class="text-right">Фото</th>
              <th class="text-left">Состояние</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="root in health.roots" :key="root.path">
              <td>{{ root.label }}</td>
              <td class="text-caption text-grey-7">{{ root.path }}</td>
              <td class="text-right">{{ root.photos }}</td>
              <td>
                <span v-if="root.available" class="text-positive">подключён</span>
                <span v-else class="text-negative">не подключён</span>
              </td>
            </tr>
          </tbody>
        </q-markup-table>

        <div class="text-caption text-grey q-mt-sm">
          Всего записей: {{ health.total_photos }} · вне разрешённых корней:
          {{ health.outside_roots }}
        </div>

        <div v-if="affected.length" class="text-caption text-negative q-mt-xs">
          На отключённом томе {{ affected.map((root) => root.label).join(', ') }} —
          {{ affectedPhotos }} фото: у них оригинал недоступен. Смонтируйте том или
          перенесите пути (<code>scripts/remap_source_root.py</code>).
        </div>
      </template>
    </template>
  </div>
</template>
