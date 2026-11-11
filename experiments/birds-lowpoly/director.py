"""Director v4 for the continuous-world videos (birds-on-power-lines topic). Same calm-camera engine as zebra-lowpoly/director.py plus SUBJECT-FIRST direction:

- the director first IDENTIFIES THE SUBJECT of the film (the one character the story is about) from the narration and the research; the choice is saved in plan.json;
- the subject gets more of everything: its own vocabulary of ACTIONS locked to cue words (it looks, tilts its head, grips the wire, ruffles its feathers, hops, lands,
  takes off), at least one in every beat of 3 s or more and two in every beat of 5.5 s or more, a more detailed model in the renderer and the most saturated colour in the frame;
- stations keep their own actions (current pulses, spark, spacing, covers...), never overlapping on a station, and nothing moves unless the narration asks for it;
- the camera stays calm: at most 30% of the beats move, never two in a row, angle and height fixed inside a station; across the film the director must still use all
  three angles and more than one height (code diversifies when it does not).

  PYTHONPATH=. uv run --locked python experiments/birds-lowpoly/director.py [--revalidate] [--out PATH]     (from the repository root)
"""
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from brainrot import llm, motion

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("cpu_planner", HERE.parent / "cpu-lowpoly" / "planner.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)  # beat splitting, cue matching, hold-cap fill, boundary snapping (topic-independent helpers)

STATIONS = ["line", "difference", "feet", "path", "circuit", "bridge", "spacing", "pole", "fixes", "lineman"]
NOUNS = {"cable": "line", "cables": "line", "voltaje": "difference", "voltajes": "difference", "diferencia": "difference", "potencial": "difference",
         "pies": "feet", "pie": "feet", "patas": "path", "resistencia": "path", "circuito": "circuit", "corriente": "circuit",
         "alas": "bridge", "tierra": "bridge", "electrocuta": "bridge", "puente": "bridge", "águilas": "spacing", "gavilanes": "spacing", "envergadura": "spacing", "separan": "spacing",
         "postes": "pole", "aterriza": "pole", "despega": "pole", "balancear": "pole", "aislante": "fixes", "protectores": "fixes", "percha": "fixes", "cubren": "fixes",
         "linieros": "lineman", "varita": "lineman"}
base.HERO = "line"
base.TARGETS = STATIONS
base.NOUN_TARGET = NOUNS
base._NOUNS = {base._plain(k): v for k, v in NOUNS.items()}
base.GLOSSARY = ["voltaje", "diferencia", "circuito", "resistencia", "envergadura", "aislante", "percha", "potencial"]
base.FORCE_STEMS = ("empuj", "estira", "toca", "pasa", "circul", "balance", "aterriz", "despeg", "separ", "cubr", "igual")
PROVIDER = os.getenv("BIRDS_PLANNER_PROVIDER", "claude-code")
MAX_ARROWS = 2
MIN_CUTAWAYS = 3
MAX_MOVE_SHARE = 0.30
BEAT_LIMIT = 6.5
HOLD_CAP = 7.0

# station -> {action: (duration in frames, description)}. Durations are used to forbid overlaps on a station.
ACTIONS = {
    "line": {"power_on": (150, "current pulses run along the wire for a moment, so the viewer sees it is live"),
             "sway": (110, "the wire sways a little when something lands on it")},
    "difference": {"show_levels": (110, "two wires take two colours: a violet one (higher voltage) and a teal one (lower)"),
                   "push": (110, "pulses are pushed from the violet wire to the teal one through a gap between them")},
    "feet": {"equal": (90, "two small rings light up at the bird's two feet in the same colour: same voltage"),
             "no_push": (110, "pulses run along the wire under the feet and none enters the bird")},
    "path": {"bypass": (130, "pulses flow along the wire, past the legs, instead of through the body"),
             "compare": (110, "a short thick road (wire) and a long thin one (body) are drawn side by side")},
    "circuit": {"open": (110, "a loop with a gap: the pulses stop at the gap"),
                "close": (110, "a second contact closes the loop and the pulses start to circulate")},
    "bridge": {"eagle_in": (100, "a big bird flies in and perches on the top wire"),
               "eagle_reach": (90, "the big bird spreads its wings toward the second wire"),
               "flash": (60, "a spark flashes where the wing touches the second wire, and the bird is thrown off")},
    "spacing": {"measure": (80, "a bracket measures the eagle's wingspan across the two wires"),
                "wires_apart": (100, "the wires move apart until the bracket can no longer reach both")},
    "pole": {"land_pole": (100, "a large bird comes in to land on the crossarm of a pole, wires close together"),
             "flock": (150, "several birds land together, the line sags and sways until the wires touch")},
    "fixes": {"cover": (100, "insulating covers slide over the insulators and exposed parts"),
              "space_arm": (90, "the crossarm is extended so the wires are farther apart"),
              "perch_guard": (90, "a perch guard rises over the crossarm")},
    "lineman": {"bond": (120, "a lineman touches the wire with a bonding wand and takes the wire's colour"),
                "work": (100, "the lineman then works on the wire safely")},
}
# the subject's own vocabulary (it applies to the subject animal wherever it is)
SUBJECT_ACTIONS = {
    "look_around": (70, "turns its head left and right, looking at what is being described"),
    "tilt": (45, "tilts its head, curious"),
    "grip": (60, "its toes tighten around the wire"),
    "fluff": (60, "ruffles its feathers once, relaxed"),
    "hop": (60, "a short hop along the wire"),
    "land": (100, "flies in and lands on the wire"),
    "take_off": (90, "flaps its wings and flies off"),
}
SUBJECT_DEFAULT = {"line": "fluff", "difference": "look_around", "feet": "grip", "path": "tilt", "circuit": "look_around", "bridge": "look_around", "spacing": "tilt",
                   "pole": "look_around", "fixes": "look_around", "lineman": "tilt"}
PRIORITY = {s: list(a) for s, a in ACTIONS.items()}
MOVES = ["hold", "push_in", "pull_out", "orbit_left", "orbit_right", "pan_left", "pan_right"]
ANGLES = ["left", "front", "right"]
HEIGHTS = ["low", "mid", "high"]

action_help = "\n".join(f"- {s}: " + "; ".join(f"{a} ({d} frames) = {t}" for a, (d, t) in acts.items()) for s, acts in ACTIONS.items())
subject_help = "\n".join(f"- {a} ({d} frames) = {t}" for a, (d, t) in SUBJECT_ACTIONS.items())
GUIDANCE = f"""You are a demanding but CALM film director for a silent low-poly explainer about why birds can perch on power lines without being electrocuted, shot in ONE
continuous 3D countryside with no cuts. World: a road with a line of poles and wires (the hero, "line"), and in front of it one round grassy stage per idea, each with a
short pole and wires. The camera never cuts; at every beat it flies (about a second and a half) to a pose and then stays almost still. Nothing moves unless the narration
justifies it: you lock named ACTIONS to cue words.

FIRST, IDENTIFY THE SUBJECT of the film (field subject): the one character the story is about. Choose "bird" (the small bird perched on the wire) or "eagle" (the big bird that
is at risk). Everything is organised around the subject: it must be the most detailed, most animated and most present element. It appears in every stage. Give it its own
ACTIONS (below) in almost every beat, tied to what is being said: it looks at what is explained, tilts its head at a question, grips the wire when the feet are the point,
ruffles its feathers when the narration says nothing happens to it, lands and takes off when the story says so. Say in subject.why how this subject carries the story.

Stations (focus): line (the hero: the road, the poles and the live wires), difference (two wires at different voltages), feet (the bird's two feet on one wire), path
(the wire as an easy road for the current, the body as a hard one), circuit (a loop that is open or closed), bridge (a big bird touching two wires), spacing (wingspan against
the spacing of the wires), pole (a pole where birds land, take off or perch in numbers), fixes (covers, a longer crossarm, perch guards), lineman (a lineman working on a live wire).

YOU DECIDE THE NATURE OF EVERY SCENE (field nature):
- context: the countryside as a whole (use it to open, to close and for the general claim). dist = wide. The station line is always context.
- exhibit: the stage performing the idea, with its actions. dist = medium.
- cutaway: a DETAIL that opens up the mechanism: the feet on the wire (feet), the road of the current (path), the open or closed loop (circuit), the wingspan measure (spacing).
  dist = medium or close. At least {MIN_CUTAWAYS} cutaway beats, only for real mechanisms.

STATION ACTIONS (valid only on their station, and the beat's focus must be that station; an action cannot start before the previous action on the same station has finished;
the number of frames is its duration at 30 frames per second):
{action_help}

SUBJECT ACTIONS (the subject's own vocabulary; kind "subject"; they cannot overlap each other, and they may happen together with a station action):
{subject_help}

For EVERY beat return: scene, focus (a station), nature, show (one sentence IN SPANISH: what the viewer sees and what moves, tied to the words), shot (dist, angle left|front|right
= where the camera stands, height low|mid|high, move one of {", ".join(MOVES)}), events and why. Events are locked to a cue copied exactly from the beat (1-3 consecutive words):
  action (field action: a station action), subject (field action: a subject action), highlight (a soft white pulse on a part that is only named; target = a station),
  term_callout (yellow term copied from the narration: voltaje, diferencia, circuito, resistencia, envergadura, aislante, percha, potencial; each at most once),
  arrow (a red arrow; RARE).

HARD RULES (checked in code; what you skip is filled with a default, which is worse than your choice):
1. Every beat of 3 s or more needs at least ONE subject action; every beat of 5.5 s or more needs TWO on different cue words. Every beat of 4 s or more also needs at least one station action,
   and beats of 6.5 s or more two (the second starting after the first has ended).
2. The action fires on the word that says it. The subject's actions follow the meaning: "mira" -> look_around, "¿Cómo?" -> tilt, "tiene los dos pies en el mismo cable" -> grip,
   "ni se despeina" -> fluff, "aterriza"/"despega" -> land/take_off.
3. CALM CAMERA: use move "hold" in at least 70% of the beats; another move only with a reason; never two moves in a row. Within a station keep the same angle and height. Across the film use
   all three angles and at least two heights (looking up at the wires from "low" is natural for a power line).
4. Stay on the station of the idea being told; revisit a station only with a different distance and a different action.
5. Use at least 12 different station actions across the video and at least one on every station.
6. The first beat is line/context/wide; the subject lands or settles on its first words (subject action land). The last beat is line/context/wide.
7. At most {MAX_ARROWS} arrow events in the whole video, none by default.
8. No more than {HOLD_CAP:.0f} seconds without an action, highlight, callout or change of station or distance."""


class Ev(BaseModel):
    kind: Literal["action", "subject", "highlight", "term_callout", "arrow"]
    cue: str
    term: str
    target: str
    action: str


class Shot(BaseModel):
    dist: Literal["wide", "medium", "close"]
    angle: Literal["left", "front", "right"]
    height: Literal["low", "mid", "high"]
    move: Literal["hold", "push_in", "pull_out", "orbit_left", "orbit_right", "pan_left", "pan_right"]


class Beat(BaseModel):
    scene: int
    focus: Literal["line", "difference", "feet", "path", "circuit", "bridge", "spacing", "pole", "fixes", "lineman"]
    nature: Literal["context", "exhibit", "cutaway"]
    shot: Shot
    show: str
    events: list[Ev]
    why: str


class Subject(BaseModel):
    id: Literal["bird", "eagle"]
    why: str


class Film(BaseModel):
    subject: Subject
    beats: list[Beat]


def _word_at(scene: dict, words: list[dict], frac: float) -> dict | None:
    inside = base._inside(scene, words)
    return inside[min(len(inside) - 1, int(len(inside) * frac))] if inside else None


def design(scenes: list[dict], words: list[dict], saved: dict | None = None) -> dict:
    if saved is None:
        prompt = "\n\n".join(f"Beat {i} ({s['start']:.1f}-{s['end']:.1f} s, {s['end'] - s['start']:.1f} s long):\n{base._timed(s, words)}" for i, s in enumerate(scenes))
        film = llm.generate(GUIDANCE, prompt, Film, max_tokens=28000, provider=PROVIDER, api_model=llm.API_MODEL)
        beats, subject = {b.scene: b for b in film.beats if 0 <= b.scene < len(scenes)}, film.subject.model_dump()
    else:
        subject = saved["subject"]
        beats = {i: Beat(scene=i, **m) for i, m in enumerate(saved["models"][:len(scenes)]) if m}
    used_terms, last_term_at, arrows = set(), -99.0, 0
    busy: dict[str, float] = {}      # station (or "subject") -> second at which its last action ends
    for i, scene in enumerate(scenes):
        scene["notes"], scene["index"] = [], i
        b = beats.get(i)
        scene["model"] = {"focus": b.focus, "nature": b.nature, "shot": b.shot.model_dump(), "show": b.show, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        focus = b.focus if b else (scenes[i - 1]["focus"] if i else "line")
        nature = b.nature if b else "exhibit"
        shot = b.shot.model_dump() if b else {"dist": "medium", "angle": "front", "height": "mid", "move": "hold"}
        if b is None:
            scene["notes"].append("model returned no beat; kept the previous focus with a default shot")
        if i == 0 and focus != "line":
            scene["notes"].append(f"first beat forced to line (model chose {focus})")
            focus = "line"
        if focus == "line" and nature != "context":
            scene["notes"].append(f"line is always context (model chose {nature})")
            nature = "context"
        want = {"context": "wide", "exhibit": "medium"}.get(nature)
        if want and shot["dist"] != want:
            scene["notes"].append(f"nature {nature} needs dist {want} (model chose {shot['dist']})")
            shot["dist"] = want
        if nature == "cutaway" and shot["dist"] == "wide":
            shot["dist"] = "medium"
        evs = []
        for e in (b.events if b else [])[:8]:
            hit = base._find(e.cue, scene, words)
            if not hit:
                scene["notes"].append(f"cue {e.cue!r} not found in beat; {e.kind} dropped")
                continue
            at, kind, target = round(hit[0]["start"], 2), e.kind, e.target.strip().lower()
            if kind in ("action", "subject"):
                table = ACTIONS[focus] if kind == "action" else SUBJECT_ACTIONS
                key = focus if kind == "action" else "subject"
                if e.action not in table:
                    scene["notes"].append(f"{kind} {e.action!r} is not valid{' on ' + focus if kind == 'action' else ''}; dropped")
                    continue
                if at < busy.get(key, -1):
                    scene["notes"].append(f"{kind} {e.action} at {at}s would overlap the previous one on {key} (busy until {busy[key]:.1f}s); dropped")
                    continue
                busy[key] = at + table[e.action][0] / 30
                evs.append({"kind": kind, "cue": e.cue, "at": at, "target": focus if kind == "action" else subject["id"], "action": e.action})
                continue
            if kind == "arrow":
                if arrows >= MAX_ARROWS or not base._is_force(e.cue):
                    scene["notes"].append("arrow dropped: " + ("limit reached" if arrows >= MAX_ARROWS else f"{e.cue!r} has no flow or motion word"))
                    continue
                arrows += 1
                evs.append({"kind": "arrow", "cue": e.cue, "at": at, "target": target if target in STATIONS else focus})
                continue
            if kind == "term_callout":
                term = e.term.strip().lower()
                if base._plain(term) not in [base._plain(g) for g in base.GLOSSARY]:
                    scene["notes"].append(f"term {term!r} is not a real part name; callout dropped")
                    continue
                if term in used_terms or at - last_term_at < 3:
                    scene["notes"].append(f"term {term!r} repeated or within 3 s of another; dropped")
                    continue
                used_terms.add(term)
                last_term_at = at
                evs.append({"kind": "term_callout", "cue": e.cue, "at": at, "target": base._NOUNS.get(base._plain(term), focus), "term": term.upper()})
                continue
            target = target if target in STATIONS else (base._noun_target(e.cue) or focus)
            if any(abs(at - x["at"]) < 0.8 for x in evs if x["kind"] == "highlight"):
                scene["notes"].append(f"highlight at {at}s dropped: collides with another highlight")
                continue
            evs.append({"kind": "highlight", "cue": e.cue, "at": at, "target": target})
        dur = scene["end"] - scene["start"]
        need_st = 2 if dur >= 6.5 else 1 if dur >= 4.0 else 0
        need_su = 2 if dur >= 5.5 else 1 if dur >= 3.0 else 0
        for kind, need, table, key, prio in (("action", need_st, ACTIONS[focus], focus, PRIORITY[focus]),
                                              ("subject", need_su, SUBJECT_ACTIONS, "subject", [SUBJECT_DEFAULT[focus]] + list(SUBJECT_ACTIONS))):
            have = [x for x in evs if x["kind"] == kind]
            if i == 0 and kind == "subject" and not any(x["action"] == "land" for x in have):
                w = _word_at(scene, words, 0.0)
                if w and w["start"] >= busy.get("subject", -1):
                    evs.append({"kind": "subject", "cue": w["text"], "at": round(w["start"], 1), "target": subject["id"], "action": "land"})
                    busy["subject"] = w["start"] + SUBJECT_ACTIONS["land"][0] / 30
                    have.append(evs[-1])
                    scene["notes"].append("first beat had no subject landing; added on its first word")
            for frac in (0.25, 0.6, 0.8, 0.42):
                if len(have) >= need:
                    break
                todo = [a for a in prio if a not in {x["action"] for x in have}] or prio
                w = _word_at(scene, words, frac)
                if w is None or w["start"] < busy.get(key, -1) or any(abs(w["start"] - x["at"]) < 0.8 for x in have):
                    continue
                evs.append({"kind": kind, "cue": w["text"], "at": round(w["start"], 2), "target": focus if kind == "action" else subject["id"], "action": todo[0]})
                have.append(evs[-1])
                busy[key] = w["start"] + table[todo[0]][0] / 30
                scene["notes"].append(f"beat of {dur:.1f} s needed {need} {kind} action(s); validator added {todo[0]} on {w['text']!r}")
        scene["focus"], scene["nature"], scene["shot"], scene["dist"], scene["show"] = focus, nature, shot, shot["dist"], b.show if b else ""
        scene["events"] = sorted(evs, key=lambda x: x["at"])
        scene.pop("keywords", None)
    cut = [s for s in scenes if s["nature"] == "cutaway"]
    for st in ("feet", "path", "circuit", "spacing"):
        if len(cut) >= MIN_CUTAWAYS:
            break
        pick = next((s for s in scenes if s["focus"] == st and s["nature"] == "exhibit" and s["end"] - s["start"] >= 3.0), None)
        if pick:
            pick["nature"] = "cutaway"
            pick["notes"].append(f"only {len(cut)} cutaways; promoted this {st} beat to a cutaway")
            cut.append(pick)
    for i in range(1, len(scenes)):
        s, p = scenes[i]["shot"], scenes[i - 1]["shot"]
        if scenes[i]["focus"] == scenes[i - 1]["focus"] and (s["angle"], s["height"]) != (p["angle"], p["height"]):
            scenes[i]["notes"].append(f"same station: angle/height kept as {p['angle']}/{p['height']} (model chose {s['angle']}/{s['height']})")
            s["angle"], s["height"] = p["angle"], p["height"]
        if s["move"] != "hold" and p["move"] != "hold":
            s["move"] = "hold"
            scenes[i]["notes"].append("two moves in a row; this beat holds")
    # variety across stations (never inside one): all three angles and more than one height
    stations_seen: list[str] = []
    for sc in scenes:
        if sc["focus"] not in stations_seen:
            stations_seen.append(sc["focus"])
    if len({sc["shot"]["angle"] for sc in scenes}) < 3:
        for k, st in enumerate(stations_seen[1:], 1):
            value = ["front", "right", "left"][k % 3]
            for sc in scenes:
                if sc["focus"] == st:
                    sc["notes"].append(f"angle diversified to {value} for variety across stations")
                    sc["shot"]["angle"] = value
    if len({sc["shot"]["height"] for sc in scenes}) < 2:
        for st in ("bridge", "pole", "spacing"):
            for sc in scenes:
                if sc["focus"] == st:
                    sc["shot"]["height"] = "low"
                    sc["notes"].append("height set to low: looking up at the wires")
    moving = [sc for sc in scenes if sc["shot"]["move"] != "hold"]
    for sc in moving[int(len(scenes) * MAX_MOVE_SHARE):]:
        sc["notes"].append(f"too many camera moves; {sc['shot']['move']} changed to hold")
        sc["shot"]["move"] = "hold"
    first, last = scenes[0], scenes[-1]
    first["shot"]["dist"], first["dist"], first["nature"] = "wide", "wide", "context"
    if last["focus"] != "line":
        last["notes"].append(f"last beat forced to line (model chose {last['focus']})")
        last["focus"] = "line"
    last["shot"]["dist"], last["dist"], last["nature"] = "wide", "wide", "context"
    if last["shot"]["move"] == "hold":
        last["shot"]["move"] = "pull_out"
    return subject


def summary(scenes: list[dict], subject: dict) -> str:
    acts = [e["action"] for s in scenes for e in s["events"] if e["kind"] == "action"]
    sacts = [e["action"] for s in scenes for e in s["events"] if e["kind"] == "subject"]
    cnt = lambda f, vals: {v: sum(f(s) == v for s in scenes) for v in vals}  # noqa: E731
    with_subject = sum(any(e["kind"] == "subject" for e in s["events"]) for s in scenes)
    return (f"subject {subject['id']} | {len(scenes)} beats | nature {cnt(lambda s: s['nature'], ['context', 'exhibit', 'cutaway'])} | {len(acts)} station actions, {len(set(acts))} distinct | "
            f"{len(sacts)} subject actions, {len(set(sacts))} distinct, in {with_subject} of {len(scenes)} beats | moves {cnt(lambda s: s['shot']['move'], MOVES)} | "
            f"angles {cnt(lambda s: s['shot']['angle'], ANGLES)} | heights {cnt(lambda s: s['shot']['height'], HEIGHTS)} | arrows {sum(e['kind'] == 'arrow' for s in scenes for e in s['events'])}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + base.TAIL_SECONDS, 2)
    motion.SCENE_SECONDS, motion.SENTENCE_GAP = 4.0, base.CLAUSE_GAP
    scenes = base.split_long(motion.plan(words, seconds)["scenes"], words, limit=BEAT_LIMIT)
    plan_path = HERE / "plan.json"
    saved = None
    if "--revalidate" in sys.argv and plan_path.exists():
        old = json.loads(plan_path.read_text(encoding="utf-8"))
        saved = {"subject": old["subject_model"], "models": [s.get("model") for s in old["scenes"]]}
    subject = design(scenes, words, saved)
    base.snap_boundaries(scenes)
    base.fill_gaps(scenes, words, seconds, cap=HOLD_CAP)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else plan_path
    out.write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "rate": spoken["rate"], "provider": PROVIDER, "director": 4, "subject": subject["id"],
                               "subject_model": subject, "model_env": os.getenv("BRAINROT_CLAUDE_MODEL"), "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("SUBJECT:", subject["id"], "-", subject["why"])
    for s in scenes:
        sh = s["shot"]
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f} ({s['end'] - s['start']:3.1f}s) {s['focus']:<10} {s['nature']:<8} {sh['dist']:<6} {sh['angle']:<5} {sh['height']:<4} {sh['move']:<10}",
              " | ".join(f"{e['at']:.1f} {('S:' if e['kind'] == 'subject' else '') + (e.get('action') or e['kind'][:5])}{('→' + e['target']) if e['kind'] not in ('action', 'subject') else ''}{(' [' + e['term'] + ']') if e.get('term') else ''}" for e in s["events"]))
        for n in s["notes"]:
            print("      note:", n)
    print(summary(scenes, subject), "| provider", PROVIDER)


if __name__ == "__main__":
    main()
