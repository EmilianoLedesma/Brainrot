"""A retried job resumes from what its earlier attempt left in the database.

Without this, a retry would call Claude again, render everything again, create
duplicate rows, and (for H2b) fail permanently on the unique reddit_post_id.
"""

import pytest

from brainrot import pipeline, reddit, render, repurpose, script, tts

SENTENCE = " ".join(["word"] * 99) + " end."  # 100 words
LONG_SCRIPT = " ".join([SENTENCE] * 3)  # splits into three chapters


@pytest.fixture
def background(fake_db):
    fake_db.files["backgrounds/bg.mp4"] = b"bg"
    fake_db.table("background_clips").insert(
        {"label": "bg", "storage_path": "backgrounds/bg.mp4", "active": True}
    ).execute()


@pytest.fixture
def narration(monkeypatch):
    calls = []

    def narrate(text, *, title):
        calls.append((title, text))
        return b"mp3", [{"text": "w", "start": 0, "end": 1}]

    monkeypatch.setattr(tts, "narrate", narrate)
    return calls


class FlakyRender:
    """Fails on the nth call, then always succeeds."""

    def __init__(self, fail_on: int | None):
        self.fail_on, self.calls = fail_on, 0

    def __call__(self, background, audio, words):
        self.calls += 1
        if self.calls == self.fail_on:
            raise TimeoutError("ffmpeg stalled")
        return b"mp4"


def run_twice(fn, job):
    with pytest.raises(TimeoutError):
        fn(job)
    return fn(job)


def test_h2_retry_reuses_the_script_and_finished_chapters(fake_db, background, narration, monkeypatch):
    writes = []
    monkeypatch.setattr(script, "write_story", lambda topic: writes.append(topic) or script.Story(title="T", script=LONG_SCRIPT))
    renders = FlakyRender(fail_on=2)
    monkeypatch.setattr(render, "render", renders)
    job = {"id": "job-1", "kind": "brainrot", "params": {"topic": "octopuses"}}

    story_id = run_twice(pipeline.run_brainrot, job)

    assert writes == ["octopuses"], "Claude is called once across both attempts"
    assert renders.calls == 4, "chapter 1 once, chapter 2 twice, chapter 3 once"
    assert [title for title, text in narration] == ["T"] * 4
    assert len(fake_db.rows("stories")) == 1
    chapters = fake_db.rows("story_chapters")
    assert sorted(c["chapter_index"] for c in chapters) == [1, 2, 3]
    assert all(c["status"] == "ready" for c in chapters)
    assert fake_db.rows("stories")[0]["status"] == "ready"
    # Chapter 1 queued on each platform exactly once.
    pubs = fake_db.rows("publications")
    assert len(pubs) == 3 and all(p["chapter_id"] for p in pubs)
    assert story_id == fake_db.rows("stories")[0]["id"]


def test_chapters_and_retry_keep_their_background_when_another_job_takes_a_turn(fake_db, background, narration, monkeypatch):
    fake_db.table("background_clips").insert(
        {"storage_path": "backgrounds/second.mp4", "active": True, "rotation_order": 2}
    ).execute()
    fake_db.files["backgrounds/second.mp4"] = b"second gameplay"
    monkeypatch.setattr(script, "write_story", lambda topic: script.Story(title="T", script=LONG_SCRIPT))
    used = []

    def render_chapter(background, audio, words):
        used.append(background)
        if len(used) == 2:
            raise TimeoutError("render interrupted")
        return b"video"

    monkeypatch.setattr(render, "render", render_chapter)
    job = {"id": "job-first", "params": {"topic": "History"}}
    with pytest.raises(TimeoutError):
        pipeline.run_brainrot(job)
    other = fake_db.table("stories").insert({"job_id": "job-other"}).execute().data[0]
    assert pipeline.pick_background(other["id"]) == b"second gameplay"
    pipeline.run_brainrot(job)
    assert used == [b"bg"] * 4


@pytest.mark.parametrize("level", [0, 35, 100])
def test_h2_applies_saved_intensity_once_across_retries(fake_db, background, narration, monkeypatch, level):
    writes = []
    def write(topic, *, brainrot_level):
        writes.append((topic, brainrot_level))
        return script.Story(title="T", script="A saved story.")
    monkeypatch.setattr(script, "write_story", write)
    monkeypatch.setattr(render, "render", FlakyRender(fail_on=1))
    job = {"id": "job-level", "kind": "brainrot", "params": {"topic": "octopuses", "brainrot_level": level}}
    run_twice(pipeline.run_brainrot, job)
    assert writes == [("octopuses", level)]
    assert len(fake_db.rows("stories")) == 1
    assert fake_db.rows("story_chapters")[0]["status"] == "ready"


