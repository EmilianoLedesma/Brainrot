from fastapi.testclient import TestClient
from brainrot import api, outputs


def test_output_details_are_scoped_to_job_and_exclude_private_metadata(fake_db):
    fake_db.table("stories").insert([{ "id": "story", "job_id": "job", "title": "Rome", "permalink": "https://example.org/source"},
                                     {"id": "other", "job_id": "another-job", "title": "Private other story"}]).execute()
    fake_db.table("story_chapters").insert([
        {"id": "chapter", "story_id": "story", "chapter_index": 1, "text": "The silver coins changed.", "status": "ready", "video_path": "stories/01.mp4"},
        {"id": "other-chapter", "story_id": "other", "chapter_index": 1, "text": "Other script", "status": "ready", "video_path": "stories/other.mp4"}]).execute()
    fake_db.table("publications").insert({"platform": "youtube", "chapter_id": "chapter", "status": "published", "platform_post_id": "abcdefghijk",
        "metadata": {"title": "Reviewed title", "access_token": "private-token"}, "analytics": {"views": 42, "averageViewPercentage": 65, "private": "private-secret"}, "error": "private diagnostic"}).execute()
    result = outputs.for_job("job", "http://localhost:8001")
    assert len(result) == 1
    assert result[0]["narration"] == "The silver coins changed."
    assert result[0]["source_url"] == "https://example.org/source"
    assert result[0]["publications"][0]["analytics"]["views"] == 42
    assert "private" not in str(result)


def test_clip_details_only_show_the_selected_transcript(fake_db):
    fake_db.table("source_videos").insert({"id": "source", "job_id": "job", "youtube_url": "https://youtube.com/watch?v=abcdefghijk", "transcript": [
        {"start": 0, "end": 10, "text": "Before"}, {"start": 10, "end": 100, "text": "Inside"}, {"start": 100, "end": 110, "text": "After"}]}).execute()
    fake_db.table("clips").insert({"id": "clip", "job_id": "job", "source_video_id": "source", "title": "A moment", "start_seconds": 10, "end_seconds": 100, "storage_path": "clips/one.mp4", "status": "ready"}).execute()
    assert outputs.for_job("job", "http://localhost")[0]["narration"] == "Inside"


def test_output_endpoint_requires_auth_and_valid_existing_job(fake_db, monkeypatch):
    monkeypatch.setattr(api, "API_KEY", "test")
    client = TestClient(api.app)
    route = "/jobs/00000000-0000-0000-0000-000000000001/outputs"
    assert client.get(route).status_code == 401
    client.headers["X-API-Key"] = "test"
    assert client.get(route).status_code == 404
    assert client.get("/jobs/not-a-uuid/outputs").status_code == 422
    fake_db.table("jobs").insert({"id": "00000000-0000-0000-0000-000000000001"}).execute()
    assert client.get(route).json() == []


def test_local_output_details_include_saved_captions(fake_db, monkeypatch, tmp_path):
    from brainrot import media
    monkeypatch.setenv("BRAINROT_MEDIA_STORAGE", "local")
    monkeypatch.setenv("BRAINROT_MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("DASHBOARD_API_KEY", "test")
    fake_db.table("stories").insert({"id": "story", "job_id": "job"}).execute()
    fake_db.table("story_chapters").insert({"id": "chapter", "story_id": "story", "chapter_index": 1, "text": "Text", "status": "ready", "video_path": "stories/01.mp4"}).execute()
    media.save("stories/01.srt", b"1\n00:00:00,000 --> 00:00:10,000\nText")
    item = outputs.for_job("job", "http://localhost:8001")[0]
    assert item["url"].startswith("http://localhost:8001/media/")
    assert item["subtitles"].endswith("Text")
