"""Narrate story.json once with Brainrot's TTS, align scenes.json anchors to the measured word times,
and write the timeline the Remotion composition and the sound bed read. No model call, no database, no upload.

    uv run --locked python -I experiments/remotion-explainer/procrastination/prepare.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from brainrot import tts  # noqa: E402
from brainrot.duration import check_media  # noqa: E402

PUBLIC = HERE.parent / "public" / "procrastination"
OUT = ROOT / "out" / "procrastination"


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def locate(words, cursor, tokens):
    """Index of the first word at or after cursor where the next normalized words equal the tokens."""
    target = "".join(norm(t) for t in tokens)
    for i in range(cursor, len(words)):
        value = ""
        for j in range(i, min(len(words), i + 20)):
            value += norm(words[j]["text"])
            if value == target:
                return i
            if len(value) >= len(target):
                break
    raise ValueError("Cannot align: " + " ".join(tokens))


def main():
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    scenes = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
    script = "\n\n".join(story["paragraphs"])
    PUBLIC.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    audio_path, words_path, cache = OUT / "narration.mp3", OUT / "words.json", OUT / "narration-cache.json"
    fingerprint = hashlib.sha256(json.dumps({"t": story["title"], "s": script, "v": story["voice"],
                                             "tts": hashlib.sha256((ROOT / "brainrot/tts.py").read_bytes()).hexdigest()}, sort_keys=True).encode()).hexdigest()
    if cache.exists() and json.loads(cache.read_text())["fingerprint"] == fingerprint and audio_path.exists() and words_path.exists():
        words = json.loads(words_path.read_text())
        print("Reusing saved narration.", flush=True)
    else:
        audio, words = tts.narrate(script, title=story["title"], voice=story["voice"])
        audio_path.write_bytes(audio)
        words_path.write_text(json.dumps(words, indent=1), encoding="utf-8")
        cache.write_text(json.dumps({"fingerprint": fingerprint}))
    seconds = check_media(str(audio_path))
    (PUBLIC / "narration.mp3").write_bytes(audio_path.read_bytes())

    # Scene starts: the title is scene 0 (t=0); each paragraph starts at its first seven spoken words.
    cursor = 0
    starts = [0.0]
    for para in story["paragraphs"]:
        i = locate(words, cursor, para.split()[:7])
        starts.append(max(0.0, words[i]["start"] - 0.10))
        cursor = i + 1
    starts.append(seconds)
    timeline = {"duration": round(seconds, 3), "scenes": [], "words": [[w["text"], round(w["start"], 3), round(w["end"], 3)] for w in words]}
    for k, scene in enumerate(scenes["scenes"]):
        a, b = starts[k], starts[k + 1]
        anchors = {}
        for name, token in scene["anchors"].items():
            hit = next((w for w in words if a - 0.05 <= w["start"] < b and norm(w["text"]) == norm(token)), None)
            if hit is None:
                raise ValueError(f"Anchor '{name}' ({token}) not found in scene {scene['id']}")
            anchors[name] = round(hit["start"], 3)
        timeline["scenes"].append({"id": scene["id"], "start": round(a, 3), "end": round(b, 3), "a": anchors})
    cues = [{"at": next(s for s in timeline["scenes"] if s["id"] == c["scene"])["a"][c["anchor"]] - 0.04, "kind": c["kind"]} for c in scenes["sfx"]]
    cues += [{"at": s["start"] - 0.2, "kind": "whoosh"} for s in timeline["scenes"][1:]]
    timeline["sfx"] = sorted(cues, key=lambda c: c["at"])
    (HERE / "timeline.json").write_text(json.dumps(timeline, indent=1), encoding="utf-8")
    print(f"narration {seconds:.1f}s; scenes: " + ", ".join(f"{s['id']} {s['start']:.1f}-{s['end']:.1f}" for s in timeline["scenes"]))


if __name__ == "__main__":
    main()
