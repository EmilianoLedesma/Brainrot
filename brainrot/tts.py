"""Narration via edge-tts.

edge-tts reports a WordBoundary event per spoken word, so the caption timings
come straight from the synthesizer. Nothing needs to transcribe the audio back.
"""

import asyncio
from pathlib import Path
import re
import subprocess
import tempfile

import edge_tts

from .domain.jobs import TransientError
from .duration import require_duration

VOICE = "en-US-AndrewNeural"
RATE = "+0%"
TITLE_PAUSE = 0.75
THOUGHT_PAUSE = 0.28
WORDS_PER_THOUGHT = 40
SAMPLE_RATE = 24_000
BYTES_PER_SECOND = SAMPLE_RATE * 2  # Signed 16-bit mono PCM.

# edge-tts reports offsets in 100-nanosecond ticks.
TICKS_PER_SECOND = 10_000_000


async def _synthesize(text: str, voice: str, rate: str) -> tuple[bytes, list[dict]]:
    audio = bytearray()
    words: list[dict] = []
    speech = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    async for chunk in speech.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / TICKS_PER_SECOND
            words.append(
                {
                    "text": chunk["text"],
                    "start": start,
                    "end": start + chunk["duration"] / TICKS_PER_SECOND,
                }
            )
    if not audio:
        # The service occasionally drops a stream; the same text succeeds on retry.
        raise TransientError("edge-tts returned no audio")
    return bytes(audio), words


def _thoughts(text: str) -> list[str]:
    """Keep sentences together, with breathing room at paragraphs or longer beats.

    Punctuation supplies the small pauses within each beat. Grouping sentences
    keeps their prosody connected rather than requesting every sentence alone.
    """
    thoughts = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
        group: list[str] = []
        count = 0
        for sentence in sentences:
            if not sentence:
                continue
            group.append(sentence)
            count += len(sentence.split())
            if count >= WORDS_PER_THOUGHT:
                thoughts.append(" ".join(group))
                group, count = [], 0
        if group:
            thoughts.append(" ".join(group))
    return thoughts


def _ffmpeg(arguments: list[str], data: bytes) -> bytes:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", *arguments],
        input=data, capture_output=True, timeout=60,
    )
    if result.returncode:
        raise RuntimeError(f"narration audio processing failed: {result.stderr.decode(errors='replace')[-500:]}")
    return result.stdout


async def _paced_narration(text: str, title: str, voice: str, rate: str, enforce_duration: bool) -> tuple[bytes, list[dict]]:
    sections = [title.strip() or "The story", *_thoughts(text)]
    pcm = bytearray()
    words: list[dict] = []
    for index, section in enumerate(sections):
        audio, section_words = await _synthesize(section, voice, rate)
        # Decode before joining. MP3 byte concatenation introduces encoder gaps
        # and makes the caption offsets drift after every inserted pause.
        decoded = _ffmpeg([
            "-i", "pipe:0", "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "1", "pipe:1",
        ], audio)
        if not decoded:
            raise TransientError("edge-tts returned empty decoded audio")
        if section_words:
            # The provider leaves a long silent tail on standalone utterances.
            # Retain a small cushion after the last word so our explicit pauses
            # do not stack with that tail or clip a final consonant.
            end = max(word["end"] for word in section_words) + 0.12
            decoded = decoded[:round(end * SAMPLE_RATE) * 2]
        offset = len(pcm) / BYTES_PER_SECOND
        words.extend({**word, "start": word["start"] + offset, "end": word["end"] + offset}
                     for word in section_words)
        pcm.extend(decoded)
        if index < len(sections) - 1:
            pause = TITLE_PAUSE if index == 0 else THOUGHT_PAUSE
            pcm.extend(b"\0\0" * round(SAMPLE_RATE * pause))

    if enforce_duration:
        require_duration(len(pcm) / BYTES_PER_SECOND)

    # A seekable output lets FFmpeg record MP3 encoder delay/padding. Players
    # then start at the same sample zero used by the caption timestamps.
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "narration.mp3"
        _ffmpeg([
            "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-i", "pipe:0",
            "-c:a", "libmp3lame", "-b:a", "64k", str(output),
        ], bytes(pcm))
        return output.read_bytes(), words


def narrate(text: str, voice: str = VOICE, rate: str = RATE, *, title: str = "The story", enforce_duration: bool = True) -> tuple[bytes, list[dict]]:
    """Speak a title, pause, then the body; return MP3 and aligned word timings."""
    if not text.strip():
        raise ValueError("narration text must not be empty")
    return asyncio.run(_paced_narration(text, title, voice, rate, enforce_duration))
