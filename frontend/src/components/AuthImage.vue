<script setup>
// Loads an image through the authenticated API and shows it from a blob URL,
// because <img>/<q-img> cannot attach the bearer token themselves.
import { onMounted, ref, watch } from 'vue'

import { authImageUrl } from '../api/client'

const props = defineProps({
  url: { type: String, required: true },
  ratio: { type: [Number, String], default: undefined },
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
  <q-img v-if="src" :src="src" :ratio="ratio" />
  <div
    v-else-if="failed"
    class="flex flex-center bg-grey-3 text-grey"
    :style="ratio ? { aspectRatio: String(ratio) } : { minHeight: '48px' }"
  >
    <q-icon name="broken_image" />
  </div>
  <q-skeleton v-else :style="ratio ? { aspectRatio: String(ratio) } : { minHeight: '48px' }" />
</template>
