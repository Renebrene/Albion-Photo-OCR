## СЕССИЯ: 19

**Создано:** 2026-08-18 23:03:48
**Обновлено:** 2026-08-22 20:17:36
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a84ba98-4cb0-83ea-b465-2599f3b75adb)

---

### 🤖 **Assistant** — 2026-08-19 00:47:29

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed manager settings, checkbox behavior, and agreed UI cleanup**
>
> 
>
> Worked for 9s

Да. Тогда фиксируем правильную модель:

1. **Первое открытие интерфейса**
   - все реальные адреса отмечены;
   - `__UNASSIGNED__` не показываем;
   - грид показывает все фото, у которых есть адрес.

2. **После первого открытия**
   - состояние чекбоксов определяется **настройками текущего менеджера**;
   - при смене менеджера подгружается его сохранённый набор адресов/клиентов;
   - ручное изменение чекбоксов меняет текущее состояние, но не должно ломать сохранённые настройки.

3. **Грид**
   - показывает только выбранные адреса;
   - количество возле адреса берём из виртуального индекса, а не из физических папок;
   - клиенты тоже формируем из данных Qwen/`client`, а не из захардкоженного списка.

И интерфейс действительно уже пора привести в порядок — сейчас в коде остались куски старой логики (`output/daily`, кнопка «Показать фотографии», старые состояния фильтров и т. д.).

Я бы сейчас **не переписывал всё сразу**. Сначала приведём структуру UI к одной понятной схеме:

```text
АЛЬБИОН: Фотобаза. Офис.

┌─────────────────────────────────────────────────────────┐
│ Менеджер: Вихляева Алена          [настройки]            │
├─────────────────────────────────────────────────────────┤
│ Клиенты                                                  │
│ ☑ Все клиенты                                            │
│   ☑ Единая Россия (1)                                   │
│   ...                                                    │
├─────────────────────────────────────────────────────────┤
│ Адреса                                                   │
│ ☑ Все                                                    │
│   ☑ 78 (84)   ☑ 79 (31)   ☑ 80 (10) ...               │
├─────────────────────────────────────────────────────────┤
│ Поиск [________________________]                         │
├─────────────────────────────────────────────────────────┤
│ Фото: 519                         Выбрано: 0             │
├─────────────────────────────────────────────────────────┤
│ [фото] [фото] [фото] [фото]                             │
│  AI     AI      AI      AI                              │
│  78     78      79      79                              │
└─────────────────────────────────────────────────────────┘
```

Причём **AI** оставляем как индикатор состояния Qwen:
- зелёный — описание готово;
- жёлтый — обрабатывается;
- серый — ещё нет;
- красный — ошибка.

И главное: **сейчас сначала надо сделать правильное состояние фильтров**, а уже потом косметику. Иначе будем несколько раз переделывать грид.

Следующим шагом предлагаю поправить `get_filtered_photos()` так, чтобы `selected_addresses=set()` означало **«ничего не выбрано»**, а не «показывать всё», и затем сделать сохранение/загрузку настроек менеджера.

---

### 👤 **User** — 2026-08-19 00:50:30

Да, это логично сделать именно как **защиту от случайного переключения**, а не как полноценную систему безопасности.

Я бы зафиксировал требования так:

### 1. Выпадающий список менеджеров

При выборе другого менеджера:

- показываем простое 	поле **«Пароль»**;  &#x9;
- пароль задаётся в 	**Настройках**;  &#x9;
- пароль хранится без 	шифрования/хеширования — обычное 	локальное значение;  &#x9;
- если пароль неверный 	— менеджер не переключается;  &#x9;
- если пароль верный 	— переключение разрешается;  &#x9;
- для текущего менеджера 	повторная авторизация не нужна;  &#x9;
- после успешной авторизации можно 	считать менеджера «разблокированным» 	до перезагрузки страницы/сессии.  &#x9;

То есть это именно **предохранитель от случайного клика**, а не механизм защиты данных.

Можно сделать ещё удобнее: при клике на другого менеджера **не менять текущего менеджера сразу**, а открыть маленькое окно:

> Смена менеджера
>  Введите пароль: `••••••`
>  **Отмена | Войти**

### 2. Настройки → менеджеры → цвет

Убираем множественный выбор цвета.

Вместо него:

**Цвет менеджера:** `[ выпадающий список ▼ ]`

В списке ровно **32 заранее заданных цвета**.

Например:

1. Красный  &#x9;
2. Оранжевый  &#x9;
3. Янтарный  &#x9;
4. Жёлтый  &#x9;
5. Лаймовый  &#x9;
6. Зелёный  &#x9;
7. Изумрудный  &#x9;
8. Бирюзовый  &#x9;
9. Циан  &#x9;
10. Голубой  &#x9;
11. Синий  &#x9;
12. Индиго  &#x9;
13. Фиолетовый  &#x9;
14. Пурпурный  &#x9;
15. Розовый  &#x9;
16. Малиновый  &#x9;
17. Коралловый  &#x9;
18. Персиковый  &#x9;
19. Коричневый  &#x9;
20. Оливковый  &#x9;
21. Тёмно-зелёный  &#x9;
22. Тёмно-бирюзовый  &#x9;
23. Тёмно-синий  &#x9;
24. Тёмно-фиолетовый  &#x9;
25. Бордовый  &#x9;
26. Серый  &#x9;
27. Сине-серый  &#x9;
28. Тёмно-серый  &#x9;
29. Светло-серый  &#x9;
30. Чёрный  &#x9;
31. Белый  &#x9;
32. Золотой  &#x9;

Но **лучше хранить не название, а конкретный HEX/RGB-код**. Тогда интерфейс везде получает один однозначный цвет.

### Важный момент по архитектуре

Я бы сделал так, чтобы менеджер имел примерно:

А `color` — **одно значение**, а не массив цветов.

И отдельно:

Это позволит сделать авторизацию максимально простой и при этом не ломать существующую логику фильтров, клиентов и отображения грида.

**И ещё:** пароль менеджера лучше не показывать в самом выпадающем списке и не требовать его при каждом обновлении грида — только именно при попытке сменить менеджера.

можно хранить кукис на ПК чтобы не вводить каждый раз пароль

Да, и для нашей задачи это даже удобнее.

Я бы сделал **локальный cookie с авторизацией менеджера**:

- пользователь выбирает 	менеджера;  &#x9;
- вводит пароль **один 	раз**;  &#x9;
- сервер проверяет 	пароль;  &#x9;
- создаёт cookie вроде 	`manager_auth`;  &#x9;
- при следующих 	переключениях на этого менеджера пароль 	уже не спрашивается;  &#x9;
- cookie хранится, например, 	**30 дней**;  &#x9;
- после очистки cookies 	или истечения срока пароль потребуется 	снова;  &#x9;
- при выходе из системы можно удалить 	cookie.  &#x9;

Но поскольку у нас пароль нужен **не для реальной защиты**, а от случайного переключения, можно сделать совсем просто:

и проверять наличие этого значения.

Однако я бы всё-таки добавил небольшой срок действия:

### Что получится для пользователя

Первый раз:

**Менеджер ▼**

> Иванов

→ появляется:

**Введите пароль:** `••••••`

→ `Войти`

После этого следующие 30 дней:

**Менеджер ▼**

> Петров

→ переключается **сразу**, без пароля.

И при этом авторизация одного менеджера не означает автоматически авторизацию всех остальных — cookie можно привязать к конкретному `manager_id`.

**Это хорошо подходит под твою задачу:** никакой сложной системы аккаунтов, JWT и т.п. нам здесь не нужно. Cookie + простой пароль вполне достаточно.

Да, именно **И-И**, то есть все активные фильтры должны одновременно сужать результат.

Например:

**Менеджер**
 → И **Клиенты**
 → И **Адреса**
 → И **остальные фильтры**
 → получаем фотографии.

Пример:

- выбран менеджер 	**Иванов**  &#x9;
- выбраны клиенты 	**Клиент 1 + Клиент 2**  &#x9;
- выбраны адреса **Адрес 	5 + Адрес 8**  &#x9;
- период: **август** 	&#x9;
- сортировка по времени  &#x9;

Тогда показываем только:

> фото, которые принадлежат Иванову **И** относятся к выбранным клиентам **И** находятся по выбранным адресам **И** попадают в заданный период.

### Внутри одного фильтра

Здесь есть важное различие.

Если выбрано несколько клиентов:

> Клиент 1 **ИЛИ** Клиент 2

и несколько адресов:

> Адрес 5 **ИЛИ** Адрес 8

то итог:

То есть **между группами — И**, а **внутри выбранных элементов одной группы — ИЛИ**.

Это стандартная и наиболее удобная логика для чекбоксов.

### Подборки тоже работают так же

