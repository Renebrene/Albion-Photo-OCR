## СЕССИЯ: Проверка ZeroTier доступа

**Создано:** 2026-08-20 14:19:32
**Обновлено:** 2026-08-21 22:48:33
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a86e2c3-fd68-83ea-9f36-3674689156ae)

---

### 👤 **User** — 2026-08-20 22:59:32

веб интерфей'$$PHOTO RECORD INDEX$$|$$VIRTUAL PHOTO INDEX$$|$$VIRTUAL ADDRESSES$$|$$UNASSIGNED$$|$$PHOTO GRID|\[PHOTO RECORD LINK$$'
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO RECORD INDEX] records= 526
Aug 20 14:19:55 NEURO uv[1497608]: [VIRTUAL PHOTO INDEX] addresses= 19 photos= 526
Aug 20 14:19:55 NEURO uv[1497608]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '__UNASSIGNED__']
Aug 20 14:19:55 NEURO uv[1497608]: [UNASSIGNED] 7
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID INITIAL LOAD]
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO RECORD LINK] linked= 0 total= 0
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:33:39 NEURO uv[1515737]: [VIRTUAL PHOTO INDEX] addresses= 19 photos= 526
Aug 20 22:33:39 NEURO uv[1515737]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '__UNASSIGNED__']
Aug 20 22:33:39 NEURO uv[1515737]: [UNASSIGNED] 7
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO RECORD LINK] linked= 0 total= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:02 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:02 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO RECORD LINK] linked= 0 total= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:17 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:17 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO RECORD LINK] linked= 0 total= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:25 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:25 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO RECORD LINK] linked= 0 total= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 22:59:32

Да, теперь картина ясна.

**Новая логика адресов работает правильно:**

```text
records = 526
addresses = 18
photos = 519
addresses = 78 ... 95
```

То есть:

- 526 записей PostgreSQL;
- 7 фото без `dino_fingerprint` отброшены;
- 519 фото попали в виртуальный индекс;
- получено 18 адресов: `78–95`;
- `__UNASSIGNED__` больше нет;
- `80–95` остаются в списке, как мы и решили.

### Но есть отдельная проблема

Грид при этом получает:

```text
[PHOTO GRID EXECUTED] loaded= 0 total= 0
[PHOTO RECORD LINK] linked= 0 total= 0
```

То есть **адресная часть уже исправлена, а грид не получает фотографии вообще**.

Это уже не проблема PostgreSQL и не проблема `address_fingerprints`.

Нужно посмотреть код, который непосредственно делает:

```text
PHOTO GRID INITIAL LOAD
PHOTO GRID EXECUTED
PHOTO RECORD LINK
```

и функцию, которая получает список файлов перед `photo_grid()`.

