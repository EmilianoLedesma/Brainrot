"""Director v2 for the continuous-world videos (pothole topic).

v1 (planner.py) only chose WHERE the camera goes and a distance, so scenes looked alike and elements moved on loops. v2 is stricter:
- the director decides the NATURE of every scene: context (the town as a whole), exhibit (a road block performing the idea) or cutaway (the block
  is cut open and we look inside at its parts: layers, rocks, soil, water between them, ice, voids), and uses cutaways whenever the narration
  explains how something works or what it is made of;
- every beat gets a full camera shot: distance, azimuth (left/front/right), height (low/mid/high) and a MOVE inside the beat
  (push_in, pull_out, orbit_left/right, pan_left/right, crane_up/down, drift);
- elements move only when the narration says so: the model picks named ACTIONS (a wheel presses, rain falls, ice lifts the asphalt, a truck
  drives in...) and locks each to a cue word. Nothing spins or loops on its own;
- arrows are rare: at most MAX_ARROWS in the video and only on a real flow word;
- code enforces the demands (nature vs distance, cutaway count, actions per beat length, camera variety, hold cap, first and last beat) and
  fills what the model skipped.

  PYTHONPATH=. uv run --locked python experiments/pothole-lowpoly/director.py [--revalidate] [--out PATH]     (from the repository root)
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
_spec = importlib.util.spec_from_file_location("pothole_planner", HERE / "planner.py")
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)  # also configures the shared base planner (nouns, stations, hero) for this topic
base = pp.base
PROVIDER = os.getenv("POTHOLE_PLANNER_PROVIDER", "claude-code")
MAX_ARROWS = 3
MIN_CUTAWAYS = 8
BEAT_LIMIT = 5.5       # longer beats are split at the longest pause near their middle
HOLD_CAP = 6.0         # seconds with no action, event or camera change

ACTIONS = {
    "road": {"car_pass": "a car drives across the street and swerves around the pothole (before the patch) or rolls smoothly over the patch (after)",
             "patch_street": "the street's pothole gets its flat patch"},
    "layers": {"reveal": "the three layers separate like a sandwich (asphalt lifts, soil sinks) and settle back",
               "wheel_pass": "a wheel crosses the top and the asphalt flexes under it",
               "wear": "the top asphalt weathers and greys"},
    "cracks": {"crack_grow": "an alligator-skin crack web grows over the surface (and fissures run down inside)",
               "flex": "a wheel crosses and the cracks open wider under it"},
    "water": {"rain": "a rain cloud slides in and drops fall onto the cracked top",
              "seep": "drops run down the crack into the base and between the rocks",
              "pool": "water pools on the subgrade and the soil darkens and softens"},
    "traffic": {"press": "a wheel presses the weak spot and water and soil squirt out sideways",
                "pump": "wheel after wheel pumps water and soil in and out, three times",
                "erode": "the void under the asphalt grows as soil is lost"},
    "pothole": {"loosen": "the chunks between the cracks loosen and lift",
                "eject": "wheels pluck the chunks out one after another and they land beside it"},
    "ice": {"freeze": "an ice lens grows between asphalt and base and lifts the asphalt; the soil below freezes",
            "thaw": "the ice melts and leaves a void; meltwater stays trapped on the frozen soil"},
    "repair": {"truck_in": "a repair truck drives in and cones are set around the hole",
               "throw": "patch material is thrown into the hole and fills it",
               "roll": "a roller crosses and compacts the patch"},
    "prevent": {"seal": "sealant runs along the cracks and fills them",
                "drain": "water runs out of a drain pipe at the side",
                "thicken": "a thicker new asphalt layer lowers onto the top"},
}
PRIORITY = {s: list(a) for s, a in ACTIONS.items()}
CUTAWAY_ORDER = ["traffic", "water", "ice", "layers", "cracks", "pothole", "repair", "prevent"]
MOVES = ["push_in", "pull_out", "orbit_left", "orbit_right", "pan_left", "pan_right", "crane_up", "crane_down", "drift"]
ANGLES = ["left", "front", "right"]
HEIGHTS = ["low", "mid", "high"]

action_help = "\n".join(f"- {s}: " + "; ".join(f"{a} = {d}" for a, d in acts.items()) for s, acts in ACTIONS.items())
GUIDANCE = f"""You are a demanding film director for a silent low-poly explainer about how potholes form, shot in ONE continuous 3D town with no cuts.
World: a street with houses, trees and poles behind it, and a sidewalk in front with one "exhibit" per idea (a block of road you can cut open).
The camera never cuts; at every beat it flies (about one second) to a new pose and then keeps moving inside the beat. Elements move ONLY when
the narration says something that justifies it: you lock named ACTIONS to cue words. Nothing spins or loops for decoration.

