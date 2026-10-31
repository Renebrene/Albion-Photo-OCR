from app.qwen.crop_aggregation import aggregate_crop_fields


def test_crop_aggregation_uses_alias_normalized_majority_per_kind():
    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"client": "ООО Лента", "brand": "Brand X", "description": "Щит Лента", "tags": ["food"]}},
            {"crop_index": 1, "fields": {"client": "Lenta shop", "brand": "Brand Y", "description": "Щит Brand Y", "tags": ["sale"]}},
            {"crop_index": 2, "fields": {"client": "Lenta shop", "brand": "Brand Y", "description": "Щит Brand Y рядом", "tags": ["sale", "2026"]}},
        ],
        alias_rows=[
            {"alias": "ООО Лента", "canonical": "Lenta shop", "kind": "client"},
            {"alias": "Brand Y", "canonical": "Brand X", "kind": "brand"},
        ],
    )
    assert result["client"] == "Lenta shop"
    assert result["brand"] == "Brand X"
    assert result["client_crop_counts"] == {"Lenta shop": 3}
    assert result["brand_crop_counts"] == {"Brand X": 3}
    assert "2026" in result["tags"]
    assert "Щит Лента" in result["description"]
    assert "Щит Brand Y" in result["description"]


def test_crop_aggregation_ties_prefer_largest_crop_value():
    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"client": "Primary", "brand": "Main", "tags": []}},
            {"crop_index": 1, "fields": {"client": "Other", "brand": "Alt", "tags": []}},
        ]
    )
    assert result["client"] == "Primary"
    assert result["brand"] == "Main"


def test_crop_aggregation_prefers_frequent_brand_over_primary_crop():
    """Бигфест чаще в базе — он и становится брендом карточки, не Sunlight."""

    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"brand": "Sunlight", "tags": []}},
            {"crop_index": 1, "fields": {"brand": "Big Fest", "tags": []}},
        ],
        alias_rows=[{"alias": "Big Fest", "canonical": "Бигфест", "kind": "brand"}],
        frequencies={"brand": {"sunlight": 95, "бигфест": 159}},
    )

    assert result["brand"] == "Бигфест"
    # Проигравший рекламодатель остаётся в тегах.
    assert "Sunlight" in result["tags"]


def test_crop_aggregation_counts_client_reading_as_brand_candidate():
    """Полный кадр положил Бигфест в client — он всё равно участвует в бренде."""

    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"brand": "Sunlight", "tags": []}},
            {"crop_index": 1, "fields": {"brand": "СК10", "tags": []}},
            {"crop_index": 2, "fields": {
                "client": "БИГФЕСТ", "brand": "SUNLIGHT", "tags": [],
            }},
        ],
        frequencies={
            "brand": {"sunlight": 98, "ск10": 155, "бигфест": 232},
            "display": {"бигфест": "Бигфест"},
        },
    )

    assert result["brand"] == "Бигфест"
    # Клиент тоже выбран из client-чтения полного кадра.
    assert result["client"] == "Бигфест"


def test_crop_aggregation_prefers_combined_mention_frequency():
    """Лента чаще в базе с учётом тегов — она побеждает Sunlight."""

    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"brand": "Sunlight", "tags": []}},
            {"crop_index": 1, "fields": {"brand": "Лента", "tags": ["Лента"]}},
        ],
        frequencies={"brand": {"sunlight": 117, "лента": 171}},
    )

    assert result["brand"] == "Лента"
    assert "Sunlight" in result["tags"]


def test_crop_aggregation_merges_spacing_variants_in_frequency():
    """«Бигфест» и «Биг фест» без алиаса складываются в один голос."""

    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"brand": "Sunlight", "tags": []}},
            {"crop_index": 1, "fields": {"brand": "Бигфест", "tags": []}},
        ],
        frequencies={
            "brand": {"sunlight": 95, "бигфест": 128, "биг фест": 29},
        },
    )

    assert result["brand"] == "Бигфест"


def test_crop_aggregation_without_frequency_keeps_primary_tie_break():
    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "fields": {"brand": "Sunlight", "tags": []}},
            {"crop_index": 1, "fields": {"brand": "Бигфест", "tags": []}},
        ],
        frequencies={"brand": {"sunlight": 95, "бигфест": 159}},
        global_frequency=False,
    )

    assert result["brand"] == "Sunlight"


def test_crop_aggregation_ignores_failed_crops_and_deduplicates_tags():
    result = aggregate_crop_fields(
        [
            {"crop_index": 0, "status": "DONE", "fields": {"client": "A", "brand": "X", "description": "A", "tags": ["promo", "2026"]}},
            {"crop_index": 1, "status": "FAILED", "fields": {"client": "B", "brand": "Y", "description": "B", "tags": ["other"]}},
            {"crop_index": 2, "status": "DONE", "fields": {"client": "A", "brand": "X", "description": "A", "tags": ["Promo", "second"]}},
        ]
    )
    assert result["client"] == "A"
    assert result["brand"] == "X"
    assert result["description"] == "A"
    # Проигравший клиент/бренд сохраняется в тегах, выигравший — в полях.
    assert result["tags"] == ["promo", "2026", "second"]
    assert result["crop_observations"] == 2
