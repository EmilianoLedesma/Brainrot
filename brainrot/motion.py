"""Motion-graphics edit: the repo's Remotion project in motion/, driven by narration timings.

An alternative to render.render: same inputs (narration + word timings), same checked
1080x1920 H.264/AAC output, but animated scenes, keyword punches and transitions replace
the looping background video.
"""

import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from . import llm
from .config import PROJECT_ROOT
from .domain.jobs import PermanentError
from .duration import check_media
from . import render

MOTION_DIR = PROJECT_ROOT / "motion"
REMOTION_CLI = MOTION_DIR / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
SCENE_SECONDS = 11.0
MAX_KEYWORDS = 3
KEYWORD_GAP = 2.5
_END = (".", "!", "?")
SENTENCE_GAP = 0.7  # the TTS word boundaries carry no punctuation; sentence pauses are ~0.85 s, commas ~0.5 s


def _ends(words: list[dict], i: int) -> bool:
    if words[i]["text"].rstrip().endswith(_END):
        return True
    return i + 1 < len(words) and words[i + 1]["start"] - words[i]["end"] >= SENTENCE_GAP


_FILLER = {"another", "because", "however", "although", "between", "through", "without", "something", "everyone"}


def _clean(text: str) -> str:
    return re.sub(r"[^\w%$°'-]", "", text)


def _score(word: dict, first: bool) -> int:
    text = _clean(word["text"])
    if any(c.isdigit() for c in text):
        return 3
    if text.lower() in _FILLER:
        return 0
    if text[:1].isupper() and not first and len(text) >= 5:
        return 2
    return 1 if len(text) >= 7 else 0


def plan(words: list[dict], seconds: float) -> dict:
    """Group sentences into ~11 s scenes and pick up to three spoken keywords per scene."""
    scenes, current, seen = [], [], set()
    for index, word in enumerate(words):
        current.append(index)
        if _ends(words, index) and word["end"] - words[current[0]]["start"] >= SCENE_SECONDS:
            scenes.append(current)
            current = []
    if current:
        if scenes and words[current[-1]]["end"] - words[current[0]]["start"] < SCENE_SECONDS / 2:
            scenes[-1] += current
        else:
            scenes.append(current)
    out = []
    for number, group in enumerate(scenes):
        start = 0.0 if number == 0 else words[group[0]]["start"]
        end = seconds if number == len(scenes) - 1 else words[scenes[number + 1][0]]["start"]
        ranked = sorted(
            ((_score(words[i], i == 0 or _ends(words, i - 1)), i) for i in group),
            key=lambda pair: (-pair[0], pair[1]),
        )
        picked: list[dict] = []
        for score, i in ranked:
            text = _clean(words[i]["text"])
            if score == 0 or text.lower() in seen or len(picked) == MAX_KEYWORDS:
                continue
            if all(abs(words[i]["start"] - p["at"]) >= KEYWORD_GAP for p in picked):
                picked.append({"text": text, "at": round(words[i]["start"], 2)})
                seen.add(text.lower())
        out.append({"start": round(start, 2), "end": round(end, 2), "text": " ".join(words[i]["text"] for i in group), "keywords": sorted(picked, key=lambda k: k["at"])})
    return {"scenes": out, "words": words, "duration": seconds, "audio": "narration.mp3"}


SKILL = Path(__file__).parent / "skills" / "motion-graphics" / "SKILL.md"
DEVICES = ("stat", "compare", "checklist", "steps", "stamp", "alert", "none")
log = logging.getLogger(__name__)


class Beat(BaseModel):
    scene: int
    device: Literal["stat", "compare", "checklist", "steps", "stamp", "alert", "none"]
    cue: str
    title: str
    big: str
    items: list[str]
    values: list[int]
    highlight: int


