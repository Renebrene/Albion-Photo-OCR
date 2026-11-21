"""
Источник описания QWEN в карточке грида ('crop' | 'full').

Колонка `qwen_source` — последняя в SELECT списка фото, за ней может идти
`similarity` у временной сортировки. Ошибка в позициях отдала бы гриду чужие
значения, поэтому проверяем разбор строки без базы.
"""

from __future__ import annotations

from app.api.repository import _photo_row


def _row(*, source="crop", has_crop=True, extra_similarity=None):
    row = (
        "PH_" + "a" * 24,  # photo_id
        "one.jpg",         # filename
        640,               # width
        480,               # height
        "JPEG",            # container_format
        "78_v33",          # address
        "Клиент",          # client
        "Бренд",           # brand
        "категория",       # category
        None,              # created_at
        None,              # taken_at
        1000,              # size_bytes
        "/photos/one.jpg", # source_path
        None,              # legal_address
        None,              # simple_address
        "DONE",            # qwen_status
        True,              # qwen_described
        0.9,               # confidence
        None,              # suggested_fingerprint
        None,              # suggested_address
        None,              # margin
        None,              # runner_up_address
        None,              # runner_up_score
        source,            # qwen_source
        has_crop,          # has_billboard_crop
    )

    if extra_similarity is not None:
        return (*row, extra_similarity)

    return row


def test_qwen_source_is_mapped_beside_the_other_fields():
    photo = _photo_row(_row(source="crop"))

    assert photo.qwen_source == "crop"
    assert photo.qwen_status == "DONE"
    assert photo.qwen_described is True
    assert photo.similarity is None


def test_full_frame_source_reaches_the_grid():
    photo = _photo_row(_row(source="full"))

    assert photo.qwen_source == "full"


def test_similarity_follows_qwen_source_in_the_similarity_sort():
    """Сортировка «по схожести» добавляет столбец последним, после источника."""

    photo = _photo_row(_row(source="full", extra_similarity=0.42))

    assert photo.qwen_source == "full"
    assert photo.similarity == 0.42


def test_billboard_crop_flag_reaches_the_grid():
    """Без кропа щита кнопка «Похожие» гаснет — поиску не по чему идти."""

    assert _photo_row(_row(has_crop=True)).has_billboard_crop is True
    assert _photo_row(_row(has_crop=False)).has_billboard_crop is False
    # Флаг стоит перед необязательным similarity и не сдвигает разбор.
    photo = _photo_row(_row(has_crop=False, extra_similarity=0.31))

    assert photo.has_billboard_crop is False
    assert photo.similarity == 0.31
