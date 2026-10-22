import json
import pytest
from fastapi.testclient import TestClient

from brainrot import api, publish, youtube_metadata as copy
from brainrot.domain.jobs import PermanentError


@pytest.fixture
def story(fake_db, monkeypatch):
    fake_db.table("jobs").insert({"id": "job", "params": {"llm_provider": "codex"}}).execute()
    fake_db.table("stories").insert({"id": "story", "job_id": "job", "title": "Silver crisis", "permalink": "https://example.org/source"}).execute()
    chapter = fake_db.table("story_chapters").insert({"id": "chapter", "story_id": "story", "chapter_index": 1,
        "text": "Rome debased its silver coins.", "status": "ready", "video_path": "stories/one.mp4"}).execute().data[0]
    fake_db.files["stories/one.mp4"] = b"video"
    calls = []
    def generate(system, user, schema, **options):
        calls.append((system, json.loads(user), options))
        return schema(title="Rome's Vanishing Silver", description="How Rome's coins changed. #History #Shorts", tags=["Rome", "silver coins", "history"])
    monkeypatch.setattr(copy.llm, "generate", generate)
    return chapter, calls


def test_draft_uses_narration_repo_skill_job_provider_and_cache(story):
    chapter, calls = story
    result = copy.draft("chapter", chapter["id"])
    assert "Source: https://example.org/source" in result["description"]
    assert copy.draft("chapter", chapter["id"]) == result
    assert len(calls) == 1
    assert calls[0][1]["narration"] == chapter["text"]
    assert calls[0][2]["provider"] == "codex"
    assert "#Shorts" in calls[0][0]
    copy.draft("chapter", chapter["id"], regenerate=True)
    assert len(calls) == 2


def test_changed_narration_invalidates_draft(story, fake_db):
    chapter, calls = story
    copy.draft("chapter", chapter["id"])
    fake_db.table("story_chapters").update({"text": "A revised explanation."}).eq("id", chapter["id"]).execute()
    copy.draft("chapter", chapter["id"])
    assert len(calls) == 2
    assert len(fake_db.rows("youtube_metadata_drafts")) == 1


def test_clip_uses_only_selected_transcript(story, fake_db):
    _, calls = story
    fake_db.table("source_videos").insert({"id": "source", "transcript": [
        {"start": 0, "end": 10, "text": "Unrelated introduction"}, {"start": 10, "end": 100, "text": "The selected story"},
        {"start": 100, "end": 120, "text": "Unrelated ending"}], "youtube_url": "https://www.youtube.com/watch?v=abcdefghijk"}).execute()
    fake_db.table("clips").insert({"id": "clip", "job_id": "job", "source_video_id": "source", "start_seconds": 10, "end_seconds": 100, "status": "ready"}).execute()
    result = copy.draft("clip", "clip")
    assert calls[0][1]["narration"] == "The selected story"
    assert "youtube.com/watch" in result["description"]


def test_automatic_upload_saves_generated_metadata_before_transmission(story, fake_db, monkeypatch):
    chapter, calls = story
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"access_token": "test", "privacy_status": "unlisted"}}).execute()
    publication = fake_db.table("publications").insert({"chapter_id": chapter["id"], "platform": "youtube"}).execute().data[0]
    def upload(creds, video, title, description, **settings):
        assert fake_db.rows("publications")[0]["metadata"]["title"] == title
        assert "#Shorts" in description and settings["tags"] == ["Rome", "silver coins", "history"]
        assert settings["privacy_status"] == "unlisted"
        return "video", "https://youtube.com/shorts/video"
    monkeypatch.setattr(publish, "post_youtube", upload)
    assert publish.publish_one(publication)
    assert len(calls) == 1


def test_reviewed_metadata_wins_without_model_call(story, fake_db, monkeypatch):
    chapter, calls = story
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"access_token": "test"}}).execute()
    row = fake_db.table("publications").insert({"chapter_id": chapter["id"], "platform": "youtube",
        "metadata": {"title": "My edit", "description": "My description", "tags": ["edited"]}}).execute().data[0]
    def upload(creds, video, title, description, **settings):
        assert title == "My edit" and description == "My description"
        return "video", ""
    monkeypatch.setattr(publish, "post_youtube", upload)
    assert publish.publish_one(row)
    assert calls == []


def test_generation_failure_never_uploads(story, fake_db, monkeypatch):
    chapter, _ = story
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"access_token": "test"}}).execute()
    row = fake_db.table("publications").insert({"chapter_id": chapter["id"], "platform": "youtube"}).execute().data[0]
    def unavailable(*args, **kwargs):
        raise PermanentError("private CLI diagnostic")
    monkeypatch.setattr(copy.llm, "generate", unavailable)
    monkeypatch.setattr(publish, "post_youtube", lambda *args, **kwargs: pytest.fail("must not upload"))
    with pytest.raises(PermanentError):
        publish.publish_one(row)
    assert not fake_db.rows("youtube_metadata_drafts")


def test_metadata_api_is_authenticated_and_hides_model_errors(monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test-key")
    def unavailable(*args, **kwargs):
        raise PermanentError("private CLI diagnostic")
    monkeypatch.setattr(copy, "draft", unavailable)
    client = TestClient(api.app)
    payload = {"source": "chapter", "target_id": "00000000-0000-0000-0000-000000000001"}
    assert client.post("/youtube/metadata", json=payload).status_code == 401
    response = client.post("/youtube/metadata", json=payload, headers={"X-API-Key": "test-key"})
    assert response.status_code == 503 and "private CLI" not in response.text


def test_metadata_drafts_cascade_and_are_not_browser_accessible(pg):
    job = pg.execute("insert into jobs(kind) values('brainrot') returning id").fetchone()["id"]
    story = pg.execute("insert into stories(job_id) values(%s) returning id", (job,)).fetchone()["id"]
    chapter = pg.execute("insert into story_chapters(story_id,chapter_index,text) values(%s,1,'text') returning id", (story,)).fetchone()["id"]
    pg.execute("insert into youtube_metadata_drafts(chapter_id,fingerprint,metadata) values(%s,'test','{}')", (chapter,))
    # Supabase may grant table SELECT by default; RLS must still hide every row.
    pg.execute("grant select on youtube_metadata_drafts to anon")
    pg.execute("set role anon")
    assert not pg.execute("select * from youtube_metadata_drafts").fetchall()
    pg.execute("reset role")
    pg.execute("delete from jobs where id=%s", (job,))
    assert not pg.execute("select * from youtube_metadata_drafts").fetchall()
