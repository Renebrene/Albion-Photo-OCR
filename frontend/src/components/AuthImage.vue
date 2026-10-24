<script setup>
// Loads an image through the authenticated API and shows it from a blob URL,
// because <img>/<q-img> cannot attach the bearer token themselves.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { acquireImageUrl, releaseImageUrl } from '../api/client'

const props = defineProps({
  url: { type: String, required: true },
  ratio: { type: [Number, String], default: undefined },
  // Grids with hundreds of cards: следим за видимостью плитки. Прямой путь
  // показывает картинку сам (у q-img `loading` по умолчанию `lazy`, это делает
  // браузер), а наблюдатель нужен, чтобы запасная загрузка через blob не
  // началась для того, что ушло за край экрана, и чтобы отпускать удержанный
  // blob при уходе плитки из окна. Off by default so the list thumbnails and
  // the viewer keep their exact layout.
  lazy: { type: Boolean, default: false },
  // q-img fit (e.g. 'contain' in the viewer so the photo is not cropped).
  fit: { type: String, default: '' },
})

// Quasar's q-img runs `Number(ratio)`, so a string like "16/9" becomes NaN and
// the image container collapses to zero height (the poster loads but is
// invisible). Normalise any ratio to a number here so callers cannot trip on
// that: a number or "a/b" both become a positive float, anything else is
// dropped (q-img then uses the image's natural size).
const ratioValue = computed(() => {
  const raw = props.ratio

  if (typeof raw === 'number') return raw > 0 ? raw : undefined

  if (typeof raw === 'string') {
    const text = raw.trim()

    if (text.includes('/')) {
      const [a, b] = text.split('/').map(Number)
      return b > 0 ? a / b : undefined
    }

    const value = Number(text)
    return Number.isFinite(value) && value > 0 ? value : undefined
  }

  return undefined
})

// The parent can react to a missing picture (e.g. a fingerprint built before
// previews existed) instead of just showing the broken-image placeholder.
const emit = defineEmits(['error', 'loaded'])

// Основной путь — обычный src: браузер сам приложит сессионную куку, сам
// загрузит и закэширует картинку, без fetch/blob на каждую плитку.
// Blob остаётся запасным путём на случай, когда куки нет (старая сессия,
// запрет сторонних cookie) — тогда грузим вручную с заголовком.
//
// Качать blob заранее нельзя: пока прямой путь работает, он не показывается
// (у `usingBlob` своя ветка шаблона), а каждая плитка скачивалась бы дважды.
// Поэтому blob грузится ровно после ошибки прямого пути и только для того,
// что видно на экране.
const usingBlob = ref(false)
const src = ref('')
const failed = ref(false)
const heldUrl = ref('')
let requestId = 0

function releaseHeld() {
  if (heldUrl.value) {
    releaseImageUrl(heldUrl.value)
    heldUrl.value = ''
  }
}

async function load(url) {
  const request = ++requestId
  failed.value = false
  src.value = ''
  releaseHeld()

  if (!url) return

  try {
    const objectUrl = await acquireImageUrl(url)

    // The URL changed or the component unmounted while the request was in
    // flight: do not leak this reference or show a stale image.
    if (request !== requestId) {
      releaseImageUrl(url)
      return
    }

    src.value = objectUrl
    heldUrl.value = url
    emit('loaded', url)
  } catch {
    if (request !== requestId) return
    failed.value = true
    emit('error', url)
  }
}

// Lazy mode: the intersection observer keeps only the visible window of the
// grid in memory. `visible` starts false so a card below the fold does not
// fetch its fallback blob until it approaches the viewport.
const rootEl = ref(null)
let observer = null
let visible = false
// Запас загрузки: примерно три строки плиток в каждую сторону (строка ~250 px).
// Слишком большой запас заставляет браузер качать десятки картинок сразу, и
// видимые ждут в очереди; уже загруженное удерживает кэш в api/client.js,
// поэтому возврат при прокрутке не требует сети.
const LAZY_MARGIN = '800px 0px'

function startLoading() {
  if (!src.value && !failed.value) load(props.url)
}

/** Прямая загрузка не сработала — переключаемся на ручную, с заголовком. */
function onDirectError() {
  if (usingBlob.value) return

  usingBlob.value = true

  // Невидимая плитка не качает blob: ошибка могла прилететь уже после того,
  // как карточка ушла за край экрана. Наблюдатель подхватит её при возврате.
  if (visible || !props.lazy) load(props.url)
}

function stopLoading() {
  requestId += 1
  releaseHeld()
  src.value = ''
  failed.value = false
}

onMounted(() => {
  // Прямой путь грузит картинку сам, и до ошибки нам нечего наблюдать: без
  // `lazy` сразу считаем плитку видимой, чтобы запасная загрузка не ждала.
  if (!props.lazy || typeof IntersectionObserver === 'undefined') {
    visible = true
    return
  }

  observer = new IntersectionObserver(
    (entries) => {
      visible = Boolean(entries[0]?.isIntersecting)

      // Наблюдатель управляет только запасной загрузкой: пока показан прямой
      // путь, отпускать нечего.
      if (!usingBlob.value) return

      if (visible) startLoading()
      else stopLoading()
    },
    { rootMargin: LAZY_MARGIN },
  )

  // Корень есть всегда: раньше ref стоял на ветке blob, поэтому у обычной
  // плитки наблюдать было нечего, и код уходил в аварийную ветку с лишней
  // загрузкой на каждую картинку.
  if (rootEl.value) observer.observe(rootEl.value)
  else visible = true
})

watch(() => props.url, () => {
  // Новый кадр: снова начинаем с прямого пути. Если он не сработает,
  // onDirectError переключит на ручную загрузку.
  usingBlob.value = false
  failed.value = false
  src.value = ''
  releaseHeld()
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
  requestId += 1
  releaseHeld()
})
</script>

<template>
  <!-- Один корень: иначе @click/class от родителя (плитка грида) не
       наследуются, и клик по превью не открывает фото. -->
  <div ref="rootEl" class="auth-image-root">
    <q-img
      v-if="!usingBlob"
      :src="url"
      :ratio="ratioValue"
      :fit="fit || undefined"
      decoding="async"
      @error="onDirectError"
    />
    <div v-else-if="lazy" class="auth-image">
      <q-img v-if="src" :src="src" :ratio="ratioValue" :fit="fit || undefined" />
      <div
        v-else-if="failed"
        class="flex flex-center bg-grey-3 text-grey"
        :style="ratioValue ? { aspectRatio: String(ratioValue) } : { minHeight: '48px' }"
      >
        <q-icon name="broken_image" />
      </div>
      <q-skeleton v-else :style="ratioValue ? { aspectRatio: String(ratioValue) } : { minHeight: '48px' }" />
    </div>
    <q-img v-else-if="src" :src="src" :ratio="ratioValue" :fit="fit || undefined" />
    <div
      v-else-if="failed"
      class="flex flex-center bg-grey-3 text-grey"
      :style="ratioValue ? { aspectRatio: String(ratioValue) } : { minHeight: '48px' }"
    >
      <q-icon name="broken_image" />
    </div>
    <q-skeleton v-else :style="ratioValue ? { aspectRatio: String(ratioValue) } : { minHeight: '48px' }" />
  </div>
</template>

<style scoped>
.auth-image-root,
.auth-image {
  display: block;
  width: 100%;
}
</style>
