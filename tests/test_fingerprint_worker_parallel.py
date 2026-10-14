"""
Parallel fingerprint builders (app.pipeline.worker).

The claim loop is tested with a fake queue and a fake manager, so no model is
loaded and no fingerprint is written; the sizing helpers are pure functions.
"""

from __future__ import annotations

import os

from app.pipeline import worker as worker_mod


def test_default_workers_is_half_the_cores():
    cores = os.cpu_count() or 1

    assert worker_mod.default_workers() == max(1, cores // 2)


def test_thread_budget_splits_the_machine():
    cores = os.cpu_count() or 1

    # One builder may use everything; many builders get at least one thread.
    assert worker_mod.threads_per_worker(1) == cores
    assert worker_mod.threads_per_worker(cores) == 1
    assert worker_mod.threads_per_worker(cores * 4) == 1
    # A nonsensical count falls back to "one builder", never to zero threads.
    assert worker_mod.threads_per_worker(0) == cores


def test_descriptor_threads_stay_bounded():
    assert worker_mod.descriptor_threads(1) == min(6, os.cpu_count() or 1)
    assert worker_mod.descriptor_threads(64) == 1


class FakeQueue:
    def __init__(self, jobs):
        self._jobs = list(jobs)
        self.completed = []
        self.failed = []

    def claim(self):
        if not self._jobs:
            return None

        return self._jobs.pop(0)

    def complete(self, job_id):
        self.completed.append(job_id)

    def fail(self, job_id, error):
        self.failed.append((job_id, error))


class FakeManager:
    def __init__(self, broken=()):
        self.broken = set(broken)
        self.created = []

    def create(self, fingerprint_id, source_folder, embedder):
        if fingerprint_id in self.broken:
            raise RuntimeError(f"cannot build {fingerprint_id}")

        self.created.append((fingerprint_id, str(source_folder)))


def _job(job_id, fingerprint_id):
    return {
        "id": job_id,
        "fingerprint_id": fingerprint_id,
        "source_folder": f"/photos/{fingerprint_id}",
    }


def test_process_queue_drains_the_queue_and_returns_the_count():
    queue = FakeQueue([_job(1, "78_v33"), _job(2, "79_v33")])
    manager = FakeManager()

    worker = worker_mod.FingerprintWorker(queue=queue, manager=manager)

    assert worker.process_queue() == 2
    assert queue.completed == [1, 2]
    assert queue.failed == []
    assert manager.created == [
        ("78_v33", "/photos/78_v33"),
        ("79_v33", "/photos/79_v33"),
    ]


def test_a_failing_job_is_recorded_and_does_not_stop_the_others():
    queue = FakeQueue([_job(1, "78_v33"), _job(2, "79_v33"), _job(3, "80_v33")])
    manager = FakeManager(broken={"79_v33"})

    worker = worker_mod.FingerprintWorker(queue=queue, manager=manager)

    assert worker.process_queue() == 3
    assert queue.completed == [1, 3]
    assert len(queue.failed) == 1
    assert queue.failed[0][0] == 2
    assert "cannot build 79_v33" in queue.failed[0][1]


def test_an_empty_queue_processes_nothing():
    queue = FakeQueue([])
    worker = worker_mod.FingerprintWorker(queue=queue, manager=FakeManager())

    assert worker.process_queue() == 0
    assert queue.completed == []


def test_builders_share_one_queue_through_the_same_database():
    """Two builders over one queue never build the same job twice."""

    shared = FakeQueue([_job(1, "78_v33"), _job(2, "79_v33")])
    first = worker_mod.FingerprintWorker(queue=shared, manager=FakeManager())
    second = worker_mod.FingerprintWorker(queue=shared, manager=FakeManager())

    processed = first.process_queue() + second.process_queue()

    assert processed == 2
    assert sorted(shared.completed) == [1, 2]
