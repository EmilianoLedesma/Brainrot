"""Director v3 for the continuous-world videos (zebra-stripes topic). Same engine as pothole-lowpoly/director.py with the fixes the user asked for:

- a CALMER camera: most beats hold (a very slow drift); at most MAX_MOVE_SHARE of the beats may use another move, and a move must be motivated.
  Within a station the angle and height stay the same, so the viewer is not re-oriented at every beat;
- looser FRAMING: the renderer's distances leave a margin around the subject (see Zebra.tsx), and cutaways are detail views, not extreme close-ups;
- NO OVERLAPS: each action has a fixed duration; on a station an action may not start before the previous one has finished, so elements never
  move on top of each other or hide one another; props enter from the sides and nothing else loops;
- the director still decides the NATURE of every scene (context / exhibit / cutaway) and locks named ACTIONS to cue words. Arrows are rare.

  PYTHONPATH=. uv run --locked python experiments/zebra-lowpoly/director.py [--revalidate] [--out PATH]     (from the repository root)
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

STATIONS = ["savanna", "coat", "predators", "heat", "hair", "landing", "coats", "cows"]
NOUNS = {"cebra": "savanna", "cebras": "savanna", "huella": "coat", "patrón": "coat", "rayas": "coat",
         "leones": "predators", "hienas": "predators", "depredadores": "predators", "camuflaje": "predators",
         "calor": "heat", "térmico": "heat", "barriles": "heat", "pieles": "heat",
         "pelo": "hair", "boca": "hair", "moscas": "hair", "tsetsé": "hair",
         "tábanos": "landing", "establo": "landing", "caballos": "landing", "aterrizar": "landing", "posaban": "landing", "aterrizaje": "landing", "sonda": "landing",
         "cobertores": "coats", "cabeza": "coats", "negros": "coats", "blancos": "coats",
         "vacas": "cows", "pintaron": "cows", "pintura": "cows", "pintadas": "cows"}
base.HERO = "savanna"
base.TARGETS = STATIONS
base.NOUN_TARGET = NOUNS
base._NOUNS = {base._plain(k): v for k, v in NOUNS.items()}
base.GLOSSARY = ["huella", "camuflaje", "depredadores", "calor", "tábanos", "caballos", "cobertores", "vacas", "pintura", "pelo"]
base.FORCE_STEMS = ("choc", "lanz", "frena", "posa", "aterriz", "acerc", "llega", "pint", "cubri", "esconde", "vuela")
PROVIDER = os.getenv("ZEBRA_PLANNER_PROVIDER", "claude-code")
MAX_ARROWS = 2
MIN_CUTAWAYS = 3
MAX_MOVE_SHARE = 0.30
BEAT_LIMIT = 6.5       # longer beats are split at the longest pause near their middle (fewer, calmer beats than the pothole film)
HOLD_CAP = 7.0         # seconds with no action, event or change of station or distance

# station -> {action: (duration in frames, description)}. Durations are enforced by the renderer and used here to forbid overlaps.
ACTIONS = {
    "savanna": {"fly_strike": (150, "a fly dives at a zebra, hits its stripes and bounces away"),
                "herd_move": (200, "the herd walks on toward the waterhole")},
    "coat": {"pair_in": (120, "a second zebra walks in beside the first; its stripe pattern is different"),
             "pattern_trace": (110, "the stripes of the first zebra light up one after another, like a fingerprint")},
    "predators": {"lion_stalk": (220, "a lion creeps through the grass toward the zebras"),
                  "haze": (100, "a haze rises between the lion and the zebras: from afar the stripes are not seen")},
    "heat": {"sun_up": (130, "the sun rises over three barrels dressed in horse, zebra and cow hide"),
             "temps_read": (120, "three thermometers rise to the same level")},
    "hair": {"fly_land": (120, "a fly lands on the skin"),
             "bite": (120, "its mouthpart is longer than the hair and reaches the skin")},
    "landing": {"approach": (140, "two flies fly toward a horse and a zebra at about the same speed"),
                "horse_land": (130, "the fly slows down, lands on the horse and probes"),
                "zebra_bump": (120, "the other fly does not slow down, bumps into the zebra and leaves"),
                "ring": (100, "a ring about two metres wide appears around the zebra: only inside it do the stripes work")},
    "coats": {"coats_on": (120, "three horses are dressed in black, white and striped coats"),
              "flies_test": (160, "flies land on the black and white coats but veer away from the striped one"),
              "head_test": (110, "flies land on the bare head of the striped horse")},
    "cows": {"paint": (140, "a brush paints black-and-white stripes on a cow"),
             "swarm": (170, "flies gather: about half as many on the striped cow as on the plain one"),
             "fade": (130, "the paint fades after some days")},
}
PRIORITY = {s: list(a) for s, a in ACTIONS.items()}
MOVES = ["hold", "push_in", "pull_out", "orbit_left", "orbit_right", "pan_left", "pan_right"]
ANGLES = ["left", "front", "right"]
HEIGHTS = ["low", "mid", "high"]

action_help = "\n".join(f"- {s}: " + "; ".join(f"{a} ({d} frames) = {t}" for a, (d, t) in acts.items()) for s, acts in ACTIONS.items())
GUIDANCE = f"""You are a demanding but CALM film director for a silent low-poly explainer about why zebras have stripes, shot in ONE continuous 3D savanna with
no cuts. World: a savanna (grass, acacias, rocks, a waterhole, a herd of zebras) and, in front of it, one round grassy stage ("exhibit") per idea.
The camera never cuts; at every beat it flies (about a second and a half) to a pose and then stays almost still. Elements move ONLY when the narration
justifies it: you lock named ACTIONS to cue words. Nothing spins or loops for decoration, and nothing moves on top of another element.