class Design(BaseModel):
    beats: list[Beat]


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _cue_time(cue: str, scene: dict, words: list[dict]) -> float:
    target = [_norm(w) for w in cue.split() if _norm(w)]
    inside = [w for w in words if scene["start"] <= w["start"] < scene["end"]]
    for i in range(len(inside) - len(target) + 1 if target else 0):
        if all(_norm(inside[i + j]["text"]) == t for j, t in enumerate(target)):
            return round(inside[i]["start"], 2)
    return round(scene["start"] + 0.8, 2)


def _device(beat: Beat, scene: dict, words: list[dict]) -> dict | None:
    items = [i.strip()[:40] for i in beat.items if i.strip()][:4]
    title, big = beat.title.strip()[:70], beat.big.strip()[:12]
    ok = {
        "stat": bool(big),
        "compare": len(items) >= 2 and len(beat.values) >= 2,
        "checklist": len(items) >= 3,
        "steps": len(items) >= 3,
        "stamp": bool(title),
        "alert": bool(title),
    }.get(beat.device, False)
    if not ok:
        return None
    return {"kind": beat.device, "title": title, "big": big, "items": items[:2] if beat.device == "compare" else items,
            "values": [min(100, max(5, v)) for v in beat.values[:2]],
            "highlight": beat.highlight if -1 <= beat.highlight < len(items) else -1,
            "at": _cue_time(beat.cue, scene, words)}


def design(scenes: list[dict], words: list[dict]) -> None:
    """Ask the selected model for one optional on-screen device per scene; attach them in place.

    The model only sees the narration, so devices restate it. Output is validated here: unknown
    scenes, malformed devices, a repeated device back to back and extra alerts are dropped.
    """
    guidance = SKILL.read_text(encoding="utf-8").split("---", 2)[-1].strip()
    prompt = "\n\n".join(f"Scene {i}:\n{scene['text']}" for i, scene in enumerate(scenes))
    result = llm.generate(guidance, prompt, Design, max_tokens=3000)
    previous, alerts = None, 0
    for beat in sorted(result.beats, key=lambda b: b.scene):
        if not 0 <= beat.scene < len(scenes) or "device" in scenes[beat.scene]:
            continue
        device = _device(beat, scenes[beat.scene], words)
        if device is None or device["kind"] == previous or (device["kind"] == "alert" and alerts):
            previous = None if device is None else previous
            continue
        scenes[beat.scene]["device"] = device
        previous = device["kind"]
        alerts += device["kind"] == "alert"


def render_video(narration: bytes, words: list[dict]) -> bytes:
    """Render the motion-graphics video for one narrated chapter and return mp4 bytes."""
    node = shutil.which("node")
    if not node or not REMOTION_CLI.is_file():
        raise PermanentError("Motion graphics are not set up on this computer. Run: npm ci --prefix motion")
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        public = folder / "public"
        public.mkdir()
        (public / "narration.mp3").write_bytes(narration)
        shutil.copyfile(MOTION_DIR / "DMSans.ttf", public / "DMSans.ttf")
        seconds = check_media(str(public / "narration.mp3"))
        render.check_captions(words, seconds)
        props = plan(words, seconds)
        try:
            design(props["scenes"], words)
        except Exception as exc:  # the edit still works with keyword punches alone
            log.warning("Motion-graphics scene design failed; rendering keyword punches only: %s", str(exc)[:200])
        (folder / "props.json").write_text(json.dumps(props), encoding="utf-8")
        command = [
            node, str(REMOTION_CLI), "render", "index.tsx", "Motion", str(folder / "raw.mp4"),
            f"--props={folder / 'props.json'}", f"--public-dir={public}",
            "--concurrency=2", "--crf=26", "--x264-preset=veryfast", "--log=error",
        ]
        result = subprocess.run(command, cwd=MOTION_DIR, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"remotion failed: {(result.stderr or result.stdout).strip()[-500:]}")
        final = folder / "out.mp4"
        mix = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(folder / "raw.mp4"),
             "-c:v", "copy", "-af", render.VOICE_FILTER, "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", str(final)],
            capture_output=True, text=True, timeout=600,
        )
        if mix.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {mix.stderr.strip()[-500:]}")
        render.check_video(str(final))
        return final.read_bytes()
