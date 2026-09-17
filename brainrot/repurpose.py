"""H1: turn a long YouTube video into vertical clips.

Downloads the source, gets a transcript, asks Claude which moments stand alone,
then cuts each one and reframes it to 9:16 following the speaker's face.
"""

import os
import re
import subprocess
import tempfile

import anthropic
import cv2
import numpy as np
import yt_dlp
from pydantic import BaseModel

from . import db, render, scheduler, script

FACE_MODEL_PATH = "models/face_detection_yunet_2023mar.onnx"

# Face positions are sampled this often and the crop is keyframed at the same rate.
# Faster sampling tracks better but makes the ffmpeg crop expression longer.
SAMPLE_FPS = 2.0
# Ignore drift smaller than this fraction of frame width, so a speaker who merely
# shifts in their seat does not make the frame wobble.
DEADZONE = 0.02
SMOOTHING_WINDOW = 5


class Moment(BaseModel):
    start_seconds: float
    end_seconds: float
    title: str
    reason: str
    score: float


class Moments(BaseModel):
    moments: list[Moment]


SELECT_SYSTEM = """You pick moments from a transcript that work as standalone
vertical short-form clips.

A moment qualifies only if it:
- opens on a line that makes sense with no preceding context,
- contains one complete idea, claim, or story,
- ends on a natural beat rather than mid-sentence,
- runs between fifteen and sixty seconds.

Score each from 0 to 1 on how likely a scrolling viewer is to watch it through.
Return the strongest moments only - returning three good ones beats returning ten
padded ones. Timestamps must come from the transcript, never invented."""


def download(url: str, directory: str) -> tuple[str, dict]:
    """Fetch the video plus any transcript YouTube already has."""
    options = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "outtmpl": os.path.join(directory, "source.%(ext)s"),
        "merge_output_format": "mp4",
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    return os.path.join(directory, "source.mp4"), info


def parse_vtt(path: str) -> list[dict]:
    """Read WebVTT cues into {text, start, end}.

    YouTube's automatic captions repeat the previous line on every new cue, so
    consecutive duplicates are dropped.
    """

    def seconds(stamp: str) -> float:
        hours, minutes, rest = stamp.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(rest.replace(",", "."))

    cues: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    for block in content.split("\n\n"):
        match = re.search(r"(\d+:\d+:\d+[.,]\d+)\s*-->\s*(\d+:\d+:\d+[.,]\d+)", block)
        if not match:
            continue
        lines = [
            re.sub(r"<[^>]+>", "", line).strip()
            for line in block.splitlines()[1:]
            if "-->" not in line
        ]
        text = " ".join(line for line in lines if line).strip()
        if not text or (cues and cues[-1]["text"] == text):
            continue
        cues.append(
            {"text": text, "start": seconds(match.group(1)), "end": seconds(match.group(2))}
        )
    return cues


def transcribe(video_path: str, directory: str) -> list[dict]:
    """Prefer YouTube's own captions; fall back to running Whisper locally.

    The published captions are free and instant. Whisper only runs when a video
    has none, which costs a model download on first use.
    """
    for name in sorted(os.listdir(directory)):
        if name.endswith(".vtt"):
            cues = parse_vtt(os.path.join(directory, name))
            if cues:
                return cues

    from faster_whisper import WhisperModel

    model = WhisperModel(os.getenv("WHISPER_MODEL", "base"), device="cpu", compute_type="int8")
    segments, _ = model.transcribe(video_path)
    return [{"text": s.text.strip(), "start": s.start, "end": s.end} for s in segments]


def select_moments(transcript: list[dict]) -> list[Moment]:
    lines = "\n".join(f"[{c['start']:.1f}] {c['text']}" for c in transcript)
    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=script.MODEL,
        max_tokens=8000,
        system=SELECT_SYSTEM,
        messages=[{"role": "user", "content": f"Transcript:\n{lines}"}],
        output_format=Moments,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined: {response.stop_details}")
    return sorted(response.parsed_output.moments, key=lambda m: m.score, reverse=True)


def face_model_path() -> str:
    """Cache the detector weights locally; the copy of record lives in Storage."""
    local = os.path.join(tempfile.gettempdir(), "yunet.onnx")
    if not os.path.exists(local):
        with open(local, "wb") as handle:
            handle.write(db.download(FACE_MODEL_PATH))
    return local


def track_face(clip_path: str) -> list[tuple[float, float]]:
    """Sample the clip and return (time, face centre x as a 0..1 fraction) pairs."""
    capture = cv2.VideoCapture(clip_path)
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    detector = cv2.FaceDetectorYN.create(face_model_path(), "", (width, height))

    step = max(1, int(round(fps / SAMPLE_FPS)))
    samples: list[tuple[float, float]] = []
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % step == 0:
            _, faces = detector.detect(frame)
            if faces is not None and len(faces):
                # Biggest face wins: in an interview that is whoever is closest to camera.
                best = max(faces, key=lambda f: f[2] * f[3])
                samples.append((index / fps, float((best[0] + best[2] / 2) / width)))
        index += 1
    capture.release()
    return samples


