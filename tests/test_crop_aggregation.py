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
