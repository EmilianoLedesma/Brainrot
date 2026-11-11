"""The world director: picks the scene pack, identifies the subject, and directs every beat of the narration, then enforces its own rules in code.

The model decides what is worth deciding (the pack that fits, the subject, each beat's station, nature, camera shot and the actions locked to cue words); code enforces what
must hold (nature versus distance, calm camera, no overlapping actions on a station, actions per beat length, the opening and closing beats, rare arrows, a hold cap) and
fills what the model skipped with defaults, noting every correction. The large call is split into chunks of CHUNK beats so each stays within a few minutes.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from .. import llm
from ..config import PROJECT_ROOT
from ..domain.jobs import PermanentError
from . import beats, catalog

CACHE = PROJECT_ROOT / "out" / "world-plans"
SKILL = Path(__file__).parent.parent / "skills" / "world-direction" / "SKILL.md"
CHUNK = 9
CALL_TIMEOUT = 900
MOVES = ["hold", "push_in", "pull_out", "orbit_left", "orbit_right", "pan_left", "pan_right"]
ANGLES = ["left", "front", "right"]
HEIGHTS = ["low", "mid", "high"]
log = logging.getLogger(__name__)


def _lit(values) -> object:
    return Literal.__getitem__(tuple(values))


def guidance(pack: dict, subject: str | None = None) -> str:
    skill = SKILL.read_text(encoding="utf-8").split("---", 2)[-1].strip()
    stations = "\n".join(f"- {s}: {pack['station_notes'].get(s, '')}" for s in pack["stations"])
    actions = "\n".join(f"- {s}: " + "; ".join(f"{a} ({d} frames) = {t}" for a, (d, t) in acts.items()) for s, acts in pack["actions"].items())
    opening = pack["opening"]
    opens = (f"the station action {opening['station_action']} on its first words" if "station_action" in opening else f"the subject action {opening['subject_action']} on its first words")
    text = (f"{skill}\n\n## This world: {pack['title']}\n{pack['world']}.\n\n### Stations (focus; the hero is {pack['hero']})\n{stations}\n\n"
            f"### Station actions (valid only on their own station; the number is the duration in frames)\n{actions}\n")
    subj = pack.get("subject")
    if subj:
        sacts = "\n".join(f"- {a} ({d} frames) = {t}" for a, (d, t) in subj["actions"].items())
        text += (f"\n### Subject\nThe subject is one of: {', '.join(subj['candidates'])} ({subj['description']}). "
                 + (f"It has been chosen: {subject}.\n" if subject else "Choose it first, in the field `subject`, with `why`.\n")
                 + f"Subject actions (kind \"subject\"; they cannot overlap each other and may happen together with a station action):\n{sacts}\n")
    text += (f"\n### Caps\n- The first beat is {pack['hero']}/context/wide with {opens}; the last beat is {pack['hero']}/context/wide.\n"
             f"- At most {pack['max_arrows']} arrow events in the whole video, none by default. At least {pack['min_cutaways']} cutaway beats, only on: {', '.join(pack['cutaway_stations'])}.\n"
             f"- No more than {pack['hold_cap']:.0f} seconds without an action, highlight, callout or change of station or distance.\n"
             f"- Term callouts: {pack['term_help']}.\n- Event kinds: action (a station action), "
             + ("subject (a subject action), " if subj else "") + "highlight (a soft white pulse on a part that is only named; target = a station), term_callout (term), arrow (rare; target).")
    return text


def models(pack: dict):
    """Typed answers for this pack: a beat is only valid on one of its stations."""
    Focus, Nature, Dist, Angle, Height, Move = (_lit(pack["stations"]), _lit(["context", "exhibit", "cutaway"]), _lit(["wide", "medium", "close"]),
                                                _lit(ANGLES), _lit(HEIGHTS), _lit(MOVES))
    subj = pack.get("subject")
    kinds = _lit(["action", "subject", "highlight", "term_callout", "arrow"] if subj else ["action", "highlight", "term_callout", "arrow"])

    class Ev(BaseModel):
        kind: kinds
        cue: str
        term: str
        target: str
        action: str

    class Shot(BaseModel):
        dist: Dist
        angle: Angle
        height: Height
        move: Move

    class Beat(BaseModel):
        scene: int
        focus: Focus
        nature: Nature
        shot: Shot
        show: str
        events: list[Ev]
        why: str

    class Next(BaseModel):
        beats: list[Beat]

    if not subj:
        return Beat, Next, Next

    class Subject(BaseModel):
        id: _lit(subj["candidates"])
        why: str

    class First(BaseModel):
        subject: Subject
        beats: list[Beat]

    return Beat, First, Next


def choose_pack(topic: str, text: str, provider: str | None = None) -> str:
    """Pick the pack whose world fits the topic. No fitting pack is an explicit, friendly stop, never a silent switch to another edit."""
    ids = list(catalog.packs())

    class Choice(BaseModel):
        pack: _lit(ids + ["none"])
        why: str

    system = ("Choose the 3D scene pack whose world can illustrate this short video. Pick \"none\" when no pack's world fits the topic: a wrong pack is worse than none.\n\n"
              "Available packs:\n" + catalog.menu())
    choice = llm.generate(system, f"Topic: {topic}\n\nNarration:\n{text[:3000]}", Choice, max_tokens=600, provider=provider, timeout=180, tier="strong")
    if choice.pack == "none":
        raise PermanentError("The continuous 3D world has no scene pack for this topic yet. Turn that option off, or use the motion-graphics edit.")
    return choice.pack


def _ask(pack: dict, scenes: list[dict], words: list[dict], provider: str | None):
    Beat, First, Next = models(pack)
    has_subject = bool(pack.get("subject"))
    chosen: dict[int, object] = {}
    subject = None
    for n in range(0, len(scenes), CHUNK):
        chunk = scenes[n:n + CHUNK]
        previous = "\n".join(f"Beat {i}: {b.focus}/{b.nature}/{b.shot.dist}/{b.shot.angle}/{b.shot.height}/{b.shot.move}; actions: "
                             + ", ".join(f"{e.kind}:{e.action}" for e in b.events if e.kind in ("action", "subject")) for i, b in sorted(chosen.items())[-4:])
        prompt = (f"Beats {n} to {n + len(chunk) - 1} of {len(scenes) - 1}.\n" + (f"Already directed (keep angle and height inside a station; do not repeat the same subject action over and over):\n{previous}\n\n" if previous else "\n")
                  + "\n\n".join(f"Beat {n + i} ({s['start']:.1f}-{s['end']:.1f} s, {s['end'] - s['start']:.1f} s long):\n{beats.timed(s, words)}" for i, s in enumerate(chunk)))
        out = llm.generate(guidance(pack, subject["id"] if subject else None), prompt, First if (n == 0 and has_subject) else Next, max_tokens=16000,
                           provider=provider, timeout=CALL_TIMEOUT, tier="strong")
        if n == 0 and has_subject:
            subject = out.subject.model_dump()
        for b in out.beats:
            if n <= b.scene < n + len(chunk):
                chosen[b.scene] = b
    return subject, chosen


def plan(words: list[dict], seconds: float, pack_id: str, provider: str | None = None, *, asked=None) -> dict:
    """Direct the narration. `asked` (subject, beat models) replaces the model calls, for tests and for re-validating a saved answer."""
    pack = catalog.get(pack_id)
    scenes = beats.split_long(beats.group(words, seconds), words, pack["beat_limit"])
    subject, chosen = asked if asked is not None else _ask(pack, scenes, words, provider)
    design(scenes, words, pack, subject, chosen)
    beats.snap_boundaries(scenes, pack["hero"])
    nouns = {beats.plain(k): v for k, v in pack["nouns"].items()}
    beats.fill_gaps(scenes, words, seconds, nouns, cap=pack["hold_cap"])
    return {"duration": round(seconds + 0.5, 2), "pack": pack_id, "subject": subject["id"] if subject else None, "subject_model": subject, "scenes": scenes}


def design(scenes: list[dict], words: list[dict], pack: dict, subject: dict | None, chosen: dict) -> None:
    hero, nouns = pack["hero"], {beats.plain(k): v for k, v in pack["nouns"].items()}
    stems, glossary = tuple(pack["force_stems"]), {beats.plain(g) for g in pack["glossary"]}
    acts = pack["actions"]
    subj = pack.get("subject")
    sacts = subj["actions"] if subj else {}
    defaults = subj["defaults"] if subj else {}
    sid = subject["id"] if subject else None
    used_terms, last_term_at, arrows = set(), -99.0, 0
    busy: dict[str, float] = {}
    for i, scene in enumerate(scenes):
        scene["notes"], scene["index"] = [], i
        b = chosen.get(i)
        scene["model"] = {"focus": b.focus, "nature": b.nature, "shot": b.shot.model_dump(), "show": b.show, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        focus = b.focus if b else (scenes[i - 1]["focus"] if i else hero)
        nature = b.nature if b else "exhibit"
        shot = b.shot.model_dump() if b else {"dist": "medium", "angle": "front", "height": "mid", "move": "hold"}
        if b is None:
            scene["notes"].append("model returned no beat; kept the previous focus with a default shot")
        if i == 0 and focus != hero:
            scene["notes"].append(f"first beat forced to {hero} (model chose {focus})")
            focus = hero
        if focus == hero and nature != "context":
            scene["notes"].append(f"{hero} is always context (model chose {nature})")
            nature = "context"
        want = {"context": "wide", "exhibit": "medium"}.get(nature)
        if want and shot["dist"] != want:
            scene["notes"].append(f"nature {nature} needs dist {want} (model chose {shot['dist']})")
            shot["dist"] = want
        if nature == "cutaway" and shot["dist"] == "wide":
            shot["dist"] = "medium"
        evs = []
        for e in (b.events if b else [])[:8]:
            hit = beats.find(e.cue, scene, words)
            if not hit:
                scene["notes"].append(f"cue {e.cue!r} not found in beat; {e.kind} dropped")
                continue
            at, kind, target = round(hit[0]["start"], 2), e.kind, e.target.strip().lower()
            if kind in ("action", "subject"):
                table = acts[focus] if kind == "action" else sacts
                key = focus if kind == "action" else "subject"
                if e.action not in table:
                    scene["notes"].append(f"{kind} {e.action!r} is not valid{' on ' + focus if kind == 'action' else ''}; dropped")
                    continue
                if at < busy.get(key, -1):
                    scene["notes"].append(f"{kind} {e.action} at {at}s would overlap the previous one on {key}; dropped")
                    continue
                busy[key] = at + table[e.action][0] / 30
                evs.append({"kind": kind, "cue": e.cue, "at": at, "target": focus if kind == "action" else sid, "action": e.action})
                continue
            if kind == "arrow":
                if arrows >= pack["max_arrows"] or not beats.is_force(e.cue, nouns, stems):
                    scene["notes"].append("arrow dropped: " + ("limit reached" if arrows >= pack["max_arrows"] else f"{e.cue!r} has no motion word"))
                    continue
                arrows += 1
                evs.append({"kind": "arrow", "cue": e.cue, "at": at, "target": target if target in pack["stations"] else focus})
                continue
            if kind == "term_callout":
                term = e.term.strip().lower()
                if beats.plain(term) not in glossary:
                    scene["notes"].append(f"term {term!r} is not in the pack's glossary; callout dropped")
                    continue
                if term in used_terms or at - last_term_at < 3:
                    scene["notes"].append(f"term {term!r} repeated or within 3 s of another; dropped")
                    continue
                used_terms.add(term)
                last_term_at = at
                evs.append({"kind": "term_callout", "cue": e.cue, "at": at, "target": nouns.get(beats.plain(term), focus), "term": term.upper()})
                continue
            target = target if target in pack["stations"] else (beats.noun_target(e.cue, nouns) or focus)
            if any(abs(at - x["at"]) < 0.8 for x in evs if x["kind"] == "highlight"):
                scene["notes"].append(f"highlight at {at}s dropped: collides with another highlight")
                continue
            evs.append({"kind": "highlight", "cue": e.cue, "at": at, "target": target})
        dur = scene["end"] - scene["start"]
        needs = [("action", 2 if dur >= 6.5 else 1 if dur >= 4.0 else 0, acts[focus], focus, list(acts[focus]))]
        if subj:
            needs.append(("subject", 2 if dur >= 5.5 else 1 if dur >= 3.0 else 0, sacts, "subject", [defaults[focus]] + list(sacts)))
        opening = pack["opening"]
        for kind, need, table, key, prio in needs:
            have = [x for x in evs if x["kind"] == kind]
            if i == 0:
                name = opening.get("station_action") if kind == "action" else opening.get("subject_action")
                w = beats.word_at(scene, words, 0.0)
                if name and w and not any(x["action"] == name for x in have) and w["start"] >= busy.get(key, -1) and name in table:
                    evs.append({"kind": kind, "cue": w["text"], "at": round(w["start"] + (0.3 if kind == "action" else 0.0), 2), "target": focus if kind == "action" else sid, "action": name})
                    busy[key] = w["start"] + table[name][0] / 30
                    have.append(evs[-1])
                    scene["notes"].append(f"first beat had no {name}; added on its first word")
            for fraction in (0.25, 0.6, 0.8, 0.42):
                if len(have) >= need:
                    break
                todo = [a for a in prio if a not in {x["action"] for x in have}] or prio
                w = beats.word_at(scene, words, fraction)
                if w is None or w["start"] < busy.get(key, -1) or any(abs(w["start"] - x["at"]) < 0.8 for x in have):
                    continue
                evs.append({"kind": kind, "cue": w["text"], "at": round(w["start"], 2), "target": focus if kind == "action" else sid, "action": todo[0]})
                have.append(evs[-1])
                busy[key] = w["start"] + table[todo[0]][0] / 30
                scene["notes"].append(f"beat of {dur:.1f} s needed {need} {kind} action(s); validator added {todo[0]} on {w['text']!r}")
        scene["focus"], scene["nature"], scene["shot"], scene["dist"], scene["show"] = focus, nature, shot, shot["dist"], (b.show.strip() if b else "") or f"{focus}, {nature}"
        scene["events"] = sorted(evs, key=lambda x: x["at"])
    _camera(scenes, pack)


def _camera(scenes: list[dict], pack: dict) -> None:
    hero = pack["hero"]
    cut = [s for s in scenes if s["nature"] == "cutaway"]
    for st in pack["cutaway_stations"]:
        if len(cut) >= pack["min_cutaways"]:
            break
        pick = next((s for s in scenes if s["focus"] == st and s["nature"] == "exhibit" and s["end"] - s["start"] >= 3.0 and s["index"] > 0), None)
        if pick:
            pick["nature"] = "cutaway"
            pick["notes"].append(f"only {len(cut)} cutaways; promoted this {st} beat to a cutaway")
            cut.append(pick)
    for i in range(1, len(scenes)):
        s, p = scenes[i]["shot"], scenes[i - 1]["shot"]
        if scenes[i]["focus"] == scenes[i - 1]["focus"] and (s["angle"], s["height"]) != (p["angle"], p["height"]):
            scenes[i]["notes"].append(f"same station: angle/height kept as {p['angle']}/{p['height']}")
            s["angle"], s["height"] = p["angle"], p["height"]
        if s["move"] != "hold" and p["move"] != "hold":
            s["move"] = "hold"
            scenes[i]["notes"].append("two moves in a row; this beat holds")
    seen: list[str] = []
    for sc in scenes:
        if sc["focus"] not in seen:
            seen.append(sc["focus"])
    if len({sc["shot"]["angle"] for sc in scenes}) < 3 and len(seen) > 3:
        for k, st in enumerate(seen[1:], 1):
            value = ["front", "right", "left"][k % 3]
            for sc in scenes:
                if sc["focus"] == st:
                    sc["notes"].append(f"angle diversified to {value} for variety across stations")
                    sc["shot"]["angle"] = value
    if len({sc["shot"]["height"] for sc in scenes}) < 2 and len(seen) > 3:
        for st in seen[3::3]:
            for sc in scenes:
                if sc["focus"] == st:
                    sc["shot"]["height"] = "low"
                    sc["notes"].append("height set to low for variety across stations")
    moving = [sc for sc in scenes if sc["shot"]["move"] != "hold"]
    for sc in moving[int(len(scenes) * pack["max_move_share"]):]:
        sc["notes"].append(f"too many camera moves; {sc['shot']['move']} changed to hold")
        sc["shot"]["move"] = "hold"
    first, last = scenes[0], scenes[-1]
    first["shot"]["dist"], first["dist"], first["nature"] = "wide", "wide", "context"
    if last["focus"] != hero:
        last["notes"].append(f"last beat forced to {hero} (model chose {last['focus']})")
        last["focus"] = hero
    last["shot"]["dist"], last["dist"], last["nature"] = "wide", "wide", "context"
    if last["shot"]["move"] == "hold":
        last["shot"]["move"] = "pull_out"


def summary(plan_: dict) -> dict:
    """Counts for the log: nothing of the narration or the model's reasoning."""
    scenes = plan_["scenes"]
    count = lambda kind: sum(e["kind"] == kind for s in scenes for e in s["events"])  # noqa: E731
    return {"pack": plan_["pack"], "subject": plan_["subject"], "beats": len(scenes), "station_actions": count("action"), "subject_actions": count("subject"),
            "cutaways": sum(s["nature"] == "cutaway" for s in scenes), "moves": sum(s["shot"]["move"] != "hold" for s in scenes), "arrows": count("arrow")}


def direct(topic: str, text: str, words: list[dict], seconds: float, provider: str | None = None) -> dict:
    """Choose the pack and direct the narration, reusing the plan an earlier attempt of the same narration saved (the director call takes minutes).

    The cache lives on this computer under out/ and is keyed by the narrated words and their timings, so a retry that re-narrates identically costs nothing.
    """
    key = hashlib.sha256(json.dumps([[w["text"], round(w["start"], 2)] for w in words] + [round(seconds, 2)]).encode()).hexdigest()[:24]
    file = CACHE / f"{key}.json"
    try:
        cached = json.loads(file.read_text(encoding="utf-8"))
        if cached.get("pack") in catalog.packs():
            return cached
    except (OSError, ValueError):
        pass
    result = plan(words, seconds, choose_pack(topic, text, provider), provider)
    log.info("world plan: %s", json.dumps(summary(result)))
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(result), encoding="utf-8")
    except OSError:
        log.warning("could not cache the world plan")
    return result
