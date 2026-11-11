"""Continuous-world director planner for the CPU experiment (an analogue of brainrot/motion.py plan() + design()).

The reference this follows has no hard cuts: one world, one camera that keeps flying between stations while parts stay where they were put.
So the model does not pick shot types. Per beat (~4 s, a clause or sentence of the narration) it picks WHERE the camera goes (a focus part and
a distance), what is on screen, and up to three events. Everything is validated in code; the model's raw choice stays in plan.json.

  PYTHONPATH=. uv run --locked python experiments/cpu-lowpoly/planner.py [--reuse] [--out PATH]     (from the repository root)
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
BEAT_SECONDS = 3.0
CLAUSE_GAP = 0.35  # TTS word boundaries carry no punctuation: a comma pause is ~0.5 s, a full stop ~0.85 s
PROVIDER = os.getenv("CPU_PLANNER_PROVIDER", "claude-code")  # "codex" or "claude-code" (saved Brainrot provider IDs)
# Stations, in the order the narration introduces them: the camera walks along this line, the chip sits behind it.
HERO = "chip"  # the station the first and last beats return to; another topic overrides it (see experiments/pothole-lowpoly/planner.py)
TARGETS = ["chip", "transistor", "gate", "adder", "alu", "clock", "control", "register", "cache", "ram", "pipeline", "core", "heatsink"]
NOUN_TARGET = {"procesador": "chip", "chip": "chip", "silicio": "chip",
               "transistor": "transistor", "transistores": "transistor", "interruptor": "transistor", "interruptores": "transistor",
               "compuerta": "gate", "compuertas": "gate", "sumador": "adder", "sumadores": "adder", "alu": "alu",
               "reloj": "clock", "pulso": "clock", "pulsos": "clock", "gigahertz": "clock",
               "control": "control", "contador": "control", "registro": "register", "registros": "register",
               "caché": "cache", "cache": "cache", "ram": "ram", "memoria": "ram", "pipeline": "pipeline", "núcleo": "core", "núcleos": "core",
               "disipador": "heatsink", "ventilador": "heatsink"}
GLOSSARY = sorted({k for k in NOUN_TARGET if k not in ("interruptor", "interruptores", "memoria", "contador", "pulso", "pulsos", "silicio", "chip", "procesador", "gigahertz")})
# A red arrow needs a real flow, push or directed motion in its cue; a part name alone is only a highlight.
FORCE_STEMS = ("corrient", "voltaj", "pasa", "cort", "salta", "avanz", "empuj", "sube", "baja", "fluy", "lee", "guarda", "sac", "marca",
               "apuest", "tira", "conmut", "mueve", "adivin", "descart", "ejecut", "busc", "decod", "buscar")

GUIDANCE = """You direct a silent low-poly explainer about how a computer processor (CPU) works, in ONE continuous 3D world with no cuts.
The world is a long desk. At the middle sits a motherboard with the processor chip (the hero, station "chip"). In FRONT of it a workbench runs
left to right, with one station per part, already placed in the order the narration introduces them. The camera never cuts: at every beat it
flies to a station (about one second) and then drifts slowly there. A part is drawn on the bench from the first beat that focuses it, so parts
accumulate and stay.

Stations (focus targets), in bench order: chip (the processor on the motherboard), transistor (a tiny switch with a lever, current on/off),
gate (logic gates NOT/AND/OR), adder (sumadores), alu (the arithmetic block), clock (a ticking pulse generator), control (the control unit and
the program counter pointing at memory addresses), register (tiny fast slots), cache (three stacked layers L1 L2 L3), ram (memory sticks, far
from the chip), pipeline (an assembly-line conveyor of instructions through stages), core (several cores side by side), heatsink (heatsink and
fan; at the end it is installed on the chip).

Distance of the camera: wide (the station and its surroundings), medium (the part), close (one detail of it).

The narration is split into numbered beats of a few seconds. For each beat return: scene (the number), focus (a station), dist, show (one short
sentence IN SPANISH: what the viewer sees and what moves), events and why (one short reason).

