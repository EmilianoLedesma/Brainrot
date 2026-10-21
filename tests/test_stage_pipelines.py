import pytest

from brainrot import db, pipeline, reddit, render, repurpose, script, tts
from brainrot.domain.pipelines import PipelineContext
from brainrot.pipelines import create_registry


@pytest.fixture
def tracked_stages(monkeypatch):
    records = []

    def start(context, name, scope):
        records.append({"context": context, "stage": name, "scope": scope, "status": "running"})
        return str(len(records) - 1)

    def finish(execution_id, worker_id, status, error=None):
        records[int(execution_id)].update(status=status, error=error)
        return True

    monkeypatch.setattr(db, "start_stage", start)
    monkeypatch.setattr(db, "finish_stage", finish)
    return records


@pytest.fixture
def story_dependencies(fake_db, monkeypatch):
    fake_db.table("background_clips").insert({"storage_path": "bg.mp4", "active": True}).execute()
    fake_db.files["bg.mp4"] = b"background"
    monkeypatch.setattr(script, "write_story", lambda topic: script.Story(title="Story", script="A short story."))
    monkeypatch.setattr(script, "rewrite_post", lambda title, body: script.Story(title=title, script="A short story."))
    monkeypatch.setattr(tts, "narrate", lambda text, **kwargs: (b"audio", []))
    monkeypatch.setattr(render, "render", lambda *args: b"video")


@pytest.mark.parametrize("kind,params", [
    ("brainrot", {"topic": "a topic"}),
    ("reddit", {"title": "A post", "body": "body", "reddit_post_id": "abc",
                "subreddit": "stories", "permalink": "link", "upvotes": 1000}),
])
def test_story_adapters_track_all_major_operations(kind, params, story_dependencies, tracked_stages):
    context = PipelineContext("job-1", kind, params, 1, "worker-a")
    create_registry().get(kind).execute(context)
    assert [(r["stage"], r["scope"]) for r in tracked_stages] == [
        ("script", ""), ("chaptering", ""), ("background", ""),
        ("tts", "chapter:1"), ("render", "chapter:1"),
        ("upload", "chapter:1"), ("schedule", ""),
    ]
    assert all(r["status"] == "done" and r["context"] == context for r in tracked_stages)


def test_resumed_story_does_not_report_cached_script_as_executed(story_dependencies, tracked_stages, monkeypatch):
    def fail(*args):
        raise TimeoutError("renderer unavailable")

    monkeypatch.setattr(render, "render", fail)
    context = PipelineContext("job-1", "brainrot", {"topic": "topic"}, 1, "worker-a")
    with pytest.raises(TimeoutError):
        create_registry().get("brainrot").execute(context)
    assert tracked_stages[-1]["stage"] == "render"
    assert tracked_stages[-1]["status"] == "failed"
    monkeypatch.setattr(render, "render", lambda *args: b"video")
    retried = PipelineContext("job-1", "brainrot", {"topic": "topic"}, 2, "worker-b")
    create_registry().get("brainrot").execute(retried)
    assert len([r for r in tracked_stages if r["stage"] == "script"]) == 1
    assert all(r["status"] == "done" for r in tracked_stages if r["context"].attempt == 2)


def test_repurpose_adapter_tracks_download_transcript_selection_render_upload_and_schedule(
    fake_db, tracked_stages, monkeypatch, tmp_path,
):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    monkeypatch.setattr(repurpose, "download", lambda *args: (str(source), {"id": "yt-1"}))
    monkeypatch.setattr(repurpose, "transcribe", lambda *args: [{"text": "hello", "start": 0, "end": 20}])
    monkeypatch.setattr(repurpose, "select_moments", lambda *args: [
        repurpose.Moment(start_seconds=0, end_seconds=20, title="Clip", reason="reason", score=0.9),
    ])
    monkeypatch.setattr(repurpose, "cut_and_reframe", lambda *args: str(source))
    context = PipelineContext("job-1", "repurpose", {"youtube_url": "https://youtu.be/example"}, 1, "worker-a")
    create_registry().get("repurpose").execute(context)
    clip_id = fake_db.rows("clips")[0]["id"]
    assert [(r["stage"], r["scope"]) for r in tracked_stages] == [
        ("download", ""), ("transcribe", ""), ("selection", ""),
        ("render", clip_id), ("upload", clip_id), ("schedule", clip_id),
    ]
    assert all(r["status"] == "done" for r in tracked_stages)
