"""Shared limits for finished narration and published videos."""

import math
import subprocess

from .domain.jobs import PermanentError

MIN_SECONDS = 90
MAX_SECONDS = 180


def require_duration(seconds: float) -> None:
    if not math.isfinite(seconds) or not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise PermanentError(
            "The narration or video must last between 90 and 180 seconds. "
            "Create a new job with a fuller or more focused story."
        )


def check_media(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    seconds = float(result.stdout.strip())
    require_duration(seconds)
    return seconds
