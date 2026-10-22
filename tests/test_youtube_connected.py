from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import requests

from brainrot import publish, scheduler, youtube, youtube_sync, worker


@pytest.fixture
def connected(fake_db, monkeypatch):
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"channel_id": "channel", "access_token": "test", "auto_publish": False, "privacy_status": "private"}}).execute()
    row = fake_db.table("publications").insert({"platform": "youtube", "chapter_id": "chapter", "status": "published",
        "platform_post_id": "abcdefghijk", "published_at": "2025-01-01T00:00:00+00:00", "metadata": {"title": "Test Short", "channel_id": "channel"}}).execute().data[0]
    calls = []
    def get(url, **options):
        calls.append(options)
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"columnHeaders": [{"name": name} for name in youtube_sync.METRICS], "rows": [[100, 80, 5, 2, 75, 62.5]]})
    monkeypatch.setattr(youtube_sync.requests, "get", get)
    return row, calls


def test_sync_writes_real_averages_and_pacing_metrics_once_per_interval(connected, fake_db):
    row, calls = connected
    assert youtube_sync.sync() == {"updated": 1, "waiting": 0, "failed": 0}
    metric = fake_db.rows("chapter_metrics")[0]
    assert metric["retention_pct"] == 62.5 and metric["avg_watch_seconds"] == 75
    assert calls[0]["params"]["filters"] == "video==abcdefghijk"
    assert fake_db.rows("publications")[0]["analytics"]["engagedViews"] == 80
    assert youtube_sync.sync()["updated"] == 0
    assert len(calls) == 1


@pytest.mark.parametrize("rows", [[], [[0, 0, 0, 0, 0, 0]]])
def test_missing_or_unviewed_data_cannot_drop_following_chapters(connected, fake_db, monkeypatch, rows):
    monkeypatch.setattr(youtube_sync.requests, "get", lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"columnHeaders": [{"name": n} for n in youtube_sync.METRICS], "rows": rows}))
    youtube_sync.sync()
    assert fake_db.rows("chapter_metrics") == []
    assert scheduler.retention("chapter") is None


def test_raw_rewatch_average_is_preserved_but_pacing_input_is_bounded(connected, fake_db, monkeypatch):
    monkeypatch.setattr(youtube_sync.requests, "get", lambda *a, **k: SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"columnHeaders": [{"name": n} for n in youtube_sync.METRICS], "rows": [[100, 80, 5, 2, 150, 125]]}))
    youtube_sync.sync()
    assert fake_db.rows("publications")[0]["analytics"]["averageViewPercentage"] == 125
    assert scheduler.retention("chapter") == 100


def test_latest_platform_snapshot_replaces_old_high_retention(fake_db):
    fake_db.table("chapter_metrics").insert([
        {"chapter_id": "chapter", "platform": "youtube", "retention_pct": 95, "captured_at": "2025-01-01"},
        {"chapter_id": "chapter", "platform": "youtube", "retention_pct": 15, "captured_at": "2025-01-02"}]).execute()
    assert scheduler.retention("chapter") == 15


