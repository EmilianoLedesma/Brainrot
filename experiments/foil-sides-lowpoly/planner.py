"""Shot planner for the foil experiment, an analogue of brainrot/motion.py (plan() + design()).

plan(): brainrot.motion.plan groups the word timings into ~11 s blocks on sentence ends.
design(): the selected model picks ONE of the four shot types in docs/motion-graphics-recipe-lowpoly.md plus at most
one event per block, as a Pydantic model (never code). Everything is validated here; the model's raw choice is kept
in plan.json next to the validated one so misfits can be studied.

  PYTHONPATH=. uv run --locked python experiments/foil-sides-lowpoly/planner.py     (from the repository root)
"""
import json
import os
import re
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from brainrot import llm, motion

HERE = Path(__file__).resolve().parent
SHOTS = ("establishing", "cutaway", "insert", "metaphor")
TAIL_SECONDS = 0.5  # hold after the last word
PROVIDER = os.getenv("FOIL_PLANNER_PROVIDER", "claude-code")  # "codex" or "claude-code" (saved Brainrot provider IDs)
MAX_CAPTION_WORDS = 13
# Reviewer decisions on the approved plan, applied after the model's choices (see README). Keys are block indexes.
OVERRIDES = {
    4: {"event": {"kind": "term_callout", "term": "RODILLOS", "cue": "rodillo"}},  # name the mechanism, not "superficie"
    5: {"event": {"kind": "curl", "cue": "brillante"}},  # a named detail on the hero instead of ambient filler
}
BLOCK_SECONDS = 8.0 # motion.plan's default of 11 s gave 15-22 s blocks on this long-sentenced narration

GUIDANCE = """You plan the camera for a silent low-poly explainer about why aluminium foil has a shiny side and a matte
side. The narration is split into numbered scenes. For each scene choose exactly one shot type and at most one event.

The hero object never changes: a partly unrolled roll of aluminium foil, seen as a cutaway so both faces of one sheet
(one shiny, one matte) are visible at once. It is on screen in every shot except the machinery metaphor.

Shot types (hard cuts between them):
- establishing: the whole roll in its context (the roll on a kitchen counter). Opens the video; may return at the end.
- cutaway: the hero shot. Half of the roll/sheet is modelled away and the camera holds on the cross-section.
- insert: an extreme close-up of one small isolated part on a near-empty background (for example the shiny face
  touching a roller, or the matte face pressed against the other sheet). Use it to land one technical term.
- metaphor: a cutaway of something that is NOT the hero, used for the most dramatic beat. Here it is the cross-section
  of the rolling mill showing two sheets passing together between polished rollers. Use it EXACTLY ONCE, on the scene
  that explains the rollers and the two sheets rolled together. Never anywhere else.

Events (each is locked to one spoken word):
- force_arrows: thin red arrows showing pressure or direction (the rollers squeezing, the sheets moving).
- split: the object changes state (for example the laminated sheets separate to reveal a shiny and a matte face).
- term_callout: a yellow technical term appears. Only on a cutaway or insert. Never on establishing or metaphor.
- curl: a detail on the hero itself: a corner of the foil sheet curls over to show its other face. Use it on a held
  cutaway that would otherwise have nothing but ambient motion.
- none: ambient motion only. Avoid it: a block with no named event reads as static.

For every scene return: scene (the number), shot, event, cue (one to three consecutive words copied exactly from that
scene's narration where the event fires; empty when event is none), term (a term of at most three words copied from
the narration, only for term_callout, otherwise empty), caption (a complete sentence or clause of at most ten words copied verbatim
from that scene's narration, starting and ending at its punctuation, never cut mid-clause, never empty) and why (one short reason). Return one beat per scene. Do not invent facts."""


class Beat(BaseModel):
    scene: int
    shot: Literal["establishing", "cutaway", "insert", "metaphor"]
    event: Literal["force_arrows", "split", "term_callout", "curl", "none"]
    cue: str
    term: str
    caption: str
    why: str


class ShotPlan(BaseModel):
    beats: list[Beat]


def _inside(scene: dict, words: list[dict]) -> list[dict]:
    return [w for w in words if scene["start"] <= w["start"] < scene["end"]]


