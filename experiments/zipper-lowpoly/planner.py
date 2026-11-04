"""Shot planner for the zipper experiment, an analogue of brainrot/motion.py (plan() + design()).

plan(): brainrot.motion.plan groups the word timings into blocks on sentence ends.
design(): the selected model (the default one for this experiment) picks, per block, a shot type, HOW the shot sustains itself
(camera-driven or assembly-driven, the recipe's two valid ways) and up to four events, as a Pydantic model, never code.
Everything is validated here; the model's raw choice stays in plan.json next to the validated one. Captions are not chosen by the
model: build_script.py groups the words into 2-5 word phrases deterministically.

  PYTHONPATH=. uv run --locked python experiments/zipper-lowpoly/planner.py [--out PATH]     (from the repository root)
"""
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from brainrot import llm, motion

HERE = Path(__file__).resolve().parent
TAIL_SECONDS = 0.5
BLOCK_SECONDS = 8.0
PROVIDER = os.getenv("ZIPPER_PLANNER_PROVIDER", "claude-code")  # "codex" or "claude-code" (saved Brainrot provider IDs)
TARGETS = ["tape", "teeth", "slider", "tab", "stop"]
PUSHIN_TARGETS = ["neck", "slider", "teeth", "tab"]
# Spanish nouns for the parts (accent-insensitive). The slider is "cursor"/"corredera", the pull tab "jalador"/"tirador".
NOUN_TARGET = {"diente": "teeth", "dientes": "teeth", "cinta": "tape", "cintas": "tape", "tela": "tape", "cursor": "slider", "corredera": "slider",
               "carro": "slider", "cuña": "slider", "divisor": "slider", "jalador": "tab", "jaladera": "tab", "tirador": "tab", "lengüeta": "tab",
               "asa": "tab", "tope": "stop", "topes": "stop"}
GLOSSARY = sorted({k for k in NOUN_TARGET if k not in ("tela", "asa", "carro")})
# A red arrow needs a real push, squeeze, pull or direction in its cue; a part name alone is only a highlight.
FORCE_STEMS = ("fuerz", "empuj", "apriet", "junt", "oblig", "presion", "tira", "jal", "abr", "separ", "cierr", "sube", "subir", "subiendo",
               "baja", "bajar", "desliz", "arrastr", "une", "unir", "pega", "aguant", "sosti", "estir", "aprision", "enganch", "trab")

