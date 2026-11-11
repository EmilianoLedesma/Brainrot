"""Web research for a topic: sourced, graded facts that ground the story. Opt-in per job (it browses and costs a long model call).

A local signed-in CLI (Claude or Chat GPT) searches and reads pages through its own web tools; nothing else is enabled. The result is validated here:
every fact must cite sources that exist, every source must be an http(s) URL, and too few facts is an error rather than a thin script. The text handed to
the writer carries each fact's caveat so a correlation is not presented as a cause. Retries reuse the story, so a job never researches twice.
"""
import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel

from . import llm
from .domain.jobs import PermanentError

SKILL = Path(__file__).parent / "skills" / "research" / "SKILL.md"
MIN_FACTS = 6
TIMEOUT_SECONDS = 900
log = logging.getLogger(__name__)


class Source(BaseModel):
    id: str
    title: str
    url: str
    read: str


class Fact(BaseModel):
    text: str
    sources: list[str]
    note: str


class ResearchPack(BaseModel):
    sources: list[Source]
    facts: list[Fact]


def run(topic: str, provider: str | None = None) -> ResearchPack:
    """Research `topic` and return a validated pack. Raises PermanentError with a friendly message when it cannot."""
    guidance = SKILL.read_text(encoding="utf-8").split("---", 2)[-1].strip()
    try:
        pack = llm.generate(guidance, f"Topic: {topic}", ResearchPack, max_tokens=12000, provider=provider, timeout=TIMEOUT_SECONDS, web=True)
    except TimeoutError:
        raise PermanentError("Research took too long. Try again, or turn research off for this video.") from None
    return validate(pack)


def validate(pack: ResearchPack) -> ResearchPack:
    sources = {s.id: s for s in pack.sources if re.match(r"^https?://\S+$", s.url.strip()) and s.id.strip()}
    facts = []
    for fact in pack.facts:
        cited = [i for i in fact.sources if i in sources]
        if fact.text.strip() and cited:
            facts.append(Fact(text=fact.text.strip(), sources=cited, note=fact.note.strip()))
    if len(facts) < MIN_FACTS:
        raise PermanentError("Research found too little reliable material for this topic. Turn research off or try a more specific topic.")
    used = {i for f in facts for i in f.sources}
    return ResearchPack(sources=[s for i, s in sources.items() if i in used], facts=facts)


def context(pack: ResearchPack) -> str:
    """The reference material handed to the writer: facts with their caveats, then the sources."""
    names = {s.id: s for s in pack.sources}
    lines = [f"- {f.text} [{', '.join(f.sources)}]" + (f" (caveat: {f.note})" if f.note else "") for f in pack.facts]
    return ("Facts researched on the web. Use only these as specifics; do not add numbers, studies or anecdotes beyond them. A fact with a caveat must be told "
            "with that limit: a correlation is not a cause, one source is not a consensus.\n" + "\n".join(lines) + "\nSources: "
            + "; ".join(f"[{i}] {s.title} ({s.read})" for i, s in names.items()))


def summary(pack: ResearchPack) -> str:
    """A safe one-line log entry (counts and hosts only, no page text)."""
    hosts = sorted({re.sub(r"^https?://([^/]+).*$", r"\1", s.url) for s in pack.sources})
    return json.dumps({"facts": len(pack.facts), "sources": len(pack.sources), "hosts": hosts[:8]})
