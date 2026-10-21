"""Deletion crosses a database transaction and Storage; failures must be recoverable."""

from types import SimpleNamespace
import uuid

import httpx
import pytest

from brainrot import db, worker
from brainrot.domain.jobs import LeaseLost
from brainrot.domain.pipelines import PipelineContext
from tests.fakes import fake_supabase
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job


@pytest.fixture
def storage(pg, monkeypatch):
    fake = fake_supabase()
    client = PgRpcClient(pg)
    client.storage = fake.storage

    class OwnerQuery:
        def __init__(self, table):
            assert table in {"story_chapters", "clips", "source_videos"}
            self.table = table

        def select(self, columns):
            assert columns == "id"
            return self

        def eq(self, column, value):
            assert column == "id"
            self.asset_id = value
            return self

        def execute(self):
            rows = pg.execute(f"select id from {self.table} where id=%s", (self.asset_id,)).fetchall()
            return SimpleNamespace(data=rows)

    client.table = OwnerQuery
    monkeypatch.setattr(db, "client", lambda: client)
    return fake.files


def chapter(pg, job_id, *, index=1, audio=None, video=None):
    story = pg.execute("insert into stories(job_id,script) values(%s,'Saved script') returning id", (job_id,)).fetchone()["id"]
    row = pg.execute(
        "insert into story_chapters(story_id,chapter_index,text,audio_path,video_path) "
        "values(%s,%s,'Body',%s,%s) returning id", (story, index, audio, video),
    ).fetchone()["id"]
    return story, row


def test_deleting_job_removes_every_related_record_and_output_but_keeps_library(pg, storage):
    job_id = add_job(pg)
    db.claim_job("worker-a")
    db.start_stage(PipelineContext(job_id, "brainrot", {}, 1, "worker-a"), "render")
    story, chapter_id = chapter(pg, job_id, audio="old/audio.mp3", video="old/video.mp4")
    pg.execute("insert into chapter_metrics(chapter_id,platform) values(%s,'youtube')", (chapter_id,))
    pg.execute("insert into publications(chapter_id,platform) values(%s,'youtube')", (chapter_id,))
    source = pg.execute(
        "insert into source_videos(job_id,youtube_url,storage_path,transcript) "
        "values(%s,'https://youtu.be/example','sources/source.mp4','[]') returning id", (job_id,),
    ).fetchone()["id"]
    clip = pg.execute(
        "insert into clips(job_id,source_video_id,start_seconds,end_seconds,storage_path) "
        "values(%s,%s,0,15,'old/clip.mp4') returning id", (job_id, source),
    ).fetchone()["id"]
    files = ["old/audio.mp3", "old/video.mp4", "sources/source.mp4", "old/clip.mp4",
             f"stories/{story}/01.mp3", f"stories/{story}/01.mp4", f"clips/{clip}.mp4"]
    storage.update({path: b"output" for path in files})
    storage["backgrounds/gameplay.mp4"] = b"shared library"
    pg.execute("insert into background_clips(label,storage_path) values('Gameplay','backgrounds/gameplay.mp4')")

    assert db.delete_job(job_id) == "deleted"
    assert db.cleanup_media(job_id)
    for table in ("jobs", "stories", "story_chapters", "source_videos", "clips", "publications", "chapter_metrics", "stage_executions", "media_cleanup"):
        assert pg.execute(f"select count(*) from {table}").fetchone()["count"] == 0, table
    assert storage == {"backgrounds/gameplay.mp4": b"shared library"}


def test_unrecorded_chapter_upload_destinations_are_cleaned_without_truncating_large_indices(pg, storage):
    job_id = add_job(pg, status="failed")
    story, _ = chapter(pg, job_id, index=101)
    storage[f"stories/{story}/101.mp3"] = b"uploaded before a crash"
    storage[f"stories/{story}/101.mp4"] = b"uploaded before a crash"
    assert db.delete_job(job_id) == "deleted"
    assert db.cleanup_media(job_id)
    assert not storage


def test_failed_storage_deletion_is_durable_and_retries_after_job_is_gone(pg, storage, monkeypatch):
    job_id = add_job(pg, status="done")
    chapter(pg, job_id, video="videos/result.mp4")
    storage["videos/result.mp4"] = b"video"
    assert db.delete_job(job_id) == "deleted"
    client = db.client()
    original = client.storage.from_

    def unavailable(bucket):
        def remove(paths):
            raise httpx.ReadError("storage connection interrupted")
        return SimpleNamespace(remove=remove)

    monkeypatch.setattr(client.storage, "from_", unavailable)
    assert db.cleanup_media(job_id) is False
    assert pg.execute("select count(*) from jobs").fetchone()["count"] == 0
    assert pg.execute("select count(*) from media_cleanup").fetchone()["count"] > 0
    assert storage["videos/result.mp4"] == b"video"
    monkeypatch.setattr(client.storage, "from_", original)
    assert db.cleanup_media(job_id)
    assert not storage
    assert pg.execute("select count(*) from media_cleanup").fetchone()["count"] == 0


