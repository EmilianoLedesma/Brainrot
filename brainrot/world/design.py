"""The design stage: from the topic and the finished script, the model designs the world (stations, pieces, actions) as validated data.

It runs after the script exists and before narration, so a topic the world cannot represent fails in minutes, not after TTS. The model asks for the strong tier. A design with
problems is sent back once with the validator's list; a second failure stops the job with a friendly error (never a silent switch to another edit). Designs are cached on this
computer under out/world-designs/, keyed by topic and script, so a retry never pays for the design twice.
"""
import hashlib
import json
import logging
from pathlib import Path

from .. import llm
from ..config import PROJECT_ROOT
from ..domain.jobs import PermanentError
from . import spec

SKILL = Path(__file__).parent.parent / "skills" / "world-design" / "SKILL.md"
CACHE = PROJECT_ROOT / "out" / "world-designs"
TIMEOUT_SECONDS = 900
log = logging.getLogger(__name__)


def guidance() -> str:
    return SKILL.read_text(encoding="utf-8").split("---", 2)[-1].strip()


def _ask(user: str, provider: str | None) -> spec.World:
    try:
        return llm.generate(guidance(), user, spec.World, max_tokens=16000, provider=provider, timeout=TIMEOUT_SECONDS, tier="strong")
    except TimeoutError:
        raise PermanentError("Designing the 3D world took too long. Try again, or turn the 3D world off for this video.") from None


def design(topic: str, text: str, provider: str | None = None, facts: str | None = None) -> spec.World:
    """A valid world for this script, or a friendly PermanentError."""
    user = f"Topic: {topic}\n\nScript:\n{text}" + (f"\n\nResearched facts the script rests on:\n{facts}" if facts else "")
    world = _ask(user, provider)
    problems = spec.check(world)
    if problems:
        log.info("world design needs a repair: %d problems", len(problems))
        shown = "\n".join(f"- {p}" for p in problems[:30])
        world = _ask(f"{user}\n\nYour previous answer:\n{world.model_dump_json()}\n\nIt cannot be used. Fix every problem and return the whole world again:\n{shown}", provider)
        problems = spec.check(world)
    if problems:
        log.warning("world design rejected: %s", "; ".join(problems[:5]))
        raise PermanentError("The 3D world for this topic could not be designed reliably. Try again, or turn the 3D world off for this video.")
    return world


def cached(topic: str, text: str, provider: str | None = None, facts: str | None = None) -> spec.World:
    """`design`, reusing the one an earlier attempt of the same topic and script saved."""
    file = CACHE / (hashlib.sha256(json.dumps([topic, text]).encode()).hexdigest()[:24] + ".json")
    try:
        world = spec.World.model_validate_json(file.read_text(encoding="utf-8"))
        if not spec.check(world):
            return world
    except (OSError, ValueError):
        pass
    world = design(topic, text, provider, facts)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        file.write_text(world.model_dump_json(), encoding="utf-8")
    except OSError:
        log.warning("could not cache the world design")
    return world
