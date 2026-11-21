"""
Запрещённые к выдаче слова (app/qwen/sanitize.py).

Правило касается только карточки фото: client/brand/tags/description. Ошибка
здесь оставила бы мат в выдаче или, наоборот, стёрла нормальные данные.
"""

from __future__ import annotations

from app.qwen.sanitize import contains_forbidden, forbidden_hits, sanitize_fields


def test_client_and_brand_are_dropped_whole_when_they_contain_a_forbidden_word():
    fields = {
        "client": "ООО «РОМАШКА»",
        "brand": "Ромашка-хулиган",
        "description": "Реклама цветов",
        "tags": ["цветы"],
    }

    result = sanitize_fields(fields, ["хулиган"])

    # Клиент чистый — остаётся; бренд с запрещённым словом уходит целиком.
    assert result["client"] == "ООО «РОМАШКА»"
    assert result["brand"] is None
    assert result["description"] == "Реклама цветов"
    assert result["tags"] == ["цветы"]


def test_tags_with_forbidden_words_are_removed():
    result = sanitize_fields(
        {
            "client": None,
            "brand": None,
            "description": None,
            "tags": ["реклама", "мат тут", "акция", "МАТ"],
        },
        ["мат"],
    )

    assert result["tags"] == ["реклама", "акция"]


def test_description_drops_the_word_and_tidies_spaces():
    result = sanitize_fields(
        {"description": "Реклама щита,   матовая поверхность и акция", "tags": []},
        ["матовая"],
    )

    assert result["description"] == "Реклама щита, поверхность и акция"


def test_description_that_becomes_empty_is_none():
    result = sanitize_fields({"description": "МАТ", "tags": []}, ["мат"])

    assert result["description"] is None


def test_empty_quotes_left_by_removal_are_cleaned():
    result = sanitize_fields(
        {"description": "Реклама скидок в сети «ПЕДО» до 1 ноября"},
        ["педо"],
    )

    assert result["description"] == "Реклама скидок в сети до 1 ноября"


def test_matching_is_case_insensitive_and_whole_word():
    assert contains_forbidden("СЛОВО", ["слово"]) is True
    assert contains_forbidden("вот слово, и всё", ["слово"]) is True
    # Подстрока в другом слове — не совпадение: иначе список режет нормальные
    # слова («педо» внутри «торпедо»).
    assert contains_forbidden("подсловом", ["слово"]) is False
    assert contains_forbidden("чисто", ["слово"]) is False


def test_whole_word_inside_another_word_is_allowed():
    assert contains_forbidden("Реклама Торпедо", ["педо"]) is False
    assert contains_forbidden("торпедо-щука", ["педо"]) is False
    assert contains_forbidden("велосипедов", ["педо"]) is False
    assert contains_forbidden("педо", ["педо"]) is True
    assert contains_forbidden("щит «ПЕДО»", ["педо"]) is True
    assert contains_forbidden("педо-щит", ["педо"]) is True
    assert contains_forbidden("вот педо.", ["педо"]) is True


def test_glued_words_are_split_by_letter_case():
    """QWEN склеивает «Система ПЕДО» в «СистемаПедо» — это тоже вхождение."""

    assert contains_forbidden("СистемаПедо", ["педо"]) is True
    assert contains_forbidden("бренд СистемаПедо", ["педо"]) is True
    assert contains_forbidden("ПедоСистема", ["педо"]) is True
    # «Торпедо» — одно слово, регистр внутри не меняется.
    assert contains_forbidden("Торпедо", ["педо"]) is False


def test_words_containing_a_forbidden_word_are_kept_whole():
    """Бренд «Торпедо» остаётся, бренд с отдельным словом уходит целиком."""

    result = sanitize_fields(
        {
            "client": "Торпедо",
            "brand": "Педо Студия",
            "description": "Реклама торпедо и педо щит",
            "tags": ["торпедо", "педо", "акция"],
        },
        ["педо"],
    )

    assert result["client"] == "Торпедо"
    assert result["brand"] is None
    assert result["description"] == "Реклама торпедо и щит"
    assert result["tags"] == ["торпедо", "акция"]


def test_manual_edit_rejects_only_the_whole_word():
    hits = forbidden_hits(
        {"client": "Торпедо", "brand": "педо", "tags": ["торпедо", "педо"]},
        ["педо"],
    )

    assert {hit["field"] for hit in hits} == {"brand", "tags"}
    assert all(hit["value"] != "Торпедо" for hit in hits)


def test_empty_list_changes_nothing():
    fields = {"client": "Мат", "brand": "МАТ", "description": "мат", "tags": ["мат"]}

    assert sanitize_fields(fields, []) == fields
    assert sanitize_fields(fields, None) == fields


def test_other_fields_are_untouched():
    fields = {"client": "Ок", "category": "мат", "address": "ул. Ленина"}

    result = sanitize_fields(fields, ["мат"])

    assert result["client"] == "Ок"
    assert result["category"] == "мат"
    assert result["address"] == "ул. Ленина"


def test_forbidden_hits_lists_manual_edit_fields():
    """Ручная правка: сервер должен назвать поле и слово, а не молча сохранить."""

    hits = forbidden_hits(
        {
            "description": "Реклама мат",
            "client": "ООО «Ромашка»",
            "brand": "МАТ",
            "tags": ["акция", "мат"],
        },
        ["мат"],
    )

    assert {"field": "description", "value": "Реклама мат", "word": "мат"} in hits
    assert {"field": "brand", "value": "МАТ", "word": "мат"} in hits
    assert {"field": "tags", "value": "мат", "word": "мат"} in hits
    assert all(hit["field"] != "client" for hit in hits)


def test_forbidden_hits_is_empty_without_the_setting():
    assert forbidden_hits({"description": "мат", "tags": ["мат"]}, []) == []
    assert forbidden_hits({"description": "мат"}, None) == []


class _FakeCursor:
    """Курсор для проверки записи «Уточнения» без живой БД."""

    rowcount = 1

    def __init__(self):
        self.updates: list[list] = []
        self._row = ("old description", ["торпедо"], "DONE")

    def execute(self, sql, params=None):
        statement = " ".join(sql.split())

        if statement.startswith("SELECT description"):
            self._row = ("old description", ["торпедо"], "DONE")
        elif statement.startswith("UPDATE"):
            self.updates.append(list(params or []))

    def fetchone(self):
        return self._row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_refine_write_cannot_reintroduce_forbidden_words(monkeypatch):
    """«Уточнение» берёт значения из серии — фильтр должен сработать и здесь."""

    from app.qwen import database as qwen_db
    from app.qwen import processor

    cursor = _FakeCursor()
    monkeypatch.setattr(qwen_db, "get_connection", lambda: _FakeConnection(cursor))
    monkeypatch.setattr(processor, "forbidden_words", lambda: ["педо"])

    applied = qwen_db.apply_refined_values(
        "PH_" + "ad" * 12,
        {
            "description": "Реклама торпедо и педо-щит",
            "client": "Педо Студия",
            "tags": ["торпедо", "педо"],
        },
        reason="refine",
    )

    assert applied is True

    values = cursor.updates[-1]
    written = str(values).lower()

    # Отдельного «педо» нет, «торпедо» остаётся.
    assert "педо-щит" not in written
    assert "педо студия" not in written
    assert "торпедо" in written
