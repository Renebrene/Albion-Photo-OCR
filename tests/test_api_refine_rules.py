from fastapi.testclient import TestClient

from app.api.main import app


def test_refine_rules_api_validates_and_versions(monkeypatch):
    from app.refine import rules

    stored = {}
    monkeypatch.setattr(rules.settings_store, "get", lambda key: stored.get(key))
    monkeypatch.setattr(rules.settings_store, "set_value", lambda key, value: stored.__setitem__(key, value))

    client = TestClient(app)
    initial = client.get("/api/v1/refine/rules")
    assert initial.status_code == 200
    assert initial.json()["version"] == 0

    payload = initial.json()["rules"]
    response = client.put("/api/v1/refine/rules", json={"rules": payload})
    assert response.status_code == 200
    assert response.json()["version"] == 1

    invalid = client.put("/api/v1/refine/rules", json={"rules": {"exec": "bad"}})
    assert invalid.status_code == 422
    assert client.get("/api/v1/refine/rules").json()["version"] == 1
