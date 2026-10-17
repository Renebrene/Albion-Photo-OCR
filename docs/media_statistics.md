# Статистика в техническом разделе

Дата: 2026-10-17

## Где

Технический раздел → вкладка **«Статистика»** (`frontend/src/components/MediaStatistics.vue`).
Данные — `GET /v1/media/statistics` (scope `read`), источник
`app/api/video_repository.py::media_statistics`.

## Что показывается

Карточки:

- дата и время последней загрузки фото (`last_photo_at`);
- дата и время последней загрузки видео (`last_video_at`);
- всего файлов: фото + видео (`photos`, `videos`);
- период, охватываемый базой (`period_start` — `period_end`).

Таблица «По периодам» (фото / видео): сегодня, вчера, позавчера, за неделю,
текущий месяц.

Таблица «Месяцы» (новые сверху): месяц, фото, видео, всего. Источник —
`months: [{month, photos, videos}]`.

## API

`GET /v1/media/statistics`:

```json
{
  "photos": 326, "videos": 9,
  "period_start": "2026-10-12T23:16:23+03:00",
  "period_end": "2026-10-16T18:21:25+03:00",
  "last_photo_at": "2026-10-15T23:07:44+03:00",
  "last_video_at": "2026-10-16T18:21:25+03:00",
  "today_photos": 0, "today_videos": 0,
  "yesterday_photos": 0, "yesterday_videos": 0,
  "day_before_photos": 70, "day_before_videos": 0,
  "last_7_days_photos": 326, "last_7_days_videos": 9,
  "this_month_photos": 326, "this_month_videos": 9,
  "months": [{"month": "2026-10-01", "photos": 326, "videos": 9}]
}
```

`last_photo_at` / `last_video_at` добавлены в тот же запрос
(`max(created_at) FILTER (WHERE kind=...)`); старые поля не менялись.

## Ограничения

- Счётчики — по дате **загрузки** (`created_at`), не по EXIF-дате съёмки.
- «Сегодня/вчера/позавчера» считаются по календарным суткам сервера
  (`CURRENT_DATE`).
