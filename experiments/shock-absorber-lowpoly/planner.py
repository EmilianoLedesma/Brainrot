"""Shot planner for the shock-absorber experiment, an analogue of brainrot/motion.py (plan() + design()).

plan(): brainrot.motion.plan groups the word timings into blocks on sentence ends.
design(): the selected model (BRAINROT_CLAUDE_MODEL when the Claude provider is used) picks one of the recipe's shot types
and at most one event per block, as a Pydantic model, never code. Everything is validated here and the model's raw choice
is kept in plan.json next to the validated one. Captions are not chosen by the model: build_script.py groups the words into
2-5 word phrases deterministically.

  PYTHONPATH=. uv run --locked python experiments/shock-absorber-lowpoly/planner.py [--reuse]     (from the repository root)
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
TAIL_SECONDS = 0.5
BLOCK_SECONDS = 8.0
PROVIDER = os.getenv("SHOCK_PLANNER_PROVIDER", "claude-code")  # "codex" or "claude-code" (saved Brainrot provider IDs)
GLOSSARY = ["pistón", "válvula", "válvulas", "amortiguador", "resorte", "aceite", "cilindro", "varilla", "suspensión", "carrocería", "rueda", "llantas", "llanta"]  # real parts only

GUIDANCE = """You plan the camera for a silent low-poly explainer about how a car's shock absorber (damper) works and why it
calms bumps instead of letting the car keep bouncing. The narration is split into numbered scenes. For each scene choose
exactly one shot type and at most one event.

Hero objects: the shock absorber (a sealed cylinder of oil with a piston on a rod, the piston having small valve passages)
and the coil spring beside it. They are always the subject.

Shot types (hard cuts between them):
- establishing: the whole suspension in context: wheel, suspension arm, chassis, road, coil spring and damper, with the car
  riding over bumps. Opens the video; may return later.
- cutaway: the hero shot. A cross-section of the damper: tube, oil, piston and rod moving, with the spring and the mounts.
  Most of the runtime lives here.
- insert: an extreme close-up of one small part against a near-empty background: the piston face and its valve passages
  with oil squeezing through. Use it to land one technical term.
- metaphor: not needed for this topic. Do not use it.

Events (each locked to one spoken word):
- force_arrows: thin red arrows for a force or a direction of push (the bump hitting the wheel, the rod being pushed).
- flow_chevrons: small grey/white chevrons showing oil flowing through the valve passages. Only on a cutaway or insert.
- term_callout: a yellow technical term appears. Only on a cutaway or insert. The term must name a real part from this list
  and be copied from the narration: pistón, válvula, amortiguador, resorte, aceite, cilindro, varilla, suspensión.
- damp: the suspension switches from ringing (bouncing for a long time) to damped (settling quickly). Only on establishing or
  cutaway; use it on the scene where the damper starts doing its job.
- none: only if no event fits. A scene with no named event reads as static, so avoid it.

