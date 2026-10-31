# Context
Рефакторинг и развитие проекта PhotoBAse / Scene Fingerprint. Основные задачи включают исправление критических багов (GRID, видео-источники), оптимизацию производительности базы данных, реализацию серверного сохранения состояний для Менеджера, автоматизацию создания слепков и расширение функционала "Дополнение".

## Objectives
- Устранить ошибки отображения и производительности в Grid.
- Реализовать надежное сохранение состояний пользователя на сервере.
- Автоматизировать генерацию ID и структуру слепков.
- Оптимизировать SQL-запросы для быстрой сортировки и подсчета.

## Implementation Plan

### Phase 1: Critical Fixes & Performance (P0/P1)
- [ ] **GRID Virtualization:** Replace standard rendering with `q-virtual-scroll` to handle large datasets (18k+ items).
- [ ] **Video Source Fix:** Correct logic for identifying source paths in the video grid.
- [ ] **SQL Optimization:**
    - Move sort keys into the base query before `LIMIT` to avoid expensive subqueries.
    - Create a lightweight `count_photos` endpoint to avoid full-table joins.
- [ ] **Worker Offloading:** Ensure heavy image decoding/processing remains in worker threads.

### Phase 2: Manager State & Persistence
- [ ] **Server-side Persistence:** Implement API endpoints to save/restore filters (Period, Sort) and UI modes (Tile/List) for users.
- [ ] **Drag-Boundary Persistence:** Save and restore the layout boundaries between "Подборка", "Адреса", and "Клиенты".
- [ ] **Mode Switching:** Save the selection of upper panel modes (e.g., "Ростов", "Видеоэкраны") in the user profile.

### Phase 3: Fingerprint Management
- [ ] **Auto-ID Generation:** Implement a 20-character ID generator based on folder names and transliteration.
- [ ] **Fingerprint Tabs:** Create UI tabs (Экраны, Малые форматы РнД, etc.) that filter and load data from corresponding XLS files.
- [ ] **Address Schema:** Add "Format" column to the address tables, mapped from XLS.

### Phase 4: Search & Enhancements
- [ ] **Unified Search:** Merge tags, brands, categories, and descriptions into a single search query with de-duplication.
- [ ] **Series Merging ("Дополнение"):** Implement logic to group adjacent frames (±15s) based on name similarity and color harmony.

## Critical Files
- `frontend/src/pages/PhotosGrid.vue`
- `app/api/repository.py`
- `app/api/routes.py`
- `app/api/auth.py`
- `frontend/src/stores/photos.js`

## Verification
- Run unit tests for ID generation and filter logic.
- Benchmark SQL queries (target < 100ms for most operations).
- Perform manual UX verification of virtual scroll and tab switching.