Дай следующую команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO GRID LOGIC ================" && \
grep -nE \
'\[PHOTO GRID|\[PHOTO RECORD LINK\]|def .*grid|def .*refresh|photo_grid\(' \
app/web/components/photos.py \
--include="*.py" && \
echo "================ GRID AREA ================" && \
nl -ba app/web/components/photos.py | sed -n '1300,1880p'
```

**Пока ничего больше не меняем.** Нам надо найти место, где `519` превращаются в `0`.

---

### 👤 **User** — 2026-08-20 23:00:05

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ PHOTO GRID LOGIC ================" && \
grep -nE \
'$$PHOTO GRID|\[PHOTO RECORD LINK$$|def .*grid|def .*refresh|photo_grid\(' \
app/web/components/photos.py \
--include="*.py" && \
echo "================ GRID AREA ================" && \
nl -ba app/web/components/photos.py | sed -n '1300,1880p'
================ PHOTO GRID LOGIC ================
517:        # photo_grid() ожидает именно Path
1410:            def render_photo_grid():
1423:                    "[PHOTO GRID EXECUTED]",
1463:                    "[PHOTO RECORD LINK]",
1774:                    "[PHOTO GRID LOAD MORE]",
1781:                render_photo_grid()
1787:            def request_photo_grid():
1793:                    "[PHOTO GRID INITIAL LOAD]",
1808:                render_photo_grid()
1811:                    "[PHOTO GRID RENDERED]",
1822:            request_photo_grid()
1830:    def refresh_photos():
1845:                "[PHOTO GRID SKIPPED] "
1861:        render_photo_grid()
================ GRID AREA ================
  1300	                "files=",
  1301	                len(files),
  1302	                "zip=",
  1303	                str(zip_path),
  1304	                flush=True,
  1305	            )
  1306	
  1307	            ui.download(
  1308	                str(zip_path),
  1309	                "albion_selected_photos.zip",
  1310	            )
  1311	
  1312	
  1313	        async def download_selected_files():
  1314	
  1315	            files = [
  1316	                Path(path)
  1317	                for path in STATE.selected_photos
  1318	                if Path(path).is_file()
  1319	            ]
  1320	
  1321	            if not files:
  1322	                ui.notify(
  1323	                    "Нет выбранных фотографий",
  1324	                    type="warning",
  1325	                )
  1326	                return
  1327	
  1328	            print(
  1329	                "[PHOTO DOWNLOAD FILES]",
  1330	                "files=",
  1331	                len(files),
  1332	                flush=True,
  1333	            )
  1334	
  1335	            for path in files:
  1336	
  1337	                ui.download(
  1338	                    str(path),
  1339	                    path.name,
  1340	                )
  1341	
  1342	                # Небольшая пауза между запросами,
  1343	                # чтобы браузер успевал их обработать.
  1344	                import asyncio
  1345	                await asyncio.sleep(0.08)
  1346	
  1347	
  1348	        # ====================================================
  1349	        # EXTERNAL ACTIONS FOR TOP ACTION BAR
  1350	        # ====================================================
  1351	
  1352	        STATE.download_selected_zip = download_selected_zip
  1353	        STATE.download_selected_files = download_selected_files
  1354	
  1355	        def add_selected_to_collection():
  1356	            ui.notify(
  1357	                "Добавление в подборку будет подключено позже",
  1358	                type="info",
  1359	            )
  1360	
  1361	        STATE.add_selected_to_collection = add_selected_to_collection
  1362	
  1363	
  1364	        # ----------------------------------------------------
  1365	        # LAZY GRID
  1366	        # ----------------------------------------------------
  1367	
  1368	        grid_requested = False
  1369	
  1370	        with ui.row().classes(
  1371	            "w-full items-center px-3 py-2"
  1372	        ):
  1373	
  1374	
  1375	            grid_status_label = ui.label(
  1376	                "Фотографии пока не загружены"
  1377	            ).classes(
  1378	                "text-sm text-grey-6"
  1379	            )
  1380	
  1381	        # ----------------------------------------------------
  1382	        # SCROLL AREA
  1383	        # ----------------------------------------------------
  1384	
  1385	        with ui.element("div").classes(
  1386	            "w-full flex-1 min-h-0 overflow-y-auto overflow-x-hidden"
  1387	        ).style(
  1388	            """
  1389	            min-height: 0;
  1390	            flex: 1 1 auto;
  1391	            overflow-y: auto;
  1392	            overflow-x: hidden;
  1393	            """
  1394	        ) as photo_scroll_area:
  1395	
  1396	            # Контейнер грида.
  1397	            # Никаких @ui.refreshable.
  1398	            with ui.column().classes(
  1399	                "w-full"
  1400	            ) as photo_grid_container:
  1401	                pass
  1402	
  1403	            def photo_key(photo):
  1404	                return str(photo.path.resolve())
  1405	
  1406	            # ------------------------------------------------
  1407	            # BUILD GRID
  1408	            # ------------------------------------------------
  1409	
  1410	            def render_photo_grid():
  1411	
  1412	                nonlocal grid_requested
  1413	                nonlocal grid_loaded
  1414	
  1415	                if not grid_requested:
  1416	                    return
  1417	
  1418	                all_files = get_filtered_photos()
  1419	
  1420	                files = all_files[:grid_loaded]
  1421	
  1422	                print(
  1423	                    "[PHOTO GRID EXECUTED]",
  1424	                    "loaded=", len(files),
  1425	                    "total=", len(all_files),
  1426	                    flush=True,
  1427	                )
  1428	
  1429	                # ------------------------------------------------
  1430	                # CLEAR PREVIOUS GRID
  1431	                # ------------------------------------------------
  1432	
  1433	                photo_grid_container.clear()
  1434	
  1435	                record_by_path = PHOTO_RECORD_INDEX
  1436	
  1437	                STATE.photos = []
  1438	
  1439	                for path in files:
  1440	
  1441	                    record = record_by_path.get(
  1442	                        str(path.resolve())
  1443	                    )
  1444	
  1445	                    # Fallback: daily-фото может иметь другой
  1446	                    # корневой путь, чем запись PostgreSQL.
  1447	                    if not record:
  1448	                        address = path.parent.name
  1449	                        filename = path.name
  1450	
  1451	                        record = record_by_path.get(
  1452	                            f"__ADDR_FILE__:{address}:{filename}"
  1453	                        )
  1454	
  1455	                    STATE.photos.append(
  1456	                        Photo(
  1457	                            path=path,
  1458	                            db_record=record,
  1459	                        )
  1460	                    )
  1461	
  1462	                print(
  1463	                    "[PHOTO RECORD LINK]",
  1464	                    "linked=",
  1465	                    sum(
  1466	                        1
  1467	                        for photo in STATE.photos
  1468	                        if photo.db_record is not None
  1469	                    ),
  1470	                    "total=",
  1471	                    len(STATE.photos),
  1472	                    flush=True,
  1473	                )
  1474	
  1475	                count_label.text = (
  1476	                    f"{len(files)} "
  1477	                    f"фотографий в текущем запуске"
  1478	                )
  1479	
  1480	                if not files:
  1481	
  1482	                    with photo_grid_container:
  1483	
  1484	                        with ui.column().classes(
  1485	                            "w-full "
  1486	                            "items-center "
  1487	                            "justify-center "
  1488	                            "p-12"
  1489	                        ):
  1490	
  1491	                            ui.icon(
  1492	                                "photo_library",
  1493	                                size="64px",
  1494	                            ).classes(
  1495	                                "text-grey-5"
  1496	                            )
  1497	
  1498	                            ui.label(
  1499	                                "Фотографий нет"
  1500	                            ).classes(
  1501	                                "text-grey-6"
  1502	                            )
  1503	
  1504	                    return
  1505	
  1506	                # ------------------------------------------------
  1507	                # GRID
  1508	                # ------------------------------------------------
  1509	
  1510	                photo_min_width = {
  1511	                    "small": "140px",
  1512	                    "medium": "190px",
  1513	                    "large": "280px",
  1514	                }.get(
  1515	                    getattr(
  1516	                        STATE,
  1517	                        "photo_size",
  1518	                        "medium",
  1519	                    ),
  1520	                    "190px",
  1521	                )
  1522	
  1523	                with photo_grid_container:
  1524	
  1525	                    with ui.element("div").classes(
  1526	                        "w-full grid gap-3 p-3"
  1527	                    ).style(
  1528	                        f"""
  1529	                        grid-template-columns: repeat(
  1530	                            auto-fill,
  1531	                            minmax(
  1532	                                {photo_min_width},
  1533	                                1fr
  1534	                            )
  1535	                        );
  1536	                        """
  1537	                    ):
  1538	
  1539	                        for photo in STATE.photos:
  1540	
  1541	                            with ui.card().classes(
  1542	                                "overflow-hidden "
  1543	                                "cursor-pointer "
  1544	                                "hover:shadow-lg"
  1545	                            ):
  1546	
  1547	                                # ----------------------------
  1548	                                # IMAGE
  1549	                                # ----------------------------
  1550	
  1551	                                with ui.element(
  1552	                                    "div"
  1553	                                ).classes(
  1554	                                    "relative "
  1555	                                    "w-full h-44 "
  1556	                                    "bg-grey-2 "
  1557	                                    "flex items-center "
  1558	                                    "justify-center"
  1559	                                ).on(
  1560	                                    "contextmenu.prevent",
  1561	                                    lambda e, p=photo:
  1562	                                        photo_menu(p),
  1563	                                ):
  1564	
  1565	                                    # В ГРИДЕ показываем PREVIEW.
  1566	                                    # Оригинал открывается только
  1567	                                    # после клика.
  1568	                                    preview_path = (
  1569	                                        get_preview_path(
  1570	                                            photo.path
  1571	                                        )
  1572	                                    )
  1573	
  1574	                                    display_path = (
  1575	                                        preview_path
  1576	                                        if preview_path
  1577	                                        else photo.path
  1578	                                    )
  1579	
  1580	                                    ui.image(
  1581	                                        str(display_path)
  1582	                                    ).classes(
  1583	                                        "w-full h-full "
  1584	                                        "object-contain"
  1585	                                    ).on(
  1586	                                        "click",
  1587	                                        lambda e, p=photo:
  1588	                                            open_photo(p),
  1589	                                    )
  1590	
  1591	                                    # ----------------------------
  1592	                                    # AI / QWEN STATUS
  1593	                                    # ----------------------------
  1594	
  1595	                                    qwen_status = (
  1596	                                        photo.db_record.get(
  1597	                                            "qwen_status"
  1598	                                        )
  1599	                                        if photo.db_record
  1600	                                        else None
  1601	                                    )
  1602	
  1603	                                    ai_class = {
  1604	                                        "done": (
  1605	                                            "text-green-600"
  1606	                                        ),
  1607	                                        "processing": (
  1608	                                            "text-yellow-600"
  1609	                                        ),
  1610	                                        "pending": (
  1611	                                            "text-grey-5"
  1612	                                        ),
  1613	                                        "error": (
  1614	                                            "text-red-600"
  1615	                                        ),
  1616	                                    }.get(
  1617	                                        qwen_status,
  1618	                                        "text-grey-5",
  1619	                                    )
  1620	
  1621	                                    ui.label(
  1622	                                        "AI"
  1623	                                    ).classes(
  1624	                                        "absolute "
  1625	                                        "top-2 right-2 "
  1626	                                        "font-bold "
  1627	                                        "text-lg "
  1628	                                        "drop-shadow "
  1629	                                        + ai_class
  1630	                                    )
  1631	
  1632	
  1633	                                # ----------------------------
  1634	                                # NAME
  1635	                                # ----------------------------
  1636	
  1637	                                with ui.row().classes(
  1638	                                    "w-full "
  1639	                                    "items-center "
  1640	                                    "px-2 pt-1"
  1641	                                ):
  1642	
  1643	                                    checkbox = ui.checkbox(
  1644	                                        value=(
  1645	                                            photo_key(photo)
  1646	                                            in STATE.selected_photos
  1647	                                        ),
  1648	                                        on_change=lambda e, p=photo:
  1649	                                            (
  1650	                                                STATE.selected_photos.add(
  1651	                                                    photo_key(p)
  1652	                                                )
  1653	                                                if e.value
  1654	                                                else STATE.selected_photos.discard(
  1655	                                                    photo_key(p)
  1656	                                                ),
  1657	                                                setattr(
  1658	                                                    selected_count_label,
  1659	                                                    "text",
  1660	                                                    f"Выбрано: {len(STATE.selected_photos)}",
  1661	                                                ),
  1662	                                            ),
  1663	                                    ).props(
  1664	                                        "dense"
  1665	                                    )
  1666	
  1667	                                    photo_checkboxes[
  1668	                                        photo_key(photo)
  1669	                                    ] = checkbox
  1670	
  1671	                                    ui.label(
  1672	                                        photo.path.name
  1673	                                    ).classes(
  1674	                                        "font-medium "
  1675	                                        "text-sm truncate"
  1676	                                    )
  1677	
  1678	                                # ----------------------------
  1679	                                # ADDRESS
  1680	                                # ----------------------------
  1681	
  1682	                                ui.label(
  1683	                                    photo.path.parent.name.replace(
  1684	                                        "_v33",
  1685	                                        "",
  1686	                                    )
  1687	                                ).classes(
  1688	                                    "px-2 pb-1 "
  1689	                                    "text-xs text-grey-6"
  1690	                                )
  1691	
  1692	                                # ----------------------------
  1693	                                # QWEN DESCRIPTION
  1694	                                # ----------------------------
  1695	
  1696	                                description = (
  1697	                                    photo.db_record.get("description")
  1698	                                    if photo.db_record
  1699	                                    else None
  1700	                                )
  1701	
  1702	                                if description:
  1703	                                    ui.label(
  1704	                                        str(description)
  1705	                                    ).classes(
  1706	                                        "px-2 pb-2 "
  1707	                                        "text-xs text-grey-8 "
  1708	                                        "leading-tight "
  1709	                                        "line-clamp-2"
  1710	                                    )
  1711	
  1712	                    # ----------------------------
  1713	                    # LOADING STATUS
  1714	                    # ----------------------------
  1715	
  1716	                    if len(files) < len(all_files):
  1717	
  1718	                        ui.label(
  1719	                            f"Показано {len(files)} из "
  1720	                            f"{len(all_files)}"
  1721	                        ).classes(
  1722	                            "w-full text-center "
  1723	                            "text-sm text-grey-6 pt-4"
  1724	                        )
  1725	
  1726	                        ui.button(
  1727	                            "Показать следующие фото",
  1728	                            icon="expand_more",
  1729	                            on_click=load_more_photos,
  1730	                        ).props(
  1731	                            "outline"
  1732	                        ).classes(
  1733	                            "mx-auto mb-6"
  1734	                        )
  1735	
  1736	                    else:
  1737	
  1738	                        ui.label(
  1739	                            f"Показаны все {len(files)} фотографий"
  1740	                        ).classes(
  1741	                            "w-full text-center "
  1742	                            "text-sm text-grey-6 p-4"
  1743	                        )
  1744	
  1745	                grid_status_label.text = (
  1746	                    f"Показано {len(files)} из "
  1747	                    f"{len(all_files)}"
  1748	                )
  1749	
  1750	            # ------------------------------------------------
  1751	            # LOAD MORE
  1752	            # ------------------------------------------------
  1753	
  1754	            def load_more_photos():
  1755	
  1756	                nonlocal grid_loaded
  1757	
  1758	                if not grid_requested:
  1759	                    return
  1760	
  1761	                all_files = get_filtered_photos()
  1762	
  1763	                if grid_loaded >= len(all_files):
  1764	                    return
  1765	
  1766	                old_loaded = grid_loaded
  1767	
  1768	                grid_loaded = min(
  1769	                    grid_loaded + GRID_PAGE_SIZE,
  1770	                    len(all_files),
  1771	                )
  1772	
  1773	                print(
  1774	                    "[PHOTO GRID LOAD MORE]",
  1775	                    "from=", old_loaded,
  1776	                    "to=", grid_loaded,
  1777	                    "total=", len(all_files),
  1778	                    flush=True,
  1779	                )
  1780	
  1781	                render_photo_grid()
  1782	
  1783	            # ------------------------------------------------
  1784	            # FIRST REQUEST
  1785	            # ------------------------------------------------
  1786	
  1787	            def request_photo_grid():
  1788	
  1789	                nonlocal grid_requested
  1790	                nonlocal grid_loaded
  1791	
  1792	                print(
  1793	                    "[PHOTO GRID INITIAL LOAD]",
  1794	                    flush=True,
  1795	                )
  1796	
  1797	                grid_requested = True
  1798	
  1799	                grid_loaded = min(
  1800	                    GRID_PAGE_SIZE,
  1801	                    len(get_filtered_photos()),
  1802	                )
  1803	
  1804	                grid_status_label.text = (
  1805	                    "Фотографии загружаются..."
  1806	                )
  1807	
  1808	                render_photo_grid()
  1809	
  1810	                print(
  1811	                    "[PHOTO GRID RENDERED]",
  1812	                    "loaded=",
  1813	                    grid_loaded,
  1814	                    flush=True,
  1815	                )
  1816	
  1817	
  1818	            # ------------------------------------------------
  1819	            # AUTO FIRST LOAD
  1820	            # ------------------------------------------------
  1821	
  1822	            request_photo_grid()
  1823	
  1824	            # ------------------------------------------------
  1825	
  1826	    # --------------------------------------------------------
  1827	    # CALLBACK FOR ADDRESS FILTER
  1828	    # --------------------------------------------------------
  1829	
  1830	    def refresh_photos():
  1831	
  1832	        nonlocal grid_loaded
  1833	
  1834	        print(
  1835	            "[PHOTO REFRESH CALL]",
  1836	            "search_query=", repr(STATE.search_query),
  1837	            "selected_addresses=",
  1838	            STATE.selected_addresses,
  1839	            "results=", len(STATE.search_results),
  1840	            flush=True,
  1841	        )
  1842	
  1843	        if not grid_requested:
  1844	            print(
  1845	                "[PHOTO GRID SKIPPED] "
  1846	                "waiting for user request",
  1847	                flush=True,
  1848	            )
  1849	            return
  1850	
  1851	        filtered = get_filtered_photos()
  1852	
  1853	        # Не сбрасываем уже показанные страницы обратно к 40.
  1854	        # При изменении фильтра только ограничиваем значение
  1855	        # фактическим количеством найденных фотографий.
  1856	        grid_loaded = min(
  1857	            grid_loaded,
  1858	            len(filtered),
  1859	        )
  1860	
  1861	        render_photo_grid()
  1862	
  1863	    STATE.refresh_photos = refresh_photos
  1864	
  1865	    return refresh_photos
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:00:07

Вот теперь нашли точное место: `render_photo_grid()` исправен. Он получает `0` уже на этапе:

```python
all_files = get_filtered_photos()
```

Значит, следующий участок — **`get_filtered_photos()`**. Именно там `PHOTO_INDEX` из 519 фотографий превращается в пустой список.

Дай только этот участок:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ GET FILTERED PHOTOS ================" && \
nl -ba app/web/components/photos.py | sed -n '620,805p'
```