def _find(phrase: str, scene: dict, words: list[dict]) -> list[dict] | None:
    target = [motion._norm(w) for w in phrase.split() if motion._norm(w)]
    inside = _inside(scene, words)
    for i in range(len(inside) - len(target) + 1 if target else 0):
        if all(motion._norm(inside[i + j]["text"]) == t for j, t in enumerate(target)):
            return inside[i:i + len(target)]
    return None


def design(scenes: list[dict], words: list[dict]) -> None:
    """Ask the model for one beat per scene, validate it, and attach the result to each scene in place."""
    prompt = "\n\n".join(f"Scene {i} ({s['start']:.1f}-{s['end']:.1f} s):\n{s['text']}" for i, s in enumerate(scenes))
    result = llm.generate(GUIDANCE, prompt, ShotPlan, max_tokens=3500, provider=PROVIDER, api_model=llm.API_MODEL)
    beats = {b.scene: b for b in result.beats if 0 <= b.scene < len(scenes)}
    for i, scene in enumerate(scenes):
        scene["notes"] = []
        b = beats.get(i)
        scene["model"] = {"shot": b.shot, "event": b.event, "why": b.why} if b else None
        if b is None:
            scene["notes"].append("model returned no beat; defaulted to cutaway/none")
        shot, event = (b.shot, b.event) if b else ("cutaway", "none")
        if i == 0 and shot != "establishing":
            scene["notes"].append(f"first scene forced to establishing (model chose {shot})")
            shot = "establishing"
        if event == "term_callout" and shot not in ("cutaway", "insert"):
            scene["notes"].append(f"term_callout dropped on {shot}")
            event = "none"
        scene.update(shot=shot, event=event, cue=b.cue if b else "", term=b.term.strip()[:40] if b and event == "term_callout" else "",
                     caption_raw=b.caption if b else "")
    # Exactly one metaphor shot, on the scene that talks about the rollers.
    metaphors = [i for i, s in enumerate(scenes) if s["shot"] == "metaphor"]
    rollers = [sum(s["text"].lower().count("rodill") for s in [scenes[i]])for i in range(len(scenes))]
    keep = max(metaphors, key=lambda i: rollers[i]) if metaphors else max(range(len(scenes)), key=lambda i: rollers[i])
    for i in metaphors:
        if i != keep:
            scenes[i]["notes"].append("extra metaphor demoted to cutaway")
            scenes[i]["shot"] = "cutaway"
    if not metaphors:
        scenes[keep]["notes"].append("no metaphor chosen; assigned to the scene that mentions the rollers most")
    if scenes[keep]["shot"] != "metaphor":
        scenes[keep]["shot"] = "metaphor"
        if scenes[keep]["event"] == "term_callout":
            scenes[keep]["event"], scenes[keep]["term"] = "none", ""
    for i, scene in enumerate(scenes):
        inside = _inside(scene, words)
        # Event time: the first word of the cue, as motion._cue_time does; fall back to just after the scene start.
        hit = _find(scene["cue"], scene, words) if scene["event"] != "none" else None
        if scene["event"] != "none" and not hit:
            scene["notes"].append(f"cue {scene['cue']!r} not found in scene; event moved to scene start + 0.8 s")
        at = round(hit[0]["start"], 2) if hit else round(scene["start"] + .8, 2)
        scene["event"] = {"kind": scene["event"], "cue": scene.pop("cue"), "at": at, "term": scene["term"]} if scene["event"] != "none" else {"kind": "none"}
        scene.pop("term")
        scene.pop("keywords", None)


def clauses(story: dict, words: list[dict]) -> list[tuple[int, int]]:
    """Word-index ranges of clauses. The TTS word list has no punctuation, so use the script's own."""
    title = story["title"].split()
    tokens = title + story["script"].split()
    if len(tokens) != len(words):
        raise ValueError(f"script has {len(tokens)} words but the narration has {len(words)}")
    out, start = [], 0
    for i, t in enumerate(tokens):
        if i == len(title) - 1 or t[-1] in ".,;:!?" or i == len(tokens) - 1:
            out.append((start, i))
            start = i + 1
    return out