For every scene return: scene (the number), shot, event, cue (one to three consecutive words copied exactly from that scene's
narration where the event fires; empty when event is none), term (only for term_callout, otherwise empty) and why (one short
reason). Return one beat per scene. Do not invent facts."""


class Beat(BaseModel):
    scene: int
    shot: Literal["establishing", "cutaway", "insert", "metaphor"]
    event: Literal["force_arrows", "flow_chevrons", "term_callout", "damp", "none"]
    cue: str
    term: str
    why: str


class ShotPlan(BaseModel):
    beats: list[Beat]


def _inside(scene: dict, words: list[dict]) -> list[dict]:
    return [w for w in words if scene["start"] - .05 <= w["start"] < scene["end"]]


def _find(phrase: str, scene: dict, words: list[dict]) -> list[dict] | None:
    target = [motion._norm(w) for w in phrase.split() if motion._norm(w)]
    inside = _inside(scene, words)
    for i in range(len(inside) - len(target) + 1 if target else 0):
        if all(motion._norm(inside[i + j]["text"]) == t for j, t in enumerate(target)):
            return inside[i:i + len(target)]
    return None


def design(scenes: list[dict], words: list[dict]) -> None:
    prompt = "\n\n".join(f"Scene {i} ({s['start']:.1f}-{s['end']:.1f} s):\n{s['text']}" for i, s in enumerate(scenes))
    result = llm.generate(GUIDANCE, prompt, ShotPlan, max_tokens=3500, provider=PROVIDER, api_model=llm.API_MODEL)
    beats = {b.scene: b for b in result.beats if 0 <= b.scene < len(scenes)}
    for i, scene in enumerate(scenes):
        scene["notes"] = []
        b = beats.get(i)
        scene["model"] = {"shot": b.shot, "event": b.event, "cue": b.cue, "term": b.term, "why": b.why} if b else None
        if b is None:
            scene["notes"].append("model returned no beat; defaulted to cutaway/none")
        shot, event = (b.shot, b.event) if b else ("cutaway", "none")
        if shot == "metaphor":
            scene["notes"].append("metaphor shot demoted to cutaway (not used for this topic)")
            shot = "cutaway"
        if i == 0 and shot != "establishing":
            scene["notes"].append(f"first scene forced to establishing (model chose {shot})")
            shot = "establishing"
        if event in ("term_callout", "flow_chevrons") and shot not in ("cutaway", "insert"):
            scene["notes"].append(f"{event} dropped on {shot}")
            event = "none"
        if event == "damp" and shot == "insert":
            scene["notes"].append("damp dropped on insert")
            event = "none"
        scene.update(shot=shot, event=event, cue=b.cue if b else "", term=b.term.strip().lower() if b else "")
        scene.pop("keywords", None)


def finalize(scenes: list[dict], words: list[dict]) -> None:
    for i, scene in enumerate(scenes):
        scene["index"] = i
        kind = scene["event"] if isinstance(scene["event"], str) else scene["event"]["kind"]
        raw = scene if isinstance(scene["event"], str) else {"cue": scene["event"].get("cue", ""), "term": scene["event"].get("term", "").lower()}
        if kind == "none":
            scene["event"] = {"kind": "none"}
            continue
        hit = _find(raw["cue"], scene, words)
        if not hit:
            scene["notes"].append(f"cue {raw['cue']!r} not found in scene; event moved to scene start + 0.8 s")
        at = round(hit[0]["start"], 2) if hit else round(scene["start"] + .8, 2)
        event = {"kind": kind, "cue": raw["cue"], "at": at}
        if kind == "term_callout":
            term = raw["term"]
            if term not in GLOSSARY:
                found = next((g for g in GLOSSARY if re.search(rf"\b{g}\b", scene["text"].lower())), None)
                scene["notes"].append(f"term {term!r} is not a real part name; " + (f"replaced by {found!r}" if found else "callout dropped"))
                term = found
            if term is None:
                scene["event"] = {"kind": "none"}
                continue
            event["term"] = term.upper()
            hit = _find(term, scene, words)
            event["at"] = round(hit[0]["start"], 2) if hit else at
        scene["event"] = event
        for key in ("cue", "term"):
            scene.pop(key, None)


# ---- v2: several events per block, with the recipe's hold cap and noun-acknowledgement rules stated in the prompt -------------------
TARGETS = ["spring", "damper", "piston", "rod", "valve", "oil", "cylinder", "wheel", "body", "suspension"]
NOUN_TARGET = {"resorte": "spring", "amortiguador": "damper", "pistón": "piston", "varilla": "rod", "válvula": "valve", "válvulas": "valve",
               "aceite": "oil", "cilindro": "cylinder", "suspensión": "suspension", "carrocería": "body", "rueda": "wheel", "llantas": "wheel", "llanta": "wheel"}
# A red arrow needs a real force, push, load or motion in its cue; otherwise it is only naming a part and becomes a highlight.
FORCE_STEMS = ("fuerz", "golp", "bache", "tope", "empuj", "apriet", "comprim", "estir", "peso", "carg", "rebot", "brinc", "salt", "sub", "baj",
               "regres", "fren", "resist", "contact", "pierd", "presion", "cuest")

GUIDANCE2 = GUIDANCE.split("Events (each locked")[0] + """Events (each locked to one spoken word; a scene may have up to three):
- force_arrows: thin red arrows. ONLY when the narration at that word describes an actual force, push, load or motion: a bump hitting
  the wheel, the spring being pressed, weight resting on the spring, the car going up or down, rebound, braking, the tyre pressing on
  or losing the road. A word such as "importa" or "largo" is not a force. Never use force_arrows just to name a part.