Особенно важны строки **примерно 650–720**, где выбираются адреса и формируется `files`.

После этого уже можно будет сделать точечный фикс, не трогая работающую логику `78–95 → 519 фото`.

---

### 👤 **User** — 2026-08-20 23:00:27

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ GET FILTERED PHOTOS ================" && \
nl -ba app/web/components/photos.py | sed -n '620,805p'
================ GET FILTERED PHOTOS ================
   620	        "date_to",
   621	        None,
   622	    )
   623	
   624	    # Диапазон не задан.
   625	    if not date_from and not date_to:
   626	        return True
   627	
   628	    filter_type = getattr(
   629	        STATE,
   630	        "date_filter_type",
   631	        "taken",
   632	    )
   633	
   634	    if filter_type == "upload":
   635	
   636	        created_at = record.get(
   637	            "created_at"
   638	        )
   639	
   640	        if created_at is None:
   641	            return False
   642	
   643	        if hasattr(created_at, "strftime"):
   644	            value = created_at.strftime(
   645	                "%Y-%m-%d"
   646	            )
   647	        else:
   648	            value = str(
   649	                created_at
   650	            )[:10]
   651	
   652	    else:
   653	
   654	        value = get_photo_taken_date(
   655	            path
   656	        )
   657	
   658	        if not value:
   659	            return False
   660	
   661	    if date_from and value < date_from:
   662	        return False
   663	
   664	    if date_to and value > date_to:
   665	        return False
   666	
   667	    return True
   668	
   669	def get_filtered_photos():
   670	
   671	    # ========================================================
   672	    # SEARCH
   673	    # ========================================================
   674	
   675	    if STATE.search_query:
   676	
   677	        files = get_db_search_photos()
   678	
   679	    else:
   680	
   681	        filter_priority = getattr(
   682	            STATE,
   683	            "filter_priority",
   684	            "both",
   685	        )
   686	
   687	        # ====================================================
   688	        # ADDRESS FILTER
   689	        # ====================================================
   690	
   691	        if filter_priority in (
   692	            "addresses",
   693	            "both",
   694	        ):
   695	
   696	            selected_addresses = STATE.selected_addresses
   697	
   698	            # None = адресный фильтр не установлен.
   699	            if selected_addresses is None:
   700	
   701	                files = get_all_indexed_photos()
   702	
   703	            # Пустой set = ничего не выбрано.
   704	            elif not selected_addresses:
   705	
   706	                files = []
   707	
   708	            else:
   709	
   710	                files = []
   711	
   712	                for address in STATE.addresses:
   713	
   714	                    if address not in selected_addresses:
   715	                        continue
   716	
   717	                    files.extend(
   718	                        PHOTO_INDEX.get(
   719	                            address,
   720	                            [],
   721	                        )
   722	                    )
   723	
   724	        else:
   725	
   726	            # Режим "только клиенты":
   727	            # адреса полностью игнорируются.
   728	            files = get_all_indexed_photos()
   729	
   730	    # ========================================================
   731	    # DATE FILTER
   732	    # ========================================================
   733	
   734	    date_files = []
   735	
   736	    for path in files:
   737	
   738	        record = PHOTO_RECORD_INDEX.get(
   739	            str(path.resolve())
   740	        )
   741	
   742	        if not record:
   743	            continue
   744	
   745	        if photo_matches_date_filter(
   746	            record,
   747	            path,
   748	        ):
   749	            date_files.append(path)
   750	
   751	    files = date_files
   752	
   753	    # ========================================================
   754	    # CLIENT FILTER
   755	    # ========================================================
   756	
   757	    filter_priority = getattr(
   758	        STATE,
   759	        "filter_priority",
   760	        "both",
   761	    )
   762	
   763	    if filter_priority not in (
   764	        "clients",
   765	        "both",
   766	    ):
   767	        return files
   768	
   769	    selected_clients = STATE.selected_clients
   770	
   771	    # None = все клиенты.
   772	    if selected_clients is None:
   773	        return files
   774	
   775	    # set() = ничего не выбрано.
   776	    if not selected_clients:
   777	        return []
   778	
   779	    selected_normalized = {
   780	        str(client).strip().casefold()
   781	        for client in selected_clients
   782	    }
   783	
   784	    result = []
   785	
   786	    for path in files:
   787	
   788	        record = PHOTO_RECORD_INDEX.get(
   789	            str(path.resolve())
   790	        )
   791	
   792	        if not record:
   793	            continue
   794	
   795	        client = str(
   796	            record.get("client") or ""
   797	        ).strip().casefold()
   798	
   799	        if client in selected_normalized:
   800	            result.append(path)
   801	
   802	    return result
   803	
   804	
   805	def get_address_count(address):
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:00:29

