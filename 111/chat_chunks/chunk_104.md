## СЕССИЯ: ЛОРА ФИНАЛ 17 авг

**Создано:** 2026-08-16 21:41:46
**Обновлено:** 2026-08-19 17:07:59
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a820465-6788-83ea-b30d-7b8dfc43468a)

---

### 👤 **User** — 2026-08-16 22:05:09

255	    _restore_and_watch_size()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID ================" && \
grep -R -n -E \
'Hybrid|hybrid|v12|rerank|RERANK' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300 && \
echo "================ SORT ================" && \
grep -R -n -E \
'sort_test_and_report|sorted|shutil.copy|copy2|mkdir|address|best_id' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300 && \
echo "================ QWEN ALL ================" && \
grep -R -n -E \
'Qwen|qwen' \
app scripts \
--exclude='*.bak*' \
--exclude='*.pyc' \
2>/dev/null | head -300
================ HYBRID ================
scripts/benchmark_sub_rerank_v04.py:26:    "data/output/benchmark_sub_rerank_v04.json"
scripts/benchmark_sub_rerank_v04.py:127:    print("SUB RERANK V04")
scripts/benchmark_hybrid_v08.py:27:    "data/output/benchmark_hybrid_v08.json"
scripts/benchmark_hybrid_v08.py:349:                "sub_rerank":
scripts/benchmark_hybrid_v08.py:372:        "sub rerank:",
scripts/benchmark_hybrid_v03.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v03.py:314:                "sub_rerank":
scripts/benchmark_hybrid_v03.py:337:        "sub rerank:",
scripts/benchmark_hybrid_v12_full.py:27:    "data/output/full_recognize_hybrid_v12_test.json"
scripts/benchmark_hybrid_v12_full.py:288:        # Change only if hybrid has strong evidence.
scripts/benchmark_hybrid_v12_full.py:408:                "sub_rerank":
scripts/benchmark_hybrid_v12_full.py:431:        "sub rerank:",
scripts/benchmark_hybrid_v10_debug.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/benchmark_hybrid_v10_debug.py:287:        # Change only if hybrid has strong evidence.
scripts/benchmark_hybrid_v10_debug.py:379:                "sub_rerank":
scripts/benchmark_hybrid_v10_debug.py:402:        "sub rerank:",
scripts/benchmark_sub_rerank_v03.py:26:    "data/output/benchmark_sub_rerank_v03.json"
scripts/benchmark_sub_rerank_v03.py:75:    print("SUB RERANK V03")
scripts/benchmark_sub_rerank_v01.py:26:    / "data/output/benchmark_sub_rerank_v01.json"
scripts/benchmark_sub_rerank_v01.py:78:    print("SUB RERANK EXP V01")
scripts/benchmark_hybrid_v11.py:27:    "data/output/benchmark_hybrid_v11.json"
scripts/benchmark_hybrid_v11.py:287:        # Change only if hybrid has strong evidence.
scripts/benchmark_hybrid_v11.py:378:                "sub_rerank":
scripts/benchmark_hybrid_v11.py:401:        "sub rerank:",
scripts/benchmark_hybrid_v02.py:27:    "data/output/benchmark_hybrid_v02.json"
scripts/benchmark_hybrid_v02.py:145:    rerank_count = 0
scripts/benchmark_hybrid_v02.py:192:            rerank_count += 1
scripts/benchmark_hybrid_v02.py:306:                "sub_rerank": rerank_count,
scripts/benchmark_hybrid_v02.py:324:        "sub rerank:",
scripts/benchmark_hybrid_v02.py:325:        rerank_count
scripts/benchmark_hybrid_v05.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v05.py:329:                "sub_rerank":
scripts/benchmark_hybrid_v05.py:352:        "sub rerank:",
scripts/benchmark_hybrid_v04.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v04.py:345:                "sub_rerank":
scripts/benchmark_hybrid_v04.py:368:        "sub rerank:",
scripts/benchmark_hybrid_v01.py:27:    "data/output/benchmark_hybrid_v01.json"
scripts/benchmark_hybrid_v01.py:173:    rerank_count=0
scripts/benchmark_hybrid_v01.py:223:            rerank_count+=1
scripts/benchmark_hybrid_v01.py:331:                "rerank":rerank_count,
scripts/benchmark_hybrid_v01.py:349:        "sub rerank:",
scripts/benchmark_hybrid_v01.py:350:        rerank_count
scripts/benchmark_hybrid_v06.py.save:287:                "sub_rerank":
scripts/benchmark_hybrid_v06.py.save:310:        "sub rerank:",
scripts/benchmark_hybrid_v07.py:27:    "data/output/benchmark_hybrid_v07.json"
scripts/benchmark_hybrid_v07.py:346:                "sub_rerank":
scripts/benchmark_hybrid_v07.py:369:        "sub rerank:",
scripts/benchmark_hybrid_v06.py:27:    "data/output/benchmark_hybrid_v03.json"
scripts/benchmark_hybrid_v06.py:346:                "sub_rerank":
scripts/benchmark_hybrid_v06.py:369:        "sub rerank:",
scripts/benchmark_sub_rerank_v02.py:28:    / "data/output/benchmark_sub_rerank_v02.json"
scripts/benchmark_sub_rerank_v02.py:82:    print("SUB RERANK V02")
scripts/export_visual_compare.py:40:def export_hybrid():
scripts/export_visual_compare.py:44:            "data/output/full_recognize_hybrid_v12_test.json",
scripts/export_visual_compare.py:58:            "hybrid_v12" /
scripts/export_visual_compare.py:73:export_hybrid()
scripts/benchmark_hybrid_v09.py:27:    "data/output/benchmark_hybrid_v09.json"
scripts/benchmark_hybrid_v09.py:287:        # Change only if hybrid has strong evidence.
scripts/benchmark_hybrid_v09.py:378:                "sub_rerank":
scripts/benchmark_hybrid_v09.py:401:        "sub rerank:",
================ SORT ================
app/web/components/photos.py.before_pg_link_20260816_183647:33:    for address in STATE.addresses:
app/web/components/photos.py.before_pg_link_20260816_183647:35:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_pg_link_20260816_183647:38:            PHOTO_INDEX[address] = []
app/web/components/photos.py.before_pg_link_20260816_183647:55:        PHOTO_INDEX[address] = files
app/web/components/photos.py.before_pg_link_20260816_183647:62:    for address in STATE.addresses:
app/web/components/photos.py.before_pg_link_20260816_183647:65:                address,
app/web/components/photos.py.before_pg_link_20260816_183647:98:        if STATE.selected_addresses:
app/web/components/photos.py.before_pg_link_20260816_183647:99:            db_address = str(
app/web/components/photos.py.before_pg_link_20260816_183647:100:                record.get("address") or ""
app/web/components/photos.py.before_pg_link_20260816_183647:103:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py.before_pg_link_20260816_183647:117:    selected = STATE.selected_addresses
app/web/components/photos.py.before_pg_link_20260816_183647:124:    for address in STATE.addresses:
app/web/components/photos.py.before_pg_link_20260816_183647:126:        if address not in selected:
app/web/components/photos.py.before_pg_link_20260816_183647:131:                address,
app/web/components/photos.py.before_pg_link_20260816_183647:139:def get_address_count(address):
app/web/components/photos.py.before_pg_link_20260816_183647:143:            address,
app/web/components/photos.py.before_pg_link_20260816_183647:282:                            f"Адрес: {value('address')}"
app/web/components/photos.py.before_pg_link_20260816_183647:430:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/photos.py.before_client_filter:34:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter:39:            PHOTO_INDEX[address] = []
app/web/components/photos.py.before_client_filter:56:        PHOTO_INDEX[address] = files
app/web/components/photos.py.before_client_filter:63:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter:66:                address,
app/web/components/photos.py.before_client_filter:99:        if STATE.selected_addresses:
app/web/components/photos.py.before_client_filter:100:            db_address = str(
app/web/components/photos.py.before_client_filter:101:                record.get("address") or ""
app/web/components/photos.py.before_client_filter:104:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py.before_client_filter:118:    selected = STATE.selected_addresses
app/web/components/photos.py.before_client_filter:125:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter:127:        if address not in selected:
app/web/components/photos.py.before_client_filter:132:                address,
app/web/components/photos.py.before_client_filter:140:def get_address_count(address):
app/web/components/photos.py.before_client_filter:144:            address,
app/web/components/photos.py.before_client_filter:250:                            value("address")
app/web/components/photos.py.before_client_filter:471:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/photos_before_cache_20260816_145128.py:22:    for address in STATE.addresses:
app/web/components/photos_before_cache_20260816_145128.py:24:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos_before_cache_20260816_145128.py:49:    selected = STATE.selected_addresses
app/web/components/photos_before_cache_20260816_145128.py:58:        address = path.parent.name.replace(
app/web/components/photos_before_cache_20260816_145128.py:63:        if address in selected:
app/web/components/search.py:28:        address
app/web/components/search.py:51:            address,
app/web/components/search.py:74:            OR address ILIKE %s
app/web/components/photos.py.before_info_panel_20260816_184210:34:    for address in STATE.addresses:
app/web/components/photos.py.before_info_panel_20260816_184210:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_info_panel_20260816_184210:39:            PHOTO_INDEX[address] = []
app/web/components/photos.py.before_info_panel_20260816_184210:56:        PHOTO_INDEX[address] = files
app/web/components/photos.py.before_info_panel_20260816_184210:63:    for address in STATE.addresses:
app/web/components/photos.py.before_info_panel_20260816_184210:66:                address,
app/web/components/photos.py.before_info_panel_20260816_184210:99:        if STATE.selected_addresses:
app/web/components/photos.py.before_info_panel_20260816_184210:100:            db_address = str(
app/web/components/photos.py.before_info_panel_20260816_184210:101:                record.get("address") or ""
app/web/components/photos.py.before_info_panel_20260816_184210:104:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py.before_info_panel_20260816_184210:118:    selected = STATE.selected_addresses
app/web/components/photos.py.before_info_panel_20260816_184210:125:    for address in STATE.addresses:
app/web/components/photos.py.before_info_panel_20260816_184210:127:        if address not in selected:
app/web/components/photos.py.before_info_panel_20260816_184210:132:                address,
app/web/components/photos.py.before_info_panel_20260816_184210:140:def get_address_count(address):
app/web/components/photos.py.before_info_panel_20260816_184210:144:            address,
app/web/components/photos.py.before_info_panel_20260816_184210:249:                            value("address")
app/web/components/photos.py.before_info_panel_20260816_184210:431:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/clients.py.before_refresh_fix:8:    get_clients_with_address_counts,
app/web/components/clients.py.before_refresh_fix:19:        clients = get_clients_with_address_counts()
app/web/components/clients.py.before_refresh_fix:88:                get_clients_with_address_counts()
app/web/components/clients.py.before_refresh_fix:146:        for name, address_count in clients:
app/web/components/clients.py.before_refresh_fix:169:                    f"({address_count})"
app/web/components/photos.py.before_viewer_layout_20260816_183842:34:    for address in STATE.addresses:
app/web/components/photos.py.before_viewer_layout_20260816_183842:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_viewer_layout_20260816_183842:39:            PHOTO_INDEX[address] = []
app/web/components/photos.py.before_viewer_layout_20260816_183842:56:        PHOTO_INDEX[address] = files
app/web/components/photos.py.before_viewer_layout_20260816_183842:63:    for address in STATE.addresses:
app/web/components/photos.py.before_viewer_layout_20260816_183842:66:                address,
app/web/components/photos.py.before_viewer_layout_20260816_183842:99:        if STATE.selected_addresses:
app/web/components/photos.py.before_viewer_layout_20260816_183842:100:            db_address = str(
app/web/components/photos.py.before_viewer_layout_20260816_183842:101:                record.get("address") or ""
app/web/components/photos.py.before_viewer_layout_20260816_183842:104:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py.before_viewer_layout_20260816_183842:118:    selected = STATE.selected_addresses
app/web/components/photos.py.before_viewer_layout_20260816_183842:125:    for address in STATE.addresses:
app/web/components/photos.py.before_viewer_layout_20260816_183842:127:        if address not in selected:
app/web/components/photos.py.before_viewer_layout_20260816_183842:132:                address,
app/web/components/photos.py.before_viewer_layout_20260816_183842:140:def get_address_count(address):
app/web/components/photos.py.before_viewer_layout_20260816_183842:144:            address,
app/web/components/photos.py.before_viewer_layout_20260816_183842:283:                            f"Адрес: {value('address')}"
app/web/components/photos.py.before_viewer_layout_20260816_183842:431:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/clients.py.before_multiclient:8:    get_clients_with_address_counts,
app/web/components/clients.py.before_multiclient:53:                get_clients_with_address_counts()
app/web/components/clients.py.before_multiclient:100:        for name, address_count in clients:
app/web/components/clients.py.before_multiclient:122:                    f"({address_count})"
app/web/components/technical_modules/photo_processing.py:30:                value="/data/output/test_sorted_v2"
app/web/components/addresses.py:15:def address_folder(address):
app/web/components/addresses.py:16:    return PHOTO_ROOT / f"{address}_v33"
app/web/components/addresses.py:19:def address_photo_count(address):
app/web/components/addresses.py:21:    folder = address_folder(address)
app/web/components/addresses.py:37:def build_addresses(refresh_photos):
app/web/components/addresses.py:59:            address_checkboxes = {}
app/web/components/addresses.py:63:                STATE.selected_addresses = set(
app/web/components/addresses.py:64:                    STATE.addresses
app/web/components/addresses.py:67:                for address, checkbox in (
app/web/components/addresses.py:68:                    address_checkboxes.items()
app/web/components/addresses.py:76:                STATE.selected_addresses.clear()
app/web/components/addresses.py:78:                for address, checkbox in (
app/web/components/addresses.py:79:                    address_checkboxes.items()
app/web/components/addresses.py:103:        for address in STATE.addresses:
app/web/components/addresses.py:105:            count = address_photo_count(
app/web/components/addresses.py:106:                address
app/web/components/addresses.py:114:                def change_address(
app/web/components/addresses.py:116:                    address=address,
app/web/components/addresses.py:120:                        STATE.selected_addresses.add(
app/web/components/addresses.py:121:                            address
app/web/components/addresses.py:124:                        STATE.selected_addresses.discard(
app/web/components/addresses.py:125:                            address
app/web/components/addresses.py:130:                        sorted(
app/web/components/addresses.py:131:                            STATE.selected_addresses
app/web/components/addresses.py:139:                    address,
app/web/components/addresses.py:141:                        address
app/web/components/addresses.py:142:                        in STATE.selected_addresses
app/web/components/addresses.py:144:                    on_change=change_address,
app/web/components/addresses.py:151:                address_checkboxes[
app/web/components/addresses.py:152:                    address
app/web/components/photos.py.before_client_filter_v3:36:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter_v3:38:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter_v3:41:            PHOTO_INDEX[address] = []
app/web/components/photos.py.before_client_filter_v3:58:        PHOTO_INDEX[address] = files
app/web/components/photos.py.before_client_filter_v3:65:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter_v3:68:                address,
app/web/components/photos.py.before_client_filter_v3:101:        if STATE.selected_addresses:
app/web/components/photos.py.before_client_filter_v3:102:            db_address = str(
app/web/components/photos.py.before_client_filter_v3:103:                record.get("address") or ""
app/web/components/photos.py.before_client_filter_v3:106:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py.before_client_filter_v3:120:    selected = STATE.selected_addresses
app/web/components/photos.py.before_client_filter_v3:127:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter_v3:129:        if address not in selected:
app/web/components/photos.py.before_client_filter_v3:134:                address,
app/web/components/photos.py.before_client_filter_v3:142:def get_address_count(address):
app/web/components/photos.py.before_client_filter_v3:146:            address,
app/web/components/photos.py.before_client_filter_v3:252:                            value("address")
app/web/components/photos.py.before_client_filter_v3:473:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/photos.py:59:    for address in STATE.addresses:
app/web/components/photos.py:61:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py:64:            PHOTO_INDEX[address] = []
app/web/components/photos.py:81:        PHOTO_INDEX[address] = files
app/web/components/photos.py:88:    for address in STATE.addresses:
app/web/components/photos.py:91:                address,
app/web/components/photos.py:124:        if STATE.selected_addresses:
app/web/components/photos.py:125:            db_address = str(
app/web/components/photos.py:126:                record.get("address") or ""
app/web/components/photos.py:129:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py:148:        selected_addresses = STATE.selected_addresses
app/web/components/photos.py:150:        if not selected_addresses:
app/web/components/photos.py:156:            for address in STATE.addresses:
app/web/components/photos.py:158:                if address not in selected_addresses:
app/web/components/photos.py:163:                        address,
app/web/components/photos.py:208:def get_address_count(address):
app/web/components/photos.py:212:            address,
app/web/components/photos.py:318:                            value("address")
app/web/components/photos.py:539:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/photos.py:673:            temp_dir.mkdir(
app/web/components/technical.py.before_modular_20260816_191419:39:            addresses_tab = ui.tab(
app/web/components/technical.py.before_modular_20260816_191419:131:            with ui.tab_panel(addresses_tab):
app/web/components/technical.py.before_modular_20260816_191419:149:                for address in [
app/web/components/technical.py.before_modular_20260816_191419:162:                            address
app/web/components/technical.py.before_modular_20260816_191419:170:                                on_click=lambda a=address:
app/web/components/technical.py.before_modular_20260816_191419:182:                                on_click=lambda a=address:
app/web/components/photos.py.before_client_filter_v2:34:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter_v2:36:        folder = PHOTO_ROOT / f"{address}_v33"
app/web/components/photos.py.before_client_filter_v2:39:            PHOTO_INDEX[address] = []
app/web/components/photos.py.before_client_filter_v2:56:        PHOTO_INDEX[address] = files
app/web/components/photos.py.before_client_filter_v2:63:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter_v2:66:                address,
app/web/components/photos.py.before_client_filter_v2:99:        if STATE.selected_addresses:
app/web/components/photos.py.before_client_filter_v2:100:            db_address = str(
app/web/components/photos.py.before_client_filter_v2:101:                record.get("address") or ""
app/web/components/photos.py.before_client_filter_v2:104:            if db_address not in STATE.selected_addresses:
app/web/components/photos.py.before_client_filter_v2:118:    selected = STATE.selected_addresses
app/web/components/photos.py.before_client_filter_v2:125:    for address in STATE.addresses:
app/web/components/photos.py.before_client_filter_v2:127:        if address not in selected:
app/web/components/photos.py.before_client_filter_v2:132:                address,
app/web/components/photos.py.before_client_filter_v2:140:def get_address_count(address):
app/web/components/photos.py.before_client_filter_v2:144:            address,
app/web/components/photos.py.before_client_filter_v2:250:                            value("address")
app/web/components/photos.py.before_client_filter_v2:471:        f"addresses={len(PHOTO_INDEX)}",
app/web/components/clients.py:5:from app.web.client_db import get_clients_with_address_counts
app/web/components/clients.py:15:        clients = get_clients_with_address_counts()
app/web/components/clients.py:168:        for name, address_count in clients:
app/web/components/clients.py:198:                    f"({address_count})"
app/web/main.py.before_client_refresh_fix:9:from app.web.components.addresses import build_addresses
app/web/main.py.before_client_refresh_fix:61:            build_addresses(
app/web/state.py.before_multiclient:42:    addresses: list[str] = field(default_factory=lambda: [
app/web/state.py.before_multiclient:72:    selected_addresses: set[str] = field(default_factory=set)
app/web/photo_db.py:20:            address,
app/web/frontend_v02.py:198:address_panel = {"value": None}
app/web/frontend_v02.py:498:                for group_name, addresses in groups.items():
app/web/frontend_v02.py:507:                        for address in addresses:
app/web/frontend_v02.py:518:                                    address
app/web/main.py.before_callback_fix2:9:from app.web.components.addresses import build_addresses
app/web/main.py.before_callback_fix2:67:            build_addresses(
app/web/main.py:9:from app.web.components.addresses import build_addresses
app/web/main.py:65:            build_addresses(
app/web/config.py:16:    / "test_sorted_v2"
app/web/frontend_v01_backup_before_modular.py:458:        for address in ADDRESSES:
app/web/frontend_v01_backup_before_modular.py:469:                    address
app/web/users_db.py:21:    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
app/web/frontend_v01.py:458:        for address in ADDRESSES:
app/web/frontend_v01.py:469:                    address
app/web/state.py:50:    addresses: list[str] = field(default_factory=lambda: [
app/web/state.py:81:    selected_addresses: set[str] = field(default_factory=set)
app/web/client_db.py:12:def get_clients_with_address_counts() -> list[tuple[str, int]]:
app/web/client_db.py:29:                            address,
app/web/client_db.py:37:            ) AS address_count
app/core/recognizer.py.before_restore_old_matching_20260815_025751:389:                        "best_id": None,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:436:            # available address. The score/confidence are kept
app/core/recognizer.py.before_restore_old_matching_20260815_025751:438:            best_id = best["id"]
app/core/recognizer.py.before_restore_old_matching_20260815_025751:451:                    "best_id": best_id,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:389:                        "best_id": None,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:436:            # available address. The score/confidence are kept
app/core/recognizer.py.before_restore_old_matching_20260815_025724:438:            best_id = best["id"]
app/core/recognizer.py.before_restore_old_matching_20260815_025724:451:                    "best_id": best_id,
app/core/recognizer.py:389:                        "best_id": None,
app/core/recognizer.py:436:            # available address. The score/confidence are kept
app/core/recognizer.py:439:                best_id = None
app/core/recognizer.py:442:                best_id = best["id"]
app/core/recognizer.py:451:                    "best_id": best_id,
app/core/fingerprint.py.before_patchfix:18:        self.root.mkdir(parents=True, exist_ok=True)
app/core/fingerprint.py.before_patchfix:29:        for d in sorted(self.root.iterdir()):
app/core/fingerprint.py.before_patchfix:58:        paths = sorted([
app/core/fingerprint.py.before_patchfix:126:        out.mkdir(parents=True)
app/core/recognizer.py.backup_before_optimization:300:                        "best_id": None,
app/core/recognizer.py.backup_before_optimization:347:            # available address. The score/confidence are kept
app/core/recognizer.py.backup_before_optimization:349:            best_id = best["id"]
app/core/recognizer.py.backup_before_optimization:362:                    "best_id": best_id,
app/core/recognizer.py.before_patchfix:153:        paths = sorted([
app/core/recognizer.py.before_patchfix:213:                best_id = best["id"]
app/core/recognizer.py.before_patchfix:216:                best_id = None
app/core/recognizer.py.before_patchfix:221:                "best_id": best_id,
app/core/recognizer.py.before_patchfix:242:        paths = sorted([
app/core/recognizer.py.before_patchfix:277:            best_idx = int(
app/core/recognizer.py.before_patchfix:288:            if best_idx < len(image_names):
app/core/recognizer.py.before_patchfix:289:                best_image = image_names[best_idx]
app/core/recognizer.py.before_patchfix:291:                best_image = str(best_idx)
app/core/recognizer.py.before_patchfix:297:                    image_scores[best_idx]
app/core/fingerprint.py:53:        self.root.mkdir(
app/core/fingerprint.py:75:        for directory in sorted(
app/core/fingerprint.py:191:        output.mkdir(
app/core/image.py:10:    return sorted(p for p in folder.rglob("*")
app/core/recognizer.py.backup_before_force_match:300:                        "best_id": None,
app/core/recognizer.py.backup_before_force_match:345:                best_id = None
app/core/recognizer.py.backup_before_force_match:348:                best_id = best["id"]
app/core/recognizer.py.backup_before_force_match:354:                    "best_id": best_id,
app/core/recognizer.py.v33_working:389:                        "best_id": None,
app/core/recognizer.py.v33_working:436:            # available address. The score/confidence are kept
app/core/recognizer.py.v33_working:439:                best_id = None
app/core/recognizer.py.v33_working:442:                best_id = best["id"]
app/core/recognizer.py.v33_working:451:                    "best_id": best_id,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:389:                        "best_id": None,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:436:            # available address. The score/confidence are kept
app/core/recognizer.py.before_restore_old_matching_20260815_025737:438:            best_id = best["id"]
app/core/recognizer.py.before_restore_old_matching_20260815_025737:451:                    "best_id": best_id,
app/pipeline/queue.py:22:        self.db_path.parent.mkdir(
app/main.py:55:                                f"{row['best_id'] or 'UNKNOWN'} "
app/web_v01_backup_20260816_142053/components/addresses.py:26:def build_addresses():
app/web_v01_backup_20260816_142053/components/addresses.py:45:        for address in ADDRESSES:
app/web_v01_backup_20260816_142053/components/addresses.py:50:                ui.label(f"Адрес {address}")
app/web_v01_backup_20260816_142053/frontend_v02.py:198:address_panel = {"value": None}
app/web_v01_backup_20260816_142053/frontend_v02.py:498:                for group_name, addresses in groups.items():
app/web_v01_backup_20260816_142053/frontend_v02.py:507:                        for address in addresses:
app/web_v01_backup_20260816_142053/frontend_v02.py:518:                                    address
app/web_v01_backup_20260816_142053/main.py:6:from app.web.components.addresses import build_addresses
app/web_v01_backup_20260816_142053/main.py:64:            build_addresses()
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:458:        for address in ADDRESSES:
app/web_v01_backup_20260816_142053/frontend_v01_backup_before_modular.py:469:                    address
app/web_v01_backup_20260816_142053/frontend_v01.py:458:        for address in ADDRESSES:
app/web_v01_backup_20260816_142053/frontend_v01.py:469:                    address
app/web_v01_backup_20260816_142053/state.py:5:        self.selected_addresses = []
app/cli.py:87:        help="First address ID",
app/cli.py:93:        help="Last address ID",
app/cli.py:238:    best_id = result.get(
app/cli.py:239:        "best_id"
app/cli.py:275:        f"{best_id or 'NONE'}"
app/ocr/grid_ocr.py:200:    temp_dir.mkdir(
app/ocr/plate_detector.py:157:    output_path.parent.mkdir(
scripts/sort_neighbor_v35_benchmark.py:15:SORTED_DIR = OUTPUT_DIR / "sorted"
scripts/sort_neighbor_v35_benchmark.py:66:    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
scripts/sort_neighbor_v35_benchmark.py:67:    SORTED_DIR.mkdir(parents=True, exist_ok=True)
scripts/sort_neighbor_v35_benchmark.py:227:        folder.mkdir(parents=True, exist_ok=True)
scripts/sort_neighbor_v35_benchmark.py:232:        shutil.copy2(src, dst)
scripts/sort_neighbor_v35_benchmark.py:302:    print(f"  sorted : {SORTED_DIR}")
scripts/benchmark_sub_rerank_v04.py:53:    for d in sorted(SUB_DIR.iterdir()):
scripts/benchmark_sub_rerank_v04.py:250:    OUT.parent.mkdir(
scripts/sort_test_and_report_v2.py:18:OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"
scripts/sort_test_and_report_v2.py:91:    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
scripts/sort_test_and_report_v2.py:154:    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
scripts/sort_test_and_report_v2.py:164:        # ВСЕГДА используем best_id = первый кандидат.
scripts/sort_test_and_report_v2.py:165:        assigned_id = item.get("best_id")
scripts/sort_test_and_report_v2.py:171:        destination_dir.mkdir(parents=True, exist_ok=True)
scripts/sort_test_and_report_v2.py:175:        shutil.copy2(source, destination)
scripts/sort_test_and_report_v2.py:224:    for k in sorted(counters, key=lambda x: int(x.split("_")[0])):
scripts/sort_test_and_report_v2.py:361:    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
scripts/make_subfingerprints_v2.py:153:            candidates = sorted(
scripts/make_subfingerprints_v2.py:167:            "members": sorted(candidates),
================ QWEN ALL ================
app/web/components/photos.py.before_pg_link_20260816_183647:286:                            f"Qwen: {value('qwen_status')}"
app/web/components/photos.py.before_client_filter:255:                        if value("qwen_status") != "—":
app/web/components/photos.py.before_client_filter:258:                                f"Qwen: {value('qwen_status')}"
app/web/components/search.py:22:    Поиск фотографий только по данным Qwen в PostgreSQL.
app/web/components/search.py:59:            qwen_status,
app/web/components/search.py:60:            qwen_time_sec,
app/web/components/photos.py.before_info_panel_20260816_184210:295:                        f"Qwen: {value('qwen_status')}"
app/web/components/photos.py.before_viewer_layout_20260816_183842:287:                            f"Qwen: {value('qwen_status')}"
app/web/components/technical_modules/photo_processing.py:43:            "DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B"
app/web/components/technical_modules/qwen.py:4:def build_qwen():
app/web/components/technical_modules/qwen.py:13:            "Qwen3-VL 4B"
app/web/components/technical_modules/qwen.py:29:                    "Настройки Qwen будут подключены следующим этапом"
app/web/components/technical_modules/qwen.py:34:                "▶  Повторно запустить Qwen",
app/web/components/technical_modules/qwen.py:36:                    "Повторный запуск Qwen будет подключён следующим этапом"
app/web/components/photos.py.before_client_filter_v3:257:                        if value("qwen_status") != "—":
app/web/components/photos.py.before_client_filter_v3:260:                                f"Qwen: {value('qwen_status')}"
app/web/components/photos.py:323:                        if value("qwen_status") != "—":
app/web/components/photos.py:326:                                f"Qwen: {value('qwen_status')}"
app/web/components/technical.py.before_modular_20260816_191419:248:                    "Qwen3-VL 4B",
app/web/components/photos.py.before_client_filter_v2:255:                        if value("qwen_status") != "—":
app/web/components/photos.py.before_client_filter_v2:258:                                f"Qwen: {value('qwen_status')}"
app/web/components/technical.py:12:from app.web.components.technical_modules.qwen import (
app/web/components/technical.py:13:    build_qwen,
app/web/components/technical.py:175:                    "qwen",
app/web/components/technical.py:176:                    label="Qwen",
app/web/components/technical.py:230:                    with ui.tab_panel("qwen"):
app/web/components/technical.py:231:                        build_qwen()
app/web/client_aliases.py:4:Qwen может распознавать одно и то же название с ошибками,
app/web/photo_db.py:28:            qwen_status,
app/web/photo_db.py:29:            qwen_time_sec,
app/web_v01_backup_20260816_142053/components/technical.py:84:                    "Qwen3-VL 4B",
app/web_v01_backup_20260816_142053/components/technical.py:85:                    "Qwen2.5-VL 3B",
app/web_v01_backup_20260816_142053/components/technical.py:86:                    "Qwen3-VL 2B",
app/web_v01_backup_20260816_142053/components/technical.py:88:                value="Qwen3-VL 4B",
scripts/banner_model_compare_v04.py:19:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v04.py:20:    "qwen2.5vl:3b",
scripts/banner_qwen25vl_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen25vl_test_v01")
scripts/banner_qwen25vl_test_v01.py:14:MODEL = "qwen2.5vl:3b"
scripts/banner_model_compare_v05.py:16:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v05.py:17:    "qwen2.5vl:3b",
scripts/banner_llm_full_v02.py:11:MODEL = "qwen3-vl:4b-instruct"
scripts/import_qwen_to_db.py:10:QWEN_DIR = PROJECT / "data/metadata/qwen4b"
scripts/import_qwen_to_db.py:53:            qwen_status TEXT,
scripts/import_qwen_to_db.py:54:            qwen_time_sec REAL,
scripts/import_qwen_to_db.py:90:        ON photos(qwen_status)
scripts/import_qwen_to_db.py:178:            qwen_status,
scripts/import_qwen_to_db.py:179:            qwen_time_sec,
scripts/import_qwen_to_db.py:216:            qwen_status = excluded.qwen_status,
scripts/import_qwen_to_db.py:217:            qwen_time_sec = excluded.qwen_time_sec,
scripts/banner_qwen4b_test_v01.py:12:OUTPUT_DIR = Path("data/banner_database/qwen4b_test_v01")
scripts/banner_qwen4b_test_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_folder_search_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01_before_compact_prompt.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01_before_compact_prompt.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/qwen4b_output_v01.py:15:OUTPUT_DIR = PROJECT / "data" / "metadata" / "qwen4b"
scripts/qwen4b_output_v01.py:17:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_llm_full_v01.py:9:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v02.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v02.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_model_compare_v01.py:22:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v01.py:23:    "qwen3-vl:2b-instruct",
scripts/banner_database_v02.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/migrate_sqlite_to_postgres.py:75:                qwen_status,
scripts/migrate_sqlite_to_postgres.py:76:                qwen_time_sec,
scripts/migrate_sqlite_to_postgres.py:111:                row["qwen_status"],
scripts/migrate_sqlite_to_postgres.py:112:                row["qwen_time_sec"],
scripts/migrate_sqlite_to_postgres.py:165:                    qwen_status,
scripts/migrate_sqlite_to_postgres.py:166:                    qwen_time_sec,
scripts/banner_database_v01.py:14:MODEL = "qwen3-vl:4b-instruct"
scripts/llm_resolver_v01.py:11:MODEL = "qwen3:4b"
scripts/qwen_prompt_ablation.py:15:MODEL = "qwen3-vl:4b-instruct"
scripts/banner_model_compare_v03.py:19:    "qwen3-vl:4b-instruct",
scripts/banner_model_compare_v03.py:20:    "qwen3-vl:2b-instruct",
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:05:12

Да. По этому выводу картина уже достаточно ясная. **Ничего сейчас не меняем.** Мы сначала фиксируем архитектуру, чтобы подключить техническую кнопку к уже рабочему пайплайну, а не изобретать новый.

### Что сейчас реально есть

**1. DINO / v33 — рабочее распознавание**

Основная логика находится в:

```text
app/core/recognizer.py
```

Причём текущий `recognizer.py` — это восстановленная рабочая версия v33:

```text
app/core/recognizer.py.v33_working
app/core/recognizer.py.before_restore_old_matching_...
app/core/recognizer.py.backup_before_force_match
```

И самое важное:

```text
best_id
```

уже формируется самим recognizer.

---

**2. Сортировка уже готова**

Есть конкретный рабочий скрипт:

```text
scripts/sort_test_and_report_v2.py
```

Причём внутри прямо зафиксирована наша нынешняя логика:

```python
# ВСЕГДА используем best_id = первый кандидат.
assigned_id = item.get("best_id")
```

И дальше:

```python
destination_dir.mkdir(...)
shutil.copy2(source, destination)
```

То есть схема:

```text
фото
 ↓
recognizer
 ↓
best_id
 ↓
sort_test_and_report_v2
 ↓
XX_v33/
```

уже существует.

---

### 3. Hybrid пока НЕ является частью основного рабочего пайплайна

Вот это особенно важно.

В проекте есть целая лаборатория:

```text
benchmark_hybrid_v01
benchmark_hybrid_v02
...
benchmark_hybrid_v12_full
```

а также:

```text
benchmark_sub_rerank_v01
...
v04
```

Но это **benchmark/исследовательские скрипты**, а не подключённый production-пайплайн.

Поэтому сейчас:

```text
DINO v33 → первый кандидат → адрес
```

а не:

```text
DINO → hybrid → rerank → адрес
```

И это соответствует тому, что мы ранее зафиксировали.

---

### 4. Qwen тоже уже существует, но пока отдельно

Есть полноценные скрипты:

```text
scripts/qwen4b_output_v01.py
scripts/qwen4b_output_v01_before_compact_prompt.py
scripts/import_qwen_to_db.py
scripts/qwen_prompt_ablation.py
scripts/banner_database_v02.py
...
```

Модель:

```text
qwen3-vl:4b-instruct
```

И уже есть БД-поля:

```text
qwen_status
qwen_time_sec
```

Плюс:

```text
app/web/search.py
app/web/photo_db.py
app/web/client_aliases.py
```

То есть Qwen — не заглушка. **Backend-часть Qwen уже существует.**

Но GUI сейчас только показывает:

> Qwen3-VL 4B  
> ● Рабочая модель

и две заглушки-кнопки.

---

# Поэтому я бы сейчас зафиксировал архитектуру именно так

```text
                 ┌────────────────────┐
                 │  Папка фотографий  │
                 └─────────┬──────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   DINO v33      │
                  │   recognizer    │
                  └────────┬────────┘
                           │
                           ▼
                       best_id
                           │
                           ▼
                ┌─────────────────────┐
                │ sort_test_and_      │
                │ report_v2.py        │
                └─────────┬───────────┘
                          │
                          ▼
                   XX_v33 / фото
                          │
                          ▼
                  ┌───────────────┐
                  │     Qwen      │
                  │    4B VL      │
                  └───────┬───────┘
                          │
                          ▼
                   metadata / DB
```

А **Hybrid v12** пока оставляем как исследовательский слой:

```text
benchmark_hybrid_v12_full.py
```

и не трогаем production.

---

## И вот что я предлагаю сделать следующим шагом

Не писать код наугад, а найти **точную точку входа существующего DINO + сортировщика**.

Нам нужно посмотреть всего три вещи:

```text
app/core/recognizer.py
scripts/sort_test_and_report_v2.py
scripts/qwen4b_output_v01.py
```

После этого мы сможем сделать кнопку:

### `▶ ЗАПУСТИТЬ ОБРАБОТКУ`

которая реально будет выполнять:

```text
Источник
   ↓
DINO v33
   ↓
best_id
   ↓
копирование в /data/output/test_sorted_v2
   ↓
Qwen 4B
   ↓
metadata
   ↓
PostgreSQL
```

Причём **не переписывая существующие алгоритмы**.

И ещё один важный момент: в GUI сейчас написано:

> `DINO / v33 → определение адреса → сортировка → Qwen3-VL 4B`

Это уже фактически **правильная схема интерфейса**. Нам осталось только подключить реальные backend-функции к этой кнопке.

Следующий диагностический шаг я бы сделал таким:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ RECOGNIZER ================" && \
sed -n '1,520p' app/core/recognizer.py && \
echo "================ SORTER ================" && \
sed -n '1,430p' scripts/sort_test_and_report_v2.py && \
echo "================ QWEN ================" && \
sed -n '1,260p' scripts/qwen4b_output_v01.py
```

**После этого уже можно будет точно определить функции, которые нужно импортировать в `photo_processing.py`, вместо запуска shell-скриптов из GUI.**

---

### 👤 **User** — 2026-08-16 22:06:17

hybrid И rerank фажная часть

---

### 🤖 **Assistant** — 2026-08-16 22:06:18

Да. Тогда **исправляем зафиксированную схему**: Hybrid и rerank — не лабораторные хвосты, а **важная часть рабочего алгоритма распознавания**.

По текущему проекту я вижу это так:

```text
ФОТО
  │
  ▼
DINO v33
  │
  ├── первый кандидат
  │
  ▼
HYBRID
  │
  ├── scene/global similarity
  ├── patch/subfingerprint similarity
  └── дополнительные признаки
  │
  ▼
RERANK
  │
  ▼
ФИНАЛЬНЫЙ best_id
  │
  ▼
СОРТИРОВКА
  │
  ▼
XX_v33/
  │
  ▼
Qwen3-VL 4B
```

### То есть главное

`best_id` в текущем `recognizer.py` **нельзя автоматически считать финальным результатом**, пока мы не выясним, какая именно версия Hybrid/Rerank была признана рабочей.

В твоём выводе есть:

```text
benchmark_hybrid_v08.py
benchmark_hybrid_v09.py
benchmark_hybrid_v10_debug.py
benchmark_hybrid_v11.py
benchmark_hybrid_v12_full.py
```

и отдельно:

```text
benchmark_sub_rerank_v01
benchmark_sub_rerank_v02
benchmark_sub_rerank_v03
benchmark_sub_rerank_v04
```

Это как раз нужно восстановить.

### И особенно важно

У нас уже была зафиксирована рабочая идея:

> **первый кандидат DINO → затем уточнение Hybrid/Rerank**

а не простое:

> DINO → `best_id`.

Поэтому `sort_test_and_report_v2.py` сейчас следует рассматривать как **финальную стадию после распознавания**, а не как источник алгоритма распознавания.

---

## Сейчас ничего не меняем

Следующим шагом надо установить **какая именно версия Hybrid + rerank была нашей финальной рабочей**.

Дай одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ HYBRID V12 ================" && \
cat -n scripts/benchmark_hybrid_v12_full.py | sed -n '1,470p' && \
echo "================ HYBRID V11 ================" && \
cat -n scripts/benchmark_hybrid_v11.py | sed -n '1,440p' && \
echo "================ SUB RERANK V04 ================" && \
cat -n scripts/benchmark_sub_rerank_v04.py | sed -n '1,330p'
```

**После этого восстановим именно тот алгоритм, который мы заморозили**, и только затем подключим его к кнопке `▶ ЗАПУСТИТЬ ОБРАБОТКУ`.

Qwen при этом остаётся **после финального Hybrid/Rerank**, а не вмешивается в определение адреса.

---

### 👤 **User** — 2026-08-16 22:06:36

benchmark_hybrid_v12_full.py

---

### 🤖 **Assistant** — 2026-08-16 22:06:38

Да — **`benchmark_hybrid_v12_full.py` берём как основной источник Hybrid/Rerank-алгоритма**.

Чтобы не ошибиться и не восстановить только часть логики, покажи его целиком:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat -n scripts/benchmark_hybrid_v12_full.py
```

После этого я разберу именно **v12 full** и выделю:

1. DINO v33 → первый кандидат.
2. Где и как запускается **Hybrid**.
3. Где выполняется **sub-rerank / rerank**.
4. Какие пороги и веса используются.
5. Как получается **окончательный `best_id`**.
6. Какие данные нужны алгоритму.
7. Как аккуратно вынести эту логику из benchmark в рабочий backend.
8. Как подключить её к кнопке **«ЗАПУСТИТЬ ОБРАБОТКУ»**, не ломая замороженный v33.

**Ничего пока не редактируем.** Сначала читаем v12 целиком и восстанавливаем точную цепочку.

---

### 👤 **User** — 2026-08-16 22:07:03

int_mvp_v02 && \
cat -n scripts/benchmark_hybrid_v12_full.py
     1	#!/usr/bin/env python3
     2	
     3	import json
     4	from pathlib import Path
     5	from collections import defaultdict, Counter
     6	
     7	import numpy as np
     8	
     9	from app.core.config import Settings
    10	from app.core.embedder import SceneEmbedder
    11	
    12	
    13	PROJECT = Path(__file__).resolve().parent.parent
    14	
    15	BENCHMARK = (
    16	    PROJECT /
    17	    "data/output/benchmark_sub_exp/benchmark.json"
    18	)
    19	
    20	SUB_DIR = (
    21	    PROJECT /
    22	    "data/fingerprints_sub_exp"
    23	)
    24	
    25	OUT = (
    26	    PROJECT /
    27	    "data/output/full_recognize_hybrid_v12_test.json"
    28	)
    29	
    30	
    31	MARGIN_LIMIT = 0.02
    32	
    33	GLOBAL_WEIGHT = 10.0
    34	SUB_WEIGHT = 2.5
    35	NEIGHBOR_WEIGHT = 6.0
    36	
    37	
    38	
    39	def normalize(x):
    40	
    41	    x = np.asarray(
    42	        x,
    43	        dtype=np.float32
    44	    )
    45	
    46	    n = np.linalg.norm(x)
    47	
    48	    if n > 0:
    49	        x = x / n
    50	
    51	    return x
    52	
    53	
    54	
    55	def load_subs():
    56	
    57	    result = {}
    58	
    59	    for d in sorted(SUB_DIR.iterdir()):
    60	
    61	        if not d.is_dir():
    62	            continue
    63	
    64	        f = d / "embeddings.npy"
    65	
    66	        if not f.exists():
    67	            continue
    68	
    69	        emb = np.load(
    70	            f
    71	        )
    72	
    73	        emb = np.array(
    74	            [
    75	                normalize(x)
    76	                for x in emb
    77	            ]
    78	        )
    79	
    80	        result[d.name] = emb
    81	
    82	
    83	    return result
    84	
    85	
    86	
    87	def get_neighbor_votes(rows, index):
    88	
    89	    votes = Counter()
    90	
    91	
    92	    if index <= 0:
    93	        return votes
    94	
    95	
    96	    if index >= len(rows)-1:
    97	        return votes
    98	
    99	
   100	    left = rows[index-1]["top1"]
   101	    right = rows[index+1]["top1"]
   102	
   103	
   104	    # только полное согласие
   105	
   106	    if left == right:
   107	
   108	        votes[left] = 1
   109	
   110	
   111	    return votes
   112	
   113	
   114	
   115	def main():
   116	
   117	    print("=" * 80)
   118	    print("HYBRID V03")
   119	    print("=" * 80)
   120	
   121	
   122	    with open(
   123	        BENCHMARK,
   124	        encoding="utf-8"
   125	    ) as f:
   126	
   127	        data = json.load(f)
   128	
   129	
   130	    rows = data["results"]
   131	
   132	
   133	    settings = Settings()
   134	
   135	    embedder = SceneEmbedder(
   136	        settings
   137	    )
   138	
   139	
   140	    subs = load_subs()
   141	
   142	
   143	    changed = []
   144	    all_results = []
   145	    sub_count = 0
   146	
   147	
   148	    for i, row in enumerate(rows):
   149	
   150	        old = row["top1"]
   151	
   152	
   153	        scores = defaultdict(float)
   154	
   155	
   156	        #
   157	        # GLOBAL TOP-5
   158	        #
   159	
   160	        for k in range(1, 6):
   161	
   162	            fp = row.get(
   163	                f"top{k}"
   164	            )
   165	
   166	            sc = row.get(
   167	                f"top{k}_score"
   168	            )
   169	
   170	            if fp:
   171	
   172	                scores[fp] += (
   173	                    float(sc)
   174	                    *
   175	                    GLOBAL_WEIGHT
   176	                )
   177	
   178	
   179	
   180	        #
   181	        # SUB ONLY BORDER CASES
   182	        #
   183	
   184	        margin = row.get(
   185	            "margin",
   186	            1
   187	        )
   188	
   189	
   190	        if margin < MARGIN_LIMIT:
   191	
   192	            sub_count += 1
   193	
   194	
   195	            image = Path(
   196	                row["file"]
   197	            )
   198	
   199	
   200	            query = embedder.embed_paths(
   201	                [image]
   202	            )[0]
   203	
   204	            query = normalize(
   205	                query
   206	            )
   207	
   208	
   209	            #
   210	            # ТОЛЬКО TOP1 и TOP2
   211	            #
   212	
   213	            candidates = [
   214	                row.get("top1"),
   215	                row.get("top2"),
   216	            ]
   217	
   218	
   219	            for parent in candidates:
   220	
   221	                if not parent:
   222	                    continue
   223	
   224	
   225	                for sub_id, sub_emb in subs.items():
   226	
   227	                    if not sub_id.startswith(
   228	                        parent
   229	                    ):
   230	                        continue
   231	
   232	
   233	                    sim = max(
   234	                        sub_emb @ query
   235	                    )
   236	
   237	
   238	                    if sim > 0.88:
   239	
   240	                        if sim > 0.92:
   241	                            bonus = 2.5
   242	                        else:
   243	                            bonus = 1.0
   244	
   245	                        scores[parent] += (
   246	                            float(sim)
   247	                            *
   248	                            bonus
   249	                        )
   250	
   251	
   252	
   253	        #
   254	        # SEQUENCE CONSENSUS
   255	        #
   256	        # Используем соседей только если
   257	        # слева и справа один и тот же адрес.
   258	        #
   259	
   260	        neighbors = get_neighbor_votes(
   261	            rows,
   262	            i
   263	        )
   264	
   265	        left_fp = None
   266	        right_fp = None
   267	
   268	        if i > 0:
   269	            left_fp = rows[i-1].get("top1")
   270	
   271	        if i < len(rows)-1:
   272	            right_fp = rows[i+1].get("top1")
   273	
   274	
   275	        if (
   276	            left_fp
   277	            and right_fp
   278	            and left_fp == right_fp
   279	        ):
   280	            scores[left_fp] += 3.0
   281	
   282	
   283	
   284	        #
   285	        # FINAL DECISION V09
   286	        #
   287	        # DINO TOP1 is default.
   288	        # Change only if hybrid has strong evidence.
   289	        #
   290	
   291	        best = old
   292	
   293	        ranked = sorted(
   294	            scores.items(),
   295	            key=lambda x: x[1],
   296	            reverse=True
   297	        )
   298	
   299	        if ranked:
   300	
   301	            candidate = ranked[0][0]
   302	
   303	            gain = (
   304	                scores[candidate]
   305	                -
   306	                scores.get(old, 0)
   307	            )
   308	
   309	            #
   310	            # Change only with real advantage
   311	            #
   312	            if (
   313	                candidate != old
   314	                and gain > 1.5
   315	            ):
   316	                best = candidate
   317	
   318	
   319	        old_score = scores.get(
   320	            old,
   321	            0
   322	        )
   323	
   324	        new_score = scores.get(
   325	            best,
   326	            0
   327	        )
   328	
   329	
   330	        # принимаем изменение только если
   331	        # новый кандидат реально сильнее
   332	
   333	        all_results.append(
   334	            {
   335	                "file":
   336	                    Path(
   337	                        row["file"]
   338	                    ).name,
   339	
   340	                "old":
   341	                    old,
   342	
   343	                "new":
   344	                    best,
   345	
   346	                "score":
   347	                    new_score,
   348	
   349	                "old_score":
   350	                    old_score,
   351	
   352	                "margin":
   353	                    margin,
   354	
   355	                "neighbors":
   356	                    dict(neighbors),
   357	            }
   358	        )
   359	
   360	
   361	
   362	        if (
   363	            best != old
   364	            and new_score > old_score
   365	        ):
   366	
   367	            changed.append(
   368	                {
   369	                    "file":
   370	                        Path(
   371	                            row["file"]
   372	                        ).name,
   373	
   374	                    "old":
   375	                        old,
   376	
   377	                    "new":
   378	                        best,
   379	
   380	                    "margin":
   381	                        margin,
   382	
   383	                    "neighbors":
   384	                        dict(neighbors),
   385	
   386	                    "old_score":
   387	                        scores[old],
   388	
   389	                    "new_score":
   390	                        scores[best],
   391	                }
   392	            )
   393	
   394	
   395	
   396	    OUT.parent.mkdir(
   397	        parents=True,
   398	        exist_ok=True
   399	    )
   400	
   401	
   402	    OUT.write_text(
   403	        json.dumps(
   404	            {
   405	                "checked":
   406	                    len(rows),
   407	
   408	                "sub_rerank":
   409	                    sub_count,
   410	
   411	                "changed":
   412	                    len(changed),
   413	
   414	                "results":
   415	                    all_results,
   416	            },
   417	            ensure_ascii=False,
   418	            indent=2
   419	        ),
   420	        encoding="utf-8"
   421	    )
   422	
   423	
   424	    print()
   425	    print(
   426	        "checked:",
   427	        len(rows)
   428	    )
   429	
   430	    print(
   431	        "sub rerank:",
   432	        sub_count
   433	    )
   434	
   435	    print(
   436	        "changed:",
   437	        len(changed)
   438	    )
   439	
   440	
   441	    for x in changed:
   442	
   443	        print()
   444	        print(
   445	            x["file"]
   446	        )
   447	
   448	        print(
   449	            x["old"],
   450	            "->",
   451	            x["new"]
   452	        )
   453	
   454	        print(
   455	            "neighbors:",
   456	            x["neighbors"]
   457	        )
   458	
   459	
   460	    print()
   461	    print("saved:")
   462	    print(OUT)
   463	
   464	
   465	
   466	if __name__ == "__main__":
   467	    main()
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:07:04

Да. Теперь алгоритм **v12 зафиксирован**, и это уже можно переносить в рабочий pipeline.

### Что делает v12

Финальная схема именно такая:

```text
DINO v33 TOP-5
       │
       ├── GLOBAL score × 10.0
       │
       ├── если margin < 0.02:
       │       │
       │       └── SUB-RERANK
       │             только TOP1 + TOP2
       │             │
       │             ├── sub similarity > 0.88
       │             ├── > 0.92 → bonus 2.5
       │             └── иначе → bonus 1.0
       │
       └── SEQUENCE CONSENSUS
             левый top1 == правый top1
             → +3.0
       
       ↓
   FINAL DECISION
       
   DINO TOP1 = default
       
   менять только если:
       candidate != old
       AND
       gain > 1.5
       
       ↓
   FINAL best
```

### Параметры v12

```python
MARGIN_LIMIT = 0.02

GLOBAL_WEIGHT = 10.0
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0
```

Но здесь есть **важный нюанс**: в фактическом коде v12 две константы сейчас **не используются напрямую**:

```python
SUB_WEIGHT = 2.5
NEIGHBOR_WEIGHT = 6.0
```

Вместо них фактически зашиты:

```python
if sim > 0.92:
    bonus = 2.5
else:
    bonus = 1.0
```

и:

```python
scores[left_fp] += 3.0
```

То есть при переносе **нельзя просто механически использовать значения констант**, нужно сохранить фактическое поведение v12.

---

## Самое важное для нашей кнопки

Сейчас `benchmark_hybrid_v12_full.py` работает не с исходными фотографиями напрямую.

Он ожидает уже готовый:

```text
data/output/benchmark_sub_exp/benchmark.json
```

и берёт оттуда:

```text
file
top1
top2
top3
top4
top5
top*_score
margin
```

То есть это **второй этап распознавания**.

Рабочая цепочка должна быть:

```text
              ФОТО
                │
                ▼
        DINO v33 recognizer
                │
                ▼
          TOP-5 + scores
                │
                ▼
       ┌─────────────────┐
       │  HYBRID v12      │
       │                  │
       │ global           │
       │ sub-rerank       │
       │ neighbors        │
       └────────┬────────┘
                │
                ▼
           FINAL best_id
                │
                ▼
             SORT
                │
                ▼
             QWEN
```

### И ещё один нюанс

В комментарии написано:

```text
FINAL DECISION V09
```

а файл называется:

```text
benchmark_hybrid_v12_full.py
```

Это нормально: **v12 — это версия эксперимента/сборки, а внутри финальная логика решения осталась от v09**.

---

## Поэтому сейчас мы НЕ должны подключать `sort_test_and_report_v2.py` напрямую к `recognizer.py`

Иначе получится:

```text
recognizer
   ↓
best_id
   ↓
sort
```

и мы потеряем Hybrid/Rerank.

Нужно сделать:

```text
recognizer
   ↓
TOP-5
   ↓
hybrid_v12
   ↓
final best_id
   ↓
sort
```

И только **после этого** передавать результат Qwen.

---

### Следующий шаг

Теперь нам нужно посмотреть **формат результата `recognizer`**, который v12 использует как `benchmark.json`.

Дай:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
echo "================ RECOGNIZER MAIN ================" && \
sed -n '1,520p' app/core/recognizer.py && \
echo "================ BENCHMARK INPUT SAMPLE ================" && \
python - <<'PY'
import json
from pathlib import Path

p = Path("data/output/benchmark_sub_exp/benchmark.json")

data = json.loads(p.read_text(encoding="utf-8"))

print("keys:", data.keys())
print("results:", len(data["results"]))

if data["results"]:
    print("\nFIRST RESULT:")
    import pprint
    pprint.pp(data["results"][0])
PY
```

**После этого мы уже сможем точно состыковать `recognizer → v12 → sorter`, не меняя сам алгоритм v33 и не меняя алгоритм Hybrid/Rerank v12.**

---

### 👤 **User** — 2026-08-16 22:08:38

Отлично. Тогда **фиксируем Hybrid v12 как контрольную стабильную версию**.

Текущее состояние:

```
scene_fingerprint_mvp_v02
```

BASE:

DINOv2 v33 fingerprints

RERANK:

Hybrid v12

TEST:

256 images

RESULT:

247 / 256 совпали автоматически

9 изменений hybrid подтверждены

визуальная проверка:

≈97.3% правильной классификации

Что сохраняем как эталон:

```
data/output/full_recognize_hybrid_v12_test.json
```

data/output/check\_visual/hybrid\_v12/

scripts/benchmark\_hybrid\_v12.py

fingerprints/\*\_v33

Дальше лучше не трогать веса и логику.

---

### 🤖 **Assistant** — 2026-08-16 22:08:40

Да. **Hybrid v12 фиксируем как контрольную стабильную версию.** Веса и алгоритм больше не меняем.

### Эталон проекта

```text
scene_fingerprint_mvp_v02
```

**BASE**
```text
DINOv2
fingerprints *_v33
```

**RERANK**
```text
Hybrid v12
```

**TEST**
```text
256 images
```

**RESULT**
```text
247 / 256 - совпали автоматически
9 - изменены Hybrid и подтверждены визуально
≈97.3% - правильная классификация
```

### Что считаем frozen

```text
data/output/full_recognize_hybrid_v12_test.json
data/output/check_visual/hybrid_v12/
scripts/benchmark_hybrid_v12.py
data/fingerprints/*_v33/
```

И отдельно: показанный тобой `benchmark_hybrid_v12_full.py` - это **важная рабочая реализация Hybrid/Rerank**, её тоже не трогаем без отдельного эксперимента.

### Правило на будущее

Теперь любые новые улучшения делаем **только как отдельные версии**:

```text
v13
v14
...
```

и сравниваем с:

```text
Hybrid v12 = CONTROL
```

То есть **v12 не оптимизируем, не переписываем и не подстраиваем под новые тесты**. Это наша контрольная точка для всего дальнейшего развития системы.

---

### 👤 **User** — 2026-08-16 22:09:21

да

---

### 🤖 **Assistant** — 2026-08-16 22:09:22

Зафиксировали. **Hybrid v12 — контрольный эталон.**

Дальше работаем поверх него, не изменяя базовую логику и веса.

---

### 👤 **User** — 2026-08-16 22:09:28

ок

---

### 🤖 **Assistant** — 2026-08-16 22:09:29

Ок. Двигаемся дальше от зафиксированного **Hybrid v12**.

---

### 👤 **User** — 2026-08-16 22:09:37

поехали

---

### 🤖 **Assistant** — 2026-08-16 22:09:37

> **Remembering**
>
>
> **Reviewed scene-fingerprint roadmaps and connected DINOv2 milestones to Qwen3-VL**
>
> 
>
> Worked for 5s

Поехали.

Сейчас правильная точка старта такая:

```text
DINOv2 v33
      ↓
Hybrid v12 / Rerank
      ↓
адрес
      ↓
сортировка фотографий
      ↓
Qwen3-VL 4B
      ↓
метаданные / поиск / база
```

### Шаг 1 — не трогаем распознавание

`v33 + Hybrid v12` считаем **замороженным ядром**.

Наша задача теперь — **подключить это ядро к рабочей операции «Обработка фото» в техническом разделе**.

Сейчас кнопка:

```text
▶ ЗАПУСТИТЬ ОБРАБОТКУ
```

ещё ничего не запускает — там только:

```python
ui.notify(
    "Запуск обработки будет подключён следующим этапом"
)
```

И именно это сейчас логично сделать.

### Шаг 2 — рабочий pipeline

Кнопка должна запускать:

```text
Источник фотографий
        │
        ▼
DINOv2 v33
        │
        ▼
Hybrid v12
        │
        ▼
best_id
        │
        ▼
создание папки адреса
        │
        ▼
копирование фото
        │
        ▼
Qwen3-VL 4B
```

Причём **не будем переносить Hybrid-логику в веб-компоненты**.

Лучше сделать отдельный backend-сервис/runner, который вызывает уже проверенные скрипты и возвращает результат интерфейсу.

### Шаг 3 — сначала проверяем существующий sorter

У нас уже есть:

```text
scripts/sort_test_and_report_v2.py
```

и в нём явно зафиксирована логика:

```python
# ВСЕГДА используем best_id = первый кандидат.
assigned_id = item.get("best_id")
```

Но для production-пайплайна нужно проверить, **какой именно JSON должен подаваться sorter'у после Hybrid v12**, чтобы случайно не потерять Hybrid-решение.

Поэтому следующий шаг предлагаю сделать чисто технический:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
cat -n scripts/sort_test_and_report_v2.py | sed -n '1,390p'
```

После этого мы свяжем:

**Hybrid v12 → JSON → sorter → папки адресов**

и только потом подключим кнопку.

Это безопасный порядок: **эталонный recognizer не трогаем вообще.**

---

### 👤 **User** — 2026-08-16 22:10:16

int_mvp_v02 && \
cat -n scripts/sort_test_and_report_v2.py | sed -n '1,390p'
     1	#!/usr/bin/env python3
     2	
     3	import csv
     4	import json
     5	import os
     6	import shutil
     7	import subprocess
     8	import time
     9	from pathlib import Path
    10	from collections import Counter
    11	
    12	import psutil
    13	
    14	
    15	PROJECT = Path(__file__).resolve().parent.parent
    16	
    17	INPUT_DIR = PROJECT / "data/input/test"
    18	OUTPUT_DIR = PROJECT / "data/output/test_sorted_v2"
    19	
    20	FINGERPRINTS = [
    21	    f"{i}_v33"
    22	    for i in range(78, 96)
    23	]
    24	
    25	RECOGNITION_JSON = OUTPUT_DIR / "recognition.json"
    26	REPORT_CSV = OUTPUT_DIR / "report.csv"
    27	REPORT_JSON = OUTPUT_DIR / "report.json"
    28	STATISTICS_JSON = OUTPUT_DIR / "statistics.json"
    29	
    30	
    31	def gpu_stats():
    32	    try:
    33	        result = subprocess.run(
    34	            [
    35	                "nvidia-smi",
    36	                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
    37	                "--format=csv,noheader,nounits",
    38	            ],
    39	            capture_output=True,
    40	            text=True,
    41	            timeout=3,
    42	        )
    43	
    44	        line = result.stdout.strip().splitlines()[0]
    45	        parts = [x.strip() for x in line.split(",")]
    46	
    47	        return {
    48	            "gpu_name": parts[0],
    49	            "gpu_utilization_percent": float(parts[1]),
    50	            "gpu_memory_used_mb": float(parts[2]),
    51	            "gpu_memory_total_mb": float(parts[3]),
    52	        }
    53	
    54	    except Exception:
    55	        return {
    56	            "gpu_name": None,
    57	            "gpu_utilization_percent": None,
    58	            "gpu_memory_used_mb": None,
    59	            "gpu_memory_total_mb": None,
    60	        }
    61	
    62	
    63	def find_json(text):
    64	    """
    65	    Find the actual JSON array, ignoring messages such as:
    66	        [SceneEmbedder]
    67	        [Recognizer]
    68	    """
    69	
    70	    decoder = json.JSONDecoder()
    71	
    72	    for i, ch in enumerate(text):
    73	        if ch != "[":
    74	            continue
    75	
    76	        candidate = text[i:]
    77	
    78	        try:
    79	            obj, end = decoder.raw_decode(candidate)
    80	
    81	            if isinstance(obj, list):
    82	                return obj
    83	
    84	        except json.JSONDecodeError:
    85	            pass
    86	
    87	    raise RuntimeError("Не удалось найти JSON-массив в выводе recognition")
    88	
    89	
    90	def run_recognition():
    91	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    92	
    93	    fp_arg = ",".join(FINGERPRINTS)
    94	
    95	    cmd = [
    96	        "uv",
    97	        "run",
    98	        "scene-fingerprint",
    99	        "recognize",
   100	        str(INPUT_DIR),
   101	        "--top-k",
   102	        "5",
   103	        "--threshold",
   104	        "0.0",
   105	        "--fingerprints",
   106	        fp_arg,
   107	        "--json",
   108	    ]
   109	
   110	    print("=" * 80)
   111	    print("RUNNING RECOGNITION")
   112	    print("=" * 80)
   113	
   114	    print("Input:", INPUT_DIR)
   115	    print("Fingerprints:", ", ".join(FINGERPRINTS))
   116	    print()
   117	
   118	    start = time.perf_counter()
   119	
   120	    process = subprocess.run(
   121	        cmd,
   122	        cwd=PROJECT,
   123	        capture_output=True,
   124	        text=True,
   125	    )
   126	
   127	    elapsed = time.perf_counter() - start
   128	
   129	    if process.returncode != 0:
   130	        print(process.stdout)
   131	        print(process.stderr)
   132	        raise RuntimeError(
   133	            f"recognize завершился с кодом {process.returncode}"
   134	        )
   135	
   136	    combined = process.stdout + "\n" + process.stderr
   137	
   138	    data = find_json(combined)
   139	
   140	    RECOGNITION_JSON.write_text(
   141	        json.dumps(data, ensure_ascii=False, indent=2),
   142	        encoding="utf-8",
   143	    )
   144	
   145	    return data, elapsed
   146	
   147	
   148	def copy_images(data):
   149	    print()
   150	    print("=" * 80)
   151	    print("SORTING")
   152	    print("=" * 80)
   153	
   154	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
   155	
   156	    rows = []
   157	
   158	    counters = Counter()
   159	
   160	    for item in data:
   161	        source = Path(item["file"])
   162	
   163	        # Главный принцип:
   164	        # ВСЕГДА используем best_id = первый кандидат.
   165	        assigned_id = item.get("best_id")
   166	
   167	        if not assigned_id:
   168	            continue
   169	
   170	        destination_dir = OUTPUT_DIR / assigned_id
   171	        destination_dir.mkdir(parents=True, exist_ok=True)
   172	
   173	        destination = destination_dir / source.name
   174	
   175	        shutil.copy2(source, destination)
   176	
   177	        counters[assigned_id] += 1
   178	
   179	        candidates = item.get("candidates", [])
   180	
   181	        row = {
   182	            "file": str(source),
   183	            "filename": source.name,
   184	            "assigned_id": assigned_id,
   185	            "score": item.get("score"),
   186	            "second_score": item.get("second_score"),
   187	            "margin": item.get("margin"),
   188	            "confidence": item.get("confidence"),
   189	            "status": item.get("status"),
   190	            "best_image": item.get("best_image"),
   191	            "best_image_score": item.get("best_image_score"),
   192	            "global": None,
   193	            "environment": None,
   194	            "color": None,
   195	            "spatial": None,
   196	            "candidate_2": None,
   197	            "candidate_2_score": None,
   198	            "candidate_3": None,
   199	            "candidate_3_score": None,
   200	            "candidate_4": None,
   201	            "candidate_4_score": None,
   202	            "candidate_5": None,
   203	            "candidate_5_score": None,
   204	        }
   205	
   206	        if candidates:
   207	            c = candidates[0]
   208	
   209	            row["global"] = c.get("global")
   210	            row["environment"] = c.get("environment")
   211	            row["color"] = c.get("color")
   212	            row["spatial"] = c.get("spatial")
   213	
   214	        for n in range(1, min(5, len(candidates))):
   215	            c = candidates[n]
   216	
   217	            row[f"candidate_{n+1}"] = c.get("id")
   218	            row[f"candidate_{n+1}_score"] = c.get("score")
   219	
   220	        rows.append(row)
   221	
   222	    print()
   223	
   224	    for k in sorted(counters, key=lambda x: int(x.split("_")[0])):
   225	        print(f"{k:10s} {counters[k]:4d}")
   226	
   227	    return rows, counters
   228	
   229	
   230	def write_reports(rows, counters, recognition_time):
   231	    fields = [
   232	        "file",
   233	        "filename",
   234	        "assigned_id",
   235	        "score",
   236	        "second_score",
   237	        "margin",
   238	        "confidence",
   239	        "status",
   240	        "best_image",
   241	        "best_image_score",
   242	        "global",
   243	        "environment",
   244	        "color",
   245	        "spatial",
   246	        "candidate_2",
   247	        "candidate_2_score",
   248	        "candidate_3",
   249	        "candidate_3_score",
   250	        "candidate_4",
   251	        "candidate_4_score",
   252	        "candidate_5",
   253	        "candidate_5_score",
   254	    ]
   255	
   256	    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
   257	        writer = csv.DictWriter(f, fieldnames=fields)
   258	        writer.writeheader()
   259	        writer.writerows(rows)
   260	
   261	    scores = [
   262	        float(x["score"])
   263	        for x in rows
   264	        if x["score"] is not None
   265	    ]
   266	
   267	    margins = [
   268	        float(x["margin"])
   269	        for x in rows
   270	        if x["margin"] is not None
   271	    ]
   272	
   273	    status_counter = Counter(
   274	        x["status"]
   275	        for x in rows
   276	        if x["status"]
   277	    )
   278	
   279	    confidence_counter = Counter(
   280	        x["confidence"]
   281	        for x in rows
   282	        if x["confidence"]
   283	    )
   284	
   285	    process = psutil.Process(os.getpid())
   286	
   287	    stats = {
   288	        "total_images": len(rows),
   289	
   290	        "recognition_time_seconds": recognition_time,
   291	
   292	        "images_per_second":
   293	            len(rows) / recognition_time
   294	            if recognition_time > 0 else None,
   295	
   296	        "milliseconds_per_image":
   297	            recognition_time * 1000 / len(rows)
   298	            if rows else None,
   299	
   300	        "score": {
   301	            "min": min(scores) if scores else None,
   302	            "mean": sum(scores) / len(scores) if scores else None,
   303	            "max": max(scores) if scores else None,
   304	        },
   305	
   306	        "margin": {
   307	            "min": min(margins) if margins else None,
   308	            "mean": sum(margins) / len(margins) if margins else None,
   309	            "max": max(margins) if margins else None,
   310	        },
   311	
   312	        "status": dict(status_counter),
   313	        "confidence": dict(confidence_counter),
   314	
   315	        "assigned": dict(counters),
   316	
   317	        "cpu": {
   318	            "logical_cpus": psutil.cpu_count(),
   319	            "process_cpu_percent": process.cpu_percent(interval=0.5),
   320	        },
   321	
   322	        "ram": {
   323	            "total_mb":
   324	                psutil.virtual_memory().total / 1024 / 1024,
   325	
   326	            "used_mb":
   327	                psutil.virtual_memory().used / 1024 / 1024,
   328	
   329	            "available_mb":
   330	                psutil.virtual_memory().available / 1024 / 1024,
   331	
   332	            "process_rss_mb":
   333	                process.memory_info().rss / 1024 / 1024,
   334	        },
   335	
   336	        "gpu": gpu_stats(),
   337	    }
   338	
   339	    REPORT_JSON.write_text(
   340	        json.dumps(rows, ensure_ascii=False, indent=2),
   341	        encoding="utf-8",
   342	    )
   343	
   344	    STATISTICS_JSON.write_text(
   345	        json.dumps(stats, ensure_ascii=False, indent=2),
   346	        encoding="utf-8",
   347	    )
   348	
   349	    return stats
   350	
   351	
   352	def main():
   353	    print()
   354	    print("=" * 80)
   355	    print("SCENE FINGERPRINT TEST SORTER V2")
   356	    print("=" * 80)
   357	
   358	    if not INPUT_DIR.exists():
   359	        raise RuntimeError(f"Нет папки: {INPUT_DIR}")
   360	
   361	    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
   362	
   363	    start_total = time.perf_counter()
   364	
   365	    data, recognition_time = run_recognition()
   366	
   367	    rows, counters = copy_images(data)
   368	
   369	    stats = write_reports(
   370	        rows,
   371	        counters,
   372	        recognition_time,
   373	    )
   374	
   375	    total_time = time.perf_counter() - start_total
   376	
   377	    stats["total_wall_time_seconds"] = total_time
   378	
   379	    STATISTICS_JSON.write_text(
   380	        json.dumps(stats, ensure_ascii=False, indent=2),
   381	        encoding="utf-8",
   382	    )
   383	
   384	    print()
   385	    print("=" * 80)
   386	    print("STATISTICS")
   387	    print("=" * 80)
   388	
   389	    print(f"Images:             {stats['total_images']}")
   390	    print(f"Recognition time:   {recognition_time:.2f} sec")
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-16 22:10:17

Да, теперь картина ясная. И здесь есть **важный момент**.

Текущий `sort_test_and_report_v2.py` **не является Hybrid sorter'ом**.

Он запускает обычный:

```text
scene-fingerprint recognize
        ↓
best_id
        ↓
copy
```

То есть строки 90–145 вызывают обычный CLI `recognize`, а строки 160–175 просто берут:

```python
assigned_id = item.get("best_id")
```

Поэтому если мы подключим его напрямую к веб-кнопке, **Hybrid v12 вообще не будет участвовать**.

### Правильная архитектура

Нам нельзя переделывать этот старый тестовый sorter так, чтобы в него запихнуть Hybrid v12.

Лучше разделить:

```text
                    ┌── DINO v33 recognize ──┐
                    │                         │
ФОТО → recognition ┤                         ├→ Hybrid v12 → FINAL best_id
                    │                         │
                    └── top1..top5 + margin ─┘
                                                    ↓
                                              SORTER
                                                    ↓
                                      /78_v33
                                      /79_v33
                                      ...
                                      /95_v33
```

При этом существующий sorter можно оставить как **старый тестовый инструмент**.

---

## Что особенно важно в Hybrid v12

У него вход:

```text
benchmark.json
```

и он использует уже рассчитанные:

```text
top1
top2
top3
top4
top5
top*_score
margin
file
```

А затем Hybrid меняет:

```text
old = DINO top1
```

на:

```text
new = Hybrid decision
```

Но в его текущем JSON:

```text
full_recognize_hybrid_v12_test.json
```

результат называется:

```json
{
    "old": "...",
    "new": "..."
}
```

а production sorter ожидает:

```json
{
    "best_id": "..."
}
```

### Значит, нужен тонкий production-адаптер

Не менять Hybrid.

Не менять v33.

Не менять `sort_test_and_report_v2.py`.

А сделать отдельный слой:

```text
app/pipeline/
    recognition.py
    hybrid.py
    sorter.py
```

или аналогичную структуру.

Он будет:

1. запускать DINO v33;
2. получать top-5;
3. передавать данные в **неизменённую логику Hybrid v12**;
4. получать финальный `best_id`;
5. копировать фотографии;
6. формировать отчёты.

---

### И ещё один нюанс

В `benchmark_hybrid_v12_full.py` сейчас жёстко прописано:

```python
BENCHMARK = data/output/benchmark_sub_exp/benchmark.json
SUB_DIR = data/fingerprints_sub_exp
OUT = data/output/full_recognize_hybrid_v12_test.json
```

Для теста это нормально.

Для рабочей кнопки — **нет**.

Нам потребуется вынести только **вход/выход** в параметры:

```text
input_dir
output_dir
```

а саму формулу Hybrid v12 оставить **байт-в-байт логически той же**.

То есть:

```text
            FROZEN
              │
       Hybrid v12 logic
              │
       ───────────────
       НЕ МЕНЯЕМ ВЕСА
       НЕ МЕНЯЕМ ПОРОГИ
       НЕ МЕНЯЕМ RULES
       ───────────────
              │
              ▼
       production runner
```

И это, на мой взгляд, гораздо безопаснее.

**Следующий шаг:** я бы сейчас посмотрел полный `benchmark.json` и формат результата `recognize --json`, чтобы точно состыковать Hybrid v12 с production sorter'ом без изменения самого алгоритма.

---

### 👤 **User** — 2026-08-16 22:11:07

дава

---

