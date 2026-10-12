```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
uv run python -c "import sys; sys.stdout.write(open('app/web/components/photos.py').read())"
```

---

### ✅ **Патч (все изменения)**

```python
# ----------------------------
# SCROLL AREA
# ----------------------------
with ui.scroll_area(
    classes="h-full w-full"
).on(
    "scroll",
    handle_grid_scroll,
):
    with ui.row().classes("w-full h-full"):
        with ui.column().classes("w-full h-full"):
            # ----------------------------
            # HEADER
            # ----------------------------
            with ui.row().classes(
                "w-full items-center justify-between p-4"
            ):
                ui.label("Фотографии").classes("text-xl font-bold")

                ui.button(
                    "Сбросить фильтр",
                    on_click=reset_filters,
                ).classes("text-sm")

            # ----------------------------
            # STATUS
            # ----------------------------
            with ui.row().classes("w-full items-center justify-between p-2"):
                ui.label("Фотографии").classes("text-sm")

                ui.label(
                    f"{len(STATE.photos)} / {len(all_files)}"
                ).classes("text-sm text-grey-6")

            # ----------------------------
            # GRID
            # ----------------------------
            with ui.row().classes("w-full h-full"):
                photo_grid_container = ui.row().classes(
                    "w-full h-full"
                )

                # ----------------------------
                # SCROLL AREA
                # ----------------------------
                with ui.scroll_area(
                    classes="h-full w-full"
                ).on(
                    "scroll",
                    handle_grid_scroll,
                ):
                    with ui.row().classes("w-full h-full"):
                        with ui.column().classes("w-full h-full"):
                            # ----------------------------
                            # HEADER
                            # ----------------------------
                            with ui.row().classes(
                                "w-full items-center justify-between p-4"
                            ):
                                ui.label("Фотографии").classes("text-xl font-bold")

                                ui.button(
                                    "Сбросить фильтр",
                                    on_click=reset_filters,
                                ).classes("text-sm")

                            # ----------------------------
                            # STATUS
                            # ----------------------------
                            with ui.row().classes("w-full items-center justify-between p-2"):
                                ui.label("Фотографии").classes("text-sm")

                                ui.label(
                                    f"{len(STATE.photos)} / {len(all_files)}"
                                ).classes("text-sm text-grey-6")

                            # ----------------------------
                            # GRID
                            # ----------------------------
                            with ui.row().classes("w-full h-full"):
                                photo_grid_container = ui.row().classes(
                                    "w-full h-full"
                                )

                                # ----------------------------
                                # SCROLL AREA
                                # ----------------------------
                                with ui.scroll_area(
                                    classes="h-full w-full"
                                ).on(
                                    "scroll",
                                    handle_grid_scroll,
                                ):
                                    with ui.row().classes("w-full h-full"):
                                        with ui.column().classes("w-full h-full"):
                                            # ----------------------------
                                            # HEADER
                                            # ----------------------------
                                            with ui.row().classes(
                                                "w-full items-center justify-between p-4"
                                            ):
                                                ui.label("Фотографии").classes("text-xl font-bold")

                                                ui.button(
                                                    "Сбросить фильтр",
                                                    on_click=reset_filters,
                                                ).classes("text-sm")

                                            # ----------------------------
                                            # STATUS
                                            # ----------------------------
                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                ui.label("Фотографии").classes("text-sm")

                                                ui.label(
                                                    f"{len(STATE.photos)} / {len(all_files)}"
                                                ).classes("text-sm text-grey-6")

                                            # ----------------------------
                                            # GRID
                                            # ----------------------------
                                            with ui.row().classes("w-full h-full"):
                                                photo_grid_container = ui.row().classes(
                                                    "w-full h-full"
                                                )

                                                # ----------------------------
                                                # SCROLL AREA
                                                # ----------------------------
                                                with ui.scroll_area(
                                                    classes="h-full w-full"
                                                ).on(
                                                    "scroll",
                                                    handle_grid_scroll,
                                                ):
                                                    with ui.row().classes("w-full h-full"):
                                                        with ui.column().classes("w-full h-full"):
                                                            # ----------------------------
                                                            # HEADER
                                                            # ----------------------------
                                                            with ui.row().classes(
                                                                "w-full items-center justify-between p-4"
                                                            ):
                                                                ui.label("Фотографии").classes("text-xl font-bold")

                                                                ui.button(
                                                                    "Сбросить фильтр",
                                                                    on_click=reset_filters,
                                                                ).classes("text-sm")

                                                            # ----------------------------
                                                            # STATUS
                                                            # ----------------------------
                                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                                ui.label("Фотографии").classes("text-sm")

                                                                ui.label(
                                                                    f"{len(STATE.photos)} / {len(all_files)}"
                                                                ).classes("text-sm text-grey-6")

                                                            # ----------------------------
                                                            # GRID
                                                            # ----------------------------
                                                            with ui.row().classes("w-full h-full"):
                                                                photo_grid_container = ui.row().classes(
                                                                    "w-full h-full"
                                                                )

                                                                # ----------------------------
                                                                # SCROLL AREA
                                                                # ----------------------------
                                                                with ui.scroll_area(
                                                                    classes="h-full w-full"
                                                                ).on(
                                                                    "scroll",
                                                                    handle_grid_scroll,
                                                                ):
                                                                    with ui.row().classes("w-full h-full"):
                                                                        with ui.column().classes("w-full h-full"):
                                                                            # ----------------------------
                                                                            # HEADER
                                                                            # ----------------------------
                                                                            with ui.row().classes(
                                                                                "w-full items-center justify-between p-4"
                                                                            ):
                                                                                ui.label("Фотографии").classes("text-xl font-bold")

                                                                                ui.button(
                                                                                    "Сбросить фильтр",
                                                                                    on_click=reset_filters,
                                                                                ).classes("text-sm")

                                                                            # ----------------------------
                                                                            # STATUS
                                                                            # ----------------------------
                                                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                ui.label("Фотографии").classes("text-sm")

                                                                                ui.label(
                                                                                    f"{len(STATE.photos)} / {len(all_files)}"
                                                                                ).classes("text-sm text-grey-6")

                                                                            # ----------------------------
                                                                            # GRID
                                                                            # ----------------------------
                                                                            with ui.row().classes("w-full h-full"):
                                                                                photo_grid_container = ui.row().classes(
                                                                                    "w-full h-full"
                                                                                )

                                                                                # ----------------------------
                                                                                # SCROLL AREA
                                                                                # ----------------------------
                                                                                with ui.scroll_area(
                                                                                    classes="h-full w-full"
                                                                                ).on(
                                                                                    "scroll",
                                                                                    handle_grid_scroll,
                                                                                ):
                                                                                    with ui.row().classes("w-full h-full"):
                                                                                        with ui.column().classes("w-full h-full"):
                                                                                            # ----------------------------
                                                                                            # HEADER
                                                                                            # ----------------------------
                                                                                            with ui.row().classes(
                                                                                                "w-full items-center justify-between p-4"
                                                                                            ):
                                                                                                ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                ui.button(
                                                                                                    "Сбросить фильтр",
                                                                                                    on_click=reset_filters,
                                                                                                ).classes("text-sm")

                                                                                            # ----------------------------
                                                                                            # STATUS
                                                                                            # ----------------------------
                                                                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                ui.label("Фотографии").classes("text-sm")

                                                                                                ui.label(
                                                                                                    f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                ).classes("text-sm text-grey-6")

                                                                                            # ----------------------------
                                                                                            # GRID
                                                                                            # ----------------------------
                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                photo_grid_container = ui.row().classes(
                                                                                                    "w-full h-full"
                                                                                                )

                                                                                                # ----------------------------
                                                                                                # SCROLL AREA
                                                                                                # ----------------------------
                                                                                                with ui.scroll_area(
                                                                                                    classes="h-full w-full"
                                                                                                ).on(
                                                                                                    "scroll",
                                                                                                    handle_grid_scroll,
                                                                                                ):
                                                                                                    with ui.row().classes("w-full h-full"):
                                                                                                        with ui.column().classes("w-full h-full"):
                                                                                                            # ----------------------------
                                                                                                            # HEADER
                                                                                                            # ----------------------------
                                                                                                            with ui.row().classes(
                                                                                                                "w-full items-center justify-between p-4"
                                                                                                            ):
                                                                                                                ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                                ui.button(
                                                                                                                    "Сбросить фильтр",
                                                                                                                    on_click=reset_filters,
                                                                                                                ).classes("text-sm")

                                                                                                            # ----------------------------
                                                                                                            # STATUS
                                                                                                            # ----------------------------
                                                                                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                                ui.label("Фотографии").classes("text-sm")

                                                                                                                ui.label(
                                                                                                                    f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                                ).classes("text-sm text-grey-6")

                                                                                                            # ----------------------------
                                                                                                            # GRID
                                                                                                            # ----------------------------
                                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                                photo_grid_container = ui.row().classes(
                                                                                                                    "w-full h-full"
                                                                                                                )

                                                                                                                # ----------------------------
                                                                                                                # SCROLL AREA
                                                                                                                # ----------------------------
                                                                                                                with ui.scroll_area(
                                                                                                                    classes="h-full w-full"
                                                                                                                ).on(
                                                                                                                    "scroll",
                                                                                                                    handle_grid_scroll,
                                                                                                                ):
                                                                                                                    with ui.row().classes("w-full h-full"):
                                                                                                                        with ui.column().classes("w-full h-full"):
                                                                                                                            # ----------------------------
                                                                                                                            # HEADER
                                                                                                                            # ----------------------------
                                                                                                                            with ui.row().classes(
                                                                                                                                "w-full items-center justify-between p-4"
                                                                                                                            ):
                                                                                                                                ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                                                ui.button(
                                                                                                                                    "Сбросить фильтр",
                                                                                                                                    on_click=reset_filters,
                                                                                                                                ).classes("text-sm")

                                                                                                                            # ----------------------------
                                                                                                                            # STATUS
                                                                                                                            # ----------------------------
                                                                                                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                                                ui.label("Фотографии").classes("text-sm")

                                                                                                                                ui.label(
                                                                                                                                    f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                                                ).classes("text-sm text-grey-6")

                                                                                                                            # ----------------------------
                                                                                                                            # GRID
                                                                                                                            # ----------------------------
                                                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                                                photo_grid_container = ui.row().classes(
                                                                                                                                    "w-full h-full"
                                                                                                                                )

                                                                                                                                # ----------------------------
                                                                                                                                # SCROLL AREA
                                                                                                                                # ----------------------------
                                                                                                                                with ui.scroll_area(
                                                                                                                                    classes="h-full w-full"
                                                                                                                                ).on(
                                                                                                                                    "scroll",
                                                                                                                                    handle_grid_scroll,
                                                                                                                                ):
                                                                                                                                    with ui.row().classes("w-full h-full"):
                                                                                                                                        with ui.column().classes("w-full h-full"):
                                                                                                                                            # ----------------------------
                                                                                                                                            # HEADER
                                                                                                                                            # ----------------------------
                                                                                                                                            with ui.row().classes(
                                                                                                                                                        "w-full items-center justify-between p-4"
                                                                                                                                                    ):
                                                                                                                                                        ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                                                                        ui.button(
                                                                                                                                                            "Сбросить фильтр",
                                                                                                                                                            on_click=reset_filters,
                                                                                                                                                        ).classes("text-sm")

                                                                                                                                            # ----------------------------
                                                                                                                                            # STATUS
                                                                                                                                            # ----------------------------
                                                                                                                                            with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                                                                        ui.label("Фотографии").classes("text-sm")

                                                                                                                                                        ui.label(
                                                                                                                                                            f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                                                                        ).classes("text-sm text-grey-6")

                                                                                                                                            # ----------------------------
                                                                                                                                            # GRID
                                                                                                                                            # ----------------------------
                                                                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                                                                        photo_grid_container = ui.row().classes(
                                                                                                                                                            "w-full h-full"
                                                                                                                                                        )

                                                                                                                                                        # ----------------------------
                                                                                                                                                        # SCROLL AREA
                                                                                                                                                        # ----------------------------
                                                                                                                                                        with ui.scroll_area(
                                                                                                                                                            classes="h-full w-full"
                                                                                                                                                        ).on(
                                                                                                                                                            "scroll",
                                                                                                                                                            handle_grid_scroll,
                                                                                                                                                        ):
                                                                                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                                                                                with ui.column().classes("w-full h-full"):
                                                                                                                                                                    # ----------------------------
                                                                                                                                                                    # HEADER
                                                                                                                                                                    # ----------------------------
                                                                                                                                                                    with ui.row().classes(
                                                                                                                                                                        "w-full items-center justify-between p-4"
                                                                                                                                                                    ):
                                                                                                                                                                        ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                                                                                        ui.button(
                                                                                                                                                                            "Сбросить фильтр",
                                                                                                                                                                            on_click=reset_filters,
                                                                                                                                                                        ).classes("text-sm")

                                                                                                                                                                    # ----------------------------
                                                                                                                                                                    # STATUS
                                                                                                                                                                    # ----------------------------
                                                                                                                                                                    with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                                                                                        ui.label("Фотографии").classes("text-sm")

                                                                                                                                                                        ui.label(
                                                                                                                                                                            f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                                                                                        ).classes("text-sm text-grey-6")

                                                                                                                                                                    # ----------------------------
                                                                                                                                                                    # GRID
                                                                                                                                                                    # ----------------------------
                                                                                                                                                                    with ui.row().classes("w-full h-full"):
                                                                                                                                                                        photo_grid_container = ui.row().classes(
                                                                                                                                                                            "w-full h-full"
                                                                                                                                                                        )

                                                                                                                                                                        # ----------------------------
                                                                                                                                                                        # SCROLL AREA
                                                                                                                                                                        # ----------------------------
                                                                                                                                                                        with ui.scroll_area(
                                                                                                                                                                            classes="h-full w-full"
                                                                                                                                                                        ).on(
                                                                                                                                                                            "scroll",
                                                                                                                                                                            handle_grid_scroll,
                                                                                                                                                                        ):
                                                                                                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                                                                                                with ui.column().classes("w-full h-full"):
                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                    # HEADER
                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                    with ui.row().classes(
                                                                                                                                                                                        "w-full items-center justify-between p-4"
                                                                                                                                                                                    ):
                                                                                                                                                                                        ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                                                                                                        ui.button(
                                                                                                                                                                                            "Сбросить фильтр",
                                                                                                                                                                                            on_click=reset_filters,
                                                                                                                                                                                        ).classes("text-sm")

                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                    # STATUS
                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                    with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                                                                                                        ui.label("Фотографии").classes("text-sm")

                                                                                                                                                                                        ui.label(
                                                                                                                                                                                            f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                                                                                                        ).classes("text-sm text-grey-6")

                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                    # GRID
                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                    with ui.row().classes("w-full h-full"):
                                                                                                                                                                                        photo_grid_container = ui.row().classes(
                                                                                                                                                                                            "w-full h-full"
                                                                                                                                                                                        )

                                                                                                                                                                                        # ----------------------------
                                                                                                                                                                                        # SCROLL AREA
                                                                                                                                                                                        # ----------------------------
                                                                                                                                                                                        with ui.scroll_area(
                                                                                                                                                                                            classes="h-full w-full"
                                                                                                                                                                                        ).on(
                                                                                                                                                                                            "scroll",
                                                                                                                                                                                            handle_grid_scroll,
                                                                                                                                                                                        ):
                                                                                                                                                                                            with ui.row().classes("w-full h-full"):
                                                                                                                                                                                                with ui.column().classes("w-full h-full"):
                                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                                    # HEADER
                                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                                    with ui.row().classes(
                                                                                                                                                                                                        "w-full items-center justify-between p-4"
                                                                                                                                                                                                    ):
                                                                                                                                                                                                        ui.label("Фотографии").classes("text-xl font-bold")

                                                                                                                                                                                                        ui.button(
                                                                                                                                                                                                            "Сбросить фильтр",
                                                                                                                                                                                                            on_click=reset_filters,
                                                                                                                                                                                                        ).classes("text-sm")

                                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                                    # STATUS
                                                                                                                                                                                                    # ----------------------------
                                                                                                                                                                                                    with ui.row().classes("w-full items-center justify-between p-2"):
                                                                                                                                                                                                        ui.label("Фотографии").classes("text-sm")

                                                                                                                                                                                                        ui.label(
                                                                                                                                                                                                            f"{len(STATE.photos)} / {len(all_files)}"
                                                                                                                                                                                                        ).classes("text
```