def test_planning_a_story_twice_does_not_double_queue(fake_db, background, narration, monkeypatch):
    monkeypatch.setattr(script, "write_story", lambda topic: script.Story(title="T", script="Short. Story."))
    monkeypatch.setattr(render, "render", FlakyRender(fail_on=None))
    job = {"id": "job-1", "kind": "brainrot", "params": {"topic": "t"}}

    pipeline.run_brainrot(job)
    pipeline.run_brainrot(job)  # e.g. completed, but the lease was lost before it was recorded

    assert len(fake_db.rows("stories")) == 1
    assert len(fake_db.rows("publications")) == 3


def test_h2b_retry_does_not_hit_the_unique_post_id(fake_db, background, narration, monkeypatch):
    monkeypatch.setattr(script, "rewrite_post", lambda title, body: script.Story(title=title, script=LONG_SCRIPT))
    monkeypatch.setattr(render, "render", FlakyRender(fail_on=1))
    job = {
        "id": "job-2",
        "kind": "reddit",
        "params": {"reddit_post_id": "abc", "subreddit": "tifu", "title": "TIFU",
                   "body": "...", "permalink": "https://reddit.com/x", "upvotes": 5000},
    }

    run_twice(reddit.run_reddit, job)

    stories = fake_db.rows("stories")
    assert len(stories) == 1 and stories[0]["reddit_post_id"] == "abc"
    assert all(title == "TIFU" for title, text in narration)


def test_reddit_scan_queues_a_post_only_once(fake_db, monkeypatch):
    post = {"reddit_post_id": "abc", "subreddit": "tifu", "title": "t", "body": "b",
            "permalink": "p", "upvotes": 1}
    monkeypatch.setattr(reddit, "find_posts", lambda: [post])

    first = reddit.scan()
    monkeypatch.setattr(reddit, "find_posts", lambda: [post])
    reddit.scan()

    assert len(fake_db.rows("jobs")) == 1
    assert fake_db.rows("jobs")[0]["idempotency_key"] == "reddit:abc"
    assert first == [fake_db.rows("jobs")[0]["id"]]


def test_find_posts_skips_posts_that_already_have_a_job(fake_db):
    fake_db.table("jobs").insert({"kind": "reddit", "idempotency_key": "reddit:abc"}).execute()
    assert reddit.already_used(["abc", "def"]) == {"abc"}


def test_h1_retry_reuses_the_transcript_and_moment_selection(fake_db, monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"src")
    monkeypatch.setattr(repurpose, "download", lambda url, d: (str(source), {"id": "yt1", "title": "Talk", "duration": 600}))
    transcripts, selections = [], []
    monkeypatch.setattr(repurpose, "transcribe", lambda path, d: transcripts.append(1) or [{"text": "hi", "start": 0, "end": 30}])
    moments = [
        repurpose.Moment(start_seconds=0, end_seconds=20, title="a", reason="r", score=0.9),
        repurpose.Moment(start_seconds=30, end_seconds=50, title="b", reason="r", score=0.8),
    ]
    monkeypatch.setattr(repurpose, "select_moments", lambda t: selections.append(1) or moments)

    cuts = []

    def cut(source_path, moment, transcript, directory):
        cuts.append(moment.title)
        if cuts == ["a", "b"]:
            raise TimeoutError("ffmpeg stalled")
        out = tmp_path / f"{moment.title}.mp4"
        out.write_bytes(b"clip")
        return str(out)

    monkeypatch.setattr(repurpose, "cut_and_reframe", cut)
    job = {"id": "job-3", "kind": "repurpose", "params": {"youtube_url": "https://youtu.be/x"}}

    run_twice(repurpose.run_repurpose, job)

    assert transcripts == [1] and selections == [1]
    assert cuts == ["a", "b", "b"], "clip a is not cut again"
    assert len(fake_db.rows("source_videos")) == 1
    clips = fake_db.rows("clips")
    assert len(clips) == 2 and all(c["status"] == "ready" for c in clips)
    assert len(fake_db.rows("publications")) == 6  # two clips x three platforms
