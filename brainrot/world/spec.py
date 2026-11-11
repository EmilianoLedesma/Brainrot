"""The world spec: what the design stage asks the model for, checked in code, and the bridge to the director.

The model describes a world as DATA: stations (one per idea of the video, plus the hero), the pieces on each station (presets or compositions of a few primitive
shapes), and the actions each station can perform, written as effects on those pieces. A generic renderer (motion/world/packs/generic.tsx) draws any valid spec;
no model-written code is ever executed. `check` lists every problem so one repair round can fix them, and `to_pack` gives the director the same manifest shape the
hand-built packs use, so its rules (camera, no overlaps, hold cap) apply unchanged.
"""
import re
from typing import Literal

from pydantic import BaseModel, Field

SHAPES = ("box", "ball", "cylinder", "cone", "disc")
PRESETS = ("custom", "person", "tree", "house", "animal", "bird")
EFFECTS = ("appear", "disappear", "move", "scale", "color", "glow", "spin", "ray", "wear")
GROUNDS = {"grass": "#CFDCA0", "sand": "#EBDDB0", "snow": "#F2F7FA", "stone": "#BDB4A4", "wood": "#C9A27A", "water": "#A9D6EC", "soil": "#B89F72", "floor": "#E8E4DA"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
NAME = re.compile(r"^[a-z][a-z0-9_]{1,23}$")
MIN_STATIONS, MAX_STATIONS = 4, 9
MAX_PIECES, MAX_PARTS_PER_PIECE, MAX_PARTS_PER_STATION, MAX_ACTIONS, MAX_EFFECTS = 12, 10, 48, 4, 8
MIN_FRAMES, MAX_FRAMES = 45, 260
STAGE_X, STAGE_Z, HERO_X, HERO_Z, MAX_Y = 8.0, 8.0, 30.0, 10.0, 10.0
GENERIC_FORCE = ["rebot", "bloque", "filtr", "refleja", "deslumbr", "llega", "absorb", "atraviesa", "pasa", "choc", "lanz", "empuj", "fluye", "cruza", "detiene",
                 "reflect", "block", "filter", "hit", "push", "flow", "pass", "reach", "cross", "stop", "bounce"]


class Part(BaseModel):
    shape: Literal["box", "ball", "cylinder", "cone", "disc"]
    size: list[float]          # box: width, height, depth; ball: radii x, y, z; cylinder, cone and disc: radius, height, radius
    pos: list[float]           # relative to the piece
    rot: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    color: str
    opacity: float = 1.0
    glow: float = 0.0


class Piece(BaseModel):
    id: str
    preset: Literal["custom", "person", "tree", "house", "animal", "bird"] = "custom"
    pos: list[float]
    rot_y: float = 0.0
    scale: float = 1.0
    color: str = ""            # presets: person shirt, tree leaves, house walls, animal body, bird body
    color2: str = ""           # presets: person skin, tree trunk, house roof, animal markings, bird wings
    hidden: bool = False       # starts invisible; needs an `appear` effect
    parts: list[Part] = Field(default_factory=list)   # only for preset custom


class Effect(BaseModel):
    type: Literal["appear", "disappear", "move", "scale", "color", "glow", "spin", "ray", "wear"]
    piece: str = ""            # empty only for ray
    start: float = 0.0         # fractions of the action's duration
    end: float = 1.0
    vec: list[float] = Field(default_factory=list)     # move: offset; scale: target multipliers; ray: start point
    vec2: list[float] = Field(default_factory=list)    # ray: end point
    color: str = ""            # color: target; ray: beam colour; wear: lens colour
    amount: float = 1.0        # glow strength; spin turns; ray thickness


class Action(BaseModel):
    name: str
    frames: int
    text: str                  # what the viewer sees, one sentence (the director reads it to choose cue words)
    effects: list[Effect]


class Station(BaseModel):
    id: str
    title: str
    note: str
    ground: Literal["grass", "sand", "snow", "stone", "wood", "water", "soil", "floor"]
    nouns: list[str]           # single spoken words that point at this station
    cutaway: bool = False
    pieces: list[Piece]
    actions: list[Action]


class World(BaseModel):
    title: str
    setting: str               # one sentence describing the whole world
    hero: str                  # id of the station that shows the world as a whole
    stations: list[Station]
    glossary: list[str]        # terms worth a yellow callout, copied from the narration
    motion_words: list[str] = Field(default_factory=list)   # stems of narration words that mean motion or flow (arrows)


PRESET_EXTENT = {"person": 2.0, "tree": 5.0, "house": 7.0, "animal": 3.0, "bird": 2.5}


def extent(p: Piece) -> float:
    """Rough size of a piece in stage units (the framing rule: the camera looks from far away, so what matters must be big enough to read)."""
    if p.preset != "custom":
        return PRESET_EXTENT[p.preset] * p.scale
    sizes = [max(abs(x) for x in part.size) * (1 if part.shape in ("box",) else 2) + max(abs(x) for x in part.pos) for part in p.parts if len(part.size) == 3 and len(part.pos) == 3]
    return (max(sizes) if sizes else 0.0) * p.scale


def _vec(v: list[float], n: int = 3) -> bool:
    return len(v) == n and all(isinstance(x, (int, float)) for x in v)


def check(world: World) -> list[str]:
    """Every reason the renderer or the director could not use this world (empty when it is usable)."""
    problems: list[str] = []
    ids = [s.id for s in world.stations]
    if not MIN_STATIONS <= len(ids) <= MAX_STATIONS:
        problems.append(f"need {MIN_STATIONS} to {MAX_STATIONS} stations including the hero, got {len(ids)}")
    if len(set(ids)) != len(ids):
        problems.append("station ids must be unique")
    if world.hero not in ids:
        problems.append(f"hero {world.hero!r} is not a station id")
    if len({s.ground for s in world.stations}) > 3:
        problems.append("use at most three different grounds in the whole world (two is better): one pastel background family per video")
    if len(world.glossary) > 14 or any(not g.strip() for g in world.glossary):
        problems.append("glossary: at most 14 non-empty terms")
    for st in world.stations:
        hero = st.id == world.hero
        bx, bz = (HERO_X, HERO_Z) if hero else (STAGE_X, STAGE_Z)
        where = f"station {st.id}"
        if not NAME.match(st.id):
            problems.append(f"{where}: id must be lower snake_case")
        if not st.title.strip() or not st.note.strip():
            problems.append(f"{where}: title and note are required")
        if not st.nouns or len(st.nouns) > 14 or any((" " in n.strip() or len(n.strip()) < 3) for n in st.nouns):
            problems.append(f"{where}: nouns are 1 to 14 single words of at least 3 letters")
        if not 1 <= len(st.pieces) <= MAX_PIECES:
            problems.append(f"{where}: 1 to {MAX_PIECES} pieces, got {len(st.pieces)}")
        pids = [p.id for p in st.pieces]
        if len(set(pids)) != len(pids):
            problems.append(f"{where}: piece ids must be unique")
        parts = 0
        appears = {e.piece for a in st.actions for e in a.effects if e.type == "appear"}
        for p in st.pieces:
            at = f"{where} piece {p.id}"
            if not NAME.match(p.id):
                problems.append(f"{at}: id must be lower snake_case")
            if not _vec(p.pos) or abs(p.pos[0]) > bx or abs(p.pos[2]) > bz or not 0 <= p.pos[1] <= MAX_Y:
                problems.append(f"{at}: pos must be [x, y, z] with |x| <= {bx:g}, |z| <= {bz:g}, 0 <= y <= {MAX_Y:g}")
            if not 0.2 <= p.scale <= 4:
                problems.append(f"{at}: scale must be between 0.2 and 4")
            for c in (p.color, p.color2):
                if c and not HEX.match(c):
                    problems.append(f"{at}: colours are #RRGGBB")
            if p.hidden and p.id not in appears:
                problems.append(f"{at}: hidden but no action makes it appear")
            if p.preset == "custom":
                if not 1 <= len(p.parts) <= MAX_PARTS_PER_PIECE:
                    problems.append(f"{at}: a custom piece has 1 to {MAX_PARTS_PER_PIECE} parts")
            elif p.parts:
                problems.append(f"{at}: preset {p.preset} takes no parts")
            parts += len(p.parts)
            for k, part in enumerate(p.parts):
                big, near = (70, 30) if hero else (12, 8)
                if not (_vec(part.size) and all(0.02 <= s <= big for s in part.size) and _vec(part.pos) and all(abs(x) <= near for x in part.pos) and _vec(part.rot)):
                    problems.append(f"{at} part {k}: size 3 values in 0.02..{big}, pos and rot 3 values (pos within {near})")
                if not HEX.match(part.color) or not 0 <= part.opacity <= 1 or not 0 <= part.glow <= 1.5:
                    problems.append(f"{at} part {k}: colour #RRGGBB, opacity 0..1, glow 0..1.5")
        biggest = max((extent(p) for p in st.pieces if len(p.pos) == 3), default=0.0)
        need = 8.0 if hero else 5.0
        if biggest < need:
            problems.append(f"{where}: nothing readable at the camera distance; the biggest piece spans about {biggest:.1f} units and must reach {need:g} (raise scale up to 4"
                            f"{' and use large pieces: the hero is seen from far away' if hero else ''})")
        if parts > MAX_PARTS_PER_STATION:
            problems.append(f"{where}: {parts} parts, at most {MAX_PARTS_PER_STATION} per station")
        if not 1 <= len(st.actions) <= MAX_ACTIONS:
            problems.append(f"{where}: 1 to {MAX_ACTIONS} actions, got {len(st.actions)}")
        names = [a.name for a in st.actions]
        if len(set(names)) != len(names):
            problems.append(f"{where}: action names must be unique")
        for a in st.actions:
            at = f"{where} action {a.name}"
            if not NAME.match(a.name) or not a.text.strip():
                problems.append(f"{at}: lower snake_case name and a description are required")
            if not MIN_FRAMES <= a.frames <= MAX_FRAMES:
                problems.append(f"{at}: frames {MIN_FRAMES} to {MAX_FRAMES}")
            if not 1 <= len(a.effects) <= MAX_EFFECTS:
                problems.append(f"{at}: 1 to {MAX_EFFECTS} effects")
            for e in a.effects:
                problems += _effect(at, e, {p.id: p for p in st.pieces}, bx, bz)
    return problems


def reserved(color: str) -> bool:
    """A saturated red or yellow (reserved by the low-poly recipe for force arrows and term callouts)."""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hi, lo = max(r, g, b), min(r, g, b)
    if hi == 0 or (hi - lo) / hi < 0.5:
        return False
    hue = (60 * ((g - b) / (hi - lo)) % 360) if hi == r else (60 * (2 + (b - r) / (hi - lo))) if hi == g else (60 * (4 + (r - g) / (hi - lo)))
    return hue >= 345 or hue <= 15 or 40 <= hue <= 70


def _effect(at: str, e: Effect, pieces: dict[str, Piece], bx: float, bz: float) -> list[str]:
    out = []
    if not 0 <= e.start < e.end <= 1:
        out.append(f"{at}: effect {e.type} needs 0 <= start < end <= 1")
    if e.type == "ray":
        if e.piece:
            out.append(f"{at}: a ray belongs to no piece (leave piece empty)")
        for v in (e.vec, e.vec2):
            if not (_vec(v) and abs(v[0]) <= bx and abs(v[2]) <= bz and 0 <= v[1] <= MAX_Y):
                out.append(f"{at}: a ray needs vec and vec2 as [x, y, z] inside the stage")
                break
        if not HEX.match(e.color) or not 0.03 <= e.amount <= 0.5:
            out.append(f"{at}: a ray needs a #RRGGBB colour and a thickness (amount) of 0.03 to 0.5")
        elif reserved(e.color):
            out.append(f"{at}: red and yellow are reserved for arrows and callouts; use the content colour, white or pale grey for a ray")
        return out
    if e.piece not in pieces:
        return out + [f"{at}: effect {e.type} names unknown piece {e.piece!r}"]
    if e.type in ("move", "scale") and not _vec(e.vec):
        out.append(f"{at}: {e.type} needs vec with 3 values")
    if e.type == "move" and _vec(e.vec) and any(abs(x) > 14 for x in e.vec):
        out.append(f"{at}: move offsets stay within 14")
    if e.type == "scale" and _vec(e.vec) and any(not 0.02 <= x <= 6 for x in e.vec):
        out.append(f"{at}: scale multipliers are 0.02 to 6")
    if e.type in ("color", "wear") and not HEX.match(e.color):
        out.append(f"{at}: {e.type} needs a #RRGGBB colour")
    if e.type == "wear" and pieces[e.piece].preset != "person":
        out.append(f"{at}: wear only works on a person preset")
    if e.type in ("glow", "spin") and not 0 < e.amount <= 4:
        out.append(f"{at}: {e.type} amount is above 0 and at most 4")
    return out


def to_pack(world: World) -> dict:
    """The director's manifest for this world (same shape as brainrot/world/packs/*.json)."""
    others = [s for s in world.stations if s.id != world.hero]
    nouns: dict[str, str] = {}
    for st in world.stations:
        for n in st.nouns:
            nouns.setdefault(n.strip().lower(), st.id)
    cut = [s.id for s in others if s.cutaway] or [s.id for s in others[:2]]
    hero = next(s for s in world.stations if s.id == world.hero)
    return {
        "id": "generic", "title": world.title, "summary": world.setting, "world": world.setting, "hero": world.hero,
        "stations": [world.hero] + [s.id for s in others],
        "station_notes": {s.id: s.note for s in world.stations},
        "nouns": nouns, "glossary": [g.strip().lower() for g in world.glossary if g.strip()],
        "force_stems": GENERIC_FORCE + [w.strip().lower() for w in world.motion_words if w.strip()],
        "actions": {s.id: {a.name: [a.frames, a.text] for a in s.actions} for s in world.stations},
        "subject": None, "cutaway_stations": cut, "min_cutaways": min(3, len(cut)),
        "opening": {"station_action": hero.actions[0].name}, "max_arrows": 2, "hold_cap": 7.0, "beat_limit": 6.5, "max_move_share": 0.3,
        "term_help": ", ".join(g for g in world.glossary[:10]) + " (copied from the narration; only terms that appear)",
    }
