import psycopg
import pytest

from brainrot import db
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job


@pytest.mark.parametrize("status", ["pending", "failed", "done", "cancelled"])
def test_delete_inactive_job_cascades_results(pg, monkeypatch, status):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    job_id = add_job(pg, status=status)
    story = pg.execute("insert into stories(job_id) values(%s) returning id", (job_id,)).fetchone()["id"]
    chapter = pg.execute("insert into story_chapters(story_id,chapter_index,text) values(%s,1,'story') returning id", (story,)).fetchone()["id"]
    pg.execute("insert into publications(chapter_id,platform) values(%s,'youtube')", (chapter,))
    assert db.delete_job(job_id) == "deleted"
    for table in ("jobs", "stories", "story_chapters", "publications"):
        assert pg.execute(f"select count(*) from {table}").fetchone()["count"] == 0
    assert db.delete_job(job_id) == "missing"


def test_running_job_is_deleted_and_its_worker_cannot_continue(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    job_id = add_job(pg)
    pg.execute("select * from claim_job('worker-a',600)")
    from brainrot.domain.pipelines import PipelineContext
    context = PipelineContext(job_id, "brainrot", {}, 1, "worker-a")
    stage = db.start_stage(context, "script")
    assert db.delete_job(job_id) == "deleted"
    assert db.renew_lease(job_id, "worker-a") is False
    assert db.complete_job(job_id, "worker-a") is False
    assert db.finish_stage(stage, "worker-a", "done") is False
    assert db.start_stage(context, "render") is None


def test_upload_in_progress_is_preserved(pg):
    job_id = add_job(pg, status="done")
    story = pg.execute("insert into stories(job_id) values(%s) returning id", (job_id,)).fetchone()["id"]
    chapter = pg.execute("insert into story_chapters(story_id,chapter_index,text) values(%s,1,'story') returning id", (story,)).fetchone()["id"]
    pg.execute("insert into publications(chapter_id,platform,status) values(%s,'youtube','uploading')", (chapter,))
    assert pg.execute("select delete_job(%s)", (job_id,)).fetchone()["delete_job"] == "uploading"
    assert pg.execute("select count(*) from jobs").fetchone()["count"] == 1


def test_claim_skips_job_while_delete_is_uncommitted(pg):
    job_id = add_job(pg)
    with psycopg.connect(pg.info.dsn) as deleting, psycopg.connect(pg.info.dsn, autocommit=True) as claiming:
        assert deleting.execute("select delete_job(%s)", (job_id,)).fetchone()[0] == "deleted"
        assert claiming.execute("select * from claim_job('worker-a',600)").fetchall() == []
    assert pg.execute("select count(*) from jobs").fetchone()["count"] == 0


def test_delete_cannot_bypass_uncommitted_claim(pg):
    job_id = add_job(pg)
    with psycopg.connect(pg.info.dsn) as claiming, psycopg.connect(pg.info.dsn, autocommit=True) as deleting:
        claiming.execute("select * from claim_job('worker-a',600)")
        deleting.execute("set lock_timeout='100ms'")
        with pytest.raises(psycopg.errors.LockNotAvailable):
            deleting.execute("select delete_job(%s)", (job_id,))
        claiming.commit()
        assert deleting.execute("select delete_job(%s)", (job_id,)).fetchone()[0] == "deleted"


def test_browser_roles_cannot_delete_jobs(pg):
    for role in ("anon", "authenticated"):
        assert not pg.execute("select has_function_privilege(%s,'delete_job(uuid)','execute')", (role,)).fetchone()["has_function_privilege"]


def test_publication_cannot_be_claimed_during_deletion(pg):
    job_id = add_job(pg, status="done")
    source = pg.execute("insert into source_videos(job_id,youtube_url) values(%s,'https://youtu.be/example') returning id", (job_id,)).fetchone()["id"]
    clip = pg.execute("insert into clips(job_id,source_video_id,start_seconds,end_seconds) values(%s,%s,0,10) returning id", (job_id, source)).fetchone()["id"]
    publication = pg.execute("insert into publications(clip_id,platform) values(%s,'youtube') returning id", (clip,)).fetchone()["id"]
    with psycopg.connect(pg.info.dsn) as deleting, psycopg.connect(pg.info.dsn, autocommit=True) as publishing:
        assert deleting.execute("select delete_job(%s)", (job_id,)).fetchone()[0] == "deleted"
        publishing.execute("set lock_timeout='100ms'")
        with pytest.raises(psycopg.errors.LockNotAvailable):
            publishing.execute("update publications set status='uploading' where id=%s and status='scheduled' returning id", (publication,))
        deleting.commit()
        assert publishing.execute("update publications set status='uploading' where id=%s and status='scheduled' returning id", (publication,)).fetchall() == []
