import base64
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from brainrot import api, db, library, media, publish, research, youtube


@pytest.fixture
def local(monkeypatch, tmp_path):
    monkeypatch.setenv("BRAINROT_MEDIA_STORAGE", "local")
    monkeypatch.setenv("BRAINROT_MEDIA_ROOT", "media")
    monkeypatch.setenv("DASHBOARD_API_KEY", "local-test-key")
    monkeypatch.setattr(media, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_local_write_and_copy_work_from_another_computer(local, fake_db, monkeypatch, tmp_path):
    relative = "stories/example/01.mp4"
    assert db.upload(relative, b"video", "video/mp4") == relative
    assert not fake_db.files
    other = tmp_path / "other-computer"
    shutil.copytree(local / "media", other / "media")
    monkeypatch.setattr(media, "PROJECT_ROOT", other)
    assert db.download(relative) == b"video"
    assert media.path(relative) == other / "media" / relative


@pytest.mark.parametrize("relative", ["../.env", "/etc/passwd", "C:/secrets", "stories/../../.env", "stories\\..\\.env", ".", ""])
def test_media_paths_cannot_escape_the_data_folder(local, relative):
    with pytest.raises(ValueError):
        media.path(relative)


def test_legacy_media_is_cached_without_uploading(local, fake_db):
    fake_db.files["backgrounds/old.mp4"] = b"legacy"
    assert db.download("backgrounds/old.mp4") == b"legacy"
    fake_db.files.clear()
    assert db.download("backgrounds/old.mp4") == b"legacy"


def test_local_video_links_support_ranges_and_reject_tampering(local):
    media.save("stories/example/01.mp4", b"0123456789")
    client = TestClient(api.app)
    url = media.signed_url("stories/example/01.mp4")
    response = client.get(url, headers={"Range": "bytes=2-4"})
    assert response.status_code == 206 and response.content == b"234"
    assert client.get(url.replace("01.mp4", "02.mp4")).status_code == 403
    assert not media.verify("stories/example/01.mp4", 1, "wrong")


def test_local_delete_cleans_subtitles_and_legacy_copy(local, fake_db):
    relative = "stories/example/01.mp4"
    media.save(relative, b"video")
    media.save("stories/example/01.srt", b"captions")
    fake_db.files[relative] = b"cloud"
    fake_db.functions["pending_media_cleanup"] = lambda **kwargs: [{"id": "one", "storage_path": relative, "is_referenced": False}]
    fake_db.functions["finish_media_cleanup"] = lambda **kwargs: True
    assert db.cleanup_media()
    assert not media.path(relative).exists()
    assert not media.path(relative).with_suffix(".srt").exists()
    assert not fake_db.files


def test_research_retains_sources_and_marks_unverified_claims(monkeypatch):
    def get(**params):
        if params.get("props") == "labels":
            return {"entities": {"P571": {"labels": {"en": {"value": "inception"}}}}}
        return {"entities": {"Q1": {"labels": {"en": {"value": "Example"}}, "claims": {"P571": [{
            "mainsnak": {"datavalue": {"value": {"time": "+1800-01-01T00:00:00Z"}}},
            "references": [{"snaks": {"P854": [{"datavalue": {"value": "https://example.org/source"}}]}}],
        }]}}}}
    monkeypatch.setattr(research, "_get", get)
    item = research.entity("Q1")
    assert item["facts"][0]["sources"] == ["https://example.org/source"]
    assert "unverified" in research.context(item)
    assert "Fictional premises retain their fictional rules" in research.context(item)


@pytest.fixture
def oauth(local, fake_db, monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "project-client")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "project-secret")
    calls = []
    def post(url, **options):
        calls.append(options["data"])
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
            "access_token": "private-access", "refresh_token": "private-refresh", "scope": " ".join(youtube.SCOPES), "expires_in": 3600})
    monkeypatch.setattr(youtube.requests, "post", post)
    monkeypatch.setattr(youtube, "_get", lambda *args, **kwargs: {"items": [{"id": "channel-one", "snippet": {"title": "My channel"},
        "contentDetails": {"relatedPlaylists": {"uploads": "uploads-one"}}}]})
    return calls


def test_oauth_uses_pkce_one_time_state_and_does_not_enable_auto_publish(oauth, fake_db):
    query = parse_qs(urlsplit(youtube.connect()["url"]).query)
    youtube.finish(query["state"][0], "auth-code")
    verifier = oauth[0]["code_verifier"]
    assert query["code_challenge"][0] == base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    with pytest.raises(ValueError, match="already used"):
        youtube.finish(query["state"][0], "auth-code")
    data = fake_db.rows("platform_credentials")[0]["data"]
    assert data["auto_publish"] is False and data["privacy_status"] == "private"
    assert "client_secret" not in data
    assert "private-access" not in json.dumps(youtube.status())
    assert len(oauth) == 1


def test_invalid_oauth_state_never_exchanges_a_code(oauth):
    with pytest.raises(ValueError):
        youtube.finish("not-issued", "code")
    assert not oauth