Например, подборка клиентов:

> «VIP»

содержит 5 клиентов.

Выбираем её → это эквивалентно выбору этих 5 клиентов вручную.

А если одновременно выбрана подборка адресов:

> «Центр»

то получаем:

**Это стоит заложить именно в ядро фильтрации**, а не реализовывать отдельно для интерфейса. Тогда неважно, выбраны элементы вручную или через подборку — результат фильтрации будет абсолютно одинаковым.

## Дорожная карта — новый интерфейс фотобазы

### Этап 1. Авторизация менеджеров

- Добавить пароль для 	каждого менеджера в настройках.  &#x9;
- В выпадающем списке 	менеджеров при переключении запрашивать 	пароль.  &#x9;
- Не считать это 	системой безопасности — только защитой 	от случайного переключения.  &#x9;
- После успешного 	ввода сохранять авторизацию в cookie на 	ПК.  &#x9;
- Не спрашивать пароль 	повторно, пока cookie действительно.  &#x9;
- Предусмотреть срок 	действия cookie, например **30 дней**. 	&#x9;
- Переключение менеджера 	не должно перезагружать всю страницу. 	&#x9;
- После выбора менеджера автоматически 	применять его настройки фильтров и 	отображения.

Да, так значительно лучше для первого варианта. **Не будем пока делать автоматическую взаимную синхронизацию чекбоксов.** Зафиксируем простую и понятную схему, а возможность менять логику оставим на следующий этап.

## Фиксируем текущую схему интерфейса

### 1. Период

Добавляем выбор периода, за который показываются фотографии.

Например:

На первом этапе можно начать с выбора месяца.

В дальнейшем можно расширить до:

- месяц;  &#x9;
- произвольный период; 	&#x9;
- день;  &#x9;
- возможно, год.  &#x9;

### 2. Первый запуск

Если пользователь ещё ничего не выбирал:

**по умолчанию — текущий месяц.**

То есть сейчас, например:

> Август 2026

### 3. Запоминание

Выбранный период сохраняется для последующего запуска.

То есть:

Можно хранить это в настройках пользователя/менеджера или в состоянии интерфейса — здесь ещё решим, что удобнее.

---

# 4. Адреса

При запуске:

**все адреса отмечены чекбоксами.**

При этом список ограничен по высоте примерно **10–15 строками** и имеет прокрутку.

---

# 5. Клиенты

При запуске:

**показываются все клиенты.**

Пока не делаем автоматического выбора клиентов на основании адресов.

То есть:

И пользователь самостоятельно выбирает нужных клиентов, когда это необходимо.

---

# 6. Грид

Грид работает **как сейчас**, но получает результат от новой системы фильтров.

На первом запуске:

→ показываются фотографии за выбранный период.

Дальше:

Без отдельной кнопки «Применить».

---

# 7. Переключение панелей — очень хорошая идея

И вот это я бы **заложил в архитектуру сразу**, даже если сначала будет использоваться один вариант.

Например:

### Режим 1 — Адресы → Клиенты

Здесь адрес — основной фильтр.

### Режим 2 — Клиенты → Адреса

Здесь первичным становится клиент.

---

## Но я бы сделал ещё лучше

Не просто менять панели местами визуально, а иметь настройку:

**Основной фильтр:**

И интерфейс автоматически перестраивается:

или:

Это даст нам возможность **потом экспериментировать с UX**, не меняя сам механизм данных.

---

# Что фиксируем сейчас

**Первая версия:**

1. **Период** — 	выбор периода отображения фотографий. 	&#x9;
2. Первый запуск → 	**текущий месяц**.  &#x9;
3. Выбранный период 	**запоминается**.  &#x9;
4. При запуске **все 	адреса отмечены**.  &#x9;
5. **Все клиенты 	отображаются** в панели.  &#x9;
6. Грид фотографий 	работает по существующей логике и 	обновляется автоматически.  &#x9;
7. Адреса и клиенты 	имеют независимый множественный выбор. 	&#x9;
8. Пользовательские 	подборки адресов/клиентов сохраняются. 	&#x9;
9. Все фильтры объединяются 	через **И**, а несколько значений 	внутри одного фильтра — через **ИЛИ**. 	&#x9;
10. В будущем добавляем 	переключение:
     **Адреса → Клиенты** 	↔ **Клиенты → Адреса**.  &#x9;
11. В будущем эта же система должна 	стать основой для:
     **текстового 	поиска → поиска по изображению → поиска 	по видео**.  &#x9;

И главное — **пока не усложняем автоматическим выставлением чекбоксов между адресами и клиентами**. Сначала посмотрим, как люди реально будут пользоваться двумя независимыми панелями.

приступаем

---

### 🤖 **Assistant** — 2026-08-19 00:50:31

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed scene fingerprint roadmap, manager UI decisions, interface files, and grid steps**
>
> 
>
> Worked for 12s

Приступаем. Виртуальный индекс уже работает: **526 записей, 519 адресных фото, 7 без адреса**, поэтому дальше не трогаем этот слой.

Следующим шагом приводим **сам интерфейс и состояние фильтров** в порядок. Сначала посмотрим, где сейчас реализованы менеджер, настройки и сборка основной страницы, чтобы не ломать уже работающие адреса/клиентов/грид.

На твоём `NEURO` выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ WEB FILES ================"
find app/web -maxdepth 2 -type f -name "*.py" | sort

echo
echo "================ MANAGER / SETTINGS ================"
grep -RniE \
'manager|Менеджер|manager_colors|settings|Настройки|selected_clients|selected_addresses' \
app/web \
--include="*.py" | head -300
```

И сразу вторую команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ MAIN ================"
sed -n '1,260p' app/main.py

echo
echo "================ STATE ================"
sed -n '1,180p' app/web/state.py
```

**Пока ничего не меняем.** После этого я дам точечные изменения по порядку:

1. состояние менеджера и его настроек;
2. период;
3. адреса — `78 (84)`, `79 (31)` и т.д.;
4. по умолчанию все адреса отмечены;
5. грид только выбранных адресов;
6. клиенты из Qwen-описаний;
7. AND между группами / OR внутри группы;
8. сохранение настроек менеджера;
9. затем cookie-авторизация;
10. и уже после этого косметически приводим интерфейс к единому виду.

---

### 👤 **User** — 2026-08-19 00:51:46

и еще техническое окно в разделе обработки не сделали

---

### 🤖 **Assistant** — 2026-08-19 00:51:47

Да, точно. **Техническое окно в разделе «Обработка» тоже включаем в текущий этап**, а не откладываем.

Я бы сейчас зафиксировал структуру интерфейса так:

### Фотобаза
- Менеджер
- Период
- Клиенты
- Адреса
- Грид фотографий
- AI-индикатор на фото
- Qwen-описание

### Обработка
Отдельное **техническое окно**, где видны:
- текущий процесс;
- статус;
- прогресс;
- количество обработанных;
- ошибки;
- время выполнения;
- текущий файл/этап;
- последние события/лог.

Причём техническое окно лучше сделать **сворачиваемым**, чтобы обычному пользователю оно не мешало.

И важный момент: техническое окно должно брать данные **из того же состояния обработки**, а не запускать отдельный мониторинг или второй процесс.

Поэтому к предыдущим командам добавим поиск существующего раздела обработки:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "================ ОБРАБОТКА ================"

find app/web -type f -name "*.py" | sort | grep -Ei \
'process|processing|photo|automation|technical|system|monitor|last_run'

echo
echo "================ UI ОБРАБОТКИ ================"

grep -RniE \
'Обработка|обработк|process|processing|progress|progress_bar|last_run|monitor|техническ' \
app/web \
--include="*.py" | head -400
```

И отдельно:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

systemctl cat lora.service
```

**`lora.service` пока не меняй.** Нам нужно сначала увидеть, как сейчас устроен UI обработки и откуда он получает состояние.

После этого соберём уже **один цельный план переделки интерфейса**, чтобы не ходить по одному компоненту и постоянно перезапускать сервис.

---

### 👤 **User** — 2026-08-19 00:52:53

мы ранее обсуждали интерфейс квен и дино обработки, старт, стоп пауза

---

### 🤖 **Assistant** — 2026-08-19 00:52:54

Да. Это было отдельным блоком — **техническая панель обработки DINO + Qwen**, а не просто окно с логом.

Логика, которую мы обсуждали, должна быть примерно такой:

### Техническое окно «Обработка»

**DINO**

- статус: `Ожидание / Работает / Пауза / Завершено / Ошибка`
- текущий этап;
- обработано / всего;
- прогресс;
- текущий файл;
- скорость;
- время;
- **Старт**
- **Пауза**
- **Стоп**

**Qwen**

