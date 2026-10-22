import pytest

from brainrot import publish, youtube_metadata


@pytest.fixture(autouse=True)
def upload_copy(monkeypatch):
    monkeypatch.setattr(youtube_metadata, "draft", lambda *args: {"title": "Tale", "description": "A short tale. #Shorts", "tags": ["tale", "story", "shorts"]})


@pytest.fixture
def chapter(fake_db):
    story = fake_db.table("stories").insert({"job_id": "j1", "title": "Tale"}).execute().data[0]
    fake_db.files["stories/s/01.mp4"] = b"video"
    return fake_db.table("story_chapters").insert(
        {"story_id": story["id"], "chapter_index": 1, "text": "t",
         "video_path": "stories/s/01.mp4", "status": "ready"}
    ).execute().data[0]


@pytest.fixture
def youtube_creds(fake_db):
    fake_db.table("platform_credentials").insert(
        {"platform": "youtube", "data": {"access_token": "tok"}}
    ).execute()


def schedule(fake_db, chapter, platform="youtube") -> dict:
    return fake_db.table("publications").insert(
        {"platform": platform, "chapter_id": chapter["id"], "scheduled_at": "2000-01-01T00:00:00+00:00"}
    ).execute().data[0]


def test_publishes_and_records_the_post(fake_db, chapter, youtube_creds, monkeypatch):
    sent = []
    monkeypatch.setattr(publish, "post_youtube", lambda creds, video, title, desc, **kwargs: sent.append(video) or ("vid1", "https://y/vid1"))
    row = schedule(fake_db, chapter)

    assert publish.publish_one(row) is True

    stored = fake_db.rows("publications")[0]
    assert sent == [b"video"]
    assert stored["status"] == "published"
    assert stored["platform_post_id"] == "vid1"


def test_a_publication_is_uploaded_once_even_when_two_callers_race(fake_db, chapter, youtube_creds, monkeypatch):
    # The worker loop and `cli publish` can both read the same due row.
    uploads = []
    monkeypatch.setattr(publish, "post_youtube", lambda *a, **kw: uploads.append(1) or ("vid1", ""))
    row = schedule(fake_db, chapter)
    stale_copy = dict(row)

    assert publish.publish_one(row) is True
    assert publish.publish_one(stale_copy) is False
    assert len(uploads) == 1


def test_missing_credentials_leave_the_publication_scheduled(fake_db, chapter):
    row = schedule(fake_db, chapter, platform="tiktok")

    with pytest.raises(publish.MissingCredentials):
        publish.publish_one(row)

    # Still scheduled, so it goes out once the app is registered.
    assert fake_db.rows("publications")[0]["status"] == "scheduled"


def test_run_due_skips_platforms_without_credentials(fake_db, chapter, youtube_creds, monkeypatch):
    monkeypatch.setattr(publish, "post_youtube", lambda *a, **kw: ("vid1", ""))
    yt = schedule(fake_db, chapter, "youtube")
    schedule(fake_db, chapter, "tiktok")

    assert publish.run_due() == [yt["id"]]
    statuses = {r["platform"]: r["status"] for r in fake_db.rows("publications")}
    assert statuses == {"youtube": "published", "tiktok": "scheduled"}


def test_upload_failure_is_recorded_and_not_retried(fake_db, chapter, youtube_creds, monkeypatch):
    def boom(*_, **kwargs):
        raise RuntimeError("platform said no")

    monkeypatch.setattr(publish, "post_youtube", boom)
    row = schedule(fake_db, chapter)

    with pytest.raises(RuntimeError):
        publish.publish_one(row)
    stored = fake_db.rows("publications")[0]
    assert stored["status"] == "failed"
    assert "platform said no" in stored["error"]
