"""Compose narration, a looping background, and karaoke captions into 9:16 video."""

import json
import math
import os
import subprocess
import tempfile

from .duration import check_media
from .domain.jobs import PermanentError

WIDTH, HEIGHT = 1080, 1920
# Leave headroom below the hosted storage service's common 50 MB object cap.
# At 180 seconds the constrained video plus 128 kbps audio stays below 45 MB.
MAX_VIDEO_BYTES = 45_000_000
VIDEO_RATE_OPTIONS = ("-maxrate", "1800k", "-bufsize", "3600k")
VOICE_FILTER = "loudnorm=I=-16:TP=-1.5:LRA=11"


def check_captions(words: list[dict], seconds: float) -> None:
    previous = -1.0
    for word in words:
        start, end = word["start"], word["end"]
        if (not math.isfinite(start) or not math.isfinite(end) or start < 0
                or start <= previous or end <= start or end > seconds + 0.25):
            raise PermanentError("The captions could not be aligned with the video. Please try again.")
        previous = start


def check_video(path: str) -> None:
    if os.path.getsize(path) > MAX_VIDEO_BYTES:
        raise PermanentError("The video is too large to store. Please try again with a simpler video.")
    check_media(path)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    streams = json.loads(probe.stdout).get("streams", [])
    video = next((stream for stream in streams if stream["codec_type"] == "video"), {})
    audio = next((stream for stream in streams if stream["codec_type"] == "audio"), {})
    if (video.get("width"), video.get("height"), video.get("codec_name"), audio.get("codec_name")) != (WIDTH, HEIGHT, "h264", "aac"):
        raise PermanentError("The video did not pass its picture and audio checks. Please try again.")

# One word on screen at a time, centred and oversized. Alignment 5 is
# middle-centre; the heavy outline keeps text readable over any background.
_ASS_HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Pop,Arial Black,120,&H00FFFFFF,&H00000000,&H00000000,1,1,8,0,5,80,80,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _timestamp(seconds: float) -> str:
    """ASS wants H:MM:SS.cc with centisecond precision."""
    centis = round(seconds * 100)
    h, rem = divmod(centis, 360000)
    m, rem = divmod(rem, 6000)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def build_captions(words: list[dict]) -> str:
    """Hold words across short gaps, clearing captions during narration pauses."""
    lines = [_ASS_HEADER]
    for i, word in enumerate(words):
        text = word["text"].strip()
        if not text:
            continue
        # Braces open an ASS override block, so they cannot reach the renderer raw.
        text = text.replace("\\", "").replace("{", "(").replace("}", ")")
        end = min(words[i + 1]["start"], word["end"] + 0.10) if i + 1 < len(words) else word["end"]
        # A provider's word boundary can overlap the next word slightly. Clear
        # the old caption at the next start rather than showing both together.
        end = max(end, word["start"])
        lines.append(
            f"Dialogue: 0,{_timestamp(word['start'])},{_timestamp(end)},Pop,,0,0,0,,{text.upper()}"
        )
    return "\n".join(lines) + "\n"


def build_srt(words: list[dict]) -> str:
    def stamp(seconds):
        milliseconds = round(seconds * 1000)
        hours, rest = divmod(milliseconds, 3_600_000)
        minutes, rest = divmod(rest, 60_000)
        seconds, milliseconds = divmod(rest, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    return "\n\n".join(f"{index}\n{stamp(word['start'])} --> {stamp(word['end'])}\n{word['text']}"
                         for index, word in enumerate(words, 1)) + "\n"


def render(background: bytes, narration: bytes, words: list[dict]) -> bytes:
    """Loop the background under the narration, burn in the captions, return mp4."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = {
            "bg.mp4": background,
            "voice.mp3": narration,
            "captions.ass": build_captions(words).encode("utf-8"),
        }
        for name, data in paths.items():
            with open(os.path.join(tmp, name), "wb") as handle:
                handle.write(data)

        seconds = check_media(os.path.join(tmp, "voice.mp3"))
        check_captions(words, seconds)

        # Run from the temp directory and pass bare filenames: the subtitles filter
        # treats ':' and '\' as syntax, which every Windows absolute path contains.
        command = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-stream_loop", "-1", "-i", "bg.mp4",
            "-i", "voice.mp3",
            "-filter_complex",
            f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},setsar=1,subtitles=captions.ass[v]",
            "-map", "[v]", "-map", "1:a",
            "-shortest",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            *VIDEO_RATE_OPTIONS,
            "-af", VOICE_FILTER,
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "out.mp4",
        ]
        result = subprocess.run(command, cwd=tmp, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[-500:]}")
        check_video(os.path.join(tmp, "out.mp4"))
        with open(os.path.join(tmp, "out.mp4"), "rb") as handle:
            return handle.read()