- статус отдельно от DINO;
- текущий этап;
- обработано / всего;
- прогресс;
- текущий файл;
- скорость / время;
- **Старт**
- **Пауза**
- **Стоп**

И желательно:

```text
┌──────────────────────────────────────────────┐
│ ОБРАБОТКА                                    │
├──────────────────────────────────────────────┤
│                                              │
│ DINO                                         │
│ ● Работает                                   │
│ ███████████████░░░░░  73%                    │
│ 382 / 519                                    │
│ Комарова_28_17.JPG                           │
│                                              │
│ [ Старт ] [ Пауза ] [ Стоп ]                 │
│                                              │
├──────────────────────────────────────────────┤
│ QWEN                                         │
│ ● Ожидание                                   │
│ ░░░░░░░░░░░░░░░░░░░  0%                      │
│ 0 / 519                                      │
│                                              │
│ [ Старт ] [ Пауза ] [ Стоп ]                 │
│                                              │
├──────────────────────────────────────────────┤
│ Последнее событие: ...                       │
└──────────────────────────────────────────────┘
```

При этом **DINO и Qwen — два независимых процесса**. Например, DINO может закончить распознавание, пока Qwen ещё обрабатывает описания.

И мы отдельно обсуждали, что:

- DINO отвечает за **адрес / fingerprint / сортировку**;
- Qwen отвечает за **описание фотографии и дополнительные признаки**;
- результаты должны попадать в PostgreSQL;
- интерфейс не должен зависать во время обработки;
- `Пауза` должна именно приостанавливать очередь, а `Стоп` — корректно завершать текущую обработку;
- после обработки грид автоматически получает обновлённые данные;
- техническая информация не должна мешать обычной работе менеджера.

### Поэтому сейчас лучше не писать новый интерфейс вслепую

Нам нужно найти **тот существующий код обработки**, который мы уже делали, и встроить его в UI.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'Пауза|Стоп|Старт|Qwen|DINO|qwen|dino|pause|stop|start|worker|queue|progress' \
app scripts \
--include="*.py" | head -500
```

И ещё:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f -name "*.py" | sort | grep -Ei \
'dino|qwen|process|processing|worker|queue|automation|run|job|task'
```

По результату **восстановим именно ту архитектуру, которую уже обсуждали**, а не будем делать второй параллельный механизм.

---

### 👤 **User** — 2026-08-19 00:53:52

alexice@NEURO:~$ cd ~/projects/scene_fingerprint_mvp_v02

echo "================ WEB FILES ================"
find app/web -maxdepth 2 -type f -name "*.py" | sort

echo
echo "================ MANAGER / SETTINGS ================"
grep -RniE \
'manager|Менеджер|manager_colors|settings|Настройки|selected_clients|selected_addresses' \
app/web \
--include="*.py" | head -300
================ WEB FILES ================
app/web/client_aliases.py
app/web/client_db.py
app/web/components/addresses.py
app/web/components/clients.py
app/web/components/collections.py
app/web/components/filters.py
app/web/components/header.py
app/web/components/__init__.py
app/web/components/photos_before_cache_20260816_145128.py
app/web/components/photos.py
app/web/components/search.py
app/web/components/technical.py
app/web/config.py
app/web/filters.py
app/web/frontend_v01_backup_before_modular.py
app/web/frontend_v01.py
app/web/frontend_v02.py
app/web/__init__.py
app/web/main.py
app/web/photo_db.py
app/web/state.py
app/web/system/__init__.py
app/web/system/monitor.py
app/web/users_db.py