- highlight: a brief neutral pulse on ONE named part, with no force colour and no flow colour. Use it whenever the narration names a part
  but nothing is being pushed and nothing is flowing. Give it a target from: spring, damper, piston, rod, valve, oil, cylinder, wheel,
  body, suspension.
- flow_chevrons: small grey/white chevrons showing oil flowing through the valve passages (oil moving). Only on a cutaway or insert.
- term_callout: a yellow technical term. Only on a cutaway or insert. The term must name a real part and be copied from the
  narration: pistón, válvula, amortiguador, resorte, aceite, cilindro, varilla, suspensión, carrocería, rueda, llantas. Each term may be
  used AT MOST ONCE in the whole video; for a later mention of the same part use highlight instead.
- damp: the suspension switches from ringing (bouncing for a long time) to damped (settling quickly). Use it exactly ONCE in the
  whole video, on the scene and word where the narration first says the damper stops or controls the bouncing. Only on
  establishing or cutaway.

HARD RULES for the whole plan (they are checked after you answer):
1. No more than 9 seconds may pass without an event or a cut to a different shot type. The scenes below show each line's start
   time in seconds so you can space events. Put several events in a long scene.
2. Every technical noun the narration says (amortiguador, resorte, pistón, varilla, carrocería, cilindro, aceite, válvula(s),
   suspensión, rueda or llantas) must get an event whose cue is that word or sits within two seconds of it. Prefer highlight for a
   part that is only named, a term_callout the first time a part is introduced, force_arrows only for real forces.
3. Never return an empty list for a scene and never use filler: every event needs a real cue copied from that scene.
4. At most one term_callout may start within any 3 seconds, and no two events may start within one second of each other.
5. A cut to a different shot type counts as a change; prefer alternating establishing, cutaway and insert over many cutaways in a row.

