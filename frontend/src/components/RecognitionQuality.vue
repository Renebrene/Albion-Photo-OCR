<script setup>
import { computed, onMounted, ref } from 'vue'

import { fetchRecognitionQuality } from '../api/client'

const snapshot = ref(null)
const error = ref(null)
const loading = ref(false)
const selectedVariantId = ref('production')
const addressFilter = ref('')
const showNamingVariants = ref(true)

const variants = computed(() => snapshot.value?.variants || [])
const selectedVariant = computed(() =>
  variants.value.find((item) => item.id === selectedVariantId.value) || variants.value[0] || null,
)
const rows = computed(() => {
  const query = addressFilter.value.trim().toLocaleLowerCase('ru')
  // Номер строки фиксируется по опубликованному снимку: при фильтре номера
  // не пересчитываются, чтобы на них можно было ссылаться при разборе.
  const items = (snapshot.value?.addresses || []).map((item, index) => ({
    ...item,
    number: index + 1,
    kind: item.classification
      || (item.is_naming_variant ? 'naming_variant' : 'recognition_error'),
  }))
  const filtered = items.filter((item) =>
    (showNamingVariants.value || item.kind === 'recognition_error')
    && (!query || String(item.name || '').toLocaleLowerCase('ru').includes(query)),
  )
  return filtered.sort((a, b) => a.number - b.number)
})
const pairRows = computed(() => {
  if (!selectedVariant.value) return []
  return (selectedVariant.value.wrong_pairs || []).map((item, index) => ({
    ...item,
    number: index + 1,
  }))
})

function formatPercent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  return `${(Number(value) * 100).toLocaleString('ru-RU', { maximumFractionDigits: 2 })}%`
}

function formatCount(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  return Number(value).toLocaleString('ru-RU')
}

function variantLabel(variant) {
  return `${variant.name} · ${formatPercent(variant.accuracy)} · Δ ${Number(variant.delta_vs_production || 0) > 0 ? '+' : ''}${formatCount(variant.delta_vs_production || 0)}`
}

