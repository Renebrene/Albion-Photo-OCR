from datetime import datetime, timedelta

from app.refine.scoped_proposals import EnrichmentFrame, propose_enrichment


T0 = datetime(2026, 9, 1, 12, 0)


def frame(photo_id, seconds, *, screen="screen-a", dhash=0, description=None, tags=()):
    return EnrichmentFrame(
        photo_id=photo_id,
        screen=screen,
        taken_at=T0 + timedelta(seconds=seconds),
        crop_dhash=dhash,
        description=description,
        tags=tuple(tags),
    )


def test_empty_description_and_unique_tags_are_proposed_without_mutating_inputs():
    first = frame("a", 0, description="BigFest", tags=("brand", "summer"))
    second = frame("b", 10, tags=("Summer", "sale"))

    report = propose_enrichment([first, second])

    assert [(proposal.photo_id, proposal.changes) for proposal in report.proposals] == [
        ("a", {"tags": ["brand", "summer", "sale"]}),
        ("b", {"description": "BigFest", "tags": ["brand", "summer", "sale"]}),
    ]
    assert report.description_variants == ()
    assert first.description == "BigFest"
    assert second.tags == ("Summer", "sale")


def test_different_descriptions_do_not_block_tag_union_or_overwrite_values():
    report = propose_enrichment(
        [
            frame("a", 0, description="BigFest", tags=("brand",)),
            frame("b", 1, description="Big Food", tags=("sale",)),
            frame("c", 2, tags=("third",)),
        ]
    )
    proposals = {item.photo_id: item.changes for item in report.proposals}
    assert proposals == {
        "a": {"tags": ["brand", "sale", "third"]},
        "b": {"tags": ["brand", "sale", "third"]},
        "c": {"tags": ["brand", "sale", "third"]},
    }
    assert report.description_variants[0]["photo_ids"] == ["a", "b", "c"]
    assert report.description_variants[0]["reason"] == "multiple_description_variants_in_visual_group"


def test_ambiguous_description_stays_empty_but_tags_are_unioned():
    report = propose_enrichment(
        [
            frame("a", 0, description="Brand A", tags=("one",)),
            frame("b", 1, description="Brand B", tags=("two",)),
            frame("c", 2, tags=("three",)),
        ]
    )
    proposals = {item.photo_id: item.changes for item in report.proposals}
    assert proposals["c"] == {"tags": ["one", "two", "three"]}
    assert "description" not in proposals["c"]
    assert report.description_variants


def test_equivalent_normalized_descriptions_allow_tag_union():
    report = propose_enrichment(
        [
            frame("a", 0, description="Big-Fest", tags=("Brand",)),
            frame("b", 1, description="big fest", tags=("brand", "Sale")),
        ]
    )
    assert report.description_variants == ()
    assert [(proposal.photo_id, proposal.changes) for proposal in report.proposals] == [
        ("a", {"tags": ["Brand", "Sale"]}),
        ("b", {"tags": ["Brand", "Sale"]}),
    ]


def test_time_boundary_is_inclusive_but_over_ten_seconds_splits_group():
    in_range = propose_enrichment([frame("a", 0, description="x"), frame("b", 10)])
    assert in_range.proposals[0].changes["description"] == "x"

    out_of_range = propose_enrichment([frame("a", 0, description="x"), frame("b", 10.01)])
    assert out_of_range.proposals == ()
    assert any(item["reason"] == "outside_time_window" for item in out_of_range.ineligible_pairs)


def test_hash_distance_six_is_inclusive_and_seven_splits_group():
    included = propose_enrichment(
        [frame("a", 0, description="x", dhash=0), frame("b", 1, dhash=(1 << 6) - 1)]
    )
    assert included.proposals

    excluded = propose_enrichment(
        [frame("a", 0, description="x", dhash=0), frame("b", 1, dhash=(1 << 7) - 1)]
    )
    assert excluded.proposals == ()
    assert any(item["reason"] == "crop_dhash_mismatch" for item in excluded.ineligible_pairs)


def test_different_screen_or_missing_hash_prevents_proposals():
    screen_mismatch = propose_enrichment(
        [frame("a", 0, description="x", screen="one"), frame("b", 1, screen="two")]
    )
    assert screen_mismatch.proposals == ()

    missing_hash = propose_enrichment(
        [frame("a", 0, description="x", dhash=None), frame("b", 1)]
    )
    assert missing_hash.proposals == ()
    assert any(item["reason"] == "missing_crop_dhash" for item in missing_hash.ineligible_pairs)


def test_nonempty_description_is_never_replaced():
    report = propose_enrichment(
        [frame("a", 0, description="MTC", tags=("one",)), frame("b", 1, description="MTC", tags=("two",))]
    )
    assert all("description" not in proposal.changes for proposal in report.proposals)


def test_nontransitive_adjacent_groups_do_not_bridge_invalid_similarity_gap():
    report = propose_enrichment(
        [
            frame("a", 0, description="BigFest", dhash=0),
            frame("b", 1, description="BigFest", dhash=0),
            frame("c", 2, description="Big Food", dhash=(1 << 7) - 1),
        ]
    )
    assert [(item.photo_id, item.changes) for item in report.proposals] == []


def test_empty_screen_is_not_treated_as_a_known_shared_screen():
    report = propose_enrichment(
        [frame("a", 0, screen="", description="Name"), frame("b", 1, screen="")]
    )
    assert report.proposals == ()
    assert any(item["reason"] == "different_or_missing_screen" for item in report.ineligible_pairs)


def test_group_requires_pairwise_hash_agreement_not_only_neighbor_chain():
    report = propose_enrichment(
        [
            frame("a", 0, description="BigFest", dhash=0),
            frame("b", 1, description="BigFest", dhash=0b11),
            frame("c", 2, dhash=0b110),
        ]
    )
    assert {item.photo_id for item in report.proposals} == {"c"}
