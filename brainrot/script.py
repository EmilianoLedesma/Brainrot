"""Story generation with Claude.

H2 turns a topic into a narration script. H2b feeds a Reddit post through
`rewrite_post` instead, which keeps the events but fixes the telling.
"""

import anthropic
from pydantic import BaseModel

MODEL = "claude-opus-5"

# Roughly 150 spoken words per minute at the default TTS rate, so ~140 words
# lands near the 55s ceiling that all three platforms treat as short-form.
_SHARED = """Write narration to be read aloud over a silent background video, for
an audience scrolling a short-form feed.

Structure every script in three beats:
- Hook: one sentence that makes stopping the scroll feel involuntary. No throat
  clearing, no "in this video", no greeting.
- Body: the actual substance, in the order that keeps a viewer watching.
- Close: land the payoff. Never ask for likes, follows, or comments.

Rules:
- 120-160 words total.
- Plain spoken prose. No headings, emoji, stage directions, or speaker labels.
- Write numbers as words, since this is read by a speech synthesizer.
- Short sentences. A listener cannot re-read a clause they lost."""

STORY_SYSTEM = _SHARED + """

You are given a topic. Write the most interesting true thing about it that a
general audience would not already know."""

REWRITE_SYSTEM = _SHARED + """

You are given a Reddit post. Retell it as narration. Keep every event, the
outcome, and the narrator's point of view intact - you are fixing the telling,
not the story. Cut the rambling, the edits, and the meta commentary. Never
invent events that are not in the post."""


class Story(BaseModel):
    title: str
    script: str


def _generate(system: str, user: str) -> Story:
    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=Story,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined: {response.stop_details}")
    return response.parsed_output


def write_story(topic: str) -> Story:
    return _generate(STORY_SYSTEM, f"Topic: {topic}")


def rewrite_post(title: str, body: str) -> Story:
    return _generate(REWRITE_SYSTEM, f"Title: {title}\n\n{body}")