async function load() {
  loading.value = true
  error.value = null
  try {
    snapshot.value = await fetchRecognitionQuality()
    if (!variants.value.some((item) => item.id === selectedVariantId.value)) {
      selectedVariantId.value = variants.value[0]?.id || ''
    }
  } catch (err) {
    error.value = err?.message || 'Не удалось загрузить снимок качества распознавания'
    snapshot.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="row items-center q-mb-sm">
      <div class="col">
        <div class="text-subtitle1">Качество распознавания</div>
        <div v-if="snapshot" class="text-caption text-grey">
          Снимок от {{ snapshot.generated_at }} · HYBRID run {{ snapshot.source.run_id }}
        </div>
      </div>
      <q-btn dense flat icon="refresh" aria-label="Обновить качество распознавания" :loading="loading" @click="load" />
    </div>

    <q-banner class="bg-orange-1 text-dark q-mb-md">
      Это зафиксированная офлайн-оценка, не live-точность production. Эталонные адреса эвристически сопоставлены по именам файлов; независимого temporal holdout в этом снимке нет.
    </q-banner>

    <q-banner v-if="error" class="bg-red-1 text-negative q-mb-md">
      {{ error }}
    </q-banner>

    <div v-if="loading && !snapshot" class="row justify-center q-my-lg">
      <q-spinner-dots color="primary" size="40px" />
    </div>
    <div v-else-if="!snapshot && !error" class="text-grey q-my-md">
      Снимок наблюдений пока не опубликован.
    </div>

    <template v-if="snapshot">
      <div class="row q-col-gutter-sm q-mb-md">
        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Фото в выборке</div>
              <div class="text-h6">{{ formatCount(snapshot.totals.items) }}</div>
              <div class="text-caption">С меткой: {{ formatCount(snapshot.totals.labelled) }}</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Текущий baseline</div>
              <div class="text-h6">{{ formatPercent(snapshot.variants.find((item) => item.id === 'production')?.accuracy) }}</div>
              <div class="text-caption">Точность в размеченной части</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Без однозначной метки</div>
              <div class="text-h6">{{ formatCount(snapshot.totals.unlabelled) }}</div>
              <div class="text-caption">Исключены из accuracy</div>
            </q-card-section>
          </q-card>
        </div>
        <div class="col-12 col-sm-6 col-md-3">
          <q-card flat bordered class="fit">
            <q-card-section>
              <div class="text-caption text-grey">Сомнительные адреса</div>
              <div class="text-h6">{{ formatCount(snapshot.address_metrics_source.error_addresses) }}</div>
              <div class="text-caption">
                из {{ formatCount(snapshot.address_metrics_source.total_addresses) }} ·
                вариантов названия — {{ formatCount(snapshot.address_metrics_source.naming_variant_addresses) }},
                ошибок в названии — {{ formatCount(snapshot.address_metrics_source.label_error_addresses) }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <q-card flat bordered class="q-mb-md">
        <q-card-section>
          <div class="row items-center q-col-gutter-sm">
            <div class="col-12 col-md-6">
              <div class="text-subtitle2">Сравнение вариантов на общей выборке</div>
              <div class="text-caption text-grey">Только направленные агрегаты; «исправлено» и «испортило» здесь не выводятся без per-photo парного diff.</div>
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="selectedVariantId"
                :options="variants.map((item) => ({ label: variantLabel(item), value: item.id }))"
                emit-value
                map-options
                dense
                outlined
                label="Вариант для разбора ошибок"
              />
            </div>
          </div>
          <q-markup-table dense flat class="q-mt-sm">
            <thead>
              <tr>
                <th class="text-left">Вариант</th>
                <th class="text-right">Верно</th>
                <th class="text-right">Ошибки</th>
                <th class="text-right">Проверка</th>
                <th class="text-right">Точность</th>
                <th class="text-right">Δ к baseline, фото</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="variant in variants" :key="variant.id" :class="variant.id === selectedVariantId ? 'bg-blue-1' : ''">
                <td>{{ variant.name }}</td>
                <td class="text-right">{{ formatCount(variant.correct) }}</td>
                <td class="text-right">{{ formatCount(variant.wrong) }}</td>
                <td class="text-right">{{ formatCount(variant.review) }}</td>
                <td class="text-right">{{ formatPercent(variant.accuracy) }} <span class="text-caption text-grey">({{ formatCount(variant.labelled) }})</span></td>
                <td class="text-right">{{ Number(variant.delta_vs_production) > 0 ? '+' : '' }}{{ formatCount(variant.delta_vs_production) }}</td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card-section>
      </q-card>

      <div class="row q-col-gutter-md">
        <div class="col-12 col-xl-7">
          <q-card flat bordered>
            <q-card-section>
              <div class="row items-center q-col-gutter-sm q-mb-sm">
                <div class="col text-subtitle2">Ошибки по адресам (более 5%)</div>
                <div class="col-12 col-sm-5">
                  <q-input v-model="addressFilter" dense outlined clearable label="Фильтр адреса" />
                </div>
                <div class="col-12 col-sm-auto">
                  <q-toggle v-model="showNamingVariants" dense label="Показывать названия" />
                </div>
              </div>
              <div class="text-caption text-grey q-mb-sm">
                В таблице {{ formatCount(snapshot.address_metrics_source.selected_addresses) }} из {{ formatCount(snapshot.address_metrics_source.total_addresses) }} адресов отчёта HYBRID run {{ snapshot.address_metrics_source.run_id }} с долей ошибок более 5%: ошибки — {{ formatCount(snapshot.address_metrics_source.error_addresses) }}, варианты названия — {{ formatCount(snapshot.address_metrics_source.naming_variant_addresses) }}, ошибки в названии — {{ formatCount(snapshot.address_metrics_source.label_error_addresses) }}. Строки с отметкой названия не входят в число сомнительных.
              </div>
              <q-markup-table dense flat wrap-cells>
                <thead>
                  <tr>
                    <th class="text-right quality-number">№</th>
                    <th class="text-left">Эталонный адрес</th>
                    <th class="text-right">Фото</th>
                    <th class="text-right">В слепке</th>
                    <th class="text-right">Верно</th>
                    <th class="text-right">Ошибки</th>
                    <th class="text-right">Без результата</th>
                    <th class="text-right">Доля ошибок</th>
                    <th class="text-left">Чаще путается с</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in rows"
                    :key="item.address_id"
                    :data-address-number="item.number"
                    :class="item.kind !== 'recognition_error' ? 'quality-variant-row' : ''"
                  >
                    <td class="text-right text-grey">{{ item.number }}</td>
                    <td>
                      {{ item.name }} <span class="text-caption text-grey">#{{ item.address_id }}</span>
                      <q-badge
                        v-if="item.kind === 'naming_variant'"
                        color="grey-6"
                        label="вариант названия"
                        class="q-ml-xs"
                      />
                      <q-badge
                        v-else-if="item.kind === 'label_error'"
                        color="orange-7"
                        label="ошибка в названии"
                        class="q-ml-xs"
                      />
                      <div v-if="item.kind === 'naming_variant'" class="text-caption text-grey">
                        → {{ item.canonical_name }} <span>#{{ item.canonical_address_id }}</span>
                        · расхождений {{ formatCount(item.wrong) }}
                      </div>
                      <div v-if="item.kind === 'label_error' && item.note" class="text-caption text-grey">
                        {{ item.note }}
                      </div>
                    </td>
                    <td class="text-right">{{ formatCount(item.items) }}</td>
                    <td class="text-right">{{ formatCount(item.fingerprint_items) }}</td>
                    <td class="text-right">{{ formatCount(item.correct) }}</td>
                    <td class="text-right">{{ item.kind !== 'recognition_error' ? '—' : formatCount(item.wrong) }}</td>
                    <td class="text-right">{{ formatCount(item.unknown) }}</td>
                    <td class="text-right">{{ item.kind !== 'recognition_error' ? '—' : formatPercent(item.error_rate) }}</td>
                    <td>
                      <div v-for="pair in item.top_confusions" :key="`${item.address_id}-${pair.address_id}`">
                        {{ pair.name }} · {{ formatCount(pair.count) }}
                      </div>
                    </td>
                  </tr>
                  <tr v-if="!rows.length">
                    <td colspan="9" class="text-center text-grey">По фильтру ничего не найдено</td>
                  </tr>
                </tbody>
              </q-markup-table>
              <div class="text-caption text-grey q-mt-sm">
                Доля ошибок рассчитана как wrong / items. Unknown — отдельная категория. «Фото в слепке» — число активных эталонных кадров, не знаменатель accuracy. Адресная таблица взята из отдельного run {{ snapshot.address_metrics_source.run_id }} ({{ formatCount(snapshot.address_metrics_source.items) }} фото), не из выборки сравнения вариантов. Показаны только адреса с долей ошибок более 5%; это не оценка каждого адреса справочника.
              </div>
            </q-card-section>
          </q-card>
        </div>

        <div class="col-12 col-xl-5">
          <q-card flat bordered>
            <q-card-section>
              <div class="text-subtitle2 q-mb-sm">Основные направленные ошибки: {{ selectedVariant?.name || '—' }}</div>
              <q-markup-table dense flat wrap-cells>
                <thead>
                  <tr>
                    <th class="text-right quality-number">№</th>
                    <th class="text-left">Ожидалось</th>
                    <th class="text-left">Предсказано</th>
                    <th class="text-right">Фото</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="pair in pairRows" :key="`${pair.expected_id}-${pair.predicted_id}-${pair.number}`">
                    <td class="text-right text-grey">{{ pair.number }}</td>
                    <td>{{ pair.expected }} <span class="text-caption text-grey">#{{ pair.expected_id }}</span></td>
                    <td>{{ pair.predicted }} <span class="text-caption text-grey">#{{ pair.predicted_id }}</span></td>
                    <td class="text-right">{{ formatCount(pair.count) }}</td>
                  </tr>
                  <tr v-if="!pairRows.length">
                    <td colspan="4" class="text-center text-grey">Для этого варианта нет записанных пар ошибок</td>
                  </tr>
                </tbody>
              </q-markup-table>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <q-expansion-item class="q-mt-md" dense label="Источник данных и ограничения">
        <q-card flat bordered>
          <q-card-section>
            <div>Метод меток: {{ snapshot.source.label_method }}.</div>
            <div>Источник: {{ snapshot.source.experiment }}, run {{ snapshot.source.run_id }}.</div>
            <div>Независимые ручные метки: {{ snapshot.source.independent_manual_labels ? 'да' : 'нет' }}.</div>
            <div>Temporal holdout: {{ snapshot.source.is_temporal_holdout ? 'да' : 'нет' }}.</div>
            <ul class="q-mb-none">
              <li v-for="(note, index) in snapshot.source.notes" :key="index">{{ note }}</li>
            </ul>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </template>
  </div>
</template>

<style scoped>
.quality-number {
  width: 36px;
  white-space: nowrap;
}

.quality-variant-row {
  background: rgba(0, 0, 0, 0.03);
}
</style>
