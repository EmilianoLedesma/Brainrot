from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from types import SimpleNamespace

import psycopg
from psycopg import sql
import pytest

from brainrot import db, publish
from tests.test_job_execution import add_job


class PublicationClient:
    """Real SQL for just the compare-and-set publication writes under test."""
    def __init__(self, connection, fail_success=False):
        self.connection = connection
        self.fail_success = fail_success

    def table(self, name):
        assert name == "publications"
        client = self

        class Update:
            def __init__(self):
                self.patch = {}
                self.filters = {}

            def update(self, patch):
                self.patch = patch
                return self

            def eq(self, name, value):
                self.filters[name] = value
                return self

            def execute(self):
                if self.patch.get("status") == "published" and client.fail_success:
                    client.fail_success = False
                    raise TimeoutError("platform accepted but success recording timed out")
                assignment = sql.SQL(",").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in self.patch)
                where = sql.SQL(" and ").join(sql.SQL("{}=%s").format(sql.Identifier(k)) for k in self.filters)
                query = sql.SQL("update publications set {} where {} returning id").format(assignment, where)
                rows = client.connection.execute(query, [*self.patch.values(), *self.filters.values()]).fetchall()
                return SimpleNamespace(data=[{"id":str(r["id"])} for r in rows])

        return Update()


@pytest.fixture
def publication(pg):
    job_id = add_job(pg, kind="repurpose")
    source = pg.execute("insert into source_videos(job_id,youtube_url) values(%s,'https://youtu.be/example') returning id", (job_id,)).fetchone()["id"]
    clip = pg.execute("insert into clips(job_id,source_video_id,start_seconds,end_seconds) values(%s,%s,0,20) returning id", (job_id,source)).fetchone()["id"]
    row = pg.execute("insert into publications(platform,clip_id,scheduled_at) values('youtube',%s,now()) returning *", (clip,)).fetchone()
    return {**row,"id":str(row["id"])}


def test_timeout_after_platform_acceptance_never_reuploads(pg, publication, monkeypatch):
    monkeypatch.setattr(db,"client",lambda:PublicationClient(pg,fail_success=True))
    # Reuse one client so only the first success write times out.
    client = PublicationClient(pg,fail_success=True)
    monkeypatch.setattr(db,"client",lambda:client)
    monkeypatch.setattr(publish,"credentials",lambda platform:{"access_token":"synthetic"})
    monkeypatch.setattr(publish,"target",lambda row:{"path":"clip.mp4","title":"Clip"})
    monkeypatch.setattr(db,"download",lambda path:b"video")
    uploads = []
    monkeypatch.setattr(publish,"post_youtube",lambda *args:uploads.append(1) or ("accepted-id",""))
    with pytest.raises(TimeoutError):
        publish.publish_one(publication)
    assert publish.publish_one(publication) is False
    assert uploads == [1]
    assert pg.execute("select status from publications").fetchone()["status"] == "failed"


def test_two_concurrent_publication_claims_have_one_winner(pg, publication, monkeypatch):
    state = local()
    barrier = Barrier(2)
    monkeypatch.setattr(db,"client",lambda:PublicationClient(state.connection))

    def take():
        with psycopg.connect(pg.info.dsn,autocommit=True,row_factory=psycopg.rows.dict_row) as connection:
            state.connection = connection
            barrier.wait(timeout=5)
            return publish._take(publication["id"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:take(),range(2)))
    assert sorted(results) == [False,True]