def _caption(raw: list[dict] | None, scene: dict, words: list[dict], cl: list[tuple[int, int]], at: float) -> tuple[dict, list[str]]:
    """A caption is a closed phrase: whole clauses, never a cut. Snap the model's phrase to its clause when that is short enough."""
    notes = []
    lo = next(i for i, w in enumerate(words) if scene["start"] - .05 <= w["start"])  # scene starts are rounded to 10 ms
    hi = max(i for i, w in enumerate(words) if w["start"] < scene["end"])
    index = {id(w): i for i, w in enumerate(words)}
    if raw:
        a, b = index[id(raw[0])], index[id(raw[-1])]
        c = next((c for c in cl if c[0] <= a and b <= c[1]), (a, b))
        if (a, b) == c:
            span = (a, b)
        elif c[1] - c[0] + 1 <= MAX_CAPTION_WORDS and lo <= c[0] and c[1] <= hi:
            span = c
            notes.append("caption snapped to its whole clause")
        elif b == c[1]:
            span = (a, b)
        elif c[1] - a + 1 <= MAX_CAPTION_WORDS:
            span = (a, c[1])
            notes.append("caption extended to the end of its clause")
        else:
            span = (a, b)
            notes.append("caption kept as the model's phrase: its clause is too long and it ends mid-clause")
    else:
        notes.append("model gave no usable caption; used the whole clause nearest the event")
        inside = [c for c in cl if lo <= c[0] and c[1] <= hi and 3 <= c[1] - c[0] + 1 <= MAX_CAPTION_WORDS] or [c for c in cl if lo <= c[0] <= hi]
        span = min(inside, key=lambda c: abs(words[c[0]]["start"] - at))
    phrase = words[span[0]:span[1] + 1]
    return {"text": " ".join(w["text"] for w in phrase), "at": round(phrase[0]["start"], 2),
            "until": round(min(phrase[-1]["end"] + 1.0, scene["end"] - .1), 2),
            "words": [{"text": w["text"], "at": round(w["start"], 2)} for w in phrase]}, notes


def finalize(scenes: list[dict], words: list[dict], cl: list[tuple[int, int]]) -> None:
    for i, scene in enumerate(scenes):
        override = OVERRIDES.get(i)
        if override:
            e = override["event"]
            hit = _find(e["cue"], scene, words)
            at = round(hit[0]["start"], 2) if hit else round(scene["start"] + .8, 2)
            scene["event"] = {**e, "at": at}
            scene["notes"] = [n for n in scene["notes"] if not n.startswith("reviewer")]
            scene["notes"].append(f"reviewer override: event {e['kind']} on {e['cue']!r}" + ("" if hit else " (cue not found)"))
        raw = scene.pop("caption_raw", None)
        phrase = _find(raw, scene, words) if raw else None
        if phrase is None and scene.get("caption"):
            starts = {w["at"] for w in scene["caption"]["words"]}
            phrase = [w for w in words if round(w["start"], 2) in starts] or None
        at = scene["event"].get("at", scene["start"] + .8)
        scene["caption"], notes = _caption(phrase, scene, words, cl, at)
        scene["notes"] = [n for n in scene["notes"] if not n.startswith("caption")] + notes


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + TAIL_SECONDS, 2)
    motion.SCENE_SECONDS = BLOCK_SECONDS  # plan() closes a block at the first sentence end after this many seconds
    cl = clauses(json.loads((HERE / "story.json").read_text(encoding="utf-8")), words)
    if "--reuse" in sys.argv:  # re-validate the saved plan without a new model call
        scenes = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))["scenes"]
    else:
        scenes = motion.plan(words, seconds)["scenes"]
        design(scenes, words)
    finalize(scenes, words, cl)
    for i, s in enumerate(scenes):
        s["index"] = i
    (HERE / "plan.json").write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in scenes:
        e = s["event"]
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f}  {s['shot']:<12} {e['kind']:<13} {('@%.1f %r' % (e['at'], e.get('term') or e['cue'])) if e['kind'] != 'none' else '':<30} | {s['caption']['text']}")
        for n in s["notes"]:
            print("      note:", n)
    print(f"{len(scenes)} blocks, {seconds} s")


if __name__ == "__main__":
    main()