Причина найдена.

Сейчас `get_filtered_photos()` при загрузке грида делает:

```python
selected_addresses = STATE.selected_addresses

elif not selected_addresses:
    files = []
```

То есть **пустой `selected_addresses` означает "ничего не показывать"**.

А нам нужно другое поведение для первоначального состояния:

- адреса `78–95` уже сформированы;
- 519 фото уже есть в `PHOTO_INDEX`;
- если пользователь ещё ничего не снял — **показывать все 519**;
- если пользователь нажал конкретные адреса — показывать только выбранные;
- кнопка «Снять» должна по-прежнему давать пустой грид.

Но перед изменением надо понять, как сейчас различается **"ещё ничего не выбрано при старте"** и **"пользователь нажал Снять"**. Посмотрим `STATE` и инициализацию адресов.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ STATE ADDRESSES ================" && \
grep -RniE \
'selected_addresses\s*=|selected_addresses:' \
app/web/state.py \
app/web/components/header.py \
app/web/components/addresses.py \
--include="*.py" && \
echo "================ HEADER ================" && \
nl -ba app/web/components/header.py | sed -n '35,80p' && \
echo "================ STATE ================" && \
grep -n -C 4 'selected_addresses' app/web/state.py
```

После этого сделаем **минимальный фикс именно начального состояния**, не ломая «Снять».

---

### 👤 **User** — 2026-08-20 23:00:43

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ STATE ADDRESSES ================" && \
grep -RniE \
'selected_addresses\s*=|selected_addresses:' \
app/web/state.py \
app/web/components/header.py \
app/web/components/addresses.py \
--include="*.py" && \
echo "================ HEADER ================" && \
nl -ba app/web/components/header.py | sed -n '35,80p' && \
echo "================ STATE ================" && \
grep -n -C 4 'selected_addresses' app/web/state.py
================ STATE ADDRESSES ================
app/web/state.py:119:    selected_addresses: set[str] = field(default_factory=set)
app/web/components/header.py:53:    STATE.selected_addresses = {
app/web/components/addresses.py:114:                STATE.selected_addresses = set(
================ HEADER ================
    35	    ).strftime("%Y-%m-%d")
    36	
    37	    if now.month == 12:
    38	        next_month = now.replace(
    39	            year=now.year + 1,
    40	            month=1,
    41	            day=1,
    42	        )
    43	    else:
    44	        next_month = now.replace(
    45	            month=now.month + 1,
    46	            day=1,
    47	        )
    48	
    49	    last_day = (
    50	        next_month - timedelta(days=1)
    51	    ).strftime("%Y-%m-%d")
    52	
    53	    STATE.selected_addresses = {
    54	        address
    55	        for address in STATE.addresses
    56	        if address != "__UNASSIGNED__"
    57	    }
    58	
    59	    STATE.date_filter_type = "taken"
    60	    STATE.date_from = first_day
    61	    STATE.date_to = last_day
    62	    STATE.selected_period = now.strftime("%Y-%m")
    63	
    64	    print(
    65	        "[GUEST DEFAULTS]",
    66	        "addresses=", sorted(STATE.selected_addresses),
    67	        "date_type=", STATE.date_filter_type,
    68	        "date_from=", STATE.date_from,
    69	        "date_to=", STATE.date_to,
    70	        "period=", STATE.selected_period,
    71	        flush=True,
    72	    )
    73	
    74	
    75	
    76	def build_header():
    77	
    78	    init_users_db()
    79	
    80	    # ========================================================
================ STATE ================
115-    ])
116-
117-    # None = все клиенты, set() = ничего не выбрано
118-    selected_clients: set[str] | None = None
119:    selected_addresses: set[str] = field(default_factory=set)
120-
121-    # ========================================================
122-    # FILTER PRIORITY
123-    #
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:00:49

Да. Теперь причина практически точно видна.

`STATE.selected_addresses` изначально `set()`. В `header.py` есть установка всех адресов, **но она выполняется раньше, чем `build_photo_index()` сформировал `STATE.addresses`**.

Получается:

1. `STATE.addresses` ещё пустой.
2. `header.py` выполняет:
   ```python
   STATE.selected_addresses = {
       address for address in STATE.addresses
   }
   ```
3. Получается `set()`.
4. Потом `build_photo_index()` создаёт `78–95`.
5. Но `selected_addresses` так и остаётся пустым.
6. `get_filtered_photos()` видит:
   ```python
   elif not selected_addresses:
       files = []
   ```
7. Поэтому **519 фото есть, но грид получает 0**.

Это полностью соответствует твоим логам.

### Правильный фикс

Не надо менять `get_filtered_photos()`: там логика «Снять = пустой грид» правильная.

Нужно после построения `STATE.addresses` при **первичной загрузке** выставить все адреса выбранными.

Но делать это каждый раз нельзя — иначе после нажатия «Снять» фильтр снова будет включаться.

Поэтому сначала посмотрим, где вызывается `init_guest_defaults()` и в каком порядке строятся компоненты.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ GUEST DEFAULTS CALLS ================" && \
grep -RniE \
'init_guest_defaults|build_photo_index|build_addresses|build_photos' \
app \
--include="*.py" | head -n 200
```