For every scene return: scene (the number), shot, events (a list; each with kind, cue = one to three consecutive words copied exactly
from that scene's narration, term only for term_callout otherwise an empty string, and target only for highlight otherwise an empty
string) and why (one short reason)."""


class Ev(BaseModel):
    kind: Literal["force_arrows", "flow_chevrons", "term_callout", "highlight", "damp"]
    cue: str
    term: str
    target: str


class Beat2(BaseModel):
    scene: int
    shot: Literal["establishing", "cutaway", "insert", "metaphor"]
    events: list[Ev]
    why: str


class ShotPlan2(BaseModel):
    beats: list[Beat2]


def _timed(scene: dict, words: list[dict]) -> str:
    ws = _inside(scene, words)
    return "\n".join(f"[{ws[i]['start']:.1f}s] " + " ".join(w["text"] for w in ws[i:i + 6]) for i in range(0, len(ws), 6))


def _noun_target(text: str) -> str:
    for w in text.split():
        t = NOUN_TARGET.get(w.lower().strip(".,;:!?¿¡"))
        if t:
            return t
    return ""


def design2(scenes: list[dict], words: list[dict]) -> None:
    prompt = "\n\n".join(f"Scene {i} ({s['start']:.1f}-{s['end']:.1f} s):\n{_timed(s, words)}" for i, s in enumerate(scenes))
    result = llm.generate(GUIDANCE2, prompt, ShotPlan2, max_tokens=6000, provider=PROVIDER, api_model=llm.API_MODEL)
    beats = {b.scene: b for b in result.beats if 0 <= b.scene < len(scenes)}
    damp_seen = False
    last_term_at = -99.0
    used_terms: set[str] = set()
    accepted: list[tuple[float, str]] = []  # (time, kind) of every event kept so far, across scenes
    for i, scene in enumerate(scenes):
        scene["notes"] = []
        b = beats.get(i)
        scene["model"] = {"shot": b.shot, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        shot = b.shot if b else "cutaway"
        if b is None:
            scene["notes"].append("model returned no beat; defaulted to cutaway")
        if shot == "metaphor":
            scene["notes"].append("metaphor shot demoted to cutaway (not used for this topic)")
            shot = "cutaway"
        if i == 0 and shot != "establishing":
            scene["notes"].append(f"first scene forced to establishing (model chose {shot})")
            shot = "establishing"
        scene["shot"] = shot
        evs = []
        for e in (b.events if b else [])[:3]:
            kind, term, target = e.kind, e.term.strip().lower(), e.target.strip().lower()
            if kind in ("term_callout", "flow_chevrons") and shot not in ("cutaway", "insert"):
                scene["notes"].append(f"{kind} dropped on {shot}")
                continue
            if kind == "damp" and (shot == "insert" or damp_seen):
                scene["notes"].append("damp dropped (" + ("insert" if shot == "insert" else "already used") + ")")
                continue
            hit = _find(e.cue, scene, words)
            if not hit:
                scene["notes"].append(f"cue {e.cue!r} not found in scene; event dropped")
                continue
            at = round(hit[0]["start"], 2)
            if any(abs(at - t) < 0.8 for t, _k in accepted) or any(abs(at - t) < 1.5 and k == kind for t, k in accepted):
                scene["notes"].append(f"{kind} at {at}s dropped: collides with another event")
                continue
            if kind == "force_arrows" and not any(st in motion._norm(w) for w in e.cue.split() for st in FORCE_STEMS):
                target = target if target in TARGETS else _noun_target(e.cue)
                scene["notes"].append(f"force_arrows on {e.cue!r} has no force or motion word; " + (f"downgraded to highlight({target})" if target else "dropped"))
                if not target:
                    continue
                kind = "highlight"
            if kind == "term_callout":
                if term not in GLOSSARY:
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
            if kind == "highlight":
                target = target if target in TARGETS else _noun_target(e.cue)
                if target not in TARGETS:
                    scene["notes"].append(f"highlight on {e.cue!r} has no valid target; dropped")
                    continue
            if kind == "damp":
                damp_seen = True
            ev = {"kind": kind, "cue": e.cue, "at": at, "target": target if kind in ("highlight", "term_callout") else ""}
            if kind == "term_callout":
                ev["term"] = term.upper()
            accepted.append((at, kind))
            evs.append(ev)
        scene["events"] = sorted(evs, key=lambda x: x["at"])
        scene["event"] = scene["events"][0] if scene["events"] else {"kind": "none"}
        scene["index"] = i
        scene.pop("keywords", None)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + TAIL_SECONDS, 2)
    if "--v2" in sys.argv:
        motion.SCENE_SECONDS = BLOCK_SECONDS
        scenes = motion.plan(words, seconds)["scenes"]
        design2(scenes, words)
    elif "--reuse" in sys.argv:
        scenes = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))["scenes"]
    else:
        motion.SCENE_SECONDS = BLOCK_SECONDS
        scenes = motion.plan(words, seconds)["scenes"]
        design(scenes, words)
    if "--v2" not in sys.argv:
        finalize(scenes, words)
    out_path = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "plan.json"
    out_path.write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "rate": spoken["rate"], "provider": PROVIDER,
                                                "model_env": os.getenv("BRAINROT_CLAUDE_MODEL"), "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in scenes:
        e = s["event"]
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f} ({s['end'] - s['start']:4.1f}s) {s['shot']:<12} {e['kind']:<14} {('@%.1f %s' % (e['at'], e.get('term', e.get('cue', '')))) if e['kind'] != 'none' else ''}")
        for n in s["notes"]:
            print("      note:", n)
    print(f"{len(scenes)} blocks, {seconds} s, provider {PROVIDER}, model {os.getenv('BRAINROT_CLAUDE_MODEL')}")


if __name__ == "__main__":
    main()
