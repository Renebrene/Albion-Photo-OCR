<script setup>
// Loads an image through the authenticated API and shows it from a blob URL,
// because <img>/<q-img> cannot attach the bearer token themselves.
import { computed, onMounted, ref, watch } from 'vue'

import { authImageUrl } from '../api/client'

const props = defineProps({
  url: { type: String, required: true },
  ratio: { type: [Number, String], default: undefined },
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

const src = ref('')
const failed = ref(false)

async function load(url) {
  failed.value = false
  src.value = ''

  if (!url) return

  try {
    src.value = await authImageUrl(url)
    emit('loaded', url)
  } catch {
    failed.value = true
    emit('error', url)
  }
}

onMounted(() => load(props.url))
watch(() => props.url, (url) => load(url))
</script>

<template>
  <q-img v-if="src" :src="src" :ratio="ratioValue" />
  <div
    v-else-if="failed"
    class="flex flex-center bg-grey-3 text-grey"
    :style="ratioValue ? { aspectRatio: String(ratioValue) } : { minHeight: '48px' }"
  >
    <q-icon name="broken_image" />
  </div>
  <q-skeleton v-else :style="ratioValue ? { aspectRatio: String(ratioValue) } : { minHeight: '48px' }" />
</template>
