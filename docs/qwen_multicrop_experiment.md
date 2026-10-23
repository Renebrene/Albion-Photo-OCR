# Стенд: кропы двух щитов и сжатие

Фото: 10 · второй щит отличается: 8 · модель: `qwen3-vl:4b-instruct` · варианты: 2048q95, 2048q90, 1280q90

Эталон — свежее чтение исходного кропа в этом же запуске; проверяется, осталось ли значение в ответе варианта. Строка `2048q95_again`, если она есть, — повтор без сжатия: её доля показывает собственную вариативность модели.

| Вариант/режим | Совпало | Проверено | Доля |
|---|---:|---:|---:|
| 2048q95 | 46 | 46 | 1.0 |
| 2048q95_again | 46 | 46 | 1.0 |
| 2048q90 | 42 | 46 | 0.913 |
| 1280q90 | 40 | 46 | 0.87 |
| combined_flat | 21 | 46 | 0.457 |
| combined_banners | 28 | 46 | 0.609 |

## Выводы

- **Оба щита уже читаются.** Отдельные запросы по кропам дают 96 % (первый)
  и 86 % (второй) совпадений с эталоном; второй щит отличается от первого
  у 8 из 10 фото.
- **Один запрос на два щита хуже.** Общий промпт видит второй щит в 9 %
  случаев, промпт-массив `banners` — в 59 %; оба проигрывают отдельным
  запросам. Отправлять несколько кропов одним запросом не нужно.
- **Информация второго щита не теряется, а уходит в tags.** По 103 фото с
  двумя кропами: в 66 случаях второй щит содержит client/brand, и во всех
  66 значение присутствует в итоговых tags/description. В скалярных
  `client`/`brand` остаётся только главный щит — это ограничение одной
  строки, а не распознавания.
- **Сжатие.** q90 совпал с эталоном в 91 %, 1280/q90 — в 87 %, повтор без
  сжатия — в 100 %. Все расхождения — формулировки и транслитерация
  («Комус»/«Коммус», «DÉMIANO»/«Demiando», синонимы категорий), сам текст
  остаётся в tags. Разница 4–6 значений на 46 проверок статистически слабая;
  для решения нужен прогон на 50+ фото.
- **Практический вывод:** оставить отдельные запросы по кропам; 1280 px
  затрагивает лишь 3 % кропов и на общий объём почти не влияет. q90 даёт
  около 25 % экономии, но требует подтверждения на большей выборке.

## PH_255deb4fea38ad7facf59eb4

- **crop_1**: brand='Единая Россия', category='Политическая реклама'
  - 2048q95: brand=да, category=да; 1.83 с, tokens=117
  - 2048q95_again: brand=да, category=да; 1.43 с, tokens=117
  - 2048q90: brand=да, category=да; 2.48 с, tokens=128
  - 1280q90: brand=да, category=да; 2.4 с, tokens=120
- **crop_2**: brand='Единая Россия', category='Политическая реклама'
  - 2048q95: brand=да, category=да; 2.09 с, tokens=158
  - 2048q95_again: brand=да, category=да; 1.98 с, tokens=158
  - 2048q90: brand=да, category=да; 2.91 с, tokens=158
  - 1280q90: brand=да, category=да; 2.15 с, tokens=175
- **combined_flat**: базирующихся щитов 1; 2.5 с, tokens=113
  - crop_1: brand=да, category=да
  - crop_2: brand=да, category=да
- **combined_banners**: базирующихся щитов 2; 4.45 с, tokens=346
  - crop_1: brand=да, category=да
  - crop_2: brand=да, category=да

## PH_2f43ff19a098aace4f9c3f78

- **crop_1**: brand='АКБ', category='Товары'
  - 2048q95: brand=да, category=да; 1.67 с, tokens=106
  - 2048q95_again: brand=да, category=да; 1.27 с, tokens=106
  - 2048q90: brand=да, category=да; 2.22 с, tokens=106
  - 1280q90: brand=да, category=да; 1.31 с, tokens=106
- **crop_2**: category='политическая реклама'
  - 2048q95: category=да; 1.35 с, tokens=99
  - 2048q95_again: category=да; 1.19 с, tokens=99
  - 2048q90: category=да; 2.12 с, tokens=99
  - 1280q90: category=да; 1.19 с, tokens=99
- **combined_flat**: базирующихся щитов 1; 2.47 с, tokens=114
  - crop_1: brand=да, category=НЕТ
  - crop_2: category=НЕТ
- **combined_banners**: базирующихся щитов 2; 4.78 с, tokens=373
  - crop_1: brand=да, category=НЕТ
  - crop_2: category=НЕТ

## PH_5d8b7af1b4f9da1c33504a6a

