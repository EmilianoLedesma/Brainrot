"""Scene packs: the worlds the continuous-world edit can direct and render.

A pack is a JSON manifest here (stations, the nouns that point at them, each station's actions with durations in frames, the optional subject and its actions,
caps and the opening action) plus a Remotion module in motion/world/packs/ with the same id that draws it. The director only ever uses what a manifest lists,
so a new topic family means a new pack: manifest + renderer. Nothing is generated as code at run time.
"""
import json
from functools import lru_cache
from pathlib import Path

from ..domain.jobs import PermanentError

PACKS_DIR = Path(__file__).parent / "packs"
REQUIRED = ("id", "title", "summary", "world", "hero", "stations", "station_notes", "nouns", "glossary", "force_stems", "actions", "cutaway_stations",
            "min_cutaways", "opening", "max_arrows", "hold_cap", "beat_limit", "max_move_share", "term_help")


@lru_cache(maxsize=1)
def packs() -> dict[str, dict]:
    found = {}
    for file in sorted(PACKS_DIR.glob("*.json")):
        pack = json.loads(file.read_text(encoding="utf-8"))
        problems = check(pack)
        if problems:
            raise PermanentError(f"scene pack {file.stem} is invalid: {problems[0]}")
        found[pack["id"]] = pack
    return found


def check(pack: dict) -> list[str]:
    """Structural problems of a manifest (empty when it is usable)."""
    missing = [k for k in REQUIRED if k not in pack]
    if missing:
        return [f"missing {missing[0]}"]
    stations, problems = set(pack["stations"]), []
    if pack["hero"] not in stations:
        problems.append("the hero is not a station")
    problems += [f"noun {n!r} points at unknown station {s!r}" for n, s in pack["nouns"].items() if s not in stations]
    problems += [f"actions for unknown station {s!r}" for s in pack["actions"] if s not in stations]
    problems += [f"station {s!r} has no actions" for s in stations if not pack["actions"].get(s)]
    problems += [f"cutaway station {s!r} unknown" for s in pack["cutaway_stations"] if s not in stations]
    subject = pack.get("subject")
    if subject and not (subject.get("candidates") and subject.get("actions") and subject.get("defaults")):
        problems.append("the subject needs candidates, actions and defaults")
    if subject:
        problems += [f"default subject action for {s!r} unknown" for s, a in subject["defaults"].items() if a not in subject["actions"]]
    return problems


def get(pack_id: str) -> dict:
    try:
        return packs()[pack_id]
    except KeyError:
        raise PermanentError(f"unknown scene pack {pack_id!r}") from None


def menu() -> str:
    return "\n".join(f"- {p['id']}: {p['title']}. {p['summary']}" for p in packs().values())