def test_connect_does_not_upload_existing_queue(oauth, fake_db, monkeypatch):
    query = parse_qs(urlsplit(youtube.connect()["url"]).query)
    youtube.finish(query["state"][0], "code")
    fake_db.table("publications").insert({"platform": "youtube", "chapter_id": "chapter", "scheduled_at": "2000-01-01T00:00:00+00:00"}).execute()
    monkeypatch.setattr(publish, "post_youtube", lambda *args, **kwargs: pytest.fail("connection must not publish backlog"))
    assert publish.run_due() == []
    assert fake_db.rows("publications")[0]["status"] == "scheduled"


def test_manual_upload_is_claimed_once_with_reviewed_metadata(fake_db):
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"access_token": "token", "auto_publish": False}}).execute()
    fake_db.table("story_chapters").insert({"id": "chapter-one", "story_id": "story", "chapter_index": 1, "status": "ready"}).execute()
    metadata = {"title": "Reviewed title", "privacy_status": "private"}
    row, claimed = youtube.prepare_upload("chapter", "chapter-one", metadata)
    assert claimed and row["metadata"] == metadata
    with pytest.raises(ValueError):
        youtube.prepare_upload("chapter", "chapter-one", {"title": "Second title"})
    assert len(fake_db.rows("publications")) == 1
    assert fake_db.rows("publications")[0]["metadata"] == metadata


def test_ambiguous_failed_upload_is_not_automatically_resubmitted(fake_db):
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"access_token": "token"}}).execute()
    fake_db.table("clips").insert({"id": "clip-one", "status": "ready"}).execute()
    fake_db.table("publications").insert({"platform": "youtube", "clip_id": "clip-one", "status": "failed"}).execute()
    with pytest.raises(ValueError, match="checked"):
        youtube.prepare_upload("clip", "clip-one", {})


def test_youtube_retention_accepts_real_nonzero_first_sample(fake_db, monkeypatch):
    fake_db.table("platform_credentials").insert({"platform": "youtube", "data": {"access_token": "token"}}).execute()
    monkeypatch.setattr(publish, "youtube_token", lambda data: "token")
    monkeypatch.setattr(youtube, "_get", lambda *args, **kwargs: {"items": [{"contentDetails": {"duration": "PT2M"}}]})
    monkeypatch.setattr(youtube.requests, "get", lambda *args, **kwargs: SimpleNamespace(raise_for_status=lambda: None,
        json=lambda: {"columnHeaders": [{"name": "elapsedVideoTimeRatio"}, {"name": "audienceWatchRatio"}], "rows": [[0.01, 1.1], [0.25, 0.8], [1, 0.6]]}))
    report = youtube.analytics("abcdefghijk", date(2025, 1, 1), date(2025, 1, 2))
    assert report["opening_start_seconds"] == 1.2
    assert report["last_observed_seconds"] == 120
    assert report["points"][0]["retention"] == pytest.approx(110)


def test_library_rejects_untrusted_download_host(local, monkeypatch):
    monkeypatch.setattr(library, "_json", lambda *args, **kwargs: {"collection": {"items": [{"href": "https://127.0.0.1/private.mp4"}]}})
    with pytest.raises(ValueError, match="unsupported"):
        library.import_video("nasa", "asset-one")


def test_library_needs_explicit_pexels_configuration(monkeypatch):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="PEXELS_API_KEY"):
        library.search("pexels", "space")


def test_oauth_callback_never_echoes_codes_or_provider_errors(local):
    response = TestClient(api.app).get("/youtube/callback?error=secret-diagnostic&state=private-state&code=private-code")
    assert response.status_code == 400
    assert all(value not in response.text for value in ("private-code", "secret-diagnostic", "private-state"))


def test_browser_range_requests_share_one_cloud_download(local, fake_db, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import time
    calls = []
    def download(path):
        calls.append(path)
        time.sleep(0.03)
        return b"one download"
    monkeypatch.setattr(fake_db.storage, "from_", lambda bucket: SimpleNamespace(download=download))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(db.download, ["stories/cached/01.mp4"] * 6))
    assert results == [b"one download"] * 6
    assert len(calls) == 1


def test_youtube_sends_reviewed_audience_and_disclosure_settings(monkeypatch):
    seen = []
    monkeypatch.setattr(publish, "youtube_token", lambda data: "token")
    def post(url, **options):
        seen.append(json.loads(options["data"]))
        return SimpleNamespace(raise_for_status=lambda: None, headers={"Location": "https://www.googleapis.com/session"})
    monkeypatch.setattr(publish.requests, "post", post)
    monkeypatch.setattr(publish.requests, "put", lambda *args, **kwargs: SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"id": "abcdefghijk"}))
    publish.post_youtube({}, b"video", "Reviewed title", "Description", privacy_status="private", tags=["story"], made_for_kids=True, contains_synthetic_media=True)
    assert seen[0]["status"] == {"privacyStatus": "private", "selfDeclaredMadeForKids": True, "containsSyntheticMedia": True}


def test_library_activation_is_idempotent_and_server_only(pg):
    first = pg.execute("select activate_library_background('backgrounds/nasa-test.mp4','Test',90,'nasa') as id").fetchone()["id"]
    second = pg.execute("select activate_library_background('backgrounds/nasa-test.mp4','Test',90,'nasa') as id").fetchone()["id"]
    assert first == second
    assert pg.execute("select count(*) from background_clips where storage_path='backgrounds/nasa-test.mp4'").fetchone()["count"] == 1
    assert not pg.execute("select has_function_privilege('anon','activate_library_background(text,text,double precision,text)','execute') as allowed").fetchone()["allowed"]
