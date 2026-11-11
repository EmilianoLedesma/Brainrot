"""Renders one narrated chapter as the continuous 3D world (Remotion + three.js) and mixes the narration in. The script is built in code from a directed plan."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .. import render as base_render
from ..config import PROJECT_ROOT
from ..domain.jobs import PermanentError
from ..duration import check_media
from . import script as script_

MOTION_DIR = PROJECT_ROOT / "motion"
REMOTION_CLI = MOTION_DIR / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
THREE = MOTION_DIR / "node_modules" / "three"


def available() -> bool:
    return bool(shutil.which("node")) and REMOTION_CLI.is_file() and THREE.is_dir()


def seconds(narration: bytes) -> float:
    """Narration length, for the director (which needs it before the render)."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "narration.mp3").write_bytes(narration)
        return check_media(str(Path(tmp) / "narration.mp3"))


def render_video(narration: bytes, words: list[dict], title: str, text: str, plan: dict) -> bytes:
    """mp4 bytes for one chapter. `plan` comes from world.director.plan; nothing here calls a model."""
    node = shutil.which("node")
    if not available():
        raise PermanentError("The continuous 3D world is not set up on this computer. Run: npm ci --prefix motion")
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        (folder / "narration.mp3").write_bytes(narration)
        seconds = check_media(str(folder / "narration.mp3"))
        base_render.check_captions(words, seconds)
        script = script_.build(plan, title, text, words)
        bad = script_.problems(script)
        if bad:
            raise RuntimeError(f"world script is not renderable: {bad[0]}")
        (folder / "props.json").write_text(json.dumps({"pack": plan["pack"], "script": script}), encoding="utf-8")
        command = [node, str(REMOTION_CLI), "render", "index.tsx", "World", str(folder / "raw.mp4"), f"--props={folder / 'props.json'}",
                   f"--gl={os.environ.get('BRAINROT_WORLD_GL', 'angle')}", "--concurrency=2", "--crf=20", "--x264-preset=veryfast", "--log=error"]
        result = subprocess.run(command, cwd=MOTION_DIR, capture_output=True, text=True, timeout=7200)
        if result.returncode != 0:
            raise RuntimeError(f"remotion failed: {(result.stderr or result.stdout).strip()[-500:]}")
        final = folder / "out.mp4"
        mix = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(folder / "raw.mp4"), "-i", str(folder / "narration.mp3"),
                              "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", base_render.VOICE_FILTER, "-c:a", "aac", "-b:a", "128k", "-shortest",
                              "-movflags", "+faststart", str(final)], capture_output=True, text=True, timeout=600)
        if mix.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {mix.stderr.strip()[-500:]}")
        base_render.check_video(str(final))
        return final.read_bytes()
