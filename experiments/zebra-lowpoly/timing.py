"""Word timings for the approved zebra script through brainrot.tts.narrate (edge-tts WordBoundary events).

The audio is discarded: the finished video is silent, and only the per-word start/end times are kept, to sync captions
and events. The rate is lowered in steps if the narration measures under the 90 s minimum.

  PYTHONPATH=. uv run --locked python experiments/zebra-lowpoly/timing.py     (from the repository root)
"""
import asyncio
import json
import sys
from pathlib import Path

from brainrot import tts

HERE = Path(__file__).resolve().parent
VOICE = "es-MX-JorgeNeural"
RATES = ["+0%", "-5%", "-8%"]

_original = tts._synthesize


async def _retry(text, voice, rate):
    """edge-tts drops a stream now and then; the repo expects a retry, so each section gets several (repo code untouched)."""
    for attempt in range(6):
        try:
            return await _original(text, voice, rate)
        except Exception:
            if attempt == 5:
                raise
            await asyncio.sleep(1.5)


tts._synthesize = _retry


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    for rate in RATES:
        _audio, words = tts.narrate(story["script"], voice=VOICE, rate=rate, title=story["title"], enforce_duration=False)
        duration = max(w["end"] for w in words)
        print(f"rate {rate}: {len(words)} words, last word ends at {duration:.2f} s")
        if 90 <= duration <= 180:
            break
    else:
        raise SystemExit("narration is outside 90-180 s at every rate tried")
    (HERE / "words.json").write_text(json.dumps({"voice": VOICE, "rate": rate, "duration": round(duration, 3), "words": [
        {**w, "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in words]}, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
