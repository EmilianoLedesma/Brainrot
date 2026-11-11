"""Topic ideas for the Tools menu: five "how X works" / "what if" prompts about everyday things."""

from pydantic import BaseModel

from . import llm
from .domain.jobs import PermanentError

SYSTEM = """You suggest topics for 90-180 second explainer videos for a short-form feed.

Return exactly five topics. Each follows one of two formats:
- How X works: "How does/do X work?" about something people use every day, where X is a common object or system.
- What if: a "what if ..." thought experiment about a common object, habit or system.

Rules:
- Subjects must be familiar: household items, food, phones, transport, money, sleep, weather, school, work.
- Mix both formats; use each at least twice.
- Each topic is one sentence of at most twelve words, specific enough to write a story from.
- Real-world and answerable. No celebrities, no politics, no medical or financial advice.
- Write in the requested language, including the "how does ... work" / "what if" wording.
- Never repeat or closely paraphrase a topic from the avoid list."""


class Ideas(BaseModel):
    topics: list[str]


def suggest(language: str = "en", avoid: list[str] | None = None, provider: str | None = None) -> list[str]:
    avoid = [a.strip() for a in (avoid or []) if a.strip()][:20]
    user = f"Language: {'Spanish' if language == 'es' else 'English'}\nAvoid list:\n" + ("\n".join(f"- {a}" for a in avoid) or "(empty)")
    out = llm.generate(SYSTEM, user, Ideas, max_tokens=800, provider=provider, timeout=120, tier="standard")
    seen, topics = {a.lower() for a in avoid}, []
    for topic in out.topics:
        topic = topic.strip()
        if topic and topic.lower() not in seen:
            seen.add(topic.lower())
            topics.append(topic[:200])
    if not topics:
        raise PermanentError("The model returned no usable topics")
    return topics[:5]