- **crop_1**: client='OMODA AAA Моторс-Запад', brand='OMODA', category='автомобили'
  - 2048q95: client=да, brand=да, category=да; 2.02 с, tokens=134
  - 2048q95_again: client=да, brand=да, category=да; 1.64 с, tokens=136
  - 2048q90: client=да, brand=да, category=да; 2.57 с, tokens=134
  - 1280q90: client=да, brand=да, category=да; 1.58 с, tokens=134
- **crop_2**: client='МегаФон', brand='realme', category='телефоны'
  - 2048q95: client=да, brand=да, category=да; 1.71 с, tokens=131
  - 2048q95_again: client=да, brand=да, category=да; 1.54 с, tokens=131
  - 2048q90: client=да, brand=да, category=да; 2.51 с, tokens=130
  - 1280q90: client=да, brand=да, category=да; 1.54 с, tokens=130
- **combined_flat**: базирующихся щитов 1; 2.42 с, tokens=110
  - crop_1: client=да, brand=да, category=да
  - crop_2: client=НЕТ, brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 0; 12.96 с, tokens=1024
  - crop_1: client=НЕТ, brand=НЕТ, category=НЕТ
  - crop_2: client=НЕТ, brand=НЕТ, category=НЕТ

## PH_13a5920187e745b7533a856b

- **crop_1**: brand='Айс Дэ Люкс', category='Продукт питания'
  - 2048q95: brand=да, category=да; 1.97 с, tokens=123
  - 2048q95_again: brand=да, category=да; 1.61 с, tokens=131
  - 2048q90: brand=да, category=НЕТ; 2.56 с, tokens=129
  - 1280q90: brand=да, category=НЕТ; 1.69 с, tokens=137
- **crop_2**: client='AAA Моторс-Запад', brand='OMODA', category='автомобили'
  - 2048q95: client=да, brand=да, category=да; 1.96 с, tokens=147
  - 2048q95_again: client=да, brand=да, category=да; 1.79 с, tokens=147
  - 2048q90: client=да, brand=да, category=да; 2.73 с, tokens=145
  - 1280q90: client=да, brand=да, category=да; 1.53 с, tokens=123
- **combined_flat**: базирующихся щитов 1; 2.55 с, tokens=114
  - crop_1: brand=да, category=НЕТ
  - crop_2: client=НЕТ, brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 2; 4.13 с, tokens=324
  - crop_1: brand=да, category=НЕТ
  - crop_2: client=да, brand=да, category=да

## PH_666fe41ab2fa3dedce2ff267

- **crop_1**: client='AAA Моторс-Запад', brand='OMODA', category='автомобили'
  - 2048q95: client=да, brand=да, category=да; 2.04 с, tokens=140
  - 2048q95_again: client=да, brand=да, category=да; 1.68 с, tokens=140
  - 2048q90: client=да, brand=да, category=да; 2.69 с, tokens=146
  - 1280q90: client=да, brand=да, category=да; 1.75 с, tokens=146
- **crop_2**: brand='Комус', category='Продажа товаров'
  - 2048q95: brand=да, category=да; 1.6 с, tokens=120
  - 2048q95_again: brand=да, category=да; 1.46 с, tokens=120
  - 2048q90: brand=НЕТ, category=да; 2.27 с, tokens=112
  - 1280q90: brand=НЕТ, category=да; 1.37 с, tokens=112
- **combined_flat**: базирующихся щитов 1; 2.57 с, tokens=122
  - crop_1: client=да, brand=да, category=НЕТ
  - crop_2: brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 2; 2.74 с, tokens=213
  - crop_1: client=да, brand=да, category=да
  - crop_2: brand=НЕТ, category=НЕТ

## PH_54a68015dda2c87763ffa08e

- **crop_1**: client='OMODA AAA Моторс-Запад', brand='OMODA', category='автомобильная реклама'
  - 2048q95: client=да, brand=да, category=да; 2.13 с, tokens=143
  - 2048q95_again: client=да, brand=да, category=да; 1.72 с, tokens=143
  - 2048q90: client=да, brand=да, category=да; 2.73 с, tokens=151
  - 1280q90: client=да, brand=да, category=да; 1.81 с, tokens=151
- **crop_2**: brand='Звук', category='музыка'
  - 2048q95: brand=да, category=да; 1.39 с, tokens=102
  - 2048q95_again: brand=да, category=да; 1.23 с, tokens=102
  - 2048q90: brand=да, category=да; 2.2 с, tokens=104
  - 1280q90: brand=да, category=да; 1.25 с, tokens=104
- **combined_flat**: базирующихся щитов 1; 2.79 с, tokens=140
  - crop_1: client=да, brand=да, category=да
  - crop_2: brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 2; 8.32 с, tokens=652
  - crop_1: client=да, brand=да, category=НЕТ
  - crop_2: brand=да, category=да

