"""Turns plan.json (validated shots, events and captions with real word timings) into script.json for FoilSides.tsx.

No model is involved here and the renderer never receives free-form code: it only interprets script.json.

  python experiments/foil-sides-lowpoly/build_script.py
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
CAMERAS = {  # one fixed camera per shot type; hard cuts, no state carried between shots
    "establishing": {"pos": [3.0, 2.2, 7.8], "target": [0.7, 0.6, 0], "fov": 35},
    "cutaway": {"pos": [2.6, 1.9, 5.8], "target": [0, 0.1, 0], "fov": 35},
    "insert": {"pos": [2.4, 1.5, 5.2], "target": [0, 0.3, 0], "fov": 35},
    "metaphor": {"pos": [1.2, 0.5, 7.3], "target": [0, 0, 0], "fov": 35},
}
STILLS = [40, 300, 500, 680, 880, 1010, 1100, 1300, 1560, 1700, 1960, 2200, 2420, 2520, 2650, 2790]  # 16, incl. every event


def frames(seconds: float) -> int:
    return round(seconds * FPS)


def main() -> None:
    plan = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
    scenes, total = plan["scenes"], frames(plan["duration"])
    shots, captions, events = [], [], []
    for n, s in enumerate(scenes):
        start = 0 if n == 0 else frames(s["start"])
        end = total if n == len(scenes) - 1 else frames(scenes[n + 1]["start"])
        shots.append({"id": f"s{n}", "type": s["shot"], "start": start, "end": end, "camera": CAMERAS[s["shot"]]})
        c = s["caption"]
        words = [{"text": w["text"], "at": frames(w["at"])} for w in c["words"]]
        size = 64 if len(words) <= 8 else 54  # long closed phrases shrink instead of being cut
        until = min(frames(c["until"]), end - 1)
        captions.append({"id": f"c{n}", "at": words[0]["at"], "until": until, "style": "word", "y": 1480, "size": size,
                         "text": c["text"], "words": words})
        e = s["event"]
        if e["kind"] == "none":
            continue
        events.append({"id": f"e{n}", "shot": f"s{n}", "kind": e["kind"], "at": frames(e["at"]), "term": e.get("term", "")})
        if e["kind"] == "term_callout" and e.get("term"):
            lines = math.ceil(len(c["text"]) / int(940 / (size * 0.56)))
            captions.append({"id": f"t{n}", "at": frames(e["at"]), "until": min(until + FPS, end - 1), "style": "term",  # holds one beat longer
                             "y": round(1480 + lines * size * 1.12 + 24), "size": 76, "text": e["term"],
                             "words": [{"text": w, "at": frames(e["at"]) + 3 * k} for k, w in enumerate(e["term"].split())]})
    out = {"title": "El secreto del aluminio", "fps": FPS, "durationFrames": total, "shots": shots, "captions": captions,
           "events": events, "stillFrames": STILLS, "sources": [],
           "note": "Generated from plan.json by build_script.py. Schematic explainer; no figures are stated on screen."}
    (HERE / "script.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"script.json: {total} frames, {len(shots)} shots, {len(captions)} captions, {len(events)} events")


if __name__ == "__main__":
    main()
