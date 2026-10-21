from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import uuid

import psycopg
from psycopg.rows import dict_row
import pytest

from brainrot import db, pipeline
from brainrot.domain.jobs import PermanentError
from tests.pgclient import PgRpcClient
from tests.test_job_execution import add_job


@pytest.fixture
def library(pg, monkeypatch):
    monkeypatch.setattr(db, "client", lambda: PgRpcClient(pg))
    for order in range(1, 6):
        pg.execute(
            "insert into background_clips(label,storage_path,rotation_order) values(%s,%s,%s)",
            (f"Parkour {order}", f"backgrounds/{order}.mp4", order),
        )


def story(pg):
    job_id = add_job(pg)
    story_id = pg.execute("insert into stories(job_id) values(%s) returning id", (job_id,)).fetchone()["id"]
    return job_id, story_id


def test_five_backgrounds_repeat_in_order_across_new_clients(pg, library):
    chosen = []
    for _ in range(10):
        _, story_id = story(pg)
        # Recreating the client must not reset the rotation.
        chosen.append(PgRpcClient(pg).rpc("assign_story_background", {"p_story": str(story_id)}).execute().data)
    assert chosen == [f"backgrounds/{n}.mp4" for n in range(1, 6)] * 2


def test_retry_keeps_the_original_choice_without_consuming_another_turn(pg, library):
    _, original = story(pg)
    assert db.assign_story_background(original) == "backgrounds/1.mp4"
    for _ in range(3):
        assert db.assign_story_background(original) == "backgrounds/1.mp4"
    _, next_story = story(pg)
    assert db.assign_story_background(next_story) == "backgrounds/2.mp4"


def test_deactivated_background_is_skipped_for_new_stories_but_kept_for_retries(pg, library):
    _, original = story(pg)
    assert db.assign_story_background(original) == "backgrounds/1.mp4"
    pg.execute("update background_clips set active=false where storage_path='backgrounds/1.mp4'")
    chosen = [db.assign_story_background(story(pg)[1]) for _ in range(5)]
    assert chosen == ["backgrounds/2.mp4", "backgrounds/3.mp4", "backgrounds/4.mp4", "backgrounds/5.mp4", "backgrounds/2.mp4"]
    assert db.assign_story_background(original) == "backgrounds/1.mp4"


def test_empty_pool_and_deleted_story_do_not_consume_rotation(pg, library):
    assert db.assign_story_background(uuid.uuid4()) is None
    pg.execute("update background_clips set active=false")
    _, waiting = story(pg)
    assert db.assign_story_background(waiting) is None
    assert pg.execute("select count(*) from background_clips where last_used_order is not null").fetchone()["count"] == 0
    pg.execute("update background_clips set active=true")
    assert db.assign_story_background(waiting) == "backgrounds/1.mp4"


def test_background_download_failure_retries_the_same_selection(pg, library, monkeypatch):
    attempts = Counter()

    def download(path):
        attempts[path] += 1
        if path == "backgrounds/1.mp4" and attempts[path] == 1:
            raise TimeoutError("temporary Storage interruption")
        return path.encode()

    monkeypatch.setattr(db, "download", download)
    _, first = story(pg)
    with pytest.raises(TimeoutError):
        pipeline.pick_background(first)
    assert pipeline.pick_background(story(pg)[1]) == b"backgrounds/2.mp4"
    assert pipeline.pick_background(first) == b"backgrounds/1.mp4"
    assert pipeline.pick_background(story(pg)[1]) == b"backgrounds/3.mp4"


def test_missing_background_is_reported_before_rendering(pg, library):
    pg.execute("update background_clips set active=false")
    with pytest.raises(PermanentError, match="no active background_clips"):
        pipeline.pick_background(story(pg)[1])


def test_deleting_a_job_keeps_the_library_and_does_not_rewind_the_rotation(pg, library):
    job_id, first = story(pg)
    assert db.assign_story_background(first) == "backgrounds/1.mp4"
    assert db.delete_job(job_id) == "deleted"
    assert pg.execute("select count(*) from background_clips").fetchone()["count"] == 5
    assert db.assign_story_background(story(pg)[1]) == "backgrounds/2.mp4"


def parallel_assign(dsn, story_ids):
    def choose(story_id):
        with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as connection:
            return PgRpcClient(connection).rpc("assign_story_background", {"p_story": str(story_id)}).execute().data
    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(choose, story_ids))


def test_concurrent_workers_take_all_five_turns_before_repeating(pg, library):
    stories = [story(pg)[1] for _ in range(10)]
    expected = Counter({f"backgrounds/{n}.mp4": 1 for n in range(1, 6)})
    assert Counter(parallel_assign(pg.info.dsn, stories[:5])) == expected
    assert Counter(parallel_assign(pg.info.dsn, stories[5:])) == expected
    assert pg.execute("select count(distinct last_used_order) from background_clips").fetchone()["count"] == 5


def test_concurrent_retries_of_one_story_reserve_only_one_background(pg, library):
    _, same_story = story(pg)
    assert parallel_assign(pg.info.dsn, [same_story] * 5) == ["backgrounds/1.mp4"] * 5
    assert db.assign_story_background(story(pg)[1]) == "backgrounds/2.mp4"


def test_browser_keys_cannot_assign_backgrounds(pg):
    for role in ("anon", "authenticated"):
        assert not pg.execute("select has_function_privilege(%s,'assign_story_background(uuid)','execute') as allowed", (role,)).fetchone()["allowed"]


def test_service_role_can_reserve_a_new_background_under_rls(pg, library):
    _, story_id = story(pg)
    pg.execute("set role service_role")
    try:
        assert db.assign_story_background(story_id) == "backgrounds/1.mp4"
    finally:
        pg.execute("reset role")
