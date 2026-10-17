Положите сюда фотографии (JPG/JPEG) и видео (MP4/MOV/M4V/MPEG/MPG)
для демонстрации. В контейнере эта папка видна как /photos.

Демо-фото можно сгенерировать командой:

    docker compose --env-file .env.demo exec api python scripts/make_demo_images.py /photos

Затем в веб-интерфейсе: Технический раздел → Загрузка → путь /photos →
Проверить → Сканировать.
