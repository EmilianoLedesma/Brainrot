"""Turns plan.json + words.json + story.json into script.json for Zebra.tsx. No model is involved here.

Continuous world: the plan's beats become camera WAYPOINTS (focus station + distance) on one shared timeline, not separate shots. The camera
leaves for the next waypoint LEAD frames before the beat starts and arrives FLIGHT frames later; between waypoints it drifts (done in Zebra.tsx).
Captions reuse the zipper experiment's phrase grouper (independent 2-5 word phrases, no accumulation, no glued sentence ends).

  python experiments/cpu-lowpoly/build_script.py [--plan PATH] [--out PATH]
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
LEAD = 15      # frames before the beat's first word at which the camera starts flying (0.5 s)
FLIGHT = 45    # frames a flight lasts (1.5 s): calmer than the pothole film
_spec = importlib.util.spec_from_file_location("zipper_build_script", HERE.parent / "zipper-lowpoly" / "build_script.py")
_zip = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_zip)


def frames(seconds: float) -> int:
    return round(seconds * FPS)


def main() -> None:
    args = sys.argv
    plan_path = Path(args[args.index("--plan") + 1]) if "--plan" in args else HERE / "plan.json"
    out_path = Path(args[args.index("--out") + 1]) if "--out" in args else HERE / "script.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    words = json.loads((HERE / "words.json").read_text(encoding="utf-8"))["words"]
    scenes, total = plan["scenes"], frames(plan["duration"])
    waypoints, events, captions, actions = [], [], [], []
    for n, s in enumerate(scenes):
        waypoints.append({"id": f"w{n}", "at": 0 if n == 0 else max(0, frames(s["start"]) - LEAD), "start": frames(s["start"]),
                          "end": total if n == len(scenes) - 1 else frames(scenes[n + 1]["start"]),
                          "focus": s["focus"], "dist": s["dist"], "nature": s["nature"], "shot": s["shot"], "show": s["show"]})
        for k, e in enumerate(s["events"]):
            if e["kind"] == "action":
                actions.append({"id": f"a{n}_{k}", "target": e["target"], "name": e["action"], "at": frames(e["at"])})
                continue
            events.append({"id": f"e{n}_{k}", "kind": e["kind"], "at": frames(e["at"]), "term": e.get("term", ""), "target": e["target"]})
    cl, tokens = _zip.clauses(story, len(words))
    ph = _zip.phrases(cl, tokens)
    for k, (a, b) in enumerate(ph):
        at = frames(words[a]["start"])
        nxt = frames(words[ph[k + 1][0]]["start"]) if k + 1 < len(ph) else total
        until = min(nxt - 1, frames(words[b]["end"]) + 24)
        captions.append({"id": f"c{k}", "at": at, "until": max(until, at + 12), "style": "phrase", "text": " ".join(w["text"] for w in words[a:b + 1])})
    for e in events:
        if e["kind"] == "term_callout":
            phrase_until = max((c["until"] for c in captions if c["style"] == "phrase" and c["at"] <= e["at"] < c["until"]), default=e["at"] + 30)
            captions.append({"id": "t" + e["id"], "at": e["at"], "until": min(phrase_until + 30, total - 1), "style": "term", "text": e["term"]})
    stills = sorted({min(total - 1, w["start"] + (w["end"] - w["start"]) // 2) for w in waypoints})
    runs = []
    for label, focus in (("flight into coat", "coat"), ("flight into hair", "hair"), ("flight into landing", "landing"), ("flight back to savanna", "savanna")):
        w = next((w for i, w in enumerate(waypoints) if w["focus"] == focus and i and waypoints[i - 1]["focus"] != focus), None)
        if w:
            runs.append({"label": label, "shot": w["id"], "start": max(0, w["at"] - 6), "step": 5, "count": 12})
    out = {"title": story["title"], "fps": FPS, "durationFrames": total, "flight": FLIGHT, "waypoints": waypoints, "actions": actions,
           "captions": captions, "events": events, "stillFrames": stills, "fluidityRuns": runs, "sources": [],
           "note": "Generated from plan.json, words.json and story.json by build_script.py. One continuous world, no cuts; captions are independent 2-5 word phrases."}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    sizes = [len(c["text"].split()) for c in captions if c["style"] == "phrase"]
    print(f"{out_path.name}: {total} frames, {len(waypoints)} waypoints, {len(sizes)} phrases (words each: min {min(sizes)}, max {max(sizes)}), {len(events)} events, {len(actions)} actions ({len({a['name'] for a in actions})} distinct)")


if __name__ == "__main__":
    main()
