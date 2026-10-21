"""Rollback-only worker/stage/metrics/API smoke. No providers or publications.

Requires DATABASE_URL and the dev dependencies. Inserts one transaction-local
job and uses a synthetic renderer; no existing queued job is executed.
"""

import io
import json
import logging
import os
import uuid

import psycopg
from psycopg.rows import dict_row
from fastapi.testclient import TestClient

from brainrot import api, db, worker
from brainrot.application import stages
from brainrot.application.registry import PipelineRegistry
from brainrot.domain.pipelines import PipelineResult
from brainrot.observability.logging import JsonFormatter, LOGGER
from tests.pgclient import PgRpcClient


def main():
    original_client, original_registry, original_key = db.client, worker.REGISTRY, api.API_KEY
    original_level = LOGGER.level
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    attempts = []

    class SyntheticPipeline:
        name = "brainrot"

        def execute(self, context):
            with stages.tracking(context), stages.stage("render", "smoke"):
                attempts.append(context.attempt)
                if len(attempts) == 1:
                    raise TimeoutError("synthetic transient failure")
            return PipelineResult()

    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=12, row_factory=dict_row) as connection:
            connection.execute("set local statement_timeout='20s'")
            before = connection.execute("select status,count(*) from jobs group by status order by status").fetchall()
            event_count = connection.execute("select count(*) as n from operational_events").fetchone()["n"]
            job_id = str(connection.execute(
                "insert into jobs(kind,run_after,idempotency_key) values('brainrot','-infinity',%s) returning id",
                ("live-smoke:" + uuid.uuid4().hex,),
            ).fetchone()["id"])
            connection.execute("set local role service_role")
            db.client = lambda: PgRpcClient(connection)
            worker.REGISTRY = PipelineRegistry([SyntheticPipeline()])
            claimed = db.claim_job("live-smoke-worker")
            assert claimed["id"] == job_id
            assert worker.execute(claimed, worker_id="live-smoke-worker") == "pending"
            connection.execute("update jobs set run_after='-infinity' where id=%s", (job_id,))
            claimed = db.claim_job("live-smoke-retry")
            assert claimed["id"] == job_id
            assert worker.execute(claimed, worker_id="live-smoke-retry") == "done"
            api.API_KEY = "ephemeral-smoke-key"
            http = TestClient(api.app, headers={"X-API-Key": api.API_KEY})
            detail = http.get("/jobs/" + job_id)
            assert detail.status_code == 200
            assert [s["status"] for s in detail.json()["stages"]] == ["failed", "done"]
            response = http.get("/metrics")
            assert response.status_code == 200 and "brainrot_jobs_retried_total" in response.text
            assert http.get("/jobs").status_code == 200
            assert TestClient(api.app).get("/metrics").status_code == 401
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            assert {"job_started", "stage_failed", "job_retry_scheduled", "stage_completed", "job_completed"} <= {row["event"] for row in events}
            connection.rollback()
            assert connection.execute("select status,count(*) from jobs group by status order by status").fetchall() == before
            assert connection.execute("select count(*) as n from operational_events").fetchone()["n"] == event_count
        print("Live worker retry, stages, JSON logs, metrics and authenticated API checks passed")
        print("Transaction rolled back; existing jobs and metric event counts unchanged")
    finally:
        db.client, worker.REGISTRY, api.API_KEY = original_client, original_registry, original_key
        LOGGER.removeHandler(handler)
        LOGGER.setLevel(original_level)


if __name__ == "__main__":
    main()
