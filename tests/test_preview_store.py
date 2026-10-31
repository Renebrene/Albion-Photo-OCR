from app.refine import preview_store


def test_preview_token_is_one_time_and_expires(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(preview_store.time, "time", lambda: now[0])
    created = preview_store.create_preview(proposals=[{"photo_id": "p", "changes": {}}], scope={"from": "a"}, rules_version=3)
    result = preview_store.consume_preview(created["preview_token"])
    assert result["rules_version"] == 3
    assert preview_store.consume_preview(created["preview_token"]) is None

    expired = preview_store.create_preview(proposals=[], scope={}, rules_version=3)
    now[0] += preview_store._TTL_SECONDS + 1
    assert preview_store.consume_preview(expired["preview_token"]) is None


def test_preview_fingerprint_changes_with_content():
    first = preview_store.create_preview(proposals=[], scope={"from": "a"}, rules_version=1)
    second = preview_store.create_preview(proposals=[{"photo_id": "p"}], scope={"from": "a"}, rules_version=1)
    assert first["preview_fingerprint"] != second["preview_fingerprint"]