После этого дам **один точечный патч**, чтобы при старте сразу были выбраны `78–95` и грид показал 519 фото, а кнопка **«Снять»** продолжила работать как сейчас.

---

### 👤 **User** — 2026-08-20 23:01:45

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ GUEST DEFAULTS CALLS ================" && \
grep -RniE \
'init_guest_defaults|build_photo_index|build_addresses|build_photos' \
app \
--include="*.py" | head -n 200
================ GUEST DEFAULTS CALLS ================
app/web/components/photos_before_cache_20260816_145128.py:175:def build_photos():
app/web/components/addresses.py:51:def build_addresses(refresh_photos):
app/web/components/photos.py:258:def build_photo_index():
app/web/components/photos.py:1122:def build_photos():
app/web/components/photos.py:1128:    build_photo_index()
app/web/main.py:10:from app.web.components.photos import build_photos
app/web/main.py:11:from app.web.components.addresses import build_addresses
app/web/main.py:378:                refresh_photos = build_photos()
app/web/main.py:397:                build_addresses(
app/web_v01_backup_20260816_142053/components/addresses.py:26:def build_addresses():
app/web_v01_backup_20260816_142053/components/photos.py:31:def build_photos():
app/web_v01_backup_20260816_142053/main.py:6:from app.web.components.addresses import build_addresses
app/web_v01_backup_20260816_142053/main.py:8:from app.web.components.photos import build_photos
app/web_v01_backup_20260816_142053/main.py:53:            build_photos()
app/web_v01_backup_20260816_142053/main.py:64:            build_addresses()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:01:48

Отлично. Теперь видно, что `build_photo_index()` вызывается **внутри `build_photos()`**, то есть порядок можно исправить без изменения фильтра.

Нужно увидеть два небольших участка: конец `build_photos()` и место сборки интерфейса в `main.py`.

Выполни:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ BUILD PHOTOS ================" && \
nl -ba app/web/components/photos.py | sed -n '1100,1160p' && \
echo "================ MAIN BUILD ORDER ================" && \
nl -ba app/web/main.py | sed -n '350,415p'
```

После этого уже дам готовую команду `uv run python`, которая внесёт минимальный патч.

---

### 👤 **User** — 2026-08-20 23:02:02

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ BUILD PHOTOS ================" && \
nl -ba app/web/components/photos.py | sed -n '1100,1160p' && \
echo "================ MAIN BUILD ORDER ================" && \
nl -ba app/web/main.py | sed -n '350,415p'
================ BUILD PHOTOS ================
  1100	            )
  1101	
  1102	            ui.button(
  1103	                "Добавить в подборку",
  1104	                icon="folder",
  1105	                on_click=lambda: (
  1106	                    dialog.close(),
  1107	                    ui.notify(
  1108	                        "Подборки будут подключены позже"
  1109	                    ),
  1110	                ),
  1111	            ).props(
  1112	                "flat align-left w-full"
  1113	            )
  1114	
  1115	    dialog.open()
  1116	
  1117	
  1118	# ============================================================
  1119	# BUILD PHOTOS
  1120	# ============================================================
  1121	
  1122	def build_photos():
  1123	
  1124	    # --------------------------------------------------------
  1125	    # Сканируем базу ОДИН РАЗ
  1126	    # --------------------------------------------------------
  1127	
  1128	    build_photo_index()
  1129	
  1130	    # ========================================================
  1131	    # LAZY GRID
  1132	    # ========================================================
  1133	
  1134	    GRID_PAGE_SIZE = 40
  1135	
  1136	    # --------------------------------------------------------
  1137	    # DISPLAY SETTINGS
  1138	    # --------------------------------------------------------
  1139	
  1140	    if not hasattr(STATE, "photo_view_mode"):
  1141	        STATE.photo_view_mode = "grid"
  1142	
  1143	    if not hasattr(STATE, "photo_size"):
  1144	        STATE.photo_size = "medium"
  1145	
  1146	    grid_loaded = 0
  1147	
  1148	    total_photos = len(
  1149	        get_all_indexed_photos()
  1150	    )
  1151	
  1152	    print(
  1153	        "[PHOTO INDEX]",
  1154	        f"addresses={len(PHOTO_INDEX)}",
  1155	        f"photos={total_photos}",
  1156	        flush=True,
  1157	    )
  1158	
  1159	    with ui.column().classes(
  1160	        "w-full h-full min-w-0"
================ MAIN BUILD ORDER ================
   350	                overflow:hidden;
   351	                min-height:0;
   352	                """
   353	            ):
   354	
   355	                build_clients_panel(
   356	                    lambda: (
   357	                        STATE.refresh_photos()
   358	                        if STATE.refresh_photos
   359	                        else None
   360	                    )
   361	                )
   362	
   363	            # =================================================
   364	            # PHOTOS
   365	            # =================================================
   366	
   367	            with ui.column().classes(
   368	                "flex-1 min-w-0 h-full min-h-0"
   369	            ).style(
   370	                """
   371	                display:flex;
   372	                flex-direction:column;
   373	                overflow:hidden;
   374	                min-height:0;
   375	                """
   376	            ):
   377	
   378	                refresh_photos = build_photos()
   379	
   380	                STATE.refresh_photos = refresh_photos
   381	
   382	            # =================================================
   383	            # ADDRESSES
   384	            # =================================================
   385	
   386	            with ui.column().classes(
   387	                "w-[280px] min-w-[280px] h-full min-h-0"
   388	            ).style(
   389	                """
   390	                display:flex;
   391	                flex-direction:column;
   392	                overflow:hidden;
   393	                min-height:0;
   394	                """
   395	            ):
   396	
   397	                build_addresses(
   398	                    lambda: (
   399	                        STATE.refresh_photos()
   400	                        if STATE.refresh_photos
   401	                        else None
   402	                    )
   403	                )
   404	
   405	        # ====================================================
   406	        # STATUS BAR
   407	        #
   408	        # Фиксированный нижний ограничитель.
   409	        # Позже сюда:
   410	        # статистика / сообщения / прогресс.
   411	        # ====================================================
   412	
   413	        with ui.row().classes(
   414	            "w-full shrink-0 items-center px-3"
   415	        ).style(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:02:03

Да, теперь всё однозначно.

`build_photos()` строит `PHOTO_INDEX`, **а `build_addresses()` вызывается только после него**. Значит, самое чистое место — сразу после `build_photo_index()` один раз инициализировать выбранные адреса, если это именно первый запуск сессии.

Но есть важный момент: нельзя просто делать `STATE.selected_addresses = set(PHOTO_INDEX)`, потому что тогда кнопка **«Снять»** перестанет нормально работать только если этот код будет выполняться повторно при refresh. Поэтому делаем флаг инициализации.

### Патч

Вставим после строки:

```python
build_photo_index()
```

в `photos.py`:

```python
    # --------------------------------------------------------
    # INITIAL ADDRESS SELECTION
    #
    # При первом построении индекса выбираем все адреса.
    # После этого пользователь управляет фильтром вручную.
    # --------------------------------------------------------

    if not getattr(
        STATE,
        "_addresses_initialized",
        False,
    ):
        STATE.selected_addresses = {
            address
            for address in PHOTO_INDEX
            if address != "__UNASSIGNED__"
        }

        STATE._addresses_initialized = True

        print(
            "[INITIAL ADDRESS SELECTION]",
            sorted(STATE.selected_addresses),
            flush=True,
        )
```

Давай применим именно этот патч.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python - <<'PY'
from pathlib import Path

p = Path("app/web/components/photos.py")
s = p.read_text()

needle = """    build_photo_index()

    # ========================================================
    # LAZY GRID
"""

replacement = """    build_photo_index()

    # --------------------------------------------------------
    # INITIAL ADDRESS SELECTION
    #
    # При первом построении индекса выбираем все адреса.
    # После этого пользователь управляет фильтром вручную.
    # --------------------------------------------------------

    if not getattr(
        STATE,
        "_addresses_initialized",
        False,
    ):
        STATE.selected_addresses = {
            address
            for address in PHOTO_INDEX
            if address != "__UNASSIGNED__"
        }

        STATE._addresses_initialized = True

        print(
            "[INITIAL ADDRESS SELECTION]",
            sorted(STATE.selected_addresses),
            flush=True,
        )

    # ========================================================
    # LAZY GRID
"""

if needle not in s:
    raise SystemExit("PATCH TARGET NOT FOUND")

if "[INITIAL ADDRESS SELECTION]" in s:
    raise SystemExit("PATCH ALREADY APPLIED")

p.write_text(s.replace(needle, replacement, 1))
print("PATCH OK")
PY
python -m py_compile app/web/components/photos.py && \
echo "PY_COMPILE OK"
```

Потом перезапусти LORA:

```bash
sudo systemctl restart lora
```

И сразу посмотри:

```bash
journalctl -u lora -n 80 --no-pager | grep -E \
'\[PHOTO RECORD INDEX\]|\[VIRTUAL PHOTO INDEX\]|\[VIRTUAL ADDRESSES\]|\[INITIAL ADDRESS SELECTION\]|\[PHOTO GRID'
```

**Ожидаем теперь примерно:**

```text
[PHOTO RECORD INDEX] records= 526
[VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
[VIRTUAL ADDRESSES] ['78', ..., '95']
[INITIAL ADDRESS SELECTION] ['78', ..., '95']
[PHOTO GRID INITIAL LOAD]
[PHOTO GRID EXECUTED] loaded= 40 total= 519
[PHOTO GRID RENDERED] loaded= 40
```

То есть при открытии интерфейса сразу появятся первые **40 фото из 519**, а дальше кнопка «Показать следующие фото».

И главное: после нажатия **«Снять»** `STATE.selected_addresses` станет пустым и грид действительно будет пустым — патч этого поведения не ломает.

---

### 👤 **User** — 2026-08-20 23:02:18

# --------------------------------------------------------
    # INITIAL ADDRESS SELECTION
    #
    # При первом построении индекса выбираем все адреса.
    # После этого пользователь управляет фильтром вручную.
    # --------------------------------------------------------

    if not getattr(
echo "PY_COMPILE OK" app/web/components/photos.py && \========
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
Command 'python' not found, did you mean:
  command 'python3' from deb python3
  command 'python' from deb python-is-python3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:02:19

Да, это не проблема патча — на сервере просто нет команды `python`, есть `python3` и у проекта есть `uv`.

Но по выводу видно ещё важное: ты, похоже, **не получил `PATCH OK`**, потому что команда оборвалась на проверке `python`.

Давай сейчас не гадать. Выполни одной командой через `uv`:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A30 -B3 'INITIAL ADDRESS SELECTION' app/web/components/photos.py && \
echo "================ COMPILE ================" && \
uv run python -m py_compile app/web/components/photos.py && \
echo "PY_COMPILE OK"
```

Если увидим блок и `PY_COMPILE OK` — патч установлен правильно.

**Пока LORA не перезапускай.** Сначала проверим, что именно записалось в `photos.py`.

---

### 👤 **User** — 2026-08-20 23:02:32

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
grep -n -A30 -B3 'INITIAL ADDRESS SELECTION' app/web/components/photos.py && \
echo "================ COMPILE ================" && \
uv run python -m py_compile app/web/components/photos.py && \
echo "PY_COMPILE OK"
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:02:34

Да — значит **патч вообще не записался**. `grep` ничего не нашёл, поэтому сразу пошёл следующий `echo`, а вывод `COMPILE` тоже отсутствует из-за того, как команда отработала.

Делаем надёжно через `sed`, без `python`.

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
sed -i '/    build_photo_index()/a\
\
    # --------------------------------------------------------\
    # INITIAL ADDRESS SELECTION\
    #\
    # При первом построении индекса выбираем все адреса.\
    # После этого пользователь управляет фильтром вручную.\
    # --------------------------------------------------------\
\
    if not getattr(\
        STATE,\
        "_addresses_initialized",\
        False,\
    ):\
        STATE.selected_addresses = {\
            address\
            for address in PHOTO_INDEX\
            if address != "__UNASSIGNED__"\
        }\
\
        STATE._addresses_initialized = True\
\
        print(\
            "[INITIAL ADDRESS SELECTION]",\
            sorted(STATE.selected_addresses),\
            flush=True,\
        )' \
app/web/components/photos.py && \
echo "================ PATCH CHECK ================" && \
grep -n -A30 -B3 'INITIAL ADDRESS SELECTION' app/web/components/photos.py && \
echo "================ COMPILE ================" && \
uv run python -m py_compile app/web/components/photos.py && \
echo "PY_COMPILE OK"
```

Если получим `PATCH CHECK` с блоком и `PY_COMPILE OK`, тогда:

```bash
sudo systemctl restart lora && \
sleep 2 && \
journalctl -u lora -n 100 --no-pager | grep -E \
'\[PHOTO RECORD INDEX\]|\[VIRTUAL PHOTO INDEX\]|\[VIRTUAL ADDRESSES\]|\[INITIAL ADDRESS SELECTION\]|\[PHOTO GRID'
```

Ожидаем ключевое:

```text
[INITIAL ADDRESS SELECTION] ['78', '79', ..., '95']
[PHOTO GRID EXECUTED] loaded= 40 total= 519
```

Если будет именно так — проблема с пустым гридом решена.

---

### 👤 **User** — 2026-08-20 23:02:46

echo "PY_COMPILE OK"compile app/web/components/photos.py && \ts/photos.py && \
================ PATCH CHECK ================
1128-    build_photo_index()
1129-
1130-    # --------------------------------------------------------
1131:    # INITIAL ADDRESS SELECTION
1132-    #
1133-    # При первом построении индекса выбираем все адреса.
1134-    # После этого пользователь управляет фильтром вручную.
1135-    # --------------------------------------------------------
1136-
1137-    if not getattr(
1138-        STATE,
1139-        "_addresses_initialized",
1140-        False,
1141-    ):
1142-        STATE.selected_addresses = {
1143-            address
1144-            for address in PHOTO_INDEX
1145-            if address != "__UNASSIGNED__"
1146-        }
1147-
1148-        STATE._addresses_initialized = True
1149-
1150-        print(
1151:            "[INITIAL ADDRESS SELECTION]",
1152-            sorted(STATE.selected_addresses),
1153-            flush=True,
1154-        )
1155-
1156-    # ========================================================
1157-    # LAZY GRID
1158-    # ========================================================
1159-
1160-    GRID_PAGE_SIZE = 40
1161-
1162-    # --------------------------------------------------------
1163-    # DISPLAY SETTINGS
1164-    # --------------------------------------------------------
1165-
1166-    if not hasattr(STATE, "photo_view_mode"):
1167-        STATE.photo_view_mode = "grid"
1168-
1169-    if not hasattr(STATE, "photo_size"):
1170-        STATE.photo_size = "medium"
1171-
1172-    grid_loaded = 0
1173-
1174-    total_photos = len(
1175-        get_all_indexed_photos()
1176-    )
1177-
1178-    print(
1179-        "[PHOTO INDEX]",
1180-        f"addresses={len(PHOTO_INDEX)}",
1181-        f"photos={total_photos}",
================ COMPILE ================
PY_COMPILE OK

---

### 🤖 **Assistant** — 2026-08-20 23:02:47

Отлично. **Патч установлен и синтаксис чистый.** Теперь перезапускаем LORA и проверяем именно первый запуск грида.

```bash
sudo systemctl restart lora && \
sleep 3 && \
journalctl -u lora -n 120 --no-pager | grep -E \
'\[PHOTO RECORD INDEX\]|\[VIRTUAL PHOTO INDEX\]|\[VIRTUAL ADDRESSES\]|\[INITIAL ADDRESS SELECTION\]|\[PHOTO GRID'
```

Нас интересуют строки примерно такого вида:

```text
[PHOTO RECORD INDEX] records= 526
[VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
[VIRTUAL ADDRESSES] ['78', ..., '95']
[INITIAL ADDRESS SELECTION] ['78', ..., '95']
[PHOTO GRID INITIAL LOAD]
[PHOTO GRID EXECUTED] loaded= 40 total= 519
[PHOTO GRID RENDERED] loaded= 40
```

**Особенно важно:** если после этого будет

```text
[INITIAL ADDRESS SELECTION] ...
[PHOTO GRID EXECUTED] loaded= 40 total= 519
```

значит мы устранили именно ту причину, из-за которой раньше было `loaded=0 total=0`.

После этого уже проверим в браузере `v2`.

---

### 👤 **User** — 2026-08-20 23:03:12

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sudo systemctl restart lora && \
sleep 3 && \
journalctl -u lora -n 120 --no-pager | grep -E \
'$$PHOTO RECORD INDEX$$|$$VIRTUAL PHOTO INDEX$$|$$VIRTUAL ADDRESSES$$|$$INITIAL ADDRESS SELECTION$$|\[PHOTO GRID'
[sudo] password for alexice: 
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO RECORD INDEX] records= 526
Aug 20 14:19:55 NEURO uv[1497608]: [VIRTUAL PHOTO INDEX] addresses= 19 photos= 526
Aug 20 14:19:55 NEURO uv[1497608]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '__UNASSIGNED__']
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID INITIAL LOAD]
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:33:39 NEURO uv[1515737]: [VIRTUAL PHOTO INDEX] addresses= 19 photos= 526
Aug 20 22:33:39 NEURO uv[1515737]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '__UNASSIGNED__']
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:02 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:02 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:17 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:17 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:25 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:25 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO RECORD INDEX] records= 526
Aug 20 23:03:02 NEURO uv[1704043]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 23:03:02 NEURO uv[1704043]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 23:03:02 NEURO uv[1704043]: [INITIAL ADDRESS SELECTION] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO GRID INITIAL LOAD]
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO GRID EXECUTED] loaded= 40 total= 519
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO GRID RENDERED] loaded= 40
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO RECORD INDEX] records= 526
Aug 20 23:03:03 NEURO uv[1704043]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 23:03:03 NEURO uv[1704043]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO GRID INITIAL LOAD]
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO GRID EXECUTED] loaded= 40 total= 519
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO GRID RENDERED] loaded= 40
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:03:14

