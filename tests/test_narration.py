"""Audio pauses and caption offsets must agree in the final, playable MP3."""

import io
import math
import struct
import wave

import pytest

from brainrot import render, tts
from brainrot.domain.jobs import TransientError


@pytest.fixture
def speech_sample():
    """One second of audible tone with a known duration, without a TTS request."""
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(tts.SAMPLE_RATE)
        wav.writeframes(b"".join(
            struct.pack("<h", round(12_000 * math.sin(2 * math.pi * 440 * i / tts.SAMPLE_RATE)))
            for i in range(tts.SAMPLE_RATE)
        ))
    return output.getvalue()


def test_spoken_title_and_thought_pauses_keep_audio_and_captions_aligned(monkeypatch, speech_sample):
    spoken = []

    async def synthesize(text, voice, rate):
        spoken.append((text, voice, rate))
        return speech_sample, [{"text": text, "start": 0.15, "end": 0.95}]

    monkeypatch.setattr(tts, "_synthesize", synthesize)
    audio, words = tts.narrate("First thought.\n\nThe payoff.", enforce_duration=False, title="A little headline")
    assert [call[0] for call in spoken] == ["A little headline", "First thought.", "The payoff."]
    assert all(call[2] == "+0%" for call in spoken)
    assert [word["start"] for word in words] == pytest.approx([0.15, 1.9, 3.18])
    assert [word["end"] for word in words] == pytest.approx([0.95, 2.7, 3.98])

    decoded = tts._ffmpeg([
        "-i", "pipe:0", "-f", "s16le", "-ar", str(tts.SAMPLE_RATE), "-ac", "1", "pipe:1",
    ], audio)
    assert len(decoded) / tts.BYTES_PER_SECOND == pytest.approx(4.03, abs=0.024)
    # Inspect the actual decoded MP3, including encoder delay and padding.
    samples = struct.unpack(f"<{len(decoded) // 2}h", decoded)
    for start, end in [(0.2, 0.8), (1.95, 2.5), (3.3, 3.8)]:
        assert max(abs(value) for value in samples[round(start * tts.SAMPLE_RATE):round(end * tts.SAMPLE_RATE)]) > 5000
    for start, end in [(1.1, 1.65), (2.82, 2.96)]:
        assert max(abs(value) for value in samples[round(start * tts.SAMPLE_RATE):round(end * tts.SAMPLE_RATE)]) < 100

    captions = render.build_captions(words)
    assert "0:00:00.15,0:00:01.05" in captions
    assert "0:00:01.90,0:00:02.80" in captions
    assert "0:00:03.18,0:00:03.98" in captions


def test_long_body_pauses_at_sentence_boundaries_without_losing_words(monkeypatch, speech_sample):
    first = " ".join(["word"] * 41) + "."
    body = first + " The final sentence."
    spoken = []

    async def synthesize(text, voice, rate):
        spoken.append(text)
        return speech_sample, []

    monkeypatch.setattr(tts, "_synthesize", synthesize)
    tts.narrate(body, enforce_duration=False, title="  ")
    assert spoken == ["The story", first, "The final sentence."]
    assert " ".join(spoken[1:]) == body


def test_provider_trailing_silence_does_not_stack_with_the_title_pause(monkeypatch, speech_sample):
    with wave.open(io.BytesIO(speech_sample), "rb") as source:
        frames = source.readframes(source.getnframes())
    padded = io.BytesIO()
    with wave.open(padded, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(tts.SAMPLE_RATE)
        output.writeframes(frames + b"\0" * tts.BYTES_PER_SECOND)

    async def synthesize(text, voice, rate):
        return padded.getvalue(), [{"text": text, "start": 0.15, "end": 0.95}]

    monkeypatch.setattr(tts, "_synthesize", synthesize)
    audio, words = tts.narrate("Body.", enforce_duration=False, title="Headline")
    assert words[1]["start"] - words[0]["end"] == pytest.approx(1.02)
    decoded = tts._ffmpeg([
        "-i", "pipe:0", "-f", "s16le", "-ar", str(tts.SAMPLE_RATE), "-ac", "1", "pipe:1",
    ], audio)
    assert len(decoded) / tts.BYTES_PER_SECOND == pytest.approx(2.89, abs=0.024)


def test_empty_body_is_rejected_before_contacting_the_synthesizer(monkeypatch):
    def unexpected_request(*args):
        pytest.fail("empty narration must not contact TTS")

    monkeypatch.setattr(tts, "_synthesize", unexpected_request)
    with pytest.raises(ValueError, match="must not be empty"):
        tts.narrate(" \n ", enforce_duration=False, title="Headline")


def test_tts_failure_does_not_return_a_partial_title_only_recording(monkeypatch, speech_sample):
    async def synthesize(text, voice, rate):
        if text == "Body.":
            raise TransientError("service dropped stream")
        return speech_sample, []

    monkeypatch.setattr(tts, "_synthesize", synthesize)
    with pytest.raises(TransientError, match="service dropped stream"):
        tts.narrate("Body.", enforce_duration=False, title="Headline")


def test_captions_hold_short_word_gaps_but_clear_for_a_title_pause():
    words = [
        {"text": "The", "start": 0.0, "end": 0.15},
        {"text": "title", "start": 0.20, "end": 0.5},
        {"text": "Body", "start": 1.75, "end": 2.0},
    ]
    captions = render.build_captions(words)
    assert "0:00:00.00,0:00:00.20" in captions
    assert "0:00:00.20,0:00:00.60" in captions
    assert "0:00:01.75,0:00:02.00" in captions


def test_stalled_narration_is_cancelled_and_retryable(monkeypatch):
    import asyncio

    cancelled = []

    async def stalled(*args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    monkeypatch.setattr(tts, "_paced_narration", stalled)
    monkeypatch.setattr(tts, "NARRATION_TIMEOUT_SECONDS", 0.01)
    with pytest.raises(TransientError, match="Speech generation timed out"):
        tts.narrate("A saved script")
    assert cancelled == [True]