Stations (focus): road (the street with the car and the pothole), layers, cracks, water, traffic, pothole, ice, repair, prevent.

YOU DECIDE THE NATURE OF EVERY SCENE (field nature), from what the narration is doing:
- context: the town seen as a whole (street, car, houses). Use it to open, to close, and when the narration talks about the road as a whole. dist = wide.
  The station road is always context.
- exhibit: the road block performing the idea: tell what happens, with its actions. dist = medium (or close).
- cutaway: the block is CUT OPEN and the camera looks inside at its parts: asphalt aggregate, the base's packed rocks, soil grains, water between the
  rocks, ice, voids, fissures. USE IT whenever the narration explains HOW something works or what something is made of in detail (the layers, how water
  gets in, what the pumping does underneath, the ice lens, the void, how a patch or a seal is built). dist = close. Actions still apply inside it.
Demand: at least {MIN_CUTAWAYS} cutaway beats across at least 5 different stations; use close, tight cutaways for mechanisms and exhibit/context
beats to tell the story around them.

ACTIONS you can use, per station (an action is only valid on its own station, and the beat's focus must be that station):
{action_help}

For EVERY beat return:
- scene: the number. focus: a station. nature: context | exhibit | cutaway. show: one sentence IN SPANISH of what the viewer sees and what moves, tied to the words.
- shot: dist (wide|medium|close, consistent with nature), angle (left|front|right = where the camera stands), height (low|mid|high), move (one of {", ".join(MOVES)}).
- events (each locked to a cue copied exactly from the beat, 1-3 consecutive words), kinds:
  action (field action = one valid action of the focus station; this is the main tool),
  highlight (neutral white pulse on a part that is only named; target = a station),
  term_callout (yellow term copied from the narration: asfalto, base, subrasante, grietas, cocodrilo, agua, bache, hielo, lentes, parche, sellar, drenar; each at most once),
  arrow (a red arrow; RARE: only where a direction is not already obvious from the motion; fill target).
- why: one short reason.

HARD RULES (checked in code; what you skip gets filled with a default, which is worse than your choice):
1. Every beat of 3.5 s or more needs at least ONE action; every beat of 5.5 s or more needs at least TWO, on different cue words.
2. The action must match the words: it fires on the word that says it ("empuja" -> press, "se congela" -> freeze, "esquiva" -> car_pass).
3. Camera variety is mandatory. Never repeat the same (dist, angle, height, move) as the previous beat. Use every move at least twice in the video, use
   all three angles and all three heights, and do not use drift for more than a quarter of the beats. Match the move to the content: push_in on a
   detail being introduced, pull_out to reveal consequences, orbit while something is explained from several sides, crane_down to look into a
   cross-section, pan along a crack or a wheel path.
4. Stay on the station of the idea being told; revisit a station only with a new angle, height and move, and a different action.
5. Use at least 14 different actions across the video and at least two actions on every exhibit station.
6. The first beat is road/context/wide with car_pass on its first words. The last beat is road/context/wide with the street patched.
7. At most {MAX_ARROWS} arrow events in the whole video, none by default.
8. No more than {HOLD_CAP:.0f} seconds without an action, highlight, callout or camera change."""


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
    move: Literal["push_in", "pull_out", "orbit_left", "orbit_right", "pan_left", "pan_right", "crane_up", "crane_down", "drift"]


class Beat(BaseModel):
    scene: int
    focus: Literal["road", "layers", "cracks", "water", "traffic", "pothole", "ice", "repair", "prevent"]
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
        beats = {b.scene: b for b in llm.generate(GUIDANCE, prompt, Film, max_tokens=28000, provider=PROVIDER, api_model=llm.API_MODEL).beats if 0 <= b.scene < len(scenes)}
    else:
        beats = {i: Beat(scene=i, **m) for i, m in enumerate(saved[:len(scenes)]) if m}
    used_terms, last_term_at, arrows = set(), -99.0, 0
    for i, scene in enumerate(scenes):
        scene["notes"], scene["index"] = [], i
        b = beats.get(i)
        scene["model"] = {"focus": b.focus, "nature": b.nature, "shot": b.shot.model_dump(), "show": b.show, "events": [e.model_dump() for e in b.events], "why": b.why} if b else None
        focus = b.focus if b else (scenes[i - 1]["focus"] if i else "road")
        nature = b.nature if b else "exhibit"
        shot = b.shot.model_dump() if b else {"dist": "medium", "angle": "front", "height": "mid", "move": "drift"}
        if b is None:
            scene["notes"].append("model returned no beat; kept the previous focus with a default shot")
        if i == 0 and focus != "road":
            scene["notes"].append(f"first beat forced to road (model chose {focus})")
            focus = "road"
        want = {"context": "wide", "cutaway": "close"}.get(nature)
        if focus == "road" and nature != "context":
            scene["notes"].append(f"road is always context (model chose {nature})")
            nature, want = "context", "wide"
        if want and shot["dist"] != want:
            scene["notes"].append(f"nature {nature} needs dist {want} (model chose {shot['dist']})")
            shot["dist"] = want
        if nature == "exhibit" and shot["dist"] == "wide":
            scene["notes"].append("exhibit beat set to medium distance (was wide)")
            shot["dist"] = "medium"
        evs, seen = [], {}
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
                if abs(at - seen.get(e.action, -99)) < 1.5:
                    scene["notes"].append(f"action {e.action} twice within 1.5 s; dropped")
                    continue
                seen[e.action] = at
                evs.append({"kind": "action", "cue": e.cue, "at": at, "target": focus, "action": e.action})
                continue
            if kind == "arrow":
                if arrows >= MAX_ARROWS or not base._is_force(e.cue):
                    scene["notes"].append("arrow dropped: " + ("limit reached" if arrows >= MAX_ARROWS else f"{e.cue!r} has no flow or motion word"))
                    continue
                arrows += 1
                evs.append({"kind": "arrow", "cue": e.cue, "at": at, "target": target if target in pp.STATIONS else focus})
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
            target = target if target in pp.STATIONS else (base._noun_target(e.cue) or focus)
            if any(abs(at - x["at"]) < 0.8 for x in evs if x["kind"] == "highlight"):
                scene["notes"].append(f"highlight at {at}s dropped: collides with another highlight")
                continue
            evs.append({"kind": "highlight", "cue": e.cue, "at": at, "target": target})
        dur = scene["end"] - scene["start"]
        need = 2 if dur >= 5.5 else 1 if dur >= 3.5 else 0
        have = [x for x in evs if x["kind"] == "action"]
        if i == 0 and not any(x["action"] == "car_pass" for x in have):
            w = _word_at(scene, words, 0.0)
            evs.append({"kind": "action", "cue": w["text"], "at": round(w["start"] + 0.3, 2), "target": "road", "action": "car_pass"})
            have.append(evs[-1])
            scene["notes"].append("first beat had no car_pass; added on its first word")
        for frac in (0.3, 0.65, 0.45):
            if len(have) >= need:
                break
            todo = [a for a in PRIORITY[focus] if a not in {x["action"] for x in have}] or PRIORITY[focus]
            w = _word_at(scene, words, frac)
            if w is None or any(abs(w["start"] - x["at"]) < 1.2 for x in have):
                continue
            evs.append({"kind": "action", "cue": w["text"], "at": round(w["start"], 2), "target": focus, "action": todo[0]})
            have.append(evs[-1])
            scene["notes"].append(f"beat of {dur:.1f} s needed {need} action(s); validator added {todo[0]} on {w['text']!r}")
        scene["focus"], scene["nature"], scene["shot"], scene["dist"], scene["show"] = focus, nature, shot, shot["dist"], b.show if b else ""
        scene["events"] = sorted(evs, key=lambda x: x["at"])
        scene.pop("keywords", None)
    # nature demands: enough cutaways, spread over stations
    cut = [s for s in scenes if s["nature"] == "cutaway"]
    for st in CUTAWAY_ORDER:
        if len(cut) >= MIN_CUTAWAYS:
            break
        pick = next((s for s in scenes if s["focus"] == st and s["nature"] == "exhibit" and s["end"] - s["start"] >= 3.5 and s["index"] > 0), None)
        if pick:
            pick["nature"], pick["shot"]["dist"], pick["dist"] = "cutaway", "close", "close"
            pick["notes"].append(f"only {len(cut)} cutaways; promoted this {st} beat to a cutaway")
            cut.append(pick)
    # camera variety: no repeated pose, angle changes at least every third beat, drift limited
    key = lambda x: (x["dist"], x["angle"], x["height"], x["move"])  # noqa: E731
    for i in range(1, len(scenes)):
        s, p = scenes[i]["shot"], scenes[i - 1]["shot"]
        if key(s) == key(p):
            s["move"] = next(m for m in MOVES if m not in (p["move"], "drift"))
            scenes[i]["notes"].append(f"same camera as the previous beat; move changed to {s['move']}")
        if i >= 2 and s["angle"] == p["angle"] == scenes[i - 2]["shot"]["angle"]:
            s["angle"] = next(a for a in ANGLES if a != s["angle"])
            scenes[i]["notes"].append(f"third beat on the same side; angle changed to {s['angle']}")
    drifts = [sc for sc in scenes if sc["shot"]["move"] == "drift"]
    for k, sc in enumerate(drifts[:max(0, len(drifts) - len(scenes) // 4)]):
        sc["shot"]["move"] = MOVES[(k * 3 + 1) % 8]
        sc["notes"].append(f"too many drift beats; move changed to {sc['shot']['move']}")
    first, last = scenes[0], scenes[-1]
    first["shot"]["dist"], first["dist"], first["nature"] = "wide", "wide", "context"
    if last["focus"] != "road":
        last["notes"].append(f"last beat forced to road (model chose {last['focus']})")
        last["focus"] = "road"
    last["shot"].update({"dist": "wide", "move": "pull_out"})
    last["dist"], last["nature"] = "wide", "context"
    if not any(e["action"] == "patch_street" for sc in scenes for e in sc["events"] if e["kind"] == "action"):
        w = _word_at(last, words, 0.0)
        last["events"].insert(0, {"kind": "action", "cue": w["text"], "at": round(w["start"], 2), "target": "road", "action": "patch_street"})
        last["notes"].append("no patch_street in the plan; added on the last beat")


def summary(scenes: list[dict]) -> str:
    acts = [e["action"] for s in scenes for e in s["events"] if e["kind"] == "action"]
    cnt = lambda f, vals: {v: sum(f(s) == v for s in scenes) for v in vals}  # noqa: E731
    return (f"{len(scenes)} beats | nature {cnt(lambda s: s['nature'], ['context', 'exhibit', 'cutaway'])} on "
            f"{len({s['focus'] for s in scenes if s['nature'] == 'cutaway'})} stations | {len(acts)} actions, {len(set(acts))} distinct | "
            f"moves {cnt(lambda s: s['shot']['move'], MOVES)} | angles {cnt(lambda s: s['shot']['angle'], ANGLES)} | heights {cnt(lambda s: s['shot']['height'], HEIGHTS)} | "
            f"arrows {sum(e['kind'] == 'arrow' for s in scenes for e in s['events'])}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    spoken = json.loads((HERE / "words.json").read_text(encoding="utf-8"))
    words, seconds = spoken["words"], round(spoken["duration"] + base.TAIL_SECONDS, 2)
    motion.SCENE_SECONDS, motion.SENTENCE_GAP = base.BEAT_SECONDS, base.CLAUSE_GAP
    scenes = base.split_long(motion.plan(words, seconds)["scenes"], words, limit=BEAT_LIMIT)
    saved = [s.get("model") for s in json.loads((HERE / "plan.json").read_text(encoding="utf-8"))["scenes"]] if "--revalidate" in sys.argv else None
    design(scenes, words, saved)
    base.snap_boundaries(scenes)
    base.fill_gaps(scenes, words, seconds, cap=HOLD_CAP)
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE / "plan.json"
    out.write_text(json.dumps({"duration": seconds, "voice": spoken["voice"], "rate": spoken["rate"], "provider": PROVIDER, "director": 2,
                               "model_env": os.getenv("BRAINROT_CLAUDE_MODEL"), "scenes": scenes}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for s in scenes:
        sh = s["shot"]
        print(f"{s['index']:>2} {s['start']:6.1f}-{s['end']:6.1f} ({s['end'] - s['start']:3.1f}s) {s['focus']:<8} {s['nature']:<8} {sh['dist']:<6} {sh['angle']:<5} {sh['height']:<4} {sh['move']:<11}",
              " | ".join(f"{e['at']:.1f} {e.get('action') or e['kind'][:5]}{('→' + e['target']) if e['kind'] != 'action' else ''}{(' [' + e['term'] + ']') if e.get('term') else ''}" for e in s["events"]))
        for n in s["notes"]:
            print("      note:", n)
    print(summary(scenes), "| provider", PROVIDER)


if __name__ == "__main__":
    main()