================ MANAGER / SETTINGS ================
app/web/components/photos_before_cache_20260816_145128.py:49:    selected = STATE.selected_addresses
app/web/components/technical_modules/users.py:310:                            STATE.manager = name
app/web/components/addresses.py:76:                STATE.selected_addresses = set(
app/web/components/addresses.py:89:                STATE.selected_addresses.clear()
app/web/components/addresses.py:138:                        STATE.selected_addresses.add(
app/web/components/addresses.py:142:                        STATE.selected_addresses.discard(
app/web/components/addresses.py:149:                            STATE.selected_addresses
app/web/components/addresses.py:160:                        in STATE.selected_addresses
app/web/components/header.py:82:            STATE.manager or "Пользователь",
app/web/components/header.py:140:                        STATE.manager = name
app/web/components/header.py:228:            icon="settings",
app/web/components/header.py:257:            if name == STATE.manager:
app/web/components/photos.py:278:    STATE.selected_addresses.intersection_update(
app/web/components/photos.py:352:        if STATE.selected_addresses:
app/web/components/photos.py:357:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py:376:        selected_addresses = STATE.selected_addresses
app/web/components/photos.py:378:        if not selected_addresses:
app/web/components/photos.py:386:                if address not in selected_addresses:
app/web/components/photos.py:400:    selected_clients = STATE.selected_clients
app/web/components/photos.py:403:    if selected_clients is None:
app/web/components/photos.py:407:    if not selected_clients:
app/web/components/photos.py:412:        for client in selected_clients
app/web/components/clients.py:39:        STATE.selected_clients = None
app/web/components/clients.py:53:        STATE.selected_clients = set()
app/web/components/clients.py:76:        if STATE.selected_clients is None:
app/web/components/clients.py:78:            STATE.selected_clients = set(
app/web/components/clients.py:87:            STATE.selected_clients.add(name)
app/web/components/clients.py:89:            STATE.selected_clients.discard(name)
app/web/components/clients.py:96:        if STATE.selected_clients == all_clients:
app/web/components/clients.py:97:            STATE.selected_clients = None
app/web/components/clients.py:104:            "STATE.selected_clients=",
app/web/components/clients.py:105:            repr(STATE.selected_clients),
app/web/components/clients.py:176:                        STATE.selected_clients is None
app/web/components/clients.py:177:                        or name in STATE.selected_clients
app/web/frontend_v02.py:19:MANAGERS = [
app/web/frontend_v02.py:174:.manager-box {
app/web/frontend_v02.py:195:current_manager = {"value": MANAGERS[0]}
app/web/frontend_v02.py:222:        with ui.column().classes("gap-0 manager-box"):
app/web/frontend_v02.py:224:            ui.label("Менеджер").classes(
app/web/frontend_v02.py:228:            manager_select = ui.select(
app/web/frontend_v02.py:229:                MANAGERS,
app/web/frontend_v02.py:230:                value=MANAGERS[0],
app/web/frontend_v02.py:235:            manager_select.on(
app/web/frontend_v02.py:237:                lambda e: current_manager.update(
app/web/state.py:21:    manager: str = "Вихляева Алена"
app/web/state.py:24:    manager_colors: dict[str, str] = field(default_factory=lambda: {
app/web/state.py:80:    selected_clients: set[str] | None = None
app/web/state.py:81:    selected_addresses: set[str] = field(default_factory=set)
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

echo "================ MAIN ================"
sed -n '1,260p' app/main.py

echo
echo "================ STATE ================"
sed -n '1,180p' app/web/state.py
================ MAIN ================
from pathlib import Path
from nicegui import ui
from app.core.config import settings
from app.core.embedder import SceneEmbedder
from app.core.fingerprint import FingerprintManager
from app.core.recognizer import SceneRecognizer

embedder = SceneEmbedder(settings)
manager = FingerprintManager(settings, embedder)
recognizer = SceneRecognizer(settings, embedder, manager)

@ui.page("/")
def page():
    ui.label("Scene Fingerprint").classes("text-3xl font-bold")
    ui.label("Распознавание локации по визуальному окружению").classes("text-lg text-gray-600")

    with ui.tabs().classes("w-full") as tabs:
        create_tab = ui.tab("Создать слепок")
        recognize_tab = ui.tab("Распознавание")
        db_tab = ui.tab("База слепков")

    with ui.tab_panels(tabs, value=create_tab).classes("w-full"):
        with ui.tab_panel(create_tab):
            ui.label("Новый визуальный слепок").classes("text-2xl")
            fp_id = ui.input("ID локации / конструкции", placeholder="78").classes("w-96")
            folder = ui.input("Папка эталонных фотографий", value="data/input/78").classes("w-full")
            info = ui.label("")

            def create():
                try:
                    r = manager.create(fp_id.value.strip(), folder.value.strip())
                    info.text = f"Создан: {r['id']} | {r['images']} фото | {r['dimension']}D"
                except Exception as e:
                    info.text = f"Ошибка: {e}"

            ui.button("СОЗДАТЬ СЛЕПОК", on_click=create)

        with ui.tab_panel(recognize_tab):
            ui.label("Распознавание папки").classes("text-2xl")
            folder2 = ui.input("Папка", value="data/input/new").classes("w-full")
            topk = ui.number("Top-K", value=5, min=1, max=20).classes("w-32")
            threshold = ui.number("Порог", value=0.65, min=0, max=1, step=0.01).classes("w-32")
            results_box = ui.column().classes("w-full")

            def run_recognition():
                results_box.clear()
                try:
                    rows = recognizer.recognize_folder(
                        folder2.value, int(topk.value), float(threshold.value)
                    )
                    with results_box:
                        for row in rows:
                            ui.label(
                                f"{Path(row['file']).name} → "
                                f"{row['best_id'] or 'UNKNOWN'} "
                                f"{row['score']:.3f}"
                            )
                            for c in row["candidates"]:
                                ui.label(f"    {c['id']}: {c['score']:.3f}").classes("text-gray-500")
                except Exception as e:
                    with results_box:
                        ui.label(f"Ошибка: {e}")

            ui.button("РАСПОЗНАТЬ", on_click=run_recognition)

        with ui.tab_panel(db_tab):
            ui.label("База слепков").classes("text-2xl")
            rows = ui.column().classes("w-full")

            def refresh():
                rows.clear()
                with rows:
                    data = manager.list_fingerprints()
                    if not data:
                        ui.label("База пуста.")
                    for x in data:
                        ui.label(
                            f"№{x['id']} — {x['images']} фото — "
                            f"{x['dimension']}D — {x['model']}"
                        )

            ui.button("Обновить", on_click=refresh)
            refresh()

ui.run(host=settings.host, port=settings.port, title="Scene Fingerprint")

================ STATE ================
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Photo:
    path: Path
    selected: bool = False
    db_record: dict | None = None

@dataclass
class Collection:
    name: str
    kind: str = "Моя"
    client: str = ""

@dataclass
class AppState:
    manager: str = "Вихляева Алена"
    user_id: int | None = None

    manager_colors: dict[str, str] = field(default_factory=lambda: {
        "Вихляева Алена": "#1976D2",
        "Пятницына Диана": "#2E7D32",
        "Аннин Илья": "#7B1FA2",
        "Иванова Елена": "#C62828",
        "Марышева Елена": "#00838F",
        "Бутовченко Ольга": "#6A1B9A",
        "Кривошлыкова Ангелина": "#1565C0",
        "Теплинская Наталья": "#2E7D32",
        "Папикян Эля": "#AD1457",
        "Путилина Татьяна": "#4E342E",
    })

    dark_mode: bool = False

    clients: list[str] = field(default_factory=lambda: [
        "Все клиенты",
        "Единая Россия",
        "Яндекс",
        "Самокат",
        "Сбер",
        "Ozon",
        "Бетсити",
        "Альбион-Тур",
    ])

    addresses: list[str] = field(default_factory=lambda: [
        "78",
        "79",
        "80",
        "81",
        "82",
        "83",
        "84",
        "85",
        "86",
        "87",
        "88",
        "89",
        "90",
        "91",
        "92",
        "93",
        "94",
        "95",
    ])

    collections: list[Collection] = field(default_factory=lambda: [
        Collection("Важное"),
        Collection("На согласование"),
        Collection("Для клиента"),
        Collection("Самокат — август", "Клиентская", "Самокат"),
        Collection("Яндекс — Москва", "Клиентская", "Яндекс"),
    ])

    # None = все клиенты, set() = ничего не выбрано
    selected_clients: set[str] | None = None
    selected_addresses: set[str] = field(default_factory=set)

    # SQLite / поиск
    search_query: str = ""
    search_results: list[dict] = field(default_factory=list)

    photos: list[Photo] = field(default_factory=list)
    selected_photos: set[str] = field(default_factory=set)

    refresh_photos: object = None

STATE = AppState()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
'Пауза|Стоп|Старт|Qwen|DINO|qwen|dino|pause|stop|start|worker|queue|progress' \
app scripts \
--include="*.py" | head -500
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:24:    DINO / fingerprint здесь НЕ используется.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/technical_modules/photo_processing.py:191:            # QWEN3-VL 4B
app/web/components/technical_modules/photo_processing.py:194:            qwen_script = PROJECT / "scripts" / "qwen4b_output_v01.py"
app/web/components/technical_modules/photo_processing.py:196:            if not qwen_script.exists():
app/web/components/technical_modules/photo_processing.py:199:                    "✓ Hybrid завершён → Qwen script не найден"
app/web/components/technical_modules/photo_processing.py:203:                    f"Не найден Qwen script: {qwen_script}",
app/web/components/technical_modules/photo_processing.py:214:            qwen_output = (
app/web/components/technical_modules/photo_processing.py:218:                / "qwen4b"
app/web/components/technical_modules/photo_processing.py:222:            qwen_output.mkdir(
app/web/components/technical_modules/photo_processing.py:228:                "▶ Qwen3-VL 4B: выполняется..."
app/web/components/technical_modules/photo_processing.py:233:                "Запускается Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:240:                qwen_process = await asyncio.create_subprocess_exec(
app/web/components/technical_modules/photo_processing.py:242:                    str(qwen_script),
app/web/components/technical_modules/photo_processing.py:246:                    str(qwen_output),
app/web/components/technical_modules/photo_processing.py:252:                qwen_lines = []
app/web/components/technical_modules/photo_processing.py:256:                    line = await qwen_process.stdout.readline()
app/web/components/technical_modules/photo_processing.py:266:                    qwen_lines.append(text)
app/web/components/technical_modules/photo_processing.py:271:                qwen_returncode = await qwen_process.wait()
app/web/components/technical_modules/photo_processing.py:273:                if qwen_returncode != 0:
app/web/components/technical_modules/photo_processing.py:277:                        "Qwen3-VL 4B: ошибка"
app/web/components/technical_modules/photo_processing.py:282:                        "но Qwen3-VL 4B завершился с ошибкой.",
app/web/components/technical_modules/photo_processing.py:290:                    "✓ Hybrid v12 + Qwen3-VL 4B: готово"
app/web/components/technical_modules/photo_processing.py:299:                    "Hybrid v12 + Qwen3-VL 4B.",
app/web/components/technical_modules/photo_processing.py:304:            except Exception as qwen_error:
app/web/components/technical_modules/photo_processing.py:308:                    "Qwen3-VL 4B: ошибка запуска"
app/web/components/technical_modules/photo_processing.py:312:                    f"Ошибка запуска Qwen: {qwen_error}",
app/web/components/technical_modules/photo_processing.py:384:            "DINO v33 → Hybrid v12 → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/fingerprints.py:17:            "Рабочая версия: DINO / v33"
app/web/components/technical_modules/data.py:13:QWEN_ROOT = PROJECT / "data" / "metadata" / "qwen4b"
app/web/components/technical_modules/data.py:78:def qwen_stats():
app/web/components/technical_modules/data.py:80:    Статистика Qwen3-VL 4B.
app/web/components/technical_modules/data.py:90:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/data.py:95:    if QWEN_ROOT.exists():
app/web/components/technical_modules/data.py:98:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/data.py:243:    qwen = qwen_stats()
app/web/components/technical_modules/data.py:298:        # DINO
app/web/components/technical_modules/data.py:308:                    "DINO v33"
app/web/components/technical_modules/data.py:368:        # QWEN
app/web/components/technical_modules/data.py:378:                    "Qwen3-VL 4B"
app/web/components/technical_modules/data.py:389:            qwen_color = (
app/web/components/technical_modules/data.py:391:                if qwen["status"] == "ГОТОВ"
app/web/components/technical_modules/data.py:396:                qwen["status"],
app/web/components/technical_modules/data.py:397:                color=qwen_color,
app/web/components/technical_modules/data.py:405:                f"Обработано: {qwen['photos']}"
app/web/components/technical_modules/data.py:409:                f"OK: {qwen['ok']}"
app/web/components/technical_modules/data.py:413:                f"Ошибок: {qwen['errors']}"
app/web/components/technical_modules/data.py:417:                f"Адресов: {qwen['addresses']}"
app/web/components/technical_modules/data.py:421:                f"Среднее время: {qwen['avg_time']:.2f} сек"
app/web/components/technical_modules/data.py:425:                f"Средняя уверенность: {qwen['avg_confidence']:.1f}%"
app/web/components/technical_modules/automation.py:62:        # MISSED START
app/web/components/technical_modules/automation.py:69:        missed_start = ui.radio(
app/web/components/technical_modules/qwen.py:10:QWEN_ROOT = (
app/web/components/technical_modules/qwen.py:14:    / "qwen4b"
app/web/components/technical_modules/qwen.py:24:QWEN_SCRIPT = (
app/web/components/technical_modules/qwen.py:27:    / "qwen4b_output_v01.py"
app/web/components/technical_modules/qwen.py:35:    root_summary = QWEN_ROOT / "summary.json"
app/web/components/technical_modules/qwen.py:40:    if QWEN_ROOT.exists():
app/web/components/technical_modules/qwen.py:44:            for p in QWEN_ROOT.glob("*/summary.json")
app/web/components/technical_modules/qwen.py:57:def _load_qwen_status():
app/web/components/technical_modules/qwen.py:72:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:156:                "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:173:            "model": "Qwen3-VL 4B",
app/web/components/technical_modules/qwen.py:200:def build_qwen():
app/web/components/technical_modules/qwen.py:205:            "QWEN3-VL 4B"
app/web/components/technical_modules/qwen.py:269:                "▶ Запустить Qwen",
app/web/components/technical_modules/qwen.py:274:            stop_button = ui.button(
app/web/components/technical_modules/qwen.py:275:                "■ Остановить Qwen",
app/web/components/technical_modules/qwen.py:280:            stop_button.disable()
app/web/components/technical_modules/qwen.py:294:    qwen_process = None
app/web/components/technical_modules/qwen.py:295:    qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:297:    async def stop_qwen():
app/web/components/technical_modules/qwen.py:298:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:299:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:301:        if qwen_process is None:
app/web/components/technical_modules/qwen.py:304:        qwen_stop_requested = True
app/web/components/technical_modules/qwen.py:307:            f"[QWEN MANUAL] STOP REQUESTED PID={qwen_process.pid}",
app/web/components/technical_modules/qwen.py:312:            qwen_process.terminate()
app/web/components/technical_modules/qwen.py:317:                f"[QWEN MANUAL] STOP FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:321:    async def run_qwen():
app/web/components/technical_modules/qwen.py:323:        nonlocal qwen_process
app/web/components/technical_modules/qwen.py:324:        nonlocal qwen_stop_requested
app/web/components/technical_modules/qwen.py:326:        print("[QWEN MANUAL] START", flush=True)
app/web/components/technical_modules/qwen.py:328:        qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:331:        stop_button.enable()
app/web/components/technical_modules/qwen.py:335:            if not QWEN_SCRIPT.exists():
app/web/components/technical_modules/qwen.py:338:                    f"[QWEN MANUAL] SCRIPT NOT FOUND: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:343:                    f"Не найден Qwen script: {QWEN_SCRIPT}",
app/web/components/technical_modules/qwen.py:355:                    "[QWEN MANUAL] HYBRID RUN NOT FOUND",
app/web/components/technical_modules/qwen.py:382:                    f"[QWEN MANUAL] NO IMAGES: {result_dir}",
app/web/components/technical_modules/qwen.py:396:            qwen_output = QWEN_ROOT / run_name
app/web/components/technical_modules/qwen.py:397:            qwen_output.mkdir(
app/web/components/technical_modules/qwen.py:403:                f"[QWEN MANUAL] INPUT: {result_dir}",
app/web/components/technical_modules/qwen.py:408:                f"[QWEN MANUAL] OUTPUT: {qwen_output}",
app/web/components/technical_modules/qwen.py:413:                f"[QWEN MANUAL] IMAGES: {total_images}",
app/web/components/technical_modules/qwen.py:420:            model_label.text = "qwen3-vl:4b-instruct"
app/web/components/technical_modules/qwen.py:435:                f"Запуск Qwen3-VL 4B: {total_images} фото",
app/web/components/technical_modules/qwen.py:447:                str(QWEN_SCRIPT),
app/web/components/technical_modules/qwen.py:451:                str(qwen_output),
app/web/components/technical_modules/qwen.py:457:            qwen_process = process
app/web/components/technical_modules/qwen.py:460:                f"[QWEN MANUAL] PID: {process.pid}",
app/web/components/technical_modules/qwen.py:488:                    f"[QWEN] {text}",
app/web/components/technical_modules/qwen.py:493:                # PROGRESS: [346/526]
app/web/components/technical_modules/qwen.py:498:                progress = re.search(
app/web/components/technical_modules/qwen.py:503:                if progress:
app/web/components/technical_modules/qwen.py:505:                    current = int(progress.group(1))
app/web/components/technical_modules/qwen.py:530:                if "[QWEN] OK |" in text:
app/web/components/technical_modules/qwen.py:580:                    "[QWEN] ERROR" in text
app/web/components/technical_modules/qwen.py:581:                    or "[QWEN] FAILED" in text
app/web/components/technical_modules/qwen.py:614:                # STOP REQUEST
app/web/components/technical_modules/qwen.py:617:                if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:627:                f"[QWEN MANUAL] FINISHED "
app/web/components/technical_modules/qwen.py:632:            if qwen_stop_requested:
app/web/components/technical_modules/qwen.py:638:                    f"Qwen остановлен: "
app/web/components/technical_modules/qwen.py:650:                    "✓ Qwen3-VL 4B завершён",
app/web/components/technical_modules/qwen.py:660:                status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:663:                    f"Qwen завершился с ошибкой: {returncode}",
app/web/components/technical_modules/qwen.py:671:                f"[QWEN MANUAL] EXCEPTION: {exc!r}",
app/web/components/technical_modules/qwen.py:676:            status_label.text = "● QWEN: ОШИБКА"
app/web/components/technical_modules/qwen.py:680:                    f"Ошибка запуска Qwen: {exc}",
app/web/components/technical_modules/qwen.py:689:            qwen_process = None
app/web/components/technical_modules/qwen.py:690:            qwen_stop_requested = False
app/web/components/technical_modules/qwen.py:698:                stop_button.disable()
app/web/components/technical_modules/qwen.py:706:                    f"[QWEN MANUAL] UI REFRESH FAILED: {exc!r}",
app/web/components/technical_modules/qwen.py:712:        data = _load_qwen_status()
app/web/components/technical_modules/qwen.py:772:    run_button.on_click(run_qwen)
app/web/components/technical_modules/qwen.py:773:    stop_button.on_click(stop_qwen)
app/web/components/header.py:201:                                    "flex-grow justify-start"
app/web/components/photos.py:199:        # используем результат DINO.
app/web/components/photos.py:204:            or record.get("dino_fingerprint")
app/web/components/photos.py:243:    # для фотографий без результата DINO.
app/web/components/photos.py:551:                        if value("qwen_status") != "—":
app/web/components/photos.py:554:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:620:                        "w-full items-start gap-1 text-xs"
app/web/components/photos.py:990:                # Небольшая пауза между запросами,
app/web/components/photos.py:1281:                                    # AI / QWEN STATUS
app/web/components/photos.py:1284:                                    qwen_status = (
app/web/components/photos.py:1286:                                            "qwen_status"
app/web/components/photos.py:1306:                                        qwen_status,
app/web/components/photos.py:1382:                                # QWEN DESCRIPTION
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:13:    build_qwen,
app/web/components/technical.py:175:                    "qwen",
app/web/components/technical.py:176:                    label="Qwen",
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:231:                        build_qwen()
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:32:            qwen_status,
app/web/photo_db.py:33:            qwen_time_sec,
app/web/photo_db.py:44:            dino_fingerprint,
app/web/photo_db.py:45:            dino_score,
app/web/photo_db.py:46:            dino_second_score,
app/web/photo_db.py:47:            dino_margin,
app/web/photo_db.py:56:            dino_status,
app/web/main.py:21:        "w-full flex-nowrap items-start gap-3 px-3"
app/web/client_db.py:14:    Возвращает клиентов из результатов Qwen.
app/web/client_db.py:17:    для которых Qwen определил клиента.
app/core/scene_analyzer.py:388:        # GLOBAL DINO
app/core/recognizer.py:26:        DINO patch tokens
app/core/recognizer.py:102:        workers=6,
app/core/recognizer.py:204:        # One DINO pass for all query images.
app/core/recognizer.py:225:        # Use CPU workers to process different images in parallel.
app/core/recognizer.py:250:        worker_count = max(
app/core/recognizer.py:252:            int(workers),
app/core/recognizer.py:256:            f"[Recognizer] CPU workers: "
app/core/recognizer.py:257:            f"{worker_count}"
app/core/recognizer.py:261:            max_workers=worker_count
app/core/recognizer.py:495:        Intended for queue/worker processing.
app/core/recognizer.py:571:        # DINO
app/core/config.py:14:        "facebook/dinov2-base"
app/core/embedder.py:10:    """DINOv2 ViT-B/14 global embedding service.
app/core/embedder.py:37:            f"[SceneEmbedder] Loading DINOv2: "
app/core/embedder.py:101:            # DINOv2 CLS token.
app/core/fingerprint.py:229:                "Invalid DINO embedding "
app/core/fingerprint.py:271:        # One image load per worker + parallel processing.
app/core/fingerprint.py:274:        workers = min(
app/core/fingerprint.py:284:            f"CPU workers={workers}"
app/core/fingerprint.py:295:            max_workers=workers
app/core/fingerprint.py:386:            "model": "dinov2_vitb14",
app/pipeline/modes.py:31:    stop_requested: bool = False
app/pipeline/modes.py:51:        stop_requested=False,
app/pipeline/modes.py:66:        stop_requested=False,
app/pipeline/modes.py:86:        stop_requested=False,
app/pipeline/modes.py:90:def can_manual_start(state: PipelineMode) -> bool:
app/pipeline/modes.py:102:def can_stop(state: PipelineMode) -> bool:
app/pipeline/controller.py:63:                    stop_requested
app/pipeline/controller.py:83:        stop_requested=bool(row["stop_requested"]),
app/pipeline/controller.py:102:                    stop_requested = %s,
app/pipeline/controller.py:113:                    state.stop_requested,
app/pipeline/controller.py:138:def start_manual():
app/pipeline/controller.py:143:            "Manual start is available only in manual mode"
app/pipeline/controller.py:158:                    stop_requested = FALSE,
app/pipeline/controller.py:159:                    started_at = CURRENT_TIMESTAMP,
app/pipeline/controller.py:160:                    stopped_at = NULL,
app/pipeline/controller.py:169:    state.stop_requested = False
app/pipeline/controller.py:174:def start_automatic():
app/pipeline/controller.py:179:            "Automatic start requested while mode is not automatic"
app/pipeline/controller.py:192:                    stop_requested = FALSE,
app/pipeline/controller.py:193:                    started_at = CURRENT_TIMESTAMP,
app/pipeline/controller.py:194:                    stopped_at = NULL,
app/pipeline/controller.py:203:    state.stop_requested = False
app/pipeline/controller.py:208:def start_watcher():
app/pipeline/controller.py:213:            "Watcher start requested while mode is not watcher"
app/pipeline/controller.py:226:                    stop_requested = FALSE,
app/pipeline/controller.py:227:                    started_at = CURRENT_TIMESTAMP,
app/pipeline/controller.py:228:                    stopped_at = NULL,
app/pipeline/controller.py:237:    state.stop_requested = False
app/pipeline/controller.py:242:def request_stop():
app/pipeline/controller.py:249:                    stop_requested = TRUE,
app/pipeline/controller.py:258:def finish_stop():
app/pipeline/controller.py:273:                    stop_requested = FALSE,
app/pipeline/controller.py:274:                    stopped_at = CURRENT_TIMESTAMP,
app/pipeline/controller.py:285:def is_stop_requested() -> bool:
app/pipeline/controller.py:290:                SELECT stop_requested
app/pipeline/controller.py:305:def manual_start_allowed() -> bool:
app/pipeline/recovery.py:26:    Возвращает зависшие worker jobs:
app/pipeline/recovery.py:30:    Только если worker находился в PROCESSING
app/pipeline/recovery.py:43:    recovered_dino = 0
app/pipeline/recovery.py:44:    recovered_qwen = 0
app/pipeline/recovery.py:54:                    dino_status = 'pending',
app/pipeline/recovery.py:55:                    dino_started_at = NULL,
app/pipeline/recovery.py:58:                    dino_status = 'processing'
app/pipeline/recovery.py:59:                    AND dino_started_at < %s
app/pipeline/recovery.py:64:            recovered_dino = cur.rowcount
app/pipeline/recovery.py:70:                    qwen_status = 'pending',
app/pipeline/recovery.py:71:                    qwen_started_at = NULL,
app/pipeline/recovery.py:74:                    qwen_status = 'processing'
app/pipeline/recovery.py:75:                    AND qwen_started_at < %s
app/pipeline/recovery.py:80:            recovered_qwen = cur.rowcount
app/pipeline/recovery.py:85:        "dino": recovered_dino,
app/pipeline/recovery.py:86:        "qwen": recovered_qwen,
app/pipeline/worker.py:8:from app.pipeline.queue import JobQueue
app/pipeline/worker.py:11:class FingerprintWorker:
app/pipeline/worker.py:14:        self.queue = JobQueue(
app/pipeline/worker.py:18:        print("[Worker] Loading SceneEmbedder...")
app/pipeline/worker.py:30:        job = self.queue.claim()
app/pipeline/worker.py:43:        print(f"[Worker] Job {job_id}")
app/pipeline/worker.py:44:        print(f"[Worker] Fingerprint: {fingerprint_id}")
app/pipeline/worker.py:45:        print(f"[Worker] Folder: {source_folder}")
app/pipeline/worker.py:55:            self.queue.complete(
app/pipeline/worker.py:60:                f"[Worker] DONE: {fingerprint_id}"
app/pipeline/worker.py:66:            self.queue.fail(
app/pipeline/worker.py:72:                f"[Worker] FAILED: "
app/pipeline/worker.py:79:        print("[Worker] Starting batch processing")
app/pipeline/worker.py:94:            f"[Worker] Batch complete. "
app/pipeline/worker.py:101:    worker = FingerprintWorker()
app/pipeline/worker.py:102:    worker.run()
app/pipeline/queue.py:8:class JobQueue:
app/pipeline/queue.py:10:    Persistent SQLite job queue.
app/pipeline/queue.py:65:                    started_at TEXT,
app/pipeline/queue.py:151:            dict with job data, or None if queue is empty.
app/pipeline/queue.py:177:            started_at = self._now()
app/pipeline/queue.py:185:                    started_at = ?,
app/pipeline/queue.py:192:                    started_at,
app/pipeline/queue.py:290:    queue = JobQueue(
app/pipeline/queue.py:294:    print("Queue:", queue.db_path)
app/pipeline/queue.py:295:    print("Counts:", queue.counts())
app/web_v01_backup_20260816_142053/components/technical.py:84:                    "Qwen3-VL 4B",
app/web_v01_backup_20260816_142053/components/technical.py:85:                    "Qwen2.5-VL 3B",
app/web_v01_backup_20260816_142053/components/technical.py:86:                    "Qwen3-VL 2B",
app/web_v01_backup_20260816_142053/components/technical.py:88:                value="Qwen3-VL 4B",
app/web_v01_backup_20260816_142053/main.py:27:        "w-full flex-nowrap items-start gap-3 px-3"
app/workers/qwen_worker.py:28:# QWEN
app/workers/qwen_worker.py:31:MODEL = "qwen3-vl:4b-instruct"
app/workers/qwen_worker.py:156:    Берём следующую фотографию, которая ещё не обработана Qwen.
app/workers/qwen_worker.py:159:        Qwen работает независимо от DINO.
app/workers/qwen_worker.py:162:        photo_id -> результат Qwen
app/workers/qwen_worker.py:177:            WHERE qwen_status = 'pending'
app/workers/qwen_worker.py:196:                qwen_status = 'processing',
app/workers/qwen_worker.py:199:              AND qwen_status = 'pending'
app/workers/qwen_worker.py:216:    Сохраняет результат Qwen.
app/workers/qwen_worker.py:244:                qwen_status = 'done',
app/workers/qwen_worker.py:252:                qwen_time_sec = %s,
app/workers/qwen_worker.py:330:                qwen_status = 'error',
app/workers/qwen_worker.py:356:# QWEN REQUEST
app/workers/qwen_worker.py:390:        started = time.time()
app/workers/qwen_worker.py:398:        elapsed = time.time() - started
app/workers/qwen_worker.py:462:        if cleaned.startswith("```"):
app/workers/qwen_worker.py:498:                    "[QWEN RETRY]",
app/workers/qwen_worker.py:517:                "[QWEN JSON ERROR]",
app/workers/qwen_worker.py:540:# WORKER
app/workers/qwen_worker.py:546:    print("QWEN3-VL 4B — DATABASE WORKER")
app/workers/qwen_worker.py:552:        "[QWEN] Works independently from DINO."
app/workers/qwen_worker.py:555:        "[QWEN] Source: photos.source_path"
app/workers/qwen_worker.py:558:        "[QWEN] Identity: photos.photo_id"
app/workers/qwen_worker.py:569:            "QWEN_MAX_ITEMS",
app/workers/qwen_worker.py:582:                WHERE qwen_status = 'pending'
app/workers/qwen_worker.py:602:                    "[QWEN] Reached "
app/workers/qwen_worker.py:615:                    "[QWEN] Queue empty."
app/workers/qwen_worker.py:628:                f"[QWEN] {photo_id}"
app/workers/qwen_worker.py:635:            started = time.time()
app/workers/qwen_worker.py:657:                    - started
app/workers/qwen_worker.py:668:                    "[QWEN] DONE",
app/workers/qwen_worker.py:709:                    - started
app/workers/qwen_worker.py:713:                    "[QWEN] ERROR",
app/workers/qwen_worker.py:735:                        "[QWEN] DB ERROR:",
app/workers/qwen_worker.py:745:        print("QWEN WORKER STOPPED")
app/workers/dino_worker.py:35:    Возвращает зависшие DINO-задачи обратно в очередь.
app/workers/dino_worker.py:49:                dino_status = 'pending',
app/workers/dino_worker.py:51:            WHERE dino_status = 'processing'
app/workers/dino_worker.py:61:            f"[DINO] Reset stale processing jobs: {count}"
app/workers/dino_worker.py:67:    Забирает следующую фотографию из DINO-очереди.
app/workers/dino_worker.py:71:    Qwen здесь вообще не учитывается.
app/workers/dino_worker.py:73:    DINO получает фотографию только потому,
app/workers/dino_worker.py:75:    dino_status = pending.
app/workers/dino_worker.py:92:                dino_status = 'pending'
app/workers/dino_worker.py:111:                dino_status = 'processing',
app/workers/dino_worker.py:115:                AND dino_status = 'pending'
app/workers/dino_worker.py:136:    Сохраняет результат DINO.
app/workers/dino_worker.py:140:        address_id = адрес, определённый DINO.
app/workers/dino_worker.py:153:                dino_status = 'done',
app/workers/dino_worker.py:157:                dino_fingerprint = %s,
app/workers/dino_worker.py:158:                dino_score = %s,
app/workers/dino_worker.py:159:                dino_second_score = %s,
app/workers/dino_worker.py:160:                dino_margin = %s,
app/workers/dino_worker.py:161:                dino_time_sec = %s,
app/workers/dino_worker.py:196:    Qwen-status при этом НЕ меняется.
app/workers/dino_worker.py:207:                dino_status = 'error',
app/workers/dino_worker.py:222:# WORKER
app/workers/dino_worker.py:230:    print("DINO WORKER")
app/workers/dino_worker.py:240:    print("[DINO] Loading SceneEmbedder...")
app/workers/dino_worker.py:261:    print("[DINO] Database connected.")
app/workers/dino_worker.py:269:    print("[DINO] Worker ready.")
app/workers/dino_worker.py:273:            "DINO_MAX_ITEMS",
app/workers/dino_worker.py:294:                    f"[DINO] "
app/workers/dino_worker.py:308:                    "[DINO] Queue empty."
app/workers/dino_worker.py:324:                "[DINO]",
app/workers/dino_worker.py:332:            started = time.perf_counter()
app/workers/dino_worker.py:358:                    - started
app/workers/dino_worker.py:377:                    f"[DINO] DONE "
app/workers/dino_worker.py:397:                    - started
app/workers/dino_worker.py:401:                    f"[DINO] ERROR "
app/workers/dino_worker.py:417:                        "[DINO] "
app/workers/dino_worker.py:428:        print("DINO WORKER STOPPED")
app/cli.py:13:from app.pipeline.queue import JobQueue
app/cli.py:50:    # QUEUE ADD
app/cli.py:53:    queue_add_parser = subparsers.add_parser(
app/cli.py:54:        "queue-add",
app/cli.py:55:        help="Add fingerprint creation job to queue",
app/cli.py:58:    queue_add_parser.add_argument(
app/cli.py:63:    queue_add_parser.add_argument(
app/cli.py:68:    queue_add_parser.add_argument(
app/cli.py:76:    # QUEUE BATCH ADD
app/cli.py:79:    queue_batch_parser = subparsers.add_parser(
app/cli.py:80:        "queue-batch-add",
app/cli.py:81:        help="Add a range of folders to fingerprint queue",
app/cli.py:84:    queue_batch_parser.add_argument(
app/cli.py:85:        "start",
app/cli.py:90:    queue_batch_parser.add_argument(
app/cli.py:96:    queue_batch_parser.add_argument(
app/cli.py:100:        help="Queue priority",
app/cli.py:152:        "--workers",
app/cli.py:155:        help="Number of CPU workers for descriptor calculation",
app/cli.py:326:            start=1,
app/cli.py:343:    if args.command == "queue-add":
app/cli.py:352:        queue = JobQueue(
app/cli.py:356:        job_id = queue.add(
app/cli.py:363:            f"[Queue] Job added: {job_id}"
app/cli.py:366:            f"[Queue] fingerprint={args.fingerprint}"
app/cli.py:369:            f"[Queue] folder={folder}"
app/cli.py:372:            f"[Queue] priority={args.priority}"
app/cli.py:375:            "[Queue] status=PENDING"
app/cli.py:420:    # QUEUE BATCH ADD
app/cli.py:423:    if args.command == "queue-batch-add":
app/cli.py:425:        from app.pipeline.queue import JobQueue
app/cli.py:427:        queue = JobQueue(
app/cli.py:431:        if args.end < args.start:
app/cli.py:433:                "END must be greater than or equal to START"
app/cli.py:438:        skipped_queue = 0
app/cli.py:442:            args.start,
app/cli.py:457:                    f"[Queue] MISSING: "
app/cli.py:478:                    f"[Queue] NO IMAGES: "
app/cli.py:491:                    f"[Queue] SKIP EXISTING: "
app/cli.py:497:            existing_jobs = queue.list()
app/cli.py:499:            already_queued = any(
app/cli.py:511:            if already_queued:
app/cli.py:513:                    f"[Queue] SKIP QUEUED: "
app/cli.py:516:                skipped_queue += 1
app/cli.py:519:            job_id = queue.add(
app/cli.py:526:                f"[Queue] ADD "
app/cli.py:536:        print("[Queue] BATCH COMPLETE")
app/cli.py:540:        print(f"Skipped queued:    {skipped_queue}")
app/cli.py:543:        print("Queue:", queue.counts())
app/cli.py:633:                workers=args.workers,
app/ocr/ocr_pipeline.py:48:        start = time.perf_counter()
app/ocr/ocr_pipeline.py:55:        elapsed = time.perf_counter() - start
app/ocr/grid_ocr.py:48:# OCR для worker-процесса
app/ocr/grid_ocr.py:51:_worker_ocr = None
app/ocr/grid_ocr.py:54:def init_worker():
app/ocr/grid_ocr.py:59:    global _worker_ocr
app/ocr/grid_ocr.py:61:    _worker_ocr = PaddleOCR(
app/ocr/grid_ocr.py:142:    global _worker_ocr
app/ocr/grid_ocr.py:147:        result = _worker_ocr.ocr(
app/ocr/grid_ocr.py:249:    workers: int = 4,
app/ocr/grid_ocr.py:296:        f"Workers: {workers}"
app/ocr/grid_ocr.py:328:    print("Starting OCR...")
app/ocr/grid_ocr.py:331:    start = time.perf_counter()
app/ocr/grid_ocr.py:350:        processes=workers,
app/ocr/grid_ocr.py:351:        initializer=init_worker,
app/ocr/grid_ocr.py:377:        - start
app/ocr/grid_ocr.py:425:            f"WORKERS: "
app/ocr/grid_ocr.py:426:            f"{workers}\n"
app/ocr/grid_ocr.py:502:        "--workers",
app/ocr/grid_ocr.py:507:            "workers (default: 4)"
app/ocr/grid_ocr.py:513:    if args.workers < 1:
app/ocr/grid_ocr.py:515:            "--workers must be >= 1"
app/ocr/grid_ocr.py:520:        workers=args.workers,
scripts/sort_neighbor_v35_benchmark.py:109:            start = max(0, i - NEIGHBOR_RADIUS)
scripts/sort_neighbor_v35_benchmark.py:112:            for j in range(start, end):
scripts/sort_test_and_report_v2.py:118:    start = time.perf_counter()
scripts/sort_test_and_report_v2.py:127:    elapsed = time.perf_counter() - start
scripts/sort_test_and_report_v2.py:363:    start_total = time.perf_counter()
scripts/sort_test_and_report_v2.py:375:    total_time = time.perf_counter() - start_total
scripts/banner_search_v03.py:31:WORKERS = min(
scripts/banner_search_v03.py:44:print("Workers:", WORKERS)
scripts/banner_search_v03.py:385:        "Workers:",
scripts/banner_search_v03.py:386:        WORKERS
scripts/banner_search_v03.py:468:        max_workers=WORKERS
scripts/banner_search_v03_2.py:5:import queue
scripts/banner_search_v03_2.py:27:CPU_WORKERS = max(
scripts/banner_search_v03_2.py:34:QUEUE_SIZE = 4
scripts/banner_search_v03_2.py:182:def gpu_worker(
scripts/banner_search_v03_2.py:322:        "CPU workers:",
scripts/banner_search_v03_2.py:323:        CPU_WORKERS
scripts/banner_search_v03_2.py:332:        "Queue:",
scripts/banner_search_v03_2.py:333:        QUEUE_SIZE
scripts/banner_search_v03_2.py:387:    tasks = queue.Queue(
scripts/banner_search_v03_2.py:388:        maxsize=QUEUE_SIZE
scripts/banner_search_v03_2.py:396:        target=gpu_worker,
scripts/banner_search_v03_2.py:405:    gpu.start()
scripts/banner_search_v03_2.py:427:        max_workers=CPU_WORKERS
scripts/sort_test_and_report.py:36:    start = None
scripts/sort_test_and_report.py:42:                if lines[j].strip().startswith("{"):
scripts/sort_test_and_report.py:43:                    start = i
scripts/sort_test_and_report.py:46:        if start is not None:
scripts/sort_test_and_report.py:49:    if start is None:
scripts/sort_test_and_report.py:54:    json_text = "\n".join(lines[start:])
scripts/sort_test_and_report.py:62:        print("JSON starts with:")
scripts/sort_test_and_report.py:77:    started = time.perf_counter()
scripts/sort_test_and_report.py:187:    elapsed = time.perf_counter() - started
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/banner_model_compare_v04.py:131:    start = time.time()
scripts/banner_model_compare_v04.py:141:    elapsed = time.time() - start
scripts/banner_model_compare_v04.py:172:        if cleaned.startswith("```"):
scripts/create_previews_v01.py:84:    print("PHOTO PREVIEW WORKER V01")
scripts/banner_crop_search_v02.py:27:WORKERS = max(
scripts/banner_crop_search_v02.py:188:        "CPU workers:",
scripts/banner_crop_search_v02.py:189:        WORKERS
scripts/banner_crop_search_v02.py:278:            for start in tqdm(
scripts/banner_crop_search_v02.py:287:                    start:
scripts/banner_crop_search_v02.py:288:                    start + BATCH_SIZE
scripts/banner_crop_search_v02.py:294:                    f"crop_{start}"
scripts/banner_crop_search_v02.py:359:            start=1
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_qwen25vl_test_v01.py:101:    started = time.time()
scripts/banner_qwen25vl_test_v01.py:109:    elapsed = time.time() - started
scripts/banner_qwen25vl_test_v01.py:124:        if cleaned.startswith("```"):
scripts/banner_qwen25vl_test_v01.py:159:    print("QWEN2.5-VL 3B TEST")
scripts/banner_qwen25vl_test_v01.py:169:    total_start = time.time()
scripts/banner_qwen25vl_test_v01.py:259:        time.time() - total_start,
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/banner_model_compare_v05.py:110:    start = time.time()
scripts/banner_model_compare_v05.py:118:    elapsed = time.time() - start
scripts/banner_model_compare_v05.py:133:        if cleaned.startswith("```"):
scripts/banner_model_compare_v05.py:159:    model_start = time.time()
scripts/banner_model_compare_v05.py:253:        time.time() - model_start,
scripts/banner_model_compare_v05.py:316:    total_start = time.time()
scripts/banner_model_compare_v05.py:332:    print("SECOND MODEL STARTING...")
scripts/banner_model_compare_v05.py:346:        time.time() - total_start,
scripts/benchmark_hybrid_v08.py:226:                    if not sub_id.startswith(
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_full_v02.py:141:    print("QWEN3-VL BANNER TEST")
scripts/photo_ingest.py:66:        if not value.startswith("PH_"):
scripts/photo_ingest.py:93:    DINO и Qwen.
scripts/photo_ingest.py:117:        if not value.startswith("IN_"):
scripts/photo_ingest.py:218:        - DINO
scripts/photo_ingest.py:219:        - Qwen
scripts/photo_ingest.py:247:                dino_status,
scripts/photo_ingest.py:248:                qwen_status,
scripts/photo_ingest.py:462:        "  DINO : dino_status = pending"
scripts/photo_ingest.py:466:        "  QWEN : qwen_status = pending"
scripts/photo_ingest.py:487:            "DINO/Qwen queues."
scripts/benchmark_hybrid_v03.py:226:                    if not sub_id.startswith(
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:114:    relative = json_path.relative_to(QWEN_DIR)
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/import_qwen_to_db.py:264:    QWEN_DIR.mkdir(
scripts/import_qwen_to_db.py:275:        QWEN_DIR.rglob("*.json")
scripts/import_qwen_to_db.py:279:    print("QWEN → SQLITE")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ 
alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

find app scripts -type f -name "*.py" | sort | grep -Ei \
'dino|qwen|process|processing|worker|queue|automation|run|job|task'
app/core/runtime.py
app/pipeline/queue.py
app/pipeline/worker.py
app/web/components/technical_modules/automation.py
app/web/components/technical_modules/last_run.py
app/web/components/technical_modules/photo_processing.py
app/web/components/technical_modules/qwen.py
app/workers/dino_worker.py
app/workers/qwen_worker.py
scripts/banner_qwen25vl_test_v01.py
scripts/banner_qwen4b_test_v01.py
scripts/dry_run_best_sequence.py
scripts/import_qwen_to_db.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/qwen4b_output_v01.py
scripts/qwen_prompt_ablation.py
scripts/run_hybrid_v12.py
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-19 00:53:53

> **Remembering**
>
>
> ****
>
> 
>
> **Reviewed scene fingerprint interface, model plans, processing controls, and queue controller**
>
> 
>
> Worked for 21s

Да. Теперь картина понятна: **техническое окно у нас уже частично есть**, а вот нормального единого управления обработкой в интерфейсе не довели до конца.

И главное - **не надо заново писать обработчики DINO/Qwen**. Они уже существуют:

- `app/workers/dino_worker.py`
- `app/workers/qwen_worker.py`
- `app/pipeline/controller.py`
- `app/pipeline/queue.py`
- `app/pipeline/recovery.py`

А UI сейчас частично дублирует эту логику, особенно `photo_processing.py` и `qwen.py`.

### Предлагаю сейчас сделать именно так

В разделе **«Обработка»** сделать одно нормальное техническое окно:

**ОБРАБОТКА ФОТОГРАФИЙ**

| Модуль | Состояние | Прогресс | Управление |
|---|---|---|---|
| **DINO v33** | ГОТОВ / РАБОТАЕТ / ПАУЗА / СТОП / ОШИБКА | `346 / 526` | ▶ Старт · ⏸ Пауза · ■ Стоп |
| **Qwen3-VL 4B** | ГОТОВ / РАБОТАЕТ / ПАУЗА / СТОП / ОШИБКА | `120 / 526` | ▶ Старт · ⏸ Пауза · ■ Стоп |

Ниже:

**Общий статус**

> Обработано: 466 / 1052  
> DINO: 346 / 526  
> Qwen: 120 / 526  
> Ошибок: 3  
> В очереди: 586

И отдельное небольшое поле:

**Последнее действие / лог**

```text
[DINO] DONE 78/526
[DINO] DONE 79/526
[QWEN] DONE PH_001245
...
```

### Важный момент

**Пауза не должна убивать worker.**

То есть:

- **Старт** → worker работает;
- **Пауза** → новые задания не берём, текущее корректно заканчиваем;
- **Продолжить** → продолжаем с очереди;
- **Стоп** → устанавливаем `stop_requested`, worker корректно заканчивает;
- после перезапуска зависшие `processing` уже умеет восстанавливать `recovery.py`.

Это как раз соответствует существующей архитектуре.

### И ещё одно

Текущий `photo_processing.py` запускает старый сценарий `run_daily_hybrid_v12.sh`, а `qwen.py` имеет собственный ручной запуск Qwen. Мы **не будем смешивать эти два управления**.

Сделаем:

**UI → controller → worker → queue → PostgreSQL**

а `photo_processing.py` оставим для самого процесса подготовки/ingest, где это действительно необходимо.

---

Но для следующего шага мне нужны **точные текущие файлы**, потому что по одному `grep` я не хочу случайно затереть уже сделанные изменения.

Выполни одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

for f in \
  app/web/components/technical.py \
  app/web/components/technical_modules/photo_processing.py \
  app/web/components/technical_modules/qwen.py \
  app/pipeline/controller.py \
  app/pipeline/modes.py \
  app/pipeline/queue.py \
  app/workers/dino_worker.py \
  app/workers/qwen_worker.py
do
    echo
    echo "============================================================"
    echo "FILE: $f"
    echo "============================================================"
    cat "$f"
done
```

**После этого я дам конкретный патч именно под текущую версию проекта**, без отката уже сделанной логики.

И параллельно уже учитываем зафиксированное:

**Адреса → чекбоксы определяют, какие фото попадают в грид.**  
При первом открытии все отмечены. После этого - состояние зависит от настроек менеджера.

И одновременно приводим весь веб-интерфейс к единому виду, а не делаем техническое окно отдельно от новой логики менеджеров/фильтров.

---