Да. **Проблема с пустым гридом исправлена.**

Сейчас лог показывает правильную цепочку:

```text
[VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
[INITIAL ADDRESS SELECTION] ['78', ..., '95']
[PHOTO GRID INITIAL LOAD]
[PHOTO GRID EXECUTED] loaded= 40 total= 519
[PHOTO GRID RENDERED] loaded= 40
```

То есть:

- адресов: **18**
- фотографий: **519**
- все 18 адресов автоматически выбраны
- грид сразу загружает **40 фото**
- остальные доступны через «Показать следующие фото»
- `80–95` остаются в списке, как мы и хотели
- `__UNASSIGNED__` в список выбранных не попадает.

### Теперь открой V2

В браузере:

**http://192.168.1.5:8081/v2/**

или с этой машины:

**http://127.0.0.1:8081/v2/**

Если интерфейс уже открыт — просто сделай **Ctrl+F5**.

После открытия **ничего пока не меняем**. Проверяем три вещи:

1. Фото сразу появились.
2. Все адреса `78–95` имеют включённые checkbox.
3. Нажатие на адрес снимает/ставит фильтр и грид сразу перестраивается.

Если это работает — этот участок можно **заморозить** и идти дальше.

---

### 👤 **User** — 2026-08-20 23:04:01

Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID INITIAL LOAD]
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 14:19:55 NEURO uv[1497608]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:33:39 NEURO uv[1515737]: [VIRTUAL PHOTO INDEX] addresses= 19 photos= 526
Aug 20 22:33:39 NEURO uv[1515737]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '__UNASSIGNED__']
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:33:39 NEURO uv[1515737]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:02 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:02 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:02 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:17 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:17 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:17 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO RECORD INDEX] records= 526
Aug 20 22:58:25 NEURO uv[1701233]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 22:58:25 NEURO uv[1701233]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID INITIAL LOAD]
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID EXECUTED] loaded= 0 total= 0
Aug 20 22:58:25 NEURO uv[1701233]: [PHOTO GRID RENDERED] loaded= 0
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO RECORD INDEX] records= 526
Aug 20 23:03:02 NEURO uv[1704043]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 23:03:02 NEURO uv[1704043]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 23:03:02 NEURO uv[1704043]: [INITIAL ADDRESS SELECTION] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO GRID INITIAL LOAD]
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO GRID EXECUTED] loaded= 40 total= 519
Aug 20 23:03:02 NEURO uv[1704043]: [PHOTO GRID RENDERED] loaded= 40
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO RECORD INDEX] records= 526
Aug 20 23:03:03 NEURO uv[1704043]: [VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
Aug 20 23:03:03 NEURO uv[1704043]: [VIRTUAL ADDRESSES] ['78', '79', '80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95']
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO GRID INITIAL LOAD]
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO GRID EXECUTED] loaded= 40 total= 519
Aug 20 23:03:03 NEURO uv[1704043]: [PHOTO GRID RENDERED] loaded= 40
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:04:02

