# Демонстрационный деплой PhotoBAse на Windows 10

Комплект поднимает весь проект в Docker Desktop: PostgreSQL, API с собранным
SPA, воркеры (DINO/HYBRID, QWEN, супервизор пайплайна). Ollama — опционально,
запускается на самом Windows.

## 1. Требования

- Windows 10 **22H2 x64**, включена виртуализация (BIOS/UEFI).
- **Docker Desktop** с backend **WSL 2** (Docker Desktop сам предложит
  установить WSL). Проверка: `docker --version` и `docker compose version`.
- 8 ГБ RAM минимум (16 ГБ рекомендуется), 20 ГБ свободного диска.
- Первая сборка занимает **15–30 минут** и около **8–12 ГБ**.

## 2. Быстрый старт

1. Скопируйте проект на Windows, например в
   `C:\PhotoBase\scene_fingerprint`.
2. Откройте PowerShell в `deploy\windows`.
3. Запустите:

```powershell
.\start.ps1
```

Скрипт создаст `.env.demo` из примера, соберёт образ и поднимет контейнеры.
Откроется **http://localhost:8010**.

Пароль БД в `.env.demo` можно сменить до первого запуска (после создания тома
смена пароля в файле не изменит пароль внутри PostgreSQL).

## 3. Демонстрационные данные

Положите фото (`.jpg/.jpeg`) и видео (`.mp4/.mov/.m4v/.mpeg/.mpg`) в
`deploy\windows\photos` — в контейнере это `/photos`.

Если своих фото нет, сгенерируйте демонстрационные (12 JPEG со щитами):

```powershell
docker compose --env-file .env.demo exec api python scripts/make_demo_images.py /photos
```

Далее в веб-интерфейсе:

1. **Технический раздел → Загрузка**.
2. Путь: `/photos` → **Проверить** → **Сканировать**.
3. Дождитесь окончания INGEST (кнопка «Обновление базы» в шапке покажет
   прогресс) — фото появятся в гриде.
4. **Сортировка** → «Запустить виртуальную сортировку» — DINO + HYBRID.
5. **Распознавание** → «Запустить QWEN (все фото)», если настроена Ollama.

## 4. QWEN и Ollama (опционально)

1. Установите [Ollama для Windows](https://ollama.com/download).
2. Разрешите доступ из контейнеров: задайте системную переменную
   `OLLAMA_HOST=0.0.0.0:11434` и перезапустите Ollama.
3. Скачайте instruct-модель (не «размышляющую»):

```powershell
ollama pull qwen3-vl:4b-instruct
```

4. Перезапустите QWEN-воркер:

```powershell
docker compose --env-file .env.demo restart qwen-worker
```

Без Ollama проект работает полностью, кроме описаний QWEN: задания будут
падать с ошибкой провайдера.

## 5. Остановка и сброс

```powershell
.\stop.ps1          # остановить, данные сохраняются
.\reset.ps1 -Force  # удалить БД и deploy\windows\data (фото в .\photos остаются)
```

## 6. Что запущено

| Сервис | Назначение |
|---|---|
| `db` | PostgreSQL 16 в томе `pgdata` |
| `api` | FastAPI + SPA, порт **8010**, применяет миграции при старте |
| `worker` | DINO/HYBRID, превью, видео |
| `qwen-worker` | только `QWEN_PHOTO` (параллельно сортировке) |
| `pipeline-worker` | супервизор «Обновление базы» |

Данные: `deploy\windows\data` (превью, кропы, логи, слепки) и том `pgdata`.
Фото: `deploy\windows\photos`.

## 7. Обновление проекта

```powershell
git pull
cd deploy\windows
.\start.ps1
```

`start.ps1` пересоберёт образ; миграции применятся автоматически.

## 8. Ограничения демо

- **Авторизация выключена** (`SCENE_AUTH_REQUIRED=0`) — только изолированная
  демонстрация, не выставляйте порт 8010 в интернет.
- Только **CPU**: GPU в контейнер не пробрасывается. DINO на большом корпусе
  будет медленным; для демо это нормально.
- Системный диалог выбора папки недоступен — используйте встроенный браузер
  папок или путь `/photos`.
- Пути, которые вводятся в UI, — **внутриконтейнерные** (`/photos`,
  `/app/data/...`), а не `C:\...`.

## 9. Если что-то не работает

```powershell
docker compose --env-file .env.demo ps
docker compose --env-file .env.demo logs -f api
docker compose --env-file .env.demo logs -f worker
```

- **Порт 8010 занят** — остановите старый контейнер или смените порт в
  `docker-compose.yml`.
- **Docker не стартует** — включите WSL 2 и виртуализацию, обновите Docker
  Desktop.
- **Сборка падает на paddle/torch** — проверьте свободное место и интернет;
  повторный `docker compose build api` обычно проходит.
- **Ollama недоступна из контейнера** — проверьте `OLLAMA_HOST=0.0.0.0:11434`
  и `curl http://localhost:11434/api/tags` на Windows.

## 10. Альтернатива без Docker (WSL 2 + systemd)

Если Docker Desktop недоступен, установите Ubuntu в WSL 2 и разверните проект
как на Linux: `deploy/systemd/README.md`, юниты из `deploy/systemd/user/`.
Браузер на Windows открывает `http://localhost:8010` так же.
