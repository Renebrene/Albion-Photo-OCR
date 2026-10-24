// Единое подтверждение для необратимых действий.
//
// Проверка аудита: удаление адреса, подборки, сохранённого поиска, очистка
// очереди заданий и сброс настроек отображения срабатывали по одному клику по
// мелкой иконке. Отмены нет — значит перед действием нужно явное согласие.
//
//   if (!(await confirmDialog({ message: 'Удалить подборку «Моя»?' }))) return
//   await remove()
import { Dialog } from 'quasar'

export function confirmDialog({
  title = 'Подтвердите действие',
  message = 'Действие нельзя отменить.',
  okLabel = 'Удалить',
  cancelLabel = 'Отмена',
  color = 'negative',
} = {}) {
  return new Promise((resolve) => {
    Dialog.create({
      title,
      message,
      ok: { label: okLabel, color, noCaps: true },
      cancel: { label: cancelLabel, flat: true, noCaps: true },
      persistent: true,
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false))
  })
}