Да, этот лог подтверждает, что **последний запуск уже исправный**.

Старые записи до `23:03:02` можно не учитывать — это предыдущие процессы.

Актуальный процесс `uv[1704043]` показывает:

```text
[PHOTO RECORD INDEX] records= 526
[VIRTUAL PHOTO INDEX] addresses= 18 photos= 519
[VIRTUAL ADDRESSES] ['78', ..., '95']
[INITIAL ADDRESS SELECTION] ['78', ..., '95']
[PHOTO GRID INITIAL LOAD]
[PHOTO GRID EXECUTED] loaded= 40 total= 519
[PHOTO GRID RENDERED] loaded= 40
```

**Именно это нам и требовалось.**

Теперь можно проверить UI. Открой:

```text
http://192.168.1.5:8081/v2/
```

Если браузер уже открыт — **Ctrl+F5**.

После проверки напиши, что видишь. Если фото отображаются, **этот фикс больше не трогаем**.

---

### 👤 **User** — 2026-08-20 23:04:31

не отображаются

---

### 🤖 **Assistant** — 2026-08-20 23:04:32

Тогда лог показывает важную вещь: **backend считает 519 фотографий, но это ещё не означает, что браузер может получить файлы**.

Нам сейчас не надо трогать фильтры. Надо проверить, **какой путь передаётся `ui.image()` и доступен ли он через HTTP**.