def test_shared_referenced_files_are_preserved(pg, storage):
    first, second = add_job(pg), add_job(pg)
    chapter(pg, first, video="shared.mp4", audio="backgrounds/gameplay.mp4")
    chapter(pg, second, video="shared.mp4")
    pg.execute("insert into background_clips(label,storage_path) values('Gameplay','backgrounds/gameplay.mp4')")
    storage.update({"shared.mp4": b"shared", "backgrounds/gameplay.mp4": b"gameplay"})
    assert db.delete_job(first) == "deleted"
    assert db.cleanup_media(first)
    assert len(storage) == 2
    assert db.delete_job(second) == "deleted"
    assert db.cleanup_media(second)
    assert storage == {"backgrounds/gameplay.mp4": b"gameplay"}


def test_deleted_owner_cannot_start_a_storage_upload(pg, storage):
    job_id = add_job(pg)
    _, chapter_id = chapter(pg, job_id)
    assert db.delete_job(job_id) == "deleted"
    with pytest.raises(LeaseLost, match="owner was deleted"):
        db.upload_job_media(job_id, "story_chapters", chapter_id, "late.mp4", b"video", "video/mp4")
    assert not storage


def test_deletion_during_upload_removes_the_late_object_and_stops_the_worker(pg, storage, monkeypatch):
    job_id = add_job(pg)
    db.claim_job("worker-a")
    story, chapter_id = chapter(pg, job_id)
    db.start_stage(PipelineContext(job_id, "brainrot", {}, 1, "worker-a"), "upload")
    path = f"stories/{story}/01.mp4"

    def upload(path, data, content_type):
        assert db.delete_job(job_id) == "deleted"
        assert db.cleanup_media(job_id)
        storage[path] = data  # The HTTP upload completes after the first cleanup.
        return path

    monkeypatch.setattr(db, "upload", upload)
    with pytest.raises(LeaseLost, match="during upload"):
        db.upload_job_media(job_id, "story_chapters", chapter_id, path, b"late", "video/mp4")
    assert path not in storage
    assert pg.execute("select count(*) from jobs").fetchone()["count"] == 0


def test_crashed_upload_is_rechecked_by_housekeeping_after_its_lease_expires(pg, storage, monkeypatch):
    job_id = add_job(pg)
    db.claim_job("worker-a")
    story, _ = chapter(pg, job_id)
    db.start_stage(PipelineContext(job_id, "brainrot", {}, 1, "worker-a"), "upload")
    assert db.delete_job(job_id) == "deleted"
    assert db.cleanup_media(job_id)
    assert pg.execute("select count(*) from media_cleanup").fetchone()["count"] > 0
    path = f"stories/{story}/01.mp4"
    storage[path] = b"completed after deletion, worker then crashed"
    pg.execute("update media_cleanup set retry_at=now()-interval '1 second', settle_until=now()-interval '1 second'")
    monkeypatch.setattr(worker.scheduler, "tick", lambda: [])
    monkeypatch.setattr(worker.publish, "run_due", lambda: None)
    worker.housekeeping()
    assert not storage
    assert pg.execute("select count(*) from media_cleanup").fetchone()["count"] == 0


def test_acknowledging_an_older_cleanup_cannot_remove_a_new_cleanup_request(pg, storage):
    job_id = str(uuid.uuid4())
    client = db.client()
    params = {"p_job": job_id, "p_paths": ["unlinked.mp4"]}
    client.rpc("queue_media_cleanup", params).execute()
    old = client.rpc("pending_media_cleanup", {"p_job": job_id}).execute().data[0]
    client.rpc("queue_media_cleanup", params).execute()
    client.rpc("finish_media_cleanup", {"p_ids": [old["id"]], "p_success": True}).execute()
    assert pg.execute("select count(*) from media_cleanup").fetchone()["count"] == 1


def test_cleanup_rpcs_are_not_available_to_browser_roles(pg):
    for role in ("anon", "authenticated"):
        for signature in ("queue_media_cleanup(uuid,text[],timestamptz)", "pending_media_cleanup(uuid,integer)", "finish_media_cleanup(uuid[],boolean)"):
            assert not pg.execute("select has_function_privilege(%s,%s,'execute') as allowed", (role, signature)).fetchone()["allowed"]