Stations (focus): savanna (the herd and the waterhole, the hero), coat (one or two zebras to show the stripe pattern), predators (a lion, a hyena and zebras
at a distance), heat (three barrels with hides and thermometers), hair (a magnified patch of skin with hair and a fly's mouthpart), landing (a horse and a zebra
with flies, to show how flies land), coats (three horses with black, white and striped coats), cows (cows, one painted with stripes).

YOU DECIDE THE NATURE OF EVERY SCENE (field nature):
- context: the savanna as a whole. Use it to open, to close, and when the narration speaks of zebras in general. dist = wide. The station savanna is always context.
- exhibit: the stage performing the idea, with its actions. dist = medium.
- cutaway: a DETAIL view that opens up the mechanism: the magnified skin and mouthpart (hair), the flight paths of the flies (landing), the stripe pattern of
  the coat (coat). Use it when the narration explains HOW something works in detail. dist = medium or close. At least {MIN_CUTAWAYS} cutaway beats, but only where
  the idea really is a mechanism.

ACTIONS (valid only on their own station, and the beat's focus must be that station; an action cannot start before the previous action on the same
station has finished: the number of frames is its duration at 30 frames per second):
{action_help}

For EVERY beat return:
- scene: the number. focus: a station. nature: context | exhibit | cutaway. show: one sentence IN SPANISH of what the viewer sees and what moves, tied to the words.
- shot: dist (wide|medium|close, consistent with nature), angle (left|front|right = where the camera stands), height (low|mid|high), move (one of {", ".join(MOVES)}).
- events (each locked to a cue copied exactly from the beat, 1-3 consecutive words), kinds:
  action (field action = one valid action of the focus station; the main tool),
  highlight (a soft white pulse on a part that is only named; target = a station),
  term_callout (yellow term copied from the narration: huella, camuflaje, depredadores, calor, tábanos, caballos, cobertores, vacas, pintura, pelo; each at most once),
  arrow (a red arrow; RARE; only if a direction is not obvious from the motion; fill target).
- why: one short reason.

HARD RULES (checked in code; what you skip is filled with a default, which is worse than your choice):
1. Every beat of 4 s or more needs at least ONE action; every beat of 6.5 s or more needs at least TWO, on different cue words, with the second starting after the first has finished.
2. The action fires on the word that says it ("choca" -> fly_strike, "se posaban" -> horse_land, "pintaron" -> paint).
3. CALM CAMERA: use move "hold" in at least 70% of the beats. Use another move only when it has a reason: push_in to arrive at a detail, pull_out to reveal the
   consequence, a slow orbit or pan when the action travels sideways. Within a station keep the same angle and the same height; change angle or height only when
   the station changes. Never two non-hold moves in a row.