Сделай одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ IMAGE SERVING ================" && \
grep -RniE \
'add_static|static|ui\.image|preview|source_path|media|FileResponse' \
app/web/main.py \
app/web/components/photos.py \
--include="*.py" | head -n 250
```

И пришли весь вывод.

Особенно интересует, **как сейчас NiceGUI раздаёт `preview_path` / `photo.path` браузеру**. Судя по логам, индекс и грид уже работают, значит следующий подозреваемый — именно HTTP-раздача изображений.

---

### 👤 **User** — 2026-08-20 23:04:48

grep -RniE \
'add_static|static|ui\.image|preview|source_path|media|FileResponse' \
app/web/main.py \
app/web/components/photos.py \
--include="*.py" | head -n 250
================ IMAGE SERVING ================
app/web/main.py:17:# FRONTEND V2 STATIC
app/web/main.py:21:from fastapi.staticfiles import StaticFiles
app/web/main.py:26:    StaticFiles(
app/web/components/photos.py:14:# PHOTO PREVIEWS
app/web/components/photos.py:17:PREVIEW_ROOT = (
app/web/components/photos.py:20:    / "preview"
app/web/components/photos.py:52:def get_latest_preview_root():
app/web/components/photos.py:53:    """Return the newest daily preview directory."""
app/web/components/photos.py:54:    if not PREVIEW_ROOT.exists():
app/web/components/photos.py:59:        for path in PREVIEW_ROOT.iterdir()
app/web/components/photos.py:72:def get_preview_path(photo_path):
app/web/components/photos.py:73:    """Map daily output photo to its preview image."""
app/web/components/photos.py:74:    preview_root = get_latest_preview_root()
app/web/components/photos.py:77:    if preview_root is None or daily_root is None:
app/web/components/photos.py:85:    preview_path = preview_root / relative
app/web/components/photos.py:87:    if preview_path.exists():
app/web/components/photos.py:88:        return preview_path
app/web/components/photos.py:295:    # Физические фотографии остаются в source_path.
app/web/components/photos.py:313:            record.get("source_path")
app/web/components/photos.py:877:                ui.image(
app/web/components/photos.py:1591:                                    # В ГРИДЕ показываем PREVIEW.
app/web/components/photos.py:1594:                                    preview_path = (
app/web/components/photos.py:1595:                                        get_preview_path(
app/web/components/photos.py:1601:                                        preview_path
app/web/components/photos.py:1602:                                        if preview_path
app/web/components/photos.py:1606:                                    ui.image(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-20 23:04:49

Вот оно. Сейчас надо проверить `main.py`: есть ли **реальная раздача `/preview` и `/daily` через HTTP**.

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN STATIC ================" && \
nl -ba app/web/main.py | sed -n '1,55p' && \
echo "================ PREVIEW FUNCTIONS ================" && \
nl -ba app/web/components/photos.py | sed -n '1,105p' && \
echo "================ IMAGE CODE ================" && \
nl -ba app/web/components/photos.py | sed -n '1580,1615p'
```

По предыдущему выводу уже видно подозрительное место:

```python
ui.image(str(display_path))
```

Если `display_path` — обычный путь вида `/.../output/daily/.../preview/...jpg`, браузер **не обязан иметь к нему HTTP-доступ**.

Сначала посмотрим `main.py` — **не будем пока ничего менять**.

---

### 👤 **User** — 2026-08-20 23:05:07

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ MAIN STATIC ================" && \
nl -ba app/web/main.py | sed -n '1,55p' && \
echo "================ PREVIEW FUNCTIONS ================" && \
nl -ba app/web/components/photos.py | sed -n '1,105p' && \
echo "================ IMAGE CODE ================" && \
nl -ba app/web/components/photos.py | sed -n '1580,1615p'
================ MAIN STATIC ================
     1	import asyncio
     2	
     3	from nicegui import ui, app
     4	
     5	from app.web.config import HOST, PORT
     6	from app.web.state import STATE
     7	from app.web.components.header import build_header
     8	from app.web.components.search import build_search
     9	from app.web.components.clients import build_clients_panel
    10	from app.web.components.photos import build_photos
    11	from app.web.components.addresses import build_addresses
    12	from app.web.components.filter_bar import build_filter_bar
    13	from app.pipeline.supervisor import supervisor_loop
    14	
    15	
    16	# ============================================================
    17	# FRONTEND V2 STATIC
    18	# ============================================================
    19	
    20	from pathlib import Path
    21	from fastapi.staticfiles import StaticFiles
    22	
    23	
    24	app.mount(
    25	    "/v2",
    26	    StaticFiles(
    27	        directory=Path(
    28	            "app/web/frontend_v2"
    29	        ).resolve(),
    30	        html=True,
    31	    ),
    32	    name="frontend_v2",
    33	)
    34	
    35	
    36	
    37	# =================================# PIPELINE SUPERVISOR
    38	# ============================================================
    39	
    40	_supervisor_task = None
    41	
    42	
    43	async def start_pipeline_supervisor():
    44	    global _supervisor_task
    45	
    46	    if (
    47	        _supervisor_task is not None
    48	        and not _supervisor_task.done()
    49	    ):
    50	        print(
    51	            "[WEB] Pipeline Supervisor already running",
    52	            flush=True,
    53	        )
    54	        return
    55	
================ PREVIEW FUNCTIONS ================
     1	from pathlib import Path
     2	from datetime import datetime
     3	import json
     4	import sqlite3
     5	import zipfile
     6	import tempfile
     7	
     8	from nicegui import ui
     9	
    10	from app.web.config import PHOTO_ROOT, DB_PATH, PROJECT_ROOT
    11	
    12	
    13	# ============================================================
    14	# PHOTO PREVIEWS
    15	# ============================================================
    16	
    17	PREVIEW_ROOT = (
    18	    PROJECT_ROOT
    19	    / "data"
    20	    / "preview"
    21	    / "daily"
    22	)
    23	
    24	DAILY_ROOT = (
    25	    PROJECT_ROOT
    26	    / "data"
    27	    / "output"
    28	    / "daily"
    29	)
    30	
    31	
    32	def get_latest_daily_root():
    33	    """Return the newest daily output directory."""
    34	    if not DAILY_ROOT.exists():
    35	        return None
    36	
    37	    runs = [
    38	        path
    39	        for path in DAILY_ROOT.iterdir()
    40	        if path.is_dir()
    41	    ]
    42	
    43	    if not runs:
    44	        return None
    45	
    46	    return max(
    47	        runs,
    48	        key=lambda path: path.name,
    49	    )
    50	
    51	
    52	def get_latest_preview_root():
    53	    """Return the newest daily preview directory."""
    54	    if not PREVIEW_ROOT.exists():
    55	        return None
    56	
    57	    runs = [
    58	        path
    59	        for path in PREVIEW_ROOT.iterdir()
    60	        if path.is_dir()
    61	    ]
    62	
    63	    if not runs:
    64	        return None
    65	
    66	    return max(
    67	        runs,
    68	        key=lambda path: path.name,
    69	    )
    70	
    71	
    72	def get_preview_path(photo_path):
    73	    """Map daily output photo to its preview image."""
    74	    preview_root = get_latest_preview_root()
    75	    daily_root = get_latest_daily_root()
    76	
    77	    if preview_root is None or daily_root is None:
    78	        return None
    79	
    80	    try:
    81	        relative = photo_path.relative_to(daily_root)
    82	    except ValueError:
    83	        return None
    84	
    85	    preview_path = preview_root / relative
    86	
    87	    if preview_path.exists():
    88	        return preview_path
    89	
    90	    return None
    91	from app.web.state import STATE, Photo
    92	from app.web.photo_db import build_photo_record_index
    93	
    94	
    95	IMAGE_EXTENSIONS = {
    96	    ".jpg",
    97	    ".jpeg",
    98	    ".png",
    99	    ".webp",
   100	}
   101	
   102	
   103	# ============================================================
   104	# PHOTO INDEX
   105	# ============================================================
================ IMAGE CODE ================
  1580	                                    "relative "
  1581	                                    "w-full h-44 "
  1582	                                    "bg-grey-2 "
  1583	                                    "flex items-center "
  1584	                                    "justify-center"
  1585	                                ).on(
  1586	                                    "contextmenu.prevent",
  1587	                                    lambda e, p=photo:
  1588	                                        photo_menu(p),
  1589	                                ):
  1590	
  1591	                                    # В ГРИДЕ показываем PREVIEW.
  1592	                                    # Оригинал открывается только
  1593	                                    # после клика.
  1594	                                    preview_path = (
  1595	                                        get_preview_path(
  1596	                                            photo.path
  1597	                                        )
  1598	                                    )
  1599	
  1600	                                    display_path = (
  1601	                                        preview_path
  1602	                                        if preview_path
  1603	                                        else photo.path
  1604	                                    )
  1605	
  1606	                                    ui.image(
  1607	                                        str(display_path)
  1608	                                    ).classes(
  1609	                                        "w-full h-full "
  1610	                                        "object-contain"
  1611	                                    ).on(
  1612	                                        "click",
  1613	                                        lambda e, p=photo:
  1614	                                            open_photo(p),
  1615	                                    )
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

