from app.jobs import database as jobs_db


class FakeCursor:
    def __init__(self):
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.params = params

    def fetchone(self):
        return (41,)


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_value = cursor

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_value


def test_enqueue_qwen_payload_can_skip_automatic_global_refine(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(jobs_db, "get_connection", lambda: FakeConnection(cursor))

    job_id = jobs_db.enqueue_qwen(
        "PH_aaaaaaaaaaaaaaaaaaaaaaaa",
        source="manual",
        skip_refine=True,
    )

    assert job_id == 41
    payload = cursor.params[0].obj
    assert payload["skip_refine"] is True


def test_enqueue_qwen_payload_keeps_legacy_refine_default(monkeypatch):
    cursor = FakeCursor()
    monkeypatch.setattr(jobs_db, "get_connection", lambda: FakeConnection(cursor))

    jobs_db.enqueue_qwen("PH_bbbbbbbbbbbbbbbbbbbbbbbb", source="manual")

    payload = cursor.params[0].obj
    assert "skip_refine" not in payload