4. Stay on the station of the idea being told; revisit a station only with a different distance and a different action.
5. Use at least 12 different actions across the video and at least one on every station.
6. The first beat is savanna/context/wide with fly_strike on its first words. The last beat is savanna/context/wide.
7. At most {MAX_ARROWS} arrow events in the whole video, none by default.
8. No more than {HOLD_CAP:.0f} seconds without an action, highlight, callout or change of station or distance."""


class Ev(BaseModel):
    kind: Literal["action", "highlight", "term_callout", "arrow"]
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
    focus: Literal["savanna", "coat", "predators", "heat", "hair", "landing", "coats", "cows"]
    nature: Literal["context", "exhibit", "cutaway"]
    shot: Shot
    show: str
    events: list[Ev]
    why: str


class Film(BaseModel):
    beats: list[Beat]


def _word_at(scene: dict, words: list[dict], frac: float) -> dict | None:
    inside = base._inside(scene, words)
    return inside[min(len(inside) - 1, int(len(inside) * frac))] if inside else None


def design(scenes: list[dict], words: list[dict], saved: list | None = None) -> None:
    if saved is None:
        prompt = "\n\n".join(f"Beat {i} ({s['start']:.1f}-{s['end']:.1f} s, {s['end'] - s['start']:.1f} s long):\n{base._timed(s, words)}" for i, s in enumerate(scenes))
        beats = {b.scene: b for b in llm.generate(GUIDANCE, prompt, Film, max_tokens=24000, provider=PROVIDER, api_model=llm.API_MODEL).beats if 0 <= b.scene < len(scenes)}
    else:
        beats = {i: Beat(scene=i, **m) for i, m in enumerate(saved[:len(scenes)]) if m}
    used_terms, last_term_at, arrows = set(), -99.0, 0
    busy_until: dict[str, float] = {}  # station -> second at which its last action ends
    for i, scene in enumerate(scenes):
        scene["notes"], scene["index"] = [], i
        b = beats.get(i)
        scene["model"] = {"focus": b.focus, "nature": b.nature, "shot": b.shot.model_dump(), "show": b.show, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        focus = b.focus if b else (scenes[i - 1]["focus"] if i else "savanna")
        nature = b.nature if b else "exhibit"
        shot = b.shot.model_dump() if b else {"dist": "medium", "angle": "front", "height": "mid", "move": "hold"}
        if b is None:
            scene["notes"].append("model returned no beat; kept the previous focus with a default shot")
        if i == 0 and focus != "savanna":
            scene["notes"].append(f"first beat forced to savanna (model chose {focus})")
            focus = "savanna"
        if focus == "savanna" and nature != "context":
            scene["notes"].append(f"savanna is always context (model chose {nature})")
            nature = "context"
        want = {"context": "wide", "exhibit": "medium"}.get(nature)
        if want and shot["dist"] != want:
            scene["notes"].append(f"nature {nature} needs dist {want} (model chose {shot['dist']})")
            shot["dist"] = want
        if nature == "cutaway" and shot["dist"] == "wide":
            shot["dist"] = "medium"
        evs = []
        for e in (b.events if b else [])[:6]:
            hit = base._find(e.cue, scene, words)
            if not hit:
                scene["notes"].append(f"cue {e.cue!r} not found in beat; {e.kind} dropped")
                continue
            at, kind, target = round(hit[0]["start"], 2), e.kind, e.target.strip().lower()
            if kind == "action":
                if e.action not in ACTIONS[focus]:
                    scene["notes"].append(f"action {e.action!r} is not valid on {focus}; dropped")
                    continue
                if at < busy_until.get(focus, -1):
                    scene["notes"].append(f"action {e.action} at {at}s would overlap the previous action on {focus} (busy until {busy_until[focus]:.1f}s); dropped")
                    continue
                busy_until[focus] = at + ACTIONS[focus][e.action][0] / 30
                evs.append({"kind": "action", "cue": e.cue, "at": at, "target": focus, "action": e.action})
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
        need = 2 if dur >= 6.5 else 1 if dur >= 4.0 else 0
        have = [x for x in evs if x["kind"] == "action"]
        if i == 0 and not any(x["action"] == "fly_strike" for x in have):
            w = _word_at(scene, words, 0.0)
            evs.append({"kind": "action", "cue": w["text"], "at": round(w["start"] + 0.3, 2), "target": "savanna", "action": "fly_strike"})
            have.append(evs[-1])
            busy_until["savanna"] = evs[-1]["at"] + ACTIONS["savanna"]["fly_strike"][0] / 30
            scene["notes"].append("first beat had no fly_strike; added on its first word")
        for frac in (0.25, 0.6, 0.8):
            if len(have) >= need:
                break
            todo = [a for a in PRIORITY[focus] if a not in {x["action"] for x in have}] or PRIORITY[focus]
            w = _word_at(scene, words, frac)
            if w is None or w["start"] < busy_until.get(focus, -1) or any(abs(w["start"] - x["at"]) < 1.2 for x in have):
                continue
            evs.append({"kind": "action", "cue": w["text"], "at": round(w["start"], 2), "target": focus, "action": todo[0]})
            have.append(evs[-1])
            busy_until[focus] = w["start"] + ACTIONS[focus][todo[0]][0] / 30
            scene["notes"].append(f"beat of {dur:.1f} s needed {need} action(s); validator added {todo[0]} on {w['text']!r}")
        scene["focus"], scene["nature"], scene["shot"], scene["dist"], scene["show"] = focus, nature, shot, shot["dist"], b.show if b else ""
        scene["events"] = sorted(evs, key=lambda x: x["at"])
        scene.pop("keywords", None)
    # cutaways only where the idea is a mechanism; at least MIN_CUTAWAYS
    cut = [s for s in scenes if s["nature"] == "cutaway"]
    for st in ("hair", "landing", "coat"):
        if len(cut) >= MIN_CUTAWAYS:
            break
        pick = next((s for s in scenes if s["focus"] == st and s["nature"] == "exhibit" and s["end"] - s["start"] >= 3.5), None)
        if pick:
            pick["nature"] = "cutaway"
            pick["notes"].append(f"only {len(cut)} cutaways; promoted this {st} beat to a cutaway")
            cut.append(pick)
    # calm camera: angle/height stay within a station, drift-like holds dominate, no two moves in a row
    for i in range(1, len(scenes)):
        s, p = scenes[i]["shot"], scenes[i - 1]["shot"]
        if scenes[i]["focus"] == scenes[i - 1]["focus"]:
            if (s["angle"], s["height"]) != (p["angle"], p["height"]):
                scenes[i]["notes"].append(f"same station: angle/height kept as {p['angle']}/{p['height']} (model chose {s['angle']}/{s['height']})")
                s["angle"], s["height"] = p["angle"], p["height"]
        if s["move"] != "hold" and p["move"] != "hold":
            s["move"] = "hold"
            scenes[i]["notes"].append("two moves in a row; this beat holds")
    moving = [sc for sc in scenes if sc["shot"]["move"] != "hold"]
    limit = int(len(scenes) * MAX_MOVE_SHARE)
    for sc in moving[limit:]:
        sc["notes"].append(f"too many camera moves; {sc['shot']['move']} changed to hold")
        sc["shot"]["move"] = "hold"
    first, last = scenes[0], scenes[-1]
    first["shot"]["dist"], first["dist"], first["nature"] = "wide", "wide", "context"
    if last["focus"] != "savanna":
        last["notes"].append(f"last beat forced to savanna (model chose {last['focus']})")
        last["focus"] = "savanna"
    last["shot"]["dist"], last["dist"], last["nature"] = "wide", "wide", "context"
    if last["shot"]["move"] == "hold":
        last["shot"]["move"] = "pull_out"  # the one closing move


def summary(scenes: list[dict]) -> str:
    acts = [e["action"] for s in scenes for e in s["events"] if e["kind"] == "action"]
    cnt = lambda f, vals: {v: sum(f(s) == v for s in scenes) for v in vals}  # noqa: E731
    return (f"{len(scenes)} beats | nature {cnt(lambda s: s['nature'], ['context', 'exhibit', 'cutaway'])} | {len(acts)} actions, {len(set(acts))} distinct | "
            f"moves {cnt(lambda s: s['shot']['move'], MOVES)} | angles {cnt(lambda s: s['shot']['angle'], ANGLES)} | heights {cnt(lambda s: s['shot']['height'], HEIGHTS)} | "
            f"arrows {sum(e['kind'] == 'arrow' for s in scenes for e in s['events'])}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + base.TAIL_SECONDS, 2)
    motion.SCENE_SECONDS, motion.SENTENCE_GAP = 4.0, base.CLAUSE_GAP
    scenes = base.split_long(motion.plan(words, seconds)["scenes"], words, limit=BEAT_LIMIT)
    plan_path = HERE / "plan.json"
    saved = [s.get("model") for s in json.loads(plan_path.read_text(encoding="utf-8"))["scenes"]] if "--revalidate" in sys.argv and plan_path.exists() else None
    design(scenes, words, saved)
    base.snap_boundaries(scenes)
    base.fill_gaps(scenes, words, seconds, cap=HOLD_CAP)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else plan_path
    out.write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "rate": spoken["rate"], "provider": PROVIDER, "director": 3,
                               "model_env": os.getenv("BRAINROT_CLAUDE_MODEL"), "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in scenes:
        sh = s["shot"]
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f} ({s['end'] - s['start']:3.1f}s) {s['focus']:<9} {s['nature']:<8} {sh['dist']:<6} {sh['angle']:<5} {sh['height']:<4} {sh['move']:<10}",
              " | ".join(f"{e['at']:.1f} {e.get('action') or e['kind'][:5]}{('→' + e['target']) if e['kind'] != 'action' else ''}{(' [' + e['term'] + ']') if e.get('term') else ''}" for e in s["events"]))
        for n in s["notes"]:
            print("      note:", n)
    print(summary(scenes), "| provider", PROVIDER)


if __name__ == "__main__":
    main()
