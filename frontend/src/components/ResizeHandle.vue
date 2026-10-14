<script setup>
// Тянущаяся граница между блоками страницы.
//
// Компонент не знает, что именно он разделяет: он сообщает смещение курсора
// (в пикселях) через emit('resize', delta), а решение о размерах принимает
// владелец состояния (stores/display.js), который и ограничивает значения.
import { onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  // 'vertical' — тянем влево/вправо (граница колонок),
  // 'horizontal' — вверх/вниз (граница блоков внутри панели).
  direction: { type: String, default: 'vertical' },
  title: { type: String, default: '' },
})

const emit = defineEmits(['resize', 'resize-end'])

const dragging = ref(false)

let startX = 0
let startY = 0
let lastX = 0
let lastY = 0

function onPointerDown(event) {
  if (event.button !== 0) return

  dragging.value = true
  startX = lastX = event.clientX
  startY = lastY = event.clientY

  // Держим указатель на элементе, чтобы не терять события при быстром движении.
  event.currentTarget.setPointerCapture?.(event.pointerId)
  document.body.style.userSelect = 'none'
}

function onPointerMove(event) {
  if (!dragging.value) return

  const delta =
    props.direction === 'vertical'
      ? event.clientX - lastX
      : event.clientY - lastY

  lastX = event.clientX
  lastY = event.clientY

  if (delta) emit('resize', delta)
}

function stop() {
  if (!dragging.value) return

  dragging.value = false
  document.body.style.userSelect = ''
  emit('resize-end', {
    x: lastX - startX,
    y: lastY - startY,
  })
}

function onKeydown(event) {
  // Клавиатура: стрелки двигают границу на 10 px.
  const step = 10

  if (props.direction === 'vertical') {
    if (event.key === 'ArrowLeft') emit('resize', -step)
    else if (event.key === 'ArrowRight') emit('resize', step)
    else return
  } else {
    if (event.key === 'ArrowUp') emit('resize', -step)
    else if (event.key === 'ArrowDown') emit('resize', step)
    else return
  }

  event.preventDefault()
}

onBeforeUnmount(() => {
  document.body.style.userSelect = ''
})
</script>

<template>
  <div
    class="resize-handle"
    :class="[
      direction === 'vertical' ? 'resize-handle--vertical' : 'resize-handle--horizontal',
      { 'resize-handle--dragging': dragging },
    ]"
    role="separator"
    tabindex="0"
    :aria-orientation="direction === 'vertical' ? 'vertical' : 'horizontal'"
    @pointerdown.prevent="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="stop"
    @pointercancel="stop"
    @lostpointercapture="stop"
    @keydown="onKeydown"
  >
    <q-tooltip v-if="title">{{ title }}</q-tooltip>
  </div>
</template>

<style scoped>
.resize-handle {
  flex: 0 0 auto;
  background: transparent;
  transition: background 120ms ease;
  touch-action: none;
}

.resize-handle:hover,
.resize-handle--dragging {
  background: var(--q-primary);
}

.resize-handle--vertical {
  width: 6px;
  cursor: col-resize;
}

.resize-handle--horizontal {
  height: 6px;
  cursor: row-resize;
}
</style>
