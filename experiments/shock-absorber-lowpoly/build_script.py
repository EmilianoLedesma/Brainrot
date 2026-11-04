"""Turns plan.json + words.json + story.json into script.json for ShockAbsorber.tsx. No model is involved here.

Captions: the TTS word list is grouped into independent 2-5 word phrases BEFORE the script is written (clause boundaries come
from the script's own punctuation), so word-by-word accumulation is structurally impossible. Each phrase replaces the previous.

  python experiments/shock-absorber-lowpoly/build_script.py
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
MAX_WORDS = 5
CAMERAS = {  # one continuous move over the WHOLE shot, independent of the caption rhythm; one rig per shot type
    "establishing": {"from": {"pos": [-5.0, 2.0, 9.8], "target": [0, 1.3, 0]}, "to": {"pos": [-1.4, 2.3, 8.4], "target": [0.15, 1.3, 0]}, "fov": 35},
    "cutaway": {"from": {"pos": [-3.4, 1.8, 9.6], "target": [0, 1.6, 0]}, "to": {"pos": [-1.7, 2.0, 8.2], "target": [0, 1.6, 0]}, "fov": 35},
    "insert": {"from": {"pos": [-2.4, 1.45, 4.9], "target": [0, 1.2, 0]}, "to": {"pos": [-1.5, 1.5, 4.1], "target": [0, 1.2, 0]}, "fov": 35},
}
AMBIENT = {
    "establishing": {"kind": "damper-cycle", "period": 60, "moving": "every 2 s a bump kicks the wheel; the chassis, coil spring and damper rod ring down and settle; road markings scroll the whole time"},
    "cutaway": {"kind": "damper-cycle", "period": 60, "moving": "every 2 s the piston strokes down and back up through the oil while the rod, coil spring and mounts move with it"},
    "insert": {"kind": "valve-cycle", "period": 60, "moving": "every 2 s the piston face strokes through the oil while oil is squeezed through the valve passages"},
}
ENVIRONMENT = {
    "establishing": ["wheel", "suspension arm", "chassis", "road", "coil spring"],
    "cutaway": ["coil spring", "chassis mount", "wheel hub mount", "outer tube"],
    "insert": [],
}


def frames(seconds: float) -> int:
    return round(seconds * FPS)


def clauses(story: dict, n_words: int) -> tuple[list[tuple[int, int]], list[str]]:
    title = story["title"].split()
    tokens = title + story["script"].split()
    if len(tokens) != n_words:
        raise ValueError(f"script has {len(tokens)} words but the narration has {n_words}")
    out, start = [], 0
    for i, t in enumerate(tokens):
        if i == len(title) - 1 or t[-1] in ".,;:!?¿" or i == len(tokens) - 1:
            out.append((start, i))
            start = i + 1
    return out, tokens


def phrases(cl: list[tuple[int, int]], tokens: list[str]) -> list[tuple[int, int]]:
    """Clauses of at most five words stay whole; longer ones are cut into balanced chunks of 3-5 words. A one-word leftover is folded
    into a neighbouring phrase of the SAME sentence (previous first, then next); it is never glued across a sentence end."""
    joined: list[tuple[int, int]] = []  # a one-word clause joins its neighbour in the same sentence (comma-joined) before chunking
    i = 0
    while i < len(cl):
        a, b = cl[i]
        if a == b and tokens[b].endswith(",") and i + 1 < len(cl):
            joined.append((a, cl[i + 1][1]))
            i += 2
        elif a == b and joined and tokens[joined[-1][1]].endswith(","):
            joined[-1] = (joined[-1][0], b)
            i += 1
        else:
            joined.append((a, b))
            i += 1
    out = []
    for a, b in joined:
        n = b - a + 1
        k = math.ceil(n / MAX_WORDS)
        sizes = [n // k + (1 if i < n % k else 0) for i in range(k)]
        at = a
        for s in sizes:
            out.append((at, at + s - 1))
            at += s
    ends = lambda i: tokens[i][-1] in ".?!"  # noqa: E731  (sentence end)
    changed = True
    while changed:
        changed = False
        for i, (a, b) in enumerate(out):
            if b - a + 1 != 1:
                continue
            if i > 0 and not ends(out[i - 1][1]) and out[i - 1][1] - out[i - 1][0] + 2 <= MAX_WORDS:
                out[i - 1] = (out[i - 1][0], b)
                del out[i]
            elif i + 1 < len(out) and not ends(b) and out[i + 1][1] - out[i + 1][0] + 2 <= MAX_WORDS:
                out[i + 1] = (a, out[i + 1][1])
                del out[i]
            else:
                continue
            changed = True
            break
    return out


def main() -> None:
    args = sys.argv
    plan_path = Path(args[args.index("--plan") + 1]) if "--plan" in args else HERE / "plan.json"
    out_path = Path(args[args.index("--out") + 1]) if "--out" in args else HERE / "script.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    words = json.loads((HERE / "words.json").read_text(encoding="utf-8"))["words"]
    scenes, total = plan["scenes"], frames(plan["duration"])
    shots, captions, events = [], [], []
    for n, s in enumerate(scenes):
        start = 0 if n == 0 else frames(s["start"])
        end = total if n == len(scenes) - 1 else frames(scenes[n + 1]["start"])
        shots.append({"id": f"s{n}", "type": s["shot"], "start": start, "end": end, "camera": CAMERAS[s["shot"]],
                      "ambient": AMBIENT[s["shot"]], "environment": ENVIRONMENT[s["shot"]]})
    cl, tokens = clauses(story, len(words))
    ph = phrases(cl, tokens)
    for k, (a, b) in enumerate(ph):
        at = frames(words[a]["start"])
        nxt = frames(words[ph[k + 1][0]]["start"]) if k + 1 < len(ph) else total
        until = min(nxt - 1, frames(words[b]["end"]) + 24)  # replaced by the next phrase, or fades 0.8 s after its last word
        captions.append({"id": f"c{k}", "at": at, "until": max(until, at + 12), "style": "phrase", "text": " ".join(w["text"] for w in words[a:b + 1])})
    for n, s in enumerate(scenes):
        shot = shots[n]
        for k, e in enumerate(s.get("events") or [s["event"]]):
            if e["kind"] == "none":
                continue
            events.append({"id": f"e{n}_{k}", "shot": shot["id"], "kind": e["kind"], "at": frames(e["at"]), "term": e.get("term", "")})
            if e["kind"] == "term_callout":
                at = frames(e["at"])
                phrase_until = max((c["until"] for c in captions if c["style"] == "phrase" and c["at"] <= at < c["until"]), default=at + 30)
                captions.append({"id": f"t{n}_{k}", "at": at, "until": min(phrase_until + 30, shot["end"] - 1), "style": "term", "text": e["term"]})  # holds a beat longer
    cut = [e["at"] for e in events]
    stills = sorted(set([round(total * (i + .5) / 24) for i in range(24)] + [min(total - 1, a + 8) for a in cut]))
    runs = []
    for kind in ("establishing", "cutaway", "insert"):
        s = next((s for s in shots if s["type"] == kind), None)
        if s:
            runs.append({"shot": s["id"], "start": s["start"] + max(0, (s["end"] - s["start"]) // 2 - 30), "step": 5, "count": 12})
    out = {"title": story["title"], "fps": FPS, "durationFrames": total, "shots": shots, "captions": captions, "events": events,
           "stillFrames": stills, "fluidityRuns": runs, "sources": [],
           "note": "Generated from plan.json, words.json and story.json by build_script.py. Captions are independent 2-5 word phrases; schematic explainer, no figures on screen."}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sizes = [len(c["text"].split()) for c in captions if c["style"] == "phrase"]
    print(f"script.json: {total} frames, {len(shots)} shots, {len(sizes)} phrases (words each: min {min(sizes)}, max {max(sizes)}), {len(events)} events")


if __name__ == "__main__":
    main()