GUIDANCE = """You plan the camera for a silent low-poly explainer about how a zipper works: two fabric tapes with rows of staggered teeth,
a Y-shaped slider (the cursor) that squeezes the rows together as it goes up and pries them apart as it goes down, a pull tab on the slider,
and the stops at the ends. The narration is split into numbered scenes. For each scene choose one shot type, how the shot sustains itself,
and up to four events.

The hero is always the zipper (teeth rows, slider, pull tab, tapes, stops) on a jacket's fabric.

Shot types (hard cuts between them):
- establishing: the whole zipper on the jacket, with the slider travelling up and down. May open and close the video.
- cutaway: the zipper opened up to show the mechanism: the slider with its top plate removed, the wedge inside it, the teeth entering and
  leaving. Most of the runtime lives here.
- insert: an extreme close-up of one small thing on a near-empty background (the teeth meshing at the slider's neck, a single tooth).

How a shot sustains itself (choose deliberately, per shot):
- camera: the camera moves slowly (orbit or push) over the whole shot while the zipper keeps working. The default.
- assembly: the camera is locked and the zipper is visibly BUILT, one part at a time, across the shot. Use it only on the scene where the
  narration introduces the parts one after another (tapes, teeth, slider, pull tab, stops). An assembly shot must have at least three
  `attach` events with different targets, spaced a few seconds apart. Do not use assembly on a scene that merely talks over a finished
  zipper.

Events (each locked to one spoken word; a scene may have up to four):
- highlight: a brief neutral pulse on ONE named part, no force colour and no flow colour. Use it whenever the narration names a part but
  nothing is being pushed. Target one of: tape, teeth, slider, tab, stop.
- force_arrows: thin red arrows. ONLY when the narration at that word describes an actual force, push, squeeze, pull or direction of
  motion: the slider pushing the rows together, prying them apart, pulling the tab, the teeth being forced to hook. A part name alone, or a
  word like "importa", is not a force. Never use force_arrows just to name a part.
- term_callout: a yellow technical term. Only on a cutaway or insert. The term must name a real part and be copied from the narration:
  diente(s), cinta, cursor, corredera, jalador, tirador, lengüeta, tope(s), cuña, divisor. Each term may be used AT MOST ONCE in the whole video.
- attach: only inside an assembly shot: the named part flies in and settles. target: tape, teeth, slider, tab or stop. One attach per part.
- pushin: a continuous push-in and pull-out of the SAME camera onto a detail (instead of cutting to an insert), lasting about five seconds.
  target: neck (where the teeth mesh inside the slider), slider, teeth or tab. Use it at least once in the whole plan, ideally to land a
  technical detail such as one tooth meshing with the slider. Not inside an assembly shot.

HARD RULES for the whole plan (checked after you answer):
1. No more than 9 seconds may pass without an event or a cut to a different shot type. Each line below shows its start time in seconds.
2. Every named part the narration says (diente(s), cinta, cursor/corredera, jalador/tirador, tope(s), cuña) must get an event whose cue is that
   word or sits within two seconds of it. Prefer highlight for a part that is only named, term_callout the first time a part is introduced,
   force_arrows only for real forces.
3. Never return an empty list and never use filler: every event needs a real cue copied from that scene.
4. At most one term_callout may start within any 3 seconds, and no two events may start within one second of each other.
5. Prefer alternating establishing, cutaway and insert over many cutaways in a row.
6. Exactly ONE scene must be an assembly shot (sustain "assembly"): the scene whose narration names the most DIFFERENT parts (tape, teeth,
   slider/cursor, pull tab/jalador, stops/topes). Put an attach event on each part's noun in that scene, at least three different parts, in
   the order the narration says them. The parts are then built one at a time while the camera stays locked. Do not use assembly anywhere else.

For every scene return: scene (the number), shot, sustain, events (a list; each with kind, cue = one to three consecutive words copied
exactly from that scene's narration, term only for term_callout otherwise an empty string, target for highlight, attach and pushin
otherwise an empty string) and why (one short reason)."""


class Ev(BaseModel):
    kind: Literal["highlight", "force_arrows", "term_callout", "attach", "pushin"]
    cue: str
    term: str
    target: str


class Beat(BaseModel):
    scene: int
    shot: Literal["establishing", "cutaway", "insert"]
    sustain: Literal["camera", "assembly"]
    events: list[Ev]
    why: str


class ShotPlan(BaseModel):
    beats: list[Beat]


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))


def _inside(scene: dict, words: list[dict]) -> list[dict]:
    return [w for w in words if scene["start"] - .05 <= w["start"] < scene["end"]]


def _find(phrase: str, scene: dict, words: list[dict]) -> list[dict] | None:
    target = [motion._norm(w) for w in phrase.split() if motion._norm(w)]
    inside = _inside(scene, words)
    for i in range(len(inside) - len(target) + 1 if target else 0):
        if all(motion._norm(inside[i + j]["text"]) == t for j, t in enumerate(target)):
            return inside[i:i + len(target)]
    return None


def _timed(scene: dict, words: list[dict]) -> str:
    ws = _inside(scene, words)
    return "\n".join(f"[{ws[i]['start']:.1f}s] " + " ".join(w["text"] for w in ws[i:i + 6]) for i in range(0, len(ws), 6))


def _noun_target(text: str) -> str:
    for w in text.split():
        t = NOUN_TARGET.get(w.lower().strip(".,;:!?¿¡"))
        if t:
            return t
    return ""


def _is_force(cue: str) -> bool:
    """A force or motion word that is not itself just a part name."""
    return any(any(st in _plain(w) for st in FORCE_STEMS) for w in cue.split() if w.lower().strip(".,;:!?¿¡") not in NOUN_TARGET)


