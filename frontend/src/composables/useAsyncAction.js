// Сквозной хелпер для кнопок с асинхронным действием.
//
// Проблема, которую он закрывает: обработчик без защиты от повторного входа.
// Двойной клик по «Запустить», «Сохранить» или «Удалить» отправляет второй
// запрос — в лучшем случае это лишняя нагрузка, в худшем дубликат данных
// (вторая подборка, второй пользователь, второй пересчёт слепков).
//
// Использование:
//
//   const save = useAsyncAction()
//   async function doSave() {
//     await save.run(async () => { ... })   // второй вызов вернётся сразу
//   }
//
//   <q-btn :loading="save.busy.value" @click="doSave" />
//
// В шаблоне `<script setup>` обращаются к `save.busy` (ref разворачивается
// автоматически). Флаг снимается в `finally`, поэтому ошибка действия не
// оставляет кнопку навсегда занятой.
import { ref } from 'vue'

export function useAsyncAction() {
  const busy = ref(false)

  async function run(action) {
    if (busy.value) return undefined

    busy.value = true

    try {
      return await action()
    } finally {
      busy.value = false
    }
  }

  return { busy, run }
}