def smooth(samples: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Moving average plus a deadzone, so the crop glides instead of snapping."""
    if not samples:
        return []
    times = [t for t, _ in samples]
    values = [x for _, x in samples]
    window = min(SMOOTHING_WINDOW, len(values))
    padded = np.pad(values, (window // 2, window // 2), mode="edge")
    averaged = np.convolve(padded, np.ones(window) / window, mode="valid")[: len(values)]

    keyframes = [(times[0], float(averaged[0]))]
    for time_s, value in zip(times[1:], averaged[1:]):
        if abs(value - keyframes[-1][1]) > DEADZONE:
            keyframes.append((time_s, float(value)))
    return keyframes


def crop_expression(keyframes: list[tuple[float, float]], width: int, crop_width: int) -> str:
    """Build a piecewise ffmpeg expression for the crop's x over time.

    ponytail: the crop steps between keyframes rather than easing between them.
    The deadzone keeps the steps small; interpolate here if they ever read as jumps.
    """
    limit = max(0, width - crop_width)

    def x_at(centre: float) -> int:
        return int(min(max(centre * width - crop_width / 2, 0), limit))

    if not keyframes:
        return str(limit // 2)

    # Each keyframe's position holds until the *next* one starts, so the
    # threshold for keyframe i is the time of keyframe i+1.
    expression = str(x_at(keyframes[-1][1]))
    for i in range(len(keyframes) - 2, -1, -1):
        threshold = keyframes[i + 1][0]
        expression = f"if(lt(t,{threshold:.2f}),{x_at(keyframes[i][1])},{expression})"
    return expression


def cut_and_reframe(source: str, moment: Moment, transcript: list[dict], directory: str) -> str:
    """Cut one moment, reframe it to 9:16 on the speaker, burn in its captions."""
    clip = os.path.join(directory, "cut.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", str(moment.start_seconds), "-to", str(moment.end_seconds),
            "-i", source,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", clip,
        ],
        check=True,
    )

    probe = cv2.VideoCapture(clip)
    width = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
    probe.release()

    crop_width = min(width, int(height * 9 / 16))
    expression = crop_expression(smooth(track_face(clip)), width, crop_width)

    # Captions for this window only, rebased so the clip starts at zero.
    cues = []
    for cue in transcript:
        if cue["end"] <= moment.start_seconds or cue["start"] >= moment.end_seconds:
            continue
        cues.append(
            {
                "text": cue["text"],
                "start": max(cue["start"] - moment.start_seconds, 0.0),
                "end": cue["end"] - moment.start_seconds,
            }
        )
    with open(os.path.join(directory, "captions.ass"), "w", encoding="utf-8") as handle:
        handle.write(render.build_captions(cues))

    # Run from the directory so the subtitles filter never sees a Windows path,
    # whose drive colon and backslashes it would read as filter syntax.
    # The expression contains commas, which the filtergraph parser would read as
    # filter separators, so it has to be quoted for ffmpeg itself.
    video_filter = (
        f"crop={crop_width}:{height}:x='{expression}':y=0,"
        f"scale={render.WIDTH}:{render.HEIGHT},setsar=1,subtitles=captions.ass"
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", "cut.mp4",
            "-vf", video_filter,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "vertical.mp4",
        ],
        cwd=directory,
        check=True,
    )
    return os.path.join(directory, "vertical.mp4")


def run_repurpose(job: dict, max_clips: int = 3) -> str:
    """Worker handler for H1. Returns the source_video id."""
    url = job["params"]["youtube_url"]
    with tempfile.TemporaryDirectory() as directory:
        source, info = download(url, directory)
        transcript = transcribe(source, directory)

        source_id = (
            db.client()
            .table("source_videos")
            .insert(
                {
                    "job_id": job["id"],
                    "youtube_url": url,
                    "youtube_id": info.get("id"),
                    "title": info.get("title"),
                    "duration_seconds": info.get("duration"),
                    "transcript": transcript,
                }
            )
            .execute()
            .data[0]["id"]
        )

        for moment in select_moments(transcript)[:max_clips]:
            clip_id = (
                db.client()
                .table("clips")
                .insert(
                    {
                        "job_id": job["id"],
                        "source_video_id": source_id,
                        "start_seconds": moment.start_seconds,
                        "end_seconds": moment.end_seconds,
                        "title": moment.title,
                        "reason": moment.reason,
                        "score": moment.score,
                        "status": "rendering",
                    }
                )
                .execute()
                .data[0]["id"]
            )
            with tempfile.TemporaryDirectory() as clip_dir:
                vertical = cut_and_reframe(source, moment, transcript, clip_dir)
                with open(vertical, "rb") as handle:
                    path = db.upload(f"clips/{clip_id}.mp4", handle.read(), "video/mp4")
            db.client().table("clips").update(
                {"storage_path": path, "status": "ready"}
            ).eq("id", clip_id).execute()
            scheduler.plan_clip(clip_id)

    return source_id
