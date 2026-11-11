"""Continuous-world director planner for the pothole experiment.

Same machinery as experiments/cpu-lowpoly/planner.py (beats, split_long, validation, snap_boundaries, fill_gaps); this file only supplies the
topic: the stations, the Spanish nouns that map to them, the flow words that justify a red arrow, and the director's guidance.

  PYTHONPATH=. uv run --locked python experiments/pothole-lowpoly/planner.py [--revalidate] [--reuse] [--out PATH]     (from the repository root)
"""
import importlib.util
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("cpu_planner", HERE.parent / "cpu-lowpoly" / "planner.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

# Hero first (the street with the car, houses and trees); exhibits on the sidewalk in the order the narration introduces them.
STATIONS = ["road", "layers", "cracks", "water", "traffic", "pothole", "ice", "repair", "prevent"]
NOUNS = {"carretera": "road", "calle": "road", "camino": "road", "auto": "road", "coche": "road", "carro": "road",
         "asfalto": "layers", "concreto": "layers", "base": "layers", "roca": "layers", "subrasante": "layers", "suelo": "layers", "capas": "layers", "capa": "layers",
         "grieta": "cracks", "grietas": "cracks", "cocodrilo": "cracks", "piel": "cracks",
         "agua": "water", "llanta": "traffic", "llantas": "traffic", "ruedas": "traffic", "rueda": "traffic", "tráfico": "traffic", "trafico": "traffic",
         "bache": "pothole", "baches": "pothole", "trozos": "pothole", "hoyo": "pothole",
         "hielo": "ice", "lentes": "ice", "congelarse": "ice", "congela": "ice", "primavera": "ice", "frío": "ice",
         "parche": "repair", "parches": "repair", "venda": "repair",
         "sellar": "prevent", "drenar": "prevent", "drenaje": "prevent", "grueso": "prevent", "prevenir": "prevent"}
base.HERO = "road"
base.TARGETS = STATIONS
base.NOUN_TARGET = NOUNS
base._NOUNS = {base._plain(k): v for k, v in NOUNS.items()}
base.GLOSSARY = ["asfalto", "base", "subrasante", "grietas", "agua", "bache", "hielo", "lentes", "parche", "sellar", "drenar", "cocodrilo"]
base.FORCE_STEMS = ("empuj", "arrastr", "bombe", "expuls", "arranc", "expand", "congel", "derrit", "rompe", "flex", "entr", "junta", "filtr",
                    "sale", "tira", "fatig", "aflo", "atrap", "pasa", "fluy", "drena", "sell", "esquiv", "hunde")
base.PROVIDER = os.getenv("POTHOLE_PLANNER_PROVIDER", "claude-code")
base.HERE = HERE

base.GUIDANCE = """You direct a silent low-poly explainer about how potholes form, in ONE continuous 3D world with no cuts.
The world is a small town: a street with a car driving along it, houses, trees and utility poles behind it, and grass. In FRONT of the street runs a
sidewalk with one "exhibit" per idea, already placed in the order the narration introduces them. Each exhibit is a cutaway block of road with its own
repeating action. The camera never cuts: at every beat it flies to a station (about one second) and then drifts slowly there. An exhibit is drawn
from the first beat that focuses it, so exhibits accumulate and stay. The street itself has a pothole that the car swerves around; late in the video
it is patched.

Stations (focus targets), in sidewalk order: road (the street with the car, houses, trees and the pothole; the hero), layers (cross-section: asphalt on
top, a base of angular rock, the subgrade soil), cracks (alligator / crocodile-skin cracking from above while a wheel flexes the surface), water
(rain falling into the cracks and pooling above the subgrade), traffic (a wheel pressing a soft spot and squirting water and soil out, the void
growing), pothole (loose chunks plucked out by wheels, leaving a pit), ice (ice lenses expanding between asphalt and base, then thawing and leaving
voids), repair (a patch thrown into the pit and compacted: the "bandage"), prevent (sealing the cracks, a drain, thicker pavement).

Distance of the camera: wide (the station and its surroundings), medium (the exhibit), close (one detail of it).

The narration is split into numbered beats of a few seconds. For each beat return: scene (the number), focus (a station), dist, show (one short
sentence IN SPANISH: what the viewer sees and what moves), events and why (one short reason).

Events (each locked to one spoken word; up to three per beat; times are the cue word's start):
- highlight: a brief neutral pulse on ONE exhibit, no force colour. Use it whenever the narration names a part but nothing moves. target = a station.
- force_arrows: thin red arrows. ONLY when the narration at that word describes real force or directed motion: a wheel pushing, water pushed out and
  carrying soil, soil being eroded, ice expanding, chunks pulled out, a patch being compacted. A part name alone is NOT a force. Never use
  force_arrows just to name a part. target = the station where the arrow is drawn.
- term_callout: a yellow technical term copied from the narration: asfalto, base, subrasante, grietas, cocodrilo, agua, hielo, lentes, bache, parche,
  sellar, drenar. Each term at most ONCE in the video.

HARD RULES (checked after you answer):
1. The first beat is focus road, dist wide: the street, the car swerving around the pothole, the houses.
2. Follow the narration: focus the station of the idea being told; do not jump back and forth. Return to road only when the narration talks about the
   street as a whole, and for the last beat.
3. Every named part the narration says (asfalto, base, subrasante, grietas, agua, llantas, bache, hielo, lentes, parche, sellar, drenar) must get an
   event whose cue is that word or sits within two seconds of it. Prefer highlight for a part that is only named, term_callout the first time a part
   is introduced, force_arrows only for real force.
4. No more than 9 seconds may pass with no event and no change of focus or distance. Vary dist between wide, medium and close across beats on the same
   station instead of repeating one.
5. At most one term_callout may start within any 3 seconds, and no two events may start within one second of each other.
6. Never return filler: every event needs a real cue copied from that beat."""


class Ev(BaseModel):
    kind: Literal["highlight", "force_arrows", "term_callout"]
    cue: str
    term: str
    target: str


class Beat(BaseModel):
    scene: int
    focus: Literal["road", "layers", "cracks", "water", "traffic", "pothole", "ice", "repair", "prevent"]
    dist: Literal["wide", "medium", "close"]
    show: str
    events: list[Ev]
    why: str


class WorldPlan(BaseModel):
    beats: list[Beat]


base.Ev, base.Beat, base.WorldPlan = Ev, Beat, WorldPlan

if __name__ == "__main__":
    base.main()
