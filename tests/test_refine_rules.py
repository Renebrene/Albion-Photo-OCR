import pytest

from app.refine import rules


VALID = {
    "schema_version": 1,
    "max_gap_seconds": 10,
    "max_crop_dhash_distance": 6,
    "description_mode": "fill_empty",
    "tags_mode": "union_unique",
    "conflict_mode": "block_group",
}


def test_validate_default_rules():
    assert rules.validate_rules(VALID) == rules.DEFAULT_RULES


def test_old_rules_without_new_fields_get_defaults_not_a_reset():
    """Сохранённые правила старой версии не должны молча сбрасываться."""

    upgraded = rules.validate_rules(VALID)

    assert upgraded["crop_frequency_date_from"] == rules.DEFAULT_RULES["crop_frequency_date_from"]
    assert upgraded["advertiser_dictionary"] == "client_aliases"


@pytest.mark.parametrize(
    "changed",
    [
        {"schema_version": 2},
        {"max_gap_seconds": 31},
        {"max_crop_dhash_distance": 7},
        {"description_mode": "replace"},
        {"tags_mode": "replace"},
        {"conflict_mode": "merge_anyway"},
        {"exec": "print('unsafe')"},
    ],
)
def test_invalid_rules_are_rejected(changed):
    value = dict(VALID)
    value.update(changed)
    with pytest.raises(ValueError):
        rules.validate_rules(value)


def test_parse_rules_json_rejects_invalid_json_and_oversized_payload():
    with pytest.raises(ValueError, match="invalid JSON"):
        rules.parse_rules_json("{")
    with pytest.raises(ValueError, match="maximum size"):
        rules.parse_rules_json(" " * (rules.MAX_RULES_BYTES + 1))


def test_save_rules_increments_version_and_keeps_last_valid(monkeypatch):
    stored = {}

    monkeypatch.setattr(rules.settings_store, "get", lambda key: stored.get(key))
    monkeypatch.setattr(rules.settings_store, "set_value", lambda key, value: stored.__setitem__(key, value))

    first = rules.save_rules(VALID)
    changed = dict(VALID, max_gap_seconds=8)
    second = rules.save_rules(changed)

    assert first["version"] == 1
    assert second["version"] == 2
    assert rules.get_rules() == second
    with pytest.raises(ValueError):
        rules.save_rules(dict(VALID, max_gap_seconds=999))
    assert rules.get_rules() == second
