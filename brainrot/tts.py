"""Narration via edge-tts.

edge-tts reports a WordBoundary event per spoken word, so the caption timings
come straight from the synthesizer. Nothing needs to transcribe the audio back.
"""

import asyncio

import edge_tts

VOICE = "en-US-AndrewNeural"
RATE = "+15%"

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
        raise RuntimeError("edge-tts returned no audio")
    return bytes(audio), words


def narrate(text: str, voice: str = VOICE, rate: str = RATE) -> tuple[bytes, list[dict]]:
    """Return (mp3 bytes, word timings in seconds)."""
    return asyncio.run(_synthesize(text, voice, rate))
