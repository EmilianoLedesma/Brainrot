"""Beat splitting, cue matching and gap filling for the world director. Pure functions: no model calls, no shared module state.

(The card-style motion edit has its own grouping in brainrot/motion.py; this one never touches its globals, so both modes can run in one worker.)
"""
import re
import unicodedata


def plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))


def strip(word: str) -> str:
    return plain(word).strip(".,;:!?¿¡")


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def group(words: list[dict], seconds: float, beat_seconds: float = 4.0, gap: float = 0.35) -> list[dict]:
    """Group the narration into beats of at least `beat_seconds`, cut on a sentence end or a pause (the TTS word boundaries carry no punctuation)."""
    def ends(i: int) -> bool:
        return words[i]["text"].rstrip().endswith((".", "!", "?")) or (i + 1 < len(words) and words[i + 1]["start"] - words[i]["end"] >= gap)

    groups, current = [], []
    for i, word in enumerate(words):
        current.append(i)
        if ends(i) and word["end"] - words[current[0]]["start"] >= beat_seconds:
            groups.append(current)
            current = []
    if current:
        if groups and words[current[-1]]["end"] - words[current[0]]["start"] < beat_seconds / 2:
            groups[-1] += current
        else:
            groups.append(current)
    out = []
    for n, g in enumerate(groups):
        start = 0.0 if n == 0 else words[g[0]]["start"]
        end = seconds if n == len(groups) - 1 else words[groups[n + 1][0]]["start"]
        out.append({"start": round(start, 2), "end": round(end, 2), "text": " ".join(words[i]["text"] for i in g)})
    return out


def inside(scene: dict, words: list[dict]) -> list[dict]:
    return [w for w in words if scene["start"] - .05 <= w["start"] < scene["end"]]


def find(phrase: str, scene: dict, words: list[dict]) -> list[dict] | None:
    target = [norm(w) for w in phrase.split() if norm(w)]
    got = inside(scene, words)
    for i in range(len(got) - len(target) + 1 if target else 0):
        if all(norm(got[i + j]["text"]) == t for j, t in enumerate(target)):
            return got[i:i + len(target)]
    return None


def timed(scene: dict, words: list[dict]) -> str:
    got = inside(scene, words)
    return "\n".join(f"[{got[i]['start']:.1f}s] " + " ".join(w["text"] for w in got[i:i + 6]) for i in range(0, len(got), 6))


def noun_target(text: str, nouns: dict[str, str]) -> str:
    for w in text.split():
        t = nouns.get(strip(w))
        if t:
            return t
    return ""


def is_force(cue: str, nouns: dict[str, str], stems: tuple[str, ...]) -> bool:
    """A motion or flow word that is not itself just the name of a part."""
    return any(any(st in plain(w) for st in stems) for w in cue.split() if strip(w) not in nouns)


def word_at(scene: dict, words: list[dict], fraction: float) -> dict | None:
    got = inside(scene, words)
    return got[min(len(got) - 1, int(len(got) * fraction))] if got else None


def split_long(scenes: list[dict], words: list[dict], limit: float = 6.5) -> list[dict]:
    """Split any beat longer than `limit` at the longest pause near its middle, repeatedly, so the camera has something new to do every few seconds."""
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


def snap_boundaries(scenes: list[dict], hero: str, lead: float = 0.3) -> None:
    """A part must be on screen when its word is spoken: if a beat has an event on the station the NEXT beat focuses (and not its own),
    move the boundary to just before that word and hand the event to the next beat."""
    for i in range(len(scenes) - 1):
        a, b = scenes[i], scenes[i + 1]
        for e in list(a["events"]):
            if e["kind"] in ("action", "subject"):
                continue
            if e["target"] != a["focus"] and e["target"] == b["focus"] and e["target"] != hero:
                cut = round(e["at"] - lead, 2)
                if cut - a["start"] >= 2.0 and b["end"] - cut >= 2.0 and b["start"] - cut <= 4.0 and not any(x["at"] >= cut for x in a["events"] if x["kind"] in ("action", "subject")):
                    a["notes"].append(f"boundary moved from {b['start']:.1f}s to {cut:.1f}s so {e['target']} is on screen at {e['at']:.1f}s")
                    a["end"], b["start"] = cut, cut
                    moved = [x for x in a["events"] if x["at"] >= cut]
                    a["events"] = [x for x in a["events"] if x["at"] < cut]
                    b["events"] = sorted(moved + b["events"], key=lambda x: x["at"])
                    break


def fill_gaps(scenes: list[dict], words: list[dict], total: float, nouns: dict[str, str], cap: float = 7.0) -> None:
    """Hold cap in code: where more than `cap` seconds pass with no event and no change of station or distance, add a neutral highlight on the nearest part noun."""
    for _ in range(30):
        changes = sorted({0.0, total} | {e["at"] for s in scenes for e in s["events"]}
                         | {b["start"] for a, b in zip(scenes, scenes[1:]) if (a["focus"], a["dist"]) != (b["focus"], b["dist"])})
        gap = next(((a, b) for a, b in zip(changes, changes[1:]) if b - a > cap), None)
        if gap is None:
            return
        a, b = gap
        taken = [e["at"] for s in scenes for e in s["events"]]
        cands = [w for w in words if a + 2.5 <= w["start"] <= b - 2.0 and all(abs(w["start"] - t) >= 0.8 for t in taken)]
        nouned = [w for w in cands if strip(w["text"]) in nouns]
        pool = nouned or cands
        pick = min(pool, key=lambda w: abs(w["start"] - (a + cap - 1.5)), default=None)
        if pick is None:
            return
        scene = next(s for s in scenes if s["start"] - .05 <= pick["start"] < s["end"])
        target = nouns.get(strip(pick["text"])) or scene["focus"]
        scene["events"] = sorted(scene["events"] + [{"kind": "highlight", "cue": pick["text"], "at": round(pick["start"], 2), "target": target}], key=lambda e: e["at"])
        scene["notes"].append(f"gap of {b - a:.1f} s with no event: validator added highlight({target}) on {pick['text']!r} at {pick['start']:.1f}s")