def design(scenes: list[dict], words: list[dict]) -> None:
    prompt = "\n\n".join(f"Scene {i} ({s['start']:.1f}-{s['end']:.1f} s):\n{_timed(s, words)}" for i, s in enumerate(scenes))
    result = llm.generate(GUIDANCE, prompt, ShotPlan, max_tokens=7000, provider=PROVIDER, api_model=llm.API_MODEL)
    beats = {b.scene: b for b in result.beats if 0 <= b.scene < len(scenes)}
    last_term_at, used_terms = -99.0, set()
    accepted: list[tuple[float, str]] = []
    for i, scene in enumerate(scenes):
        scene["notes"] = []
        b = beats.get(i)
        scene["model"] = {"shot": b.shot, "sustain": b.sustain, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        shot, sustain = (b.shot, b.sustain) if b else ("cutaway", "camera")
        if b is None:
            scene["notes"].append("model returned no beat; defaulted to cutaway/camera")
        if i == 0 and shot != "establishing":
            scene["notes"].append(f"first scene forced to establishing (model chose {shot})")
            shot = "establishing"
        if sustain == "assembly" and shot == "insert":
            scene["notes"].append("assembly on an insert is not allowed; sustain set to camera")
            sustain = "camera"
        evs = []
        for e in (b.events if b else [])[:4]:
            kind, term, target = e.kind, e.term.strip().lower(), e.target.strip().lower()
            if kind == "term_callout" and shot not in ("cutaway", "insert"):
                scene["notes"].append("term_callout dropped on establishing")
                continue
            if kind == "attach" and sustain != "assembly":
                scene["notes"].append(f"attach {e.cue!r} dropped: scene is not an assembly shot")
                continue
            if kind == "pushin" and sustain == "assembly":
                scene["notes"].append("pushin dropped inside an assembly shot")
                continue
            hit = _find(e.cue, scene, words)
            if not hit:
                scene["notes"].append(f"cue {e.cue!r} not found in scene; event dropped")
                continue
            at = round(hit[0]["start"], 2)
            if any(abs(at - t) < 0.8 for t, _k in accepted) or any(abs(at - t) < 1.5 and k == kind for t, k in accepted):
                scene["notes"].append(f"{kind} at {at}s dropped: collides with another event")
                continue
            if kind == "force_arrows" and not _is_force(e.cue):
                target = target if target in TARGETS else _noun_target(e.cue)
                scene["notes"].append(f"force_arrows on {e.cue!r} has no force or motion word; " + (f"downgraded to highlight({target})" if target else "dropped"))
                if not target:
                    continue
                kind = "highlight"
            if kind == "term_callout":
                if _plain(term) not in [_plain(g) for g in GLOSSARY]:
                    scene["notes"].append(f"term {term!r} is not a real part name; callout dropped")
                    continue
                if term in used_terms or at - last_term_at < 3:
                    target = NOUN_TARGET.get(term, "")
                    scene["notes"].append(f"term {term!r} " + ("already used" if term in used_terms else "within 3 s of another callout") + f"; downgraded to highlight({target})")
                    if not target:
                        continue
                    kind = "highlight"
                else:
                    used_terms.add(term)
                    last_term_at = at
                    target = NOUN_TARGET.get(term, "")
            if kind in ("highlight", "attach"):
                target = target if target in TARGETS else _noun_target(e.cue)
                if target not in TARGETS:
                    scene["notes"].append(f"{kind} on {e.cue!r} has no valid target; dropped")
                    continue
            if kind == "pushin" and target not in PUSHIN_TARGETS:
                target = "neck"
            if kind == "attach" and any(x["kind"] == "attach" and x["target"] == target for x in evs):
                scene["notes"].append(f"attach {target} dropped: already attached in this shot")
                continue
            ev = {"kind": kind, "cue": e.cue, "at": at, "target": target if kind in ("highlight", "attach", "pushin", "term_callout") else ""}
            if kind == "term_callout":
                ev["term"] = term.upper()
            accepted.append((at, kind))
            evs.append(ev)
        if sustain == "assembly" and len({x["target"] for x in evs if x["kind"] == "attach"}) < 3:
            scene["notes"].append("assembly shot has fewer than three distinct attach events; sustain set to camera and attach events dropped")
            sustain = "camera"
            evs = [x for x in evs if x["kind"] != "attach"]
        scene["shot"], scene["sustain"] = shot, sustain
        scene["events"] = sorted(evs, key=lambda x: x["at"])
        scene["index"] = i
        scene.pop("keywords", None)
    if not any(x["kind"] == "pushin" for s in scenes for x in s["events"]):  # the recipe asks for a push-in/pull-out at least once
        cand = next((s for s in scenes if s["shot"] == "cutaway" and s["sustain"] == "camera"), None) or next(s for s in scenes if s["sustain"] == "camera")
        at = round(cand["start"] + (cand["end"] - cand["start"]) / 2, 2)
        cand["events"] = sorted(cand["events"] + [{"kind": "pushin", "cue": "", "at": at, "target": "neck"}], key=lambda x: x["at"])
        cand["notes"].append(f"no pushin from the model; validator added one on the neck at {at}s")
    for s in scenes:
        s["event"] = s["events"][0] if s["events"] else {"kind": "none"}


def fill_gaps(scenes: list[dict], words: list[dict], total: float, cap: float = 9.0) -> None:
    """Enforce the recipe's hold cap in code: where more than `cap` seconds pass with no event and no cut to a different shot type,
    add a neutral highlight on the nearest part noun (never a red arrow)."""
    for _ in range(30):
        changes = sorted({0.0, total} | {e["at"] for s in scenes for e in s["events"]}
                         | {b["start"] for a, b in zip(scenes, scenes[1:]) if (a["shot"], a["sustain"]) != (b["shot"], b["sustain"])})
        gap = next(((a, b) for a, b in zip(changes, changes[1:]) if b - a > cap), None)
        if gap is None:
            return
        a, b = gap
        taken = [e["at"] for s in scenes for e in s["events"]]
        cands = [w for w in words if a + 2.5 <= w["start"] <= b - 2.0 and all(abs(w["start"] - t) >= 0.8 for t in taken)]
        nouns = [w for w in cands if w["text"].lower().strip(".,;:!?¿¡") in NOUN_TARGET]
        pick = min(nouns or cands, key=lambda w: abs(w["start"] - (a + cap - 1.5)), default=None) if (nouns or cands) else None
        if pick is None:
            return
        scene = next(s for s in scenes if s["start"] - .05 <= pick["start"] < s["end"])
        before = [e for e in scene["events"] if e["at"] < pick["start"] and e.get("target") in TARGETS]
        target = NOUN_TARGET.get(pick["text"].lower().strip(".,;:!?¿¡")) or (before[-1]["target"] if before else "teeth")
        scene["events"] = sorted(scene["events"] + [{"kind": "highlight", "cue": pick["text"], "at": round(pick["start"], 2), "target": target}], key=lambda e: e["at"])
        scene["notes"].append(f"gap of {b - a:.1f} s with no event: validator added highlight({target}) on {pick['text']!r} at {pick['start']:.1f}s")
    for s in scenes:
        s["event"] = s["events"][0] if s["events"] else {"kind": "none"}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + TAIL_SECONDS, 2)
    if "--reuse" in sys.argv:  # re-validate a saved plan (adds hold-cap highlights) without a new model call
        scenes = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))["scenes"]
        fill_gaps(scenes, words, seconds)
        for s in scenes:
            s["event"] = s["events"][0] if s["events"] else {"kind": "none"}
    else:
        motion.SCENE_SECONDS = BLOCK_SECONDS
        scenes = motion.plan(words, seconds)["scenes"]
        design(scenes, words)
        fill_gaps(scenes, words, seconds)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "plan.json"
    out.write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "rate": spoken["rate"], "provider": PROVIDER,
                               "model_env": os.getenv("BRAINROT_CLAUDE_MODEL"), "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in scenes:
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f} ({s['end'] - s['start']:4.1f}s) {s['shot']:<12} {s['sustain']:<8}",
              " | ".join(f"{e['at']:.1f} {e['kind'][:5]}{('→' + e['target']) if e.get('target') else ''}{(' [' + e['term'] + ']') if e.get('term') else ''}" for e in s["events"]))
        for n in s["notes"]:
            print("      note:", n)
    print(f"{len(scenes)} blocks, {seconds} s, provider {PROVIDER}, model {os.getenv('BRAINROT_CLAUDE_MODEL')}")


if __name__ == "__main__":
    main()