def test_sync_failure_does_not_modify_upload_status_and_is_throttled(connected, fake_db, monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.ConnectionError("offline")
    monkeypatch.setattr(youtube_sync.requests, "get", unavailable)
    assert youtube_sync.sync()["failed"] == 1
    assert fake_db.rows("publications")[0]["status"] == "published"
    assert youtube_sync.sync()["failed"] == 0


def test_worker_syncs_before_pacing_and_keeps_publishing_on_analytics_failure(monkeypatch):
    events = []
    monkeypatch.setattr(worker, "_last_youtube_sync", None)
    monkeypatch.setattr(worker.db, "cleanup_media", lambda: events.append("cleanup"))
    def fail():
        events.append("analytics")
        raise RuntimeError("unavailable")
    monkeypatch.setattr(worker.youtube_sync, "sync", fail)
    monkeypatch.setattr(worker.scheduler, "tick", lambda: events.append("pacing") or [])
    monkeypatch.setattr(worker.publish, "run_due", lambda: events.append("publish"))
    worker.housekeeping()
    worker.housekeeping()
    assert events == ["cleanup", "analytics", "pacing", "publish", "cleanup", "pacing", "publish"]


def test_enable_automation_excludes_backlog_until_explicitly_included(connected, fake_db, monkeypatch):
    old = fake_db.table("publications").insert({"platform": "youtube", "chapter_id": "old", "status": "scheduled", "created_at": "2025-01-01T00:00:00+00:00", "scheduled_at": "2025-01-01T00:00:00+00:00"}).execute().data[0]
    settings = youtube.settings(True, "unlisted", False)
    assert settings["auto_publish"] and settings["auto_publish_after"]
    new = fake_db.table("publications").insert({"platform": "youtube", "chapter_id": "new", "status": "scheduled", "created_at": (datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat(), "scheduled_at": "2025-01-01T00:00:00+00:00"}).execute().data[0]
    uploaded = []
    monkeypatch.setattr(publish, "publish_one", lambda row: uploaded.append(row["id"]) or True)
    publish.run_due()
    assert uploaded == [new["id"]]
    youtube.settings(True, "unlisted", True)
    publish.run_due()
    assert old["id"] in uploaded
    youtube.settings(False, "private", False)
    uploaded.clear()
    publish.run_due()
    assert not uploaded


def test_wrong_channel_publication_is_not_synced(connected, fake_db):
    row, calls = connected
    fake_db.table("publications").update({"metadata": {"channel_id": "another-channel"}}).eq("id", row["id"]).execute()
    assert youtube_sync.sync()["updated"] == 0
    assert not calls


@pytest.mark.parametrize("source", ["chapter", "clip"])
@pytest.mark.parametrize("mode", ["review", "auto", "off"])
def test_new_job_publishing_choice_controls_the_worker(connected, fake_db, monkeypatch, source, mode):
    options = {"mode": mode, "privacy_status": "unlisted", "channel_id": "channel", "made_for_kids": True, "contains_synthetic_media": True}
    job = fake_db.table("jobs").insert({"params": {"youtube_publishing": options}}).execute().data[0]
    if source == "chapter":
        story = fake_db.table("stories").insert({"job_id": job["id"]}).execute().data[0]
        target = fake_db.table("story_chapters").insert({"story_id": story["id"], "chapter_index": 1, "status": "ready"}).execute().data[0]
        scheduler.plan_story(story["id"])
    else:
        target = fake_db.table("clips").insert({"job_id": job["id"], "status": "ready"}).execute().data[0]
        scheduler.plan_clip(target["id"])
    rows = [row for row in fake_db.rows("publications") if row.get(source + "_id") == target["id"] and row["platform"] == "youtube"]
    assert len(rows) == (0 if mode == "off" else 1)
    if rows:
        assert rows[0]["metadata"]["youtube_mode"] == mode
        assert rows[0]["metadata"]["made_for_kids"] is True
    if mode == "review":
        data = publish.credentials("youtube")
        publish._save("youtube", {**data, "auto_publish": True})
    uploaded = []
    monkeypatch.setattr(publish, "publish_one", lambda row: uploaded.append(row["id"]) or True)
    publish.run_due()
    assert uploaded == ([rows[0]["id"]] if mode == "auto" else [])


def test_new_job_automatic_upload_stays_bound_to_selected_channel(connected, fake_db, monkeypatch):
    fake_db.table("publications").insert({"platform": "youtube", "status": "scheduled", "chapter_id": "target", "scheduled_at": "2025-01-01T00:00:00+00:00",
        "metadata": {"youtube_mode": "auto", "channel_id": "another-channel"}}).execute()
    monkeypatch.setattr(publish, "publish_one", lambda row: pytest.fail("wrong channel"))
    assert publish.run_due() == []


def test_new_job_auto_validates_connection_and_binds_channel_server_side(fake_db, monkeypatch):
    from fastapi.testclient import TestClient
    from brainrot import api
    monkeypatch.setattr(api, "API_KEY", "test")
    monkeypatch.setattr(youtube, "status", lambda: {"connected": False})
    client = TestClient(api.app, headers={"X-API-Key": "test"})
    payload = {"kind": "brainrot", "topic": "History", "youtube_publishing": {"mode": "auto", "privacy_status": "unlisted"}}
    assert client.post("/jobs", json=payload).status_code == 409
    assert not fake_db.rows("jobs")
    monkeypatch.setattr(youtube, "status", lambda: {"connected": True, "channel_id": "real-channel"})
    assert client.post("/jobs", json=payload).status_code == 200
    assert fake_db.rows("jobs")[0]["params"]["youtube_publishing"]["channel_id"] == "real-channel"
    payload["youtube_publishing"]["channel_id"] = "injected-channel"
    assert client.post("/jobs", json=payload).status_code == 422
