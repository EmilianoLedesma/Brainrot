"""Turns plan.json + words.json + story.json into script.json for Zipper.tsx. No model is involved here.

Captions: the TTS word list is grouped into independent 2-5 word phrases BEFORE the script is written (clause boundaries come from the
script's own punctuation), so word-by-word accumulation is structurally impossible. A one-word leftover is folded into a neighbouring
phrase of the SAME sentence, never glued across a sentence end.

  python experiments/zipper-lowpoly/build_script.py [--plan PATH] [--out PATH]
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
MAX_WORDS = 5
# One continuous camera move over the WHOLE shot, independent of the caption rhythm. `follow` makes the target track the slider.
CAMERAS = {
    "establishing": {"from": {"pos": [-4.6, 1.2, 10.5], "target": [0, 0, 0]}, "to": {"pos": [-1.8, 0.8, 9.0], "target": [0, 0, 0]}, "fov": 35, "follow": 0},
    "cutaway": {"from": {"pos": [-3.0, 1.0, 7.5], "target": [0, 0.3, 0]}, "to": {"pos": [-1.6, 0.7, 6.2], "target": [0, 0.3, 0]}, "fov": 35, "follow": 0.5},
    "insert": {"from": {"pos": [-1.8, 0.3, 4.2], "target": [0, 0.4, 0]}, "to": {"pos": [-1.2, 0.3, 3.6], "target": [0, 0.4, 0]}, "fov": 35, "follow": 1},
    "assembly": {"from": {"pos": [-0.9, 0.3, 9.6], "target": [0, 0, 0]}, "to": {"pos": [-0.9, 0.3, 9.6], "target": [0, 0, 0]}, "fov": 35, "follow": 0},  # locked off on purpose
}
AMBIENT = {
    "camera": {"kind": "slider-cycle", "period": 120, "moving": "the slider travels up and back down every 4 s: teeth below it interlock one after another, teeth above it pry apart; the pull tab swings; the jacket and wall stripes slide past as the camera orbits"},
    "assembly": {"kind": "assembly-cycle", "period": 120, "moving": "parts arrive one at a time and settle (tapes, teeth, slider, pull tab, stops); once assembled the slider keeps zipping up and down"},
}
ENVIRONMENT = {
    "establishing": ["jacket fabric", "hanger", "wall stripes", "stitching", "button"],
    "cutaway": ["jacket fabric", "stitching", "wall stripes"],
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
        asm = s["sustain"] == "assembly"
        shots.append({"id": f"s{n}", "type": s["shot"], "sustain": s["sustain"], "start": start, "end": end,
                      "camera": CAMERAS["assembly" if asm else s["shot"]], "ambient": AMBIENT[s["sustain"]],
                      "environment": ["jacket fabric", "wall stripes"] if asm else ENVIRONMENT[s["shot"]]})
    cl, tokens = clauses(story, len(words))
    ph = phrases(cl, tokens)
    for k, (a, b) in enumerate(ph):
        at = frames(words[a]["start"])
        nxt = frames(words[ph[k + 1][0]]["start"]) if k + 1 < len(ph) else total
        until = min(nxt - 1, frames(words[b]["end"]) + 24)  # replaced by the next phrase, or fades 0.8 s after its last word
        captions.append({"id": f"c{k}", "at": at, "until": max(until, at + 12), "style": "phrase", "text": " ".join(w["text"] for w in words[a:b + 1])})
    for n, s in enumerate(scenes):
        shot = shots[n]
        for k, e in enumerate(s["events"]):
            events.append({"id": f"e{n}_{k}", "shot": shot["id"], "kind": e["kind"], "at": frames(e["at"]), "term": e.get("term", ""), "target": e.get("target", "")})
            if e["kind"] == "term_callout":
                at = frames(e["at"])
                phrase_until = max((c["until"] for c in captions if c["style"] == "phrase" and c["at"] <= at < c["until"]), default=at + 30)
                captions.append({"id": f"t{n}_{k}", "at": at, "until": min(phrase_until + 30, shot["end"] - 1), "style": "term", "text": e["term"]})  # holds a beat longer
    cut = [e["at"] for e in events][::max(1, len(events) // 12)]
    stills = sorted(set([round(total * (i + .5) / 24) for i in range(24)] + [min(total - 1, a + 8) for a in cut]))
    runs = []
    for label, pick in (("camera establishing", lambda s: s["type"] == "establishing" and s["sustain"] == "camera"),
                        ("camera cutaway", lambda s: s["type"] == "cutaway" and s["sustain"] == "camera"),
                        ("insert", lambda s: s["type"] == "insert"), ("assembly", lambda s: s["sustain"] == "assembly")):
        s = next((s for s in shots if pick(s)), None)
        if s:
            first = next((e["at"] for e in events if e["shot"] == s["id"] and e["kind"] == "attach"), None)
            start = max(s["start"], first - 10) if first else s["start"] + max(0, (s["end"] - s["start"]) // 2 - 30)
            runs.append({"label": label, "shot": s["id"], "start": min(start, s["end"] - 60), "step": 5, "count": 12})
    out = {"title": story["title"], "fps": FPS, "durationFrames": total, "shots": shots, "captions": captions, "events": events,
           "stillFrames": stills, "fluidityRuns": runs, "sources": [],
           "note": "Generated from plan.json, words.json and story.json by build_script.py. Captions are independent 2-5 word phrases; schematic explainer, no figures on screen."}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sizes = [len(c["text"].split()) for c in captions if c["style"] == "phrase"]
    print(f"{out_path.name}: {total} frames, {len(shots)} shots, {len(sizes)} phrases (words each: min {min(sizes)}, max {max(sizes)}), {len(events)} events")


if __name__ == "__main__":
    main()
