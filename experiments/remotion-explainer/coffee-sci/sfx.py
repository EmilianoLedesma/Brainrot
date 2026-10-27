"""Synthesize the sound-effect bed for the silent coffee test from script.json cues. No speech, no samples."""
import json, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
rng = np.random.default_rng(7)


def env(n, a=.003, d=1.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t * d)


def hit():
    n = int(.5 * SR); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 18)) / SR) * env(n, .002, 7)
    click = rng.standard_normal(n) * env(n, .001, 90) * .5
    return (body + click) * .9


def tick():
    n = int(.07 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * 2400 * t) * env(n, .001, 55) * .35


def whoosh():
    n = int(.8 * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n); out = np.zeros(n); y = 0.
    for i in range(n):
        a = .02 + .5 * np.sin(np.pi * i / n) ** 2
        y += a * (x[i] - y); out[i] = y
    return out * np.sin(np.pi * t / t[-1]) ** 2 * 2.2


def riser():
    n = int(1.0 * SR); t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * np.cumsum(180 + 1400 * t ** 2) / SR)
    return (tone * .35 + rng.standard_normal(n) * .08) * (t / t[-1]) ** 2


KINDS = {"hit": hit, "tick": tick, "whoosh": whoosh, "riser": riser}


def main(script, out):
    s = json.loads(Path(script).read_text(encoding="utf8"))
    buf = np.zeros(int((s["duration"] + 1) * SR))
    for c in s["sfx"]:
        w = KINDS[c["kind"]](); i = int(c["at"] * SR); buf[i:i + len(w)] += w[:len(buf) - i]
    buf = buf / max(1e-6, np.abs(buf).max()) * .85
    with wave.open(out, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((buf * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
