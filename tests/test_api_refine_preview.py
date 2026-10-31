from fastapi.testclient import TestClient

from app.api.main import app
from app.refine.preview_store import create_preview


def test_apply_refine_preview_consumes_token_and_updates_through_history(monkeypatch):
    from app.api import routes
    from app.refine import rules

    current_rules = {"version": 2, "rules": dict(rules.DEFAULT_RULES)}
    monkeypatch.setattr(rules, "get_rules", lambda: current_rules)
    captured = []
    monkeypatch.setattr(routes.qwen_db, "apply_refined_values", lambda *args, **kwargs: captured.append((args, kwargs)) or True)

    token = create_preview(
        proposals=[{
            "photo_id": "PH_aaaaaaaaaaaaaaaaaaaaaaaa",
            "changes": {"tags": ["tag1", "2026"]},
            "expected_description": "same",
            "expected_tags": ["tag1"],
            "expected_status": "DONE",
        }],
        scope={"date_from": "2026-09-01", "date_to": "2026-10-29"},
        rules_version=2,
    )["preview_token"]
    client = TestClient(app)
    response = client.post("/api/v1/refine/apply", json={"preview_token": token})
    assert response.status_code == 200
    assert response.json() == {"applied_photos": 1, "stale_skipped": 0, "writes_performed": True}
    assert captured[0][0][0] == "PH_aaaaaaaaaaaaaaaaaaaaaaaa"
    assert captured[0][1]["expected_tags"] == ["tag1"]

    reused = client.post("/api/v1/refine/apply", json={"preview_token": token})
    assert reused.status_code == 410
