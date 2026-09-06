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
