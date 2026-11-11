"""Turns a directed plan plus the narration timings into the script the Remotion world reads. No model is involved here.

Captions are independent 2-5 word phrases grouped BEFORE the script is written (clause boundaries come from the source text's punctuation when it lines up with
the narrated words, otherwise from the pauses), so word-by-word accumulation is structurally impossible and a one-word leftover is folded into a neighbour of the
SAME sentence. Camera waypoints leave LEAD frames before a beat and fly for FLIGHT frames.
"""
import math

FPS = 30
LEAD = 15       # frames before the beat's first word at which the camera starts flying (0.5 s)
FLIGHT = 45     # frames a flight lasts (1.5 s)
MAX_WORDS = 5


def frames(seconds: float) -> int:
    return round(seconds * FPS)


def tokens(words: list[dict], title: str, text: str) -> list[str]:
    """One punctuated token per narrated word: the spoken title and text when they line up exactly, otherwise punctuation inferred from the pauses."""
    source = title.split() + text.split()
    if len(source) == len(words):
        return source
    out = []
    for i, w in enumerate(words):
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 9.0
        out.append(w["text"].rstrip(".,;:!?") + ("." if gap >= 0.7 else "," if gap >= 0.35 else ""))
    return out


def clauses(toks: list[str], title_len: int) -> list[tuple[int, int]]:
    out, start = [], 0
    for i, t in enumerate(toks):
        if i == title_len - 1 or t[-1:] in ".,;:!?¿" or i == len(toks) - 1:
            out.append((start, i))
            start = i + 1
    return out


def phrases(cl: list[tuple[int, int]], toks: list[str]) -> list[tuple[int, int]]:
    joined: list[tuple[int, int]] = []  # a one-word clause joins its neighbour in the same sentence (comma-joined) before chunking
    i = 0
    while i < len(cl):
        a, b = cl[i]
        if a == b and toks[b].endswith(",") and i + 1 < len(cl):
            joined.append((a, cl[i + 1][1]))
            i += 2
        elif a == b and joined and toks[joined[-1][1]].endswith(","):
            joined[-1] = (joined[-1][0], b)
            i += 1
        else:
            joined.append((a, b))
            i += 1
    out = []
    for a, b in joined:
        n = b - a + 1
        k = math.ceil(n / MAX_WORDS)
        sizes = [n // k + (1 if i < n % k else 0) for i in range(k)]
        at = a
        for s in sizes:
            out.append((at, at + s - 1))
            at += s

    def ends(i: int) -> bool:
        return toks[i][-1:] in ".?!"

    changed = True
    while changed:
        changed = False
        for i, (a, b) in enumerate(out):
            if b - a + 1 != 1:
                continue
            if i > 0 and not ends(out[i - 1][1]) and out[i - 1][1] - out[i - 1][0] + 2 <= MAX_WORDS:
                out[i - 1] = (out[i - 1][0], b)
                del out[i]
            elif i + 1 < len(out) and not ends(b) and out[i + 1][1] - out[i + 1][0] + 2 <= MAX_WORDS:
                out[i + 1] = (a, out[i + 1][1])
                del out[i]
            else:
                continue
            changed = True
            break
    return out


def build(plan: dict, title: str, text: str, words: list[dict]) -> dict:
    """The script for one narrated chapter. `plan` is the director's output."""
    scenes, total = plan["scenes"], frames(plan["duration"])
    waypoints, events, actions, subject_actions, captions = [], [], [], [], []
    for n, s in enumerate(scenes):
        waypoints.append({"id": f"w{n}", "at": 0 if n == 0 else max(0, frames(s["start"]) - LEAD), "start": frames(s["start"]),
                          "end": total if n == len(scenes) - 1 else frames(scenes[n + 1]["start"]),
                          "focus": s["focus"], "dist": s["dist"], "nature": s["nature"], "shot": s["shot"], "show": s["show"]})
        for k, e in enumerate(s["events"]):
            at = frames(e["at"])
            if e["kind"] == "action":
                actions.append({"id": f"a{n}_{k}", "target": e["target"], "name": e["action"], "at": at})
            elif e["kind"] == "subject":
                subject_actions.append({"id": f"s{n}_{k}", "name": e["action"], "at": at})
            else:
                events.append({"id": f"e{n}_{k}", "kind": e["kind"], "at": at, "term": e.get("term", ""), "target": e["target"]})
    toks = tokens(words, title, text)
    ph = phrases(clauses(toks, len(title.split())), toks)
    for k, (a, b) in enumerate(ph):
        at = frames(words[a]["start"])
        nxt = frames(words[ph[k + 1][0]]["start"]) if k + 1 < len(ph) else total
        until = min(nxt - 1, frames(words[b]["end"]) + 24)
        captions.append({"id": f"c{k}", "at": at, "until": max(until, at + 12), "style": "phrase", "text": " ".join(w["text"] for w in words[a:b + 1])})
    for e in events:
        if e["kind"] == "term_callout":
            phrase_until = max((c["until"] for c in captions if c["style"] == "phrase" and c["at"] <= e["at"] < c["until"]), default=e["at"] + 30)
            captions.append({"id": "t" + e["id"], "at": e["at"], "until": min(phrase_until + 30, total - 1), "style": "term", "text": e["term"]})
    return {"title": title, "fps": FPS, "durationFrames": total, "flight": FLIGHT, "subject": plan.get("subject"), "waypoints": waypoints, "actions": actions,
            "subjectActions": subject_actions, "events": events, "captions": captions, "world": plan.get("world")}


def problems(script: dict) -> list[str]:
    """What would make the Remotion world refuse the script (checked here first so a job fails before the long render)."""
    wps, found = script["waypoints"], []
    if not wps:
        return ["no waypoints"]
    found += [f"waypoint {w['id']} is closer than one flight to the previous one" for i, w in enumerate(wps) if i and w["at"] - wps[i - 1]["at"] < script["flight"]]
    found += [f"phrase {c['id']} has more than {MAX_WORDS} words" for c in script["captions"] if c["style"] == "phrase" and len(c["text"].split()) > MAX_WORDS]
    return found