## PH_a8a206d6c24be8d75963d79f

- **crop_1**: client='OMODA AAA Моторс-Запад', brand='OMODA', category='автомобильная реклама'
  - 2048q95: client=да, brand=да, category=да; 2.16 с, tokens=147
  - 2048q95_again: client=да, brand=да, category=да; 1.76 с, tokens=147
  - 2048q90: client=да, brand=да, category=да; 2.66 с, tokens=145
  - 1280q90: client=да, brand=да, category=да; 1.85 с, tokens=155
- **crop_2**: client='Яндекс.Маркет', brand='DÉMIANO', category='Электроника / Кухонная техника'
  - 2048q95: client=да, brand=да, category=да; 2.61 с, tokens=139
  - 2048q95_again: client=да, brand=да, category=да; 1.67 с, tokens=139
  - 2048q90: client=да, brand=НЕТ, category=НЕТ; 2.62 с, tokens=141
  - 1280q90: client=да, brand=НЕТ, category=НЕТ; 1.55 с, tokens=128
- **combined_flat**: базирующихся щитов 1; 2.48 с, tokens=112
  - crop_1: client=да, brand=да, category=НЕТ
  - crop_2: client=НЕТ, brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 2; 3.16 с, tokens=243
  - crop_1: client=да, brand=да, category=НЕТ
  - crop_2: client=да, brand=да, category=НЕТ

## PH_e55d4f1f1c89618442e77056

- **crop_1**: client='СБЕР', brand='Сбер', category='Реклама банковских скидок'
  - 2048q95: client=да, brand=да, category=да; 2.88 с, tokens=150
  - 2048q95_again: client=да, brand=да, category=да; 1.81 с, tokens=150
  - 2048q90: client=да, brand=да, category=да; 2.78 с, tokens=150
  - 1280q90: client=да, brand=да, category=НЕТ; 1.75 с, tokens=146
- **crop_2**: brand='ТОЧНО', category='ЖК'
  - 2048q95: brand=да, category=да; 2.33 с, tokens=110
  - 2048q95_again: brand=да, category=да; 1.37 с, tokens=113
  - 2048q90: brand=да, category=да; 2.29 с, tokens=110
  - 1280q90: brand=да, category=НЕТ; 1.48 с, tokens=123
- **combined_flat**: базирующихся щитов 1; 2.45 с, tokens=109
  - crop_1: client=да, brand=да, category=НЕТ
  - crop_2: brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 3; 9.16 с, tokens=720
  - crop_1: client=да, brand=да, category=НЕТ
  - crop_2: brand=да, category=НЕТ

## PH_f078ce974faf8da939e4f77d

- **crop_1**: category='рекламные щиты'
  - 2048q95: category=да; 3.07 с, tokens=162
  - 2048q95_again: category=да; 1.99 с, tokens=166
  - 2048q90: category=да; 2.92 с, tokens=166
  - 1280q90: category=да; 1.98 с, tokens=166
- **crop_2**: brand='Единая Россия', category='Политическая реклама'
  - 2048q95: brand=да, category=да; 2.6 с, tokens=138
  - 2048q95_again: brand=да, category=да; 1.65 с, tokens=138
  - 2048q90: brand=да, category=да; 2.38 с, tokens=119
  - 1280q90: brand=да, category=да; 1.44 с, tokens=119
- **combined_flat**: базирующихся щитов 1; 2.75 с, tokens=136
  - crop_1: category=да
  - crop_2: brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 2; 5.39 с, tokens=402
  - crop_1: category=НЕТ
  - crop_2: brand=да, category=да

## PH_6fcea930fd6f4b3dba77f129

- **crop_1**: brand='Бронницкий ювелир', category='Ювелирные изделия'
  - 2048q95: brand=да, category=да; 2.77 с, tokens=121
  - 2048q95_again: brand=да, category=да; 1.4 с, tokens=113
  - 2048q90: brand=да, category=да; 2.45 с, tokens=121
  - 1280q90: brand=да, category=да; 1.73 с, tokens=142
- **crop_2**: brand='Единая Россия', category='Политическая реклама'
  - 2048q95: brand=да, category=да; 2.69 с, tokens=142
  - 2048q95_again: brand=да, category=да; 1.72 с, tokens=142
  - 2048q90: brand=да, category=да; 2.78 с, tokens=148
  - 1280q90: brand=да, category=да; 1.74 с, tokens=142
- **combined_flat**: базирующихся щитов 1; 2.6 с, tokens=121
  - crop_1: brand=да, category=да
  - crop_2: brand=НЕТ, category=НЕТ
- **combined_banners**: базирующихся щитов 2; 6.01 с, tokens=471
  - crop_1: brand=да, category=да
  - crop_2: brand=да, category=НЕТ
