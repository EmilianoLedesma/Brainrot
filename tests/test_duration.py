import subprocess
from types import SimpleNamespace

import pytest

from brainrot import duration, pipeline, render, repurpose, tts
from brainrot.domain.jobs import PermanentError


@pytest.mark.parametrize("seconds", [90, 120, 180])
def test_duration_includes_both_boundaries(seconds):
    duration.require_duration(seconds)


@pytest.mark.parametrize("seconds", [0, 89.99, 180.01, float("nan"), float("inf")])
def test_duration_rejects_outside_range(seconds):
    with pytest.raises(PermanentError, match="between 90 and 180 seconds"):
        duration.require_duration(seconds)


def test_normal_story_is_not_split_into_short_videos():
    story = " ".join(["A complete sentence about the next event."] * 45)
    assert 280 <= len(story.split()) <= 380
    assert pipeline.split_chapters(story) == [story]


def test_long_story_balances_chapters_without_short_tail():
    sentence = " ".join(["word"] * 49) + " end."
    story = " ".join([sentence] * 12)
    chapters = pipeline.split_chapters(story)
    assert [len(chapter.split()) for chapter in chapters] == [300, 300]
    assert " ".join(chapters) == story


def test_too_short_narration_is_rejected_before_encoding(monkeypatch):
    async def synthesize(*args):
        return b"speech", []

    monkeypatch.setattr(tts, "_synthesize", synthesize)
    monkeypatch.setattr(tts, "_ffmpeg", lambda *args: b"\0" * tts.BYTES_PER_SECOND)
    with pytest.raises(PermanentError, match="between 90 and 180 seconds"):
        tts.narrate("This story is too short.", title="A title")


@pytest.mark.parametrize("seconds,valid", [(89, False), (90, True), (180, True), (181, False)])
def test_moment_selection_filters_duration(monkeypatch, seconds, valid):
    moment = repurpose.Moment(start_seconds=0, end_seconds=seconds, title="Story", reason="Complete", score=0.9)
    monkeypatch.setattr(repurpose.llm, "generate", lambda *args, **kwargs: SimpleNamespace(moments=[moment]))
    if valid:
        assert repurpose.select_moments([]) == [moment]
    else:
        with pytest.raises(PermanentError, match="No complete"):
            repurpose.select_moments([])


def test_real_rendered_video_duration_is_checked(tmp_path, monkeypatch):
    background = tmp_path / "bg.mp4"
    narration = tmp_path / "voice.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "color=c=blue:s=160x284:r=10:d=1", "-c:v", "libx264", str(background)], check=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=91", "-c:a", "libmp3lame", str(narration)], check=True)
    monkeypatch.setattr(render, "WIDTH", 160)
    monkeypatch.setattr(render, "HEIGHT", 284)
    output = tmp_path / "video.mp4"
    output.write_bytes(render.render(background.read_bytes(), narration.read_bytes(), []))
    assert 90 <= duration.check_media(output) <= 180
    assert output.stat().st_size < render.MAX_VIDEO_BYTES


def test_oversized_finished_video_cannot_reach_upload(tmp_path, monkeypatch):
    output = tmp_path / "oversized.mp4"
    output.write_bytes(b"too large")
    monkeypatch.setattr(render, "check_media", lambda path: 120)
    monkeypatch.setattr(render, "MAX_VIDEO_BYTES", 4)
    with pytest.raises(PermanentError, match="too large to store"):
        render.check_video(output)


def test_render_rejects_short_audio_before_encoding_video(tmp_path):
    narration = tmp_path / "short.mp3"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "sine=duration=1", str(narration)], check=True)
    with pytest.raises(PermanentError, match="between 90 and 180 seconds"):
        render.render(b"unused background", narration.read_bytes(), [])
