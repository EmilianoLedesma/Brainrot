"""Audit scene plans against the explicit rules of docs/motion-graphics-recipe-lowpoly.md, no rendering needed.

For every plan-<name>.json it builds that plan's script.json (build_script.py) and measures: caption rules, the ambient and camera
fields, the 8-10 s no-new-event cap, reserved colours, acknowledgement of every technical noun, variety and validator interventions.
Rules that are enforced by code (captions, ambient, camera) cannot differ between models: the audit reports them anyway, so it is
clear which findings depend on the model (shot and event choices) and which do not.

  python experiments/shock-absorber-lowpoly/audit.py opus1 opus2 default1 default2
"""
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
FPS = 30
NOUNS = ["amortiguador", "resorte", "pistón", "varilla", "carrocería", "cilindro", "aceite", "válvulas", "suspensión", "rueda", "llantas"]
COLOR = {"force_arrows": "red", "term_callout": "yellow", "flow_chevrons": "gray/white", "damp": "none (state change)"}
CAP = 10.0  # seconds: the recipe's "roughly 8-10 s with no new event, callout or camera move" cap


def norm(w: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", w.lower()) if c.isalpha() and not unicodedata.combining(c))


def audit(name: str) -> dict:
    subprocess.run([sys.executable, str(HERE / "build_script.py"), "--plan", str(HERE / f"plan-{name}.json"), "--out", str(HERE / f"script-{name}.json")], check=True, capture_output=True)
    plan = json.loads((HERE / f"plan-{name}.json").read_text(encoding="utf-8"))
    script = json.loads((HERE / f"script-{name}.json").read_text(encoding="utf-8"))
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    words = json.loads((HERE / "words.json").read_text(encoding="utf-8"))["words"]
    total = script["durationFrames"] / FPS
    title_n = len(story["title"].split())
    tokens = story["title"].split() + story["script"].split()
    # captions
    phrases = [c["text"] for c in script["captions"] if c["style"] == "phrase"]
    ptr, cross, bad_len, accum = 0, [], [], 0
    for i, t in enumerate(phrases):
        n = len(t.split())
        if n < 2 or n > 5:
            bad_len.append(t)
        sl = tokens[ptr:ptr + n]
        if any(tok[-1] in ".?!" for tok in sl[:-1]) or ptr < title_n < ptr + n:
            cross.append(t)
        if i and t.lower().startswith(phrases[i - 1].lower()):
            accum += 1
        ptr += n
    # ambient and camera (code-enforced, identical for every plan)
    amb_ok = all(s.get("ambient") and s["ambient"].get("kind") and s["ambient"].get("moving") and s["ambient"].get("period") for s in script["shots"])
    cam_ok = all(s["camera"]["from"] != s["camera"]["to"] for s in script["shots"])
    same_type_cuts = sum(1 for a, b in zip(script["shots"], script["shots"][1:]) if a["type"] == b["type"])
    # visual changes: events, and cuts where the composition type changes
    changes = sorted({0.0, total} | {e["at"] / FPS for e in script["events"] if e["kind"] != "damp" or True}
                     | {b["start"] / FPS for a, b in zip(script["shots"], script["shots"][1:]) if a["type"] != b["type"]})
    gaps = [(b - a, a) for a, b in zip(changes, changes[1:])]
    longest = max(gaps)
    over = [g for g in gaps if g[0] > CAP]
    # technical nouns: acknowledged when an event fires within 3 s of an occurrence of that noun
    ev_t = [(e["at"] / FPS, e["kind"], e.get("term", "")) for e in script["events"]]
    occ = {n: [w["start"] for w in words if norm(w["text"]) == norm(n)] for n in NOUNS}
    mentioned = {n: t for n, t in occ.items() if t}
    acked = {n for n, ts in mentioned.items() if any(abs(t - et) <= 3 for t in ts for et, _k, _x in ev_t)}
    dampt = next((e["at"] / FPS for e in script["events"] if e["kind"] == "damp"), None)
    first_damper = occ["amortiguador"][0] if occ["amortiguador"] else None
    kinds = {}
    for e in script["events"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    shots = {}
    for s in script["shots"]:
        shots[s["type"]] = shots.get(s["type"], 0) + 1
    notes = [f"block {s['index']}: {n}" for s in plan["scenes"] for n in s["notes"]]
    blocks = [round(s["end"] - s["start"], 1) for s in plan["scenes"]]
    return {"name": name, "model": plan.get("model_env") or "CLI default", "blocks": len(blocks), "block_seconds": blocks, "shots": shots, "events": kinds,
            "terms": [e["term"] for e in script["events"] if e["kind"] == "term_callout"], "phrases": len(phrases), "phrase_length_violations": bad_len,
            "cross_sentence_phrases": cross, "accumulating_phrases": accum, "ambient_every_shot": amb_ok, "camera_moves_every_shot": cam_ok,
            "consecutive_same_type_cuts": same_type_cuts, "longest_no_change_s": round(longest[0], 1), "longest_starts_at_s": round(longest[1], 1),
            "gaps_over_cap": [[round(g, 1), round(a, 1)] for g, a in over], "seconds_in_gaps_over_cap": round(sum(g for g, _a in over), 1),
            "nouns_mentioned": sorted(mentioned), "nouns_acknowledged": sorted(acked), "nouns_unacknowledged": sorted(set(mentioned) - acked),
            "damp_at_s": dampt, "first_amortiguador_s": round(first_damper, 1) if first_damper else None,
            "event_list": [{"at_s": round(e["at"] / FPS, 1), "kind": e["kind"], "color": COLOR[e["kind"]], "shot": e["shot"], "term": e.get("term", "")} for e in script["events"]],
            "model_cues": [{"block": s["index"], "shot": s["shot"], "event": [e["kind"] for e in (s.get("events") or [s["event"]])], "cue": [e.get("cue", "") for e in (s.get("events") or [s["event"]])], "why": (s.get("model") or {}).get("why", "")} for s in plan["scenes"]],
            "validator_notes": notes}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    results = [audit(n) for n in sys.argv[1:]]
    (HERE / "audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rows = ["model", "blocks", "shots", "events", "terms", "phrases", "phrase_length_violations", "cross_sentence_phrases", "accumulating_phrases", "ambient_every_shot",
            "camera_moves_every_shot", "consecutive_same_type_cuts", "longest_no_change_s", "longest_starts_at_s", "seconds_in_gaps_over_cap", "nouns_unacknowledged", "damp_at_s", "first_amortiguador_s", "validator_notes"]
    for r in rows:
        print(f"{r:28}", " | ".join(f"{str(x[r])[:44]:44}" for x in results))
    print("names:", [x["name"] for x in results])


if __name__ == "__main__":
    main()
