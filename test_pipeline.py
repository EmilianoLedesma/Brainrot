"""Self-checks for the parts with real logic in them.

Everything here runs offline: no Supabase, no Claude, no network. Run with
`python test_pipeline.py`.
"""

import os
import subprocess
import tempfile

from brainrot import render, repurpose
from brainrot.pipeline import split_chapters


def test_split_chapters():
    short = "One sentence. Two sentence."
    assert split_chapters(short) == [short]

    sentence = "word " * 50 + "end. "
    long_script = sentence * 5
    chapters = split_chapters(long_script)
    assert len(chapters) > 1, "a long script must split"
    # Splitting mid-sentence would cut a chapter off mid-thought.
    assert all(c.rstrip().endswith((".", "!", "?")) for c in chapters), chapters
    # Nothing may be dropped on the way through.
    assert sum(len(c.split()) for c in chapters) == len(long_script.split())


def test_timestamps():
    assert render._timestamp(0) == "0:00:00.00"
    assert render._timestamp(61.5) == "0:01:01.50"
    assert render._timestamp(3661.239) == "1:01:01.24"


def test_captions_cover_gaps():
    words = [
        {"text": "hello", "start": 0.0, "end": 0.3},
        {"text": "there", "start": 1.0, "end": 1.4},
    ]
    ass = render.build_captions(words)
    # The first word must hold until the second starts, or the screen goes blank
    # mid-sentence between them.
    assert "0:00:00.00,0:00:01.00" in ass, ass
    assert "HELLO" in ass and "THERE" in ass
    # Braces would open an ASS override block and swallow the text.
    assert "{" not in ass.split("[Events]")[1]


def test_vtt_parsing():
    vtt = """WEBVTT

00:00:01.000 --> 00:00:03.000
<c>first line</c>

00:00:03.000 --> 00:00:05.000
first line

00:00:05.000 --> 00:00:07.500
second line
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "subs.vtt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(vtt)
        cues = repurpose.parse_vtt(path)
    # YouTube repeats the previous line on every new cue; duplicates must collapse.
    assert [c["text"] for c in cues] == ["first line", "second line"], cues
    assert cues[0]["start"] == 1.0 and cues[1]["end"] == 7.5


def test_crop_expression_stays_in_frame():
    width, crop = 1920, 1080
    limit = width - crop

    # A face hard against either edge must not crop outside the frame.
    assert repurpose.crop_expression([(0.0, 0.0)], width, crop) == "0"
    assert repurpose.crop_expression([(0.0, 1.0)], width, crop) == str(limit)
    # No detections at all: centre the frame rather than crash.
    assert repurpose.crop_expression([], width, crop) == str(limit // 2)

    expression = repurpose.crop_expression([(0.0, 0.2), (1.0, 0.8)], width, crop)
    assert expression.startswith("if(lt(t,1.00),"), expression


def test_smoothing_applies_deadzone():
    # Jitter below the deadzone must not produce a keyframe.
    jitter = [(i * 0.5, 0.5 + (0.001 if i % 2 else -0.001)) for i in range(10)]
    assert len(repurpose.smooth(jitter)) == 1

    # A real move must.
    move = [(i * 0.5, 0.2 if i < 5 else 0.8) for i in range(10)]
    assert len(repurpose.smooth(move)) > 1
    assert repurpose.smooth([]) == []


def test_reframe_produces_vertical_video():
    """The one check that actually runs ffmpeg end to end."""
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "src.mp4")
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "testsrc2=size=1280x720:rate=30:duration=3",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", source],
            check=True,
        )
        moment = repurpose.Moment(
            start_seconds=0.0, end_seconds=2.0, title="t", reason="r", score=0.9
        )
        transcript = [{"text": "spoken words here", "start": 0.0, "end": 2.0}]
        # Skip face detection: a test pattern has no face, and the model would
        # have to be fetched from Storage.
        repurpose.track_face = lambda path: [(0.0, 0.3), (1.0, 0.7)]
        output = repurpose.cut_and_reframe(source, moment, transcript, tmp)

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", output],
            capture_output=True, text=True, check=True,
        )
        assert probe.stdout.strip() == f"{render.WIDTH},{render.HEIGHT}", probe.stdout


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
            print(f"ok  {name}")
    print("all checks passed")