Events (each locked to one spoken word; up to three per beat; times are the cue word's start):
- highlight: a brief neutral pulse on ONE part, no force colour. Use it whenever the narration names a part but nothing moves. target = a station.
- force_arrows: thin red arrows. ONLY when the narration at that word describes real flow or directed motion: current passing or being cut, a
  pulse stepping, the program counter jumping or reading, a result saved, the chip guessing a branch, heat leaving. A part name alone is NOT a
  force. Never use force_arrows just to name a part. target = the station where the arrow is drawn.
- term_callout: a yellow technical term copied from the narration: transistor, compuertas, ALU, reloj, registro, caché, RAM, núcleos, pipeline,
  disipador. Each term at most ONCE in the video.

HARD RULES (checked after you answer):
1. The first beat is focus chip, dist wide.
2. Follow the narration: focus the station of the part being talked about; do not jump back and forth. Return to chip only for the opening, when
   the narration talks about the chip as a whole, and for the last beat.
3. Every named part the narration says (transistores, compuertas, sumadores, ALU, reloj, registros, caché, RAM, núcleos, pipeline, disipador)
   must get an event whose cue is that word or sits within two seconds of it. Prefer highlight for a part that is only named, term_callout the
   first time a part is introduced, force_arrows only for real flow.
4. No more than 9 seconds may pass with no event and no change of focus or distance. Vary dist between wide, medium and close across beats on
   the same station instead of repeating one.
5. At most one term_callout may start within any 3 seconds, and no two events may start within one second of each other.
6. Never return filler: every event needs a real cue copied from that beat."""


class Ev(BaseModel):
    kind: Literal["highlight", "force_arrows", "term_callout"]
    cue: str
    term: str
    target: str


class Beat(BaseModel):
    scene: int
    focus: Literal["chip", "transistor", "gate", "adder", "alu", "clock", "control", "register", "cache", "ram", "pipeline", "core", "heatsink"]
    dist: Literal["wide", "medium", "close"]
    show: str
    events: list[Ev]
    why: str


class WorldPlan(BaseModel):
    beats: list[Beat]


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))


_NOUNS = {_plain(k): v for k, v in NOUN_TARGET.items()}


def _strip(word: str) -> str:
    return _plain(word).strip(".,;:!?¿¡")


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
        t = _NOUNS.get(_strip(w))
        if t:
            return t
    return ""


def _is_force(cue: str) -> bool:
    return any(any(st in _plain(w) for st in FORCE_STEMS) for w in cue.split() if _strip(w) not in _NOUNS)


def design(scenes: list[dict], words: list[dict], saved: list | None = None) -> None:
    """`saved` re-validates the model's raw beats from an earlier plan.json (--revalidate) without a new model call."""
    if saved is None:
        prompt = "\n\n".join(f"Beat {i} ({s['start']:.1f}-{s['end']:.1f} s):\n{_timed(s, words)}" for i, s in enumerate(scenes))
        result = llm.generate(GUIDANCE, prompt, WorldPlan, max_tokens=16000, provider=PROVIDER, api_model=llm.API_MODEL)
        beats = {b.scene: b for b in result.beats if 0 <= b.scene < len(scenes)}
    else:
        beats = {i: Beat(scene=i, **m) for i, m in enumerate(saved[:len(scenes)]) if m}
    last_term_at, used_terms = -99.0, set()
    accepted: list[float] = []
    for i, scene in enumerate(scenes):
        scene["notes"], scene["index"] = [], i
        b = beats.get(i)
        scene["model"] = {"focus": b.focus, "dist": b.dist, "show": b.show, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        focus, dist, show = (b.focus, b.dist, b.show) if b else (scenes[i - 1]["focus"] if i else HERO, "medium", "")
        if b is None:
            scene["notes"].append("model returned no beat; kept the previous focus at medium distance")
        if i == 0 and (focus, dist) != (HERO, "wide"):
            scene["notes"].append(f"first beat forced to chip/wide (model chose {focus}/{dist})")
            focus, dist = HERO, "wide"
        evs = []
        for e in (b.events if b else [])[:3]:
            kind, term, target = e.kind, e.term.strip().lower(), e.target.strip().lower()
            hit = _find(e.cue, scene, words)
            if not hit:
                scene["notes"].append(f"cue {e.cue!r} not found in beat; event dropped")
                continue
            at = round(hit[0]["start"], 2)
            if kind == "force_arrows" and not _is_force(e.cue):
                target = target if target in TARGETS else _noun_target(e.cue)
                scene["notes"].append(f"force_arrows on {e.cue!r} has no flow or motion word; " + (f"downgraded to highlight({target})" if target else "dropped"))
                if not target:
                    continue
                kind = "highlight"
            if kind == "term_callout":
                if _plain(term) not in [_plain(g) for g in GLOSSARY]:
                    scene["notes"].append(f"term {term!r} is not a real part name; callout dropped")
                    continue
                target = _NOUNS.get(_plain(term), "")
                if term in used_terms or at - last_term_at < 3:
                    scene["notes"].append(f"term {term!r} " + ("already used" if term in used_terms else "within 3 s of another callout") + f"; downgraded to highlight({target})")
                    if not target:
                        continue
                    kind = "highlight"
                else:
                    used_terms.add(term)
                    last_term_at = at
            if target not in TARGETS:
                target = _noun_target(e.cue) or focus
            if kind != "term_callout" and any(abs(at - t) < 0.8 for t in accepted):  # a callout is a caption, it never collides with an on-part effect
                scene["notes"].append(f"{kind} at {at}s dropped: collides with another event")
                continue
            ev = {"kind": kind, "cue": e.cue, "at": at, "target": target}
            if kind == "term_callout":
                ev["term"] = term.upper()
            else:
                accepted.append(at)
            evs.append(ev)
        scene["focus"], scene["dist"], scene["show"] = focus, dist, show
        scene["events"] = sorted(evs, key=lambda x: x["at"])
        scene.pop("keywords", None)
    last = scenes[-1]
    if last["focus"] != HERO:
        last["notes"].append(f"last beat forced to chip (model chose {last['focus']}) so the heatsink is installed and the camera pulls back")
        last["focus"], last["dist"] = HERO, "wide"


def snap_boundaries(scenes: list[dict], lead: float = 0.3) -> None:
    """A part must be on screen when its word is spoken: if a beat has an event on the station the NEXT beat focuses (and not its own),
    move the boundary to just before that word and hand the event to the next beat."""
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        for e in list(a["events"]):
            if e["target"] != a["focus"] and e["target"] == b["focus"] and e["target"] != HERO:
                cut = round(e["at"] - lead, 2)
                if cut - a["start"] >= 2.0 and b["end"] - cut >= 2.0 and b["start"] - cut <= 4.0:
                    a["notes"].append(f"boundary moved from {b['start']:.1f}s to {cut:.1f}s so {e['target']} is on screen at {e['at']:.1f}s")
                    a["end"], b["start"] = cut, cut
                    moved = [x for x in a["events"] if x["at"] >= cut]
                    a["events"] = [x for x in a["events"] if x["at"] < cut]
                    b["events"] = sorted(moved + b["events"], key=lambda x: x["at"])
                    break


def split_long(scenes: list[dict], words: list[dict], limit: float = 6.5) -> list[dict]:
    """motion.plan() only cuts on sentence ends. Split any beat longer than `limit` at the longest pause near its middle, repeatedly,
    so the camera has something new to do every ~3-6 s."""
    out, stack = [], list(reversed(scenes))
    while stack:
        s = stack.pop()
        if s["end"] - s["start"] <= limit:
            out.append(s)
            continue
        idx = [i for i, w in enumerate(words) if s["start"] - .05 <= w["start"] < s["end"]]
        mid = (s["start"] + s["end"]) / 2
        cands = [i for i in idx[1:] if s["start"] + 2.2 <= words[i]["start"] <= s["end"] - 2.2]
        if not cands:
            out.append(s)
            continue
        k = max(cands, key=lambda i: (round(words[i]["start"] - words[i - 1]["end"], 1), -abs(words[i]["start"] - mid)))
        cut = words[k]["start"]
        first = {**s, "end": round(cut, 2), "text": " ".join(words[i]["text"] for i in idx if i < k)}
        second = {**s, "start": round(cut, 2), "text": " ".join(words[i]["text"] for i in idx if i >= k)}
        stack += [second, first]
    return out


def fill_gaps(scenes: list[dict], words: list[dict], total: float, cap: float = 9.0) -> None:
    """Hold cap in code: where more than `cap` seconds pass with no event and no change of focus or distance, add a neutral highlight
    on the nearest part noun (never a red arrow)."""
    for _ in range(30):
        changes = sorted({0.0, total} | {e["at"] for s in scenes for e in s["events"]}
                         | {b["start"] for a, b in zip(scenes, scenes[1:]) if (a["focus"], a["dist"]) != (b["focus"], b["dist"])})
        gap = next(((a, b) for a, b in zip(changes, changes[1:]) if b - a > cap), None)
        if gap is None:
            return
        a, b = gap
        taken = [e["at"] for s in scenes for e in s["events"]]
        cands = [w for w in words if a + 2.5 <= w["start"] <= b - 2.0 and all(abs(w["start"] - t) >= 0.8 for t in taken)]
        nouns = [w for w in cands if _strip(w["text"]) in _NOUNS]
        pick = min(nouns or cands, key=lambda w: abs(w["start"] - (a + cap - 1.5)), default=None) if (nouns or cands) else None
        if pick is None:
            return
        scene = next(s for s in scenes if s["start"] - .05 <= pick["start"] < s["end"])
        target = _NOUNS.get(_strip(pick["text"])) or scene["focus"]
        scene["events"] = sorted(scene["events"] + [{"kind": "highlight", "cue": pick["text"], "at": round(pick["start"], 2), "target": target}], key=lambda e: e["at"])
        scene["notes"].append(f"gap of {b - a:.1f} s with no event: validator added highlight({target}) on {pick['text']!r} at {pick['start']:.1f}s")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + TAIL_SECONDS, 2)
    if "--reuse" in sys.argv:  # re-validate a saved plan (adds hold-cap highlights) without a new model call
        scenes = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))["scenes"]
        fill_gaps(scenes, words, seconds)
    else:
        motion.SCENE_SECONDS, motion.SENTENCE_GAP = BEAT_SECONDS, CLAUSE_GAP
        scenes = split_long(motion.plan(words, seconds)["scenes"], words)
        saved = [s.get("model") for s in json.loads((HERE / "plan.json").read_text(encoding="utf-8"))["scenes"]] if "--revalidate" in sys.argv else None
        design(scenes, words, saved)  # --revalidate: same model beats, new validator rules, no model call
        snap_boundaries(scenes)
        fill_gaps(scenes, words, seconds)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "plan.json"
    out.write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "rate": spoken["rate"], "provider": PROVIDER,
                               "model_env": os.getenv("BRAINROT_CLAUDE_MODEL"), "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in scenes:
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f} ({s['end'] - s['start']:4.1f}s) {s['focus']:<10} {s['dist']:<6}",
              " | ".join(f"{e['at']:.1f} {e['kind'][:5]}→{e['target']}{(' [' + e['term'] + ']') if e.get('term') else ''}" for e in s["events"]))
        print("      show:", s["show"])
        for n in s["notes"]:
            print("      note:", n)
    print(f"{len(scenes)} beats, {seconds} s, provider {PROVIDER}, model {os.getenv('BRAINROT_CLAUDE_MODEL')}")


if __name__ == "__main__":
    main()
