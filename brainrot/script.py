"""Story generation through the configured local CLI or explicit API provider.

H2 turns a topic into a narration script. H2b feeds a Reddit post through
`rewrite_post` instead, which keeps the events but fixes the telling.
"""

from pydantic import BaseModel

from . import llm

MODEL = llm.API_MODEL

_BRAINROT_STYLES = (
    "Grounded: straightforward, clear storytelling. No meme slang or absurd comparisons.",
    "Playful: conversational wit, a few jokes and lightly unexpected comparisons. Keep it easy to follow.",
    "Chaotic: punchy meme-fluent delivery, rapid comedic turns and dramatic, obviously exaggerated comparisons.",
    "Unhinged: theatrical overreaction, ridiculous metaphors, escalating jokes and surreal imagery throughout.",
    "Max brainrot: maximal comic absurdity. Turn the topic into an over-the-top miniature epic, with ludicrous "
    "analogies, cartoonish personification and escalating, clearly figurative chaos. Make almost every line a payoff.",
)


def _brainrot_style(level: int | None) -> str:
    if level is None:
        return ""  # Existing jobs and callers retain their original narration style.
    if type(level) is not int or not 0 <= level <= 100:
        raise ValueError("brainrot_level must be an integer from zero to one hundred")
    return (
        f"\n\nBrainrot intensity: {level}/100. This controls the writing style.\n"
        + _BRAINROT_STYLES[min(level // 20, 4)]
        + "\nApply this intensity to both the title and narration. Keep the factual core accurate; "
        "make invented scenarios and hyperbole unmistakably figurative, never new factual claims. "
        "Keep the spoken format and word count above. Do not mention this setting or its numeric score."
    )

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


def _generate(system: str, user: str, provider: str | None = None) -> Story:
    return llm.generate(
        system, user, Story, max_tokens=4000, provider=provider, api_model=MODEL,
    )


def write_story(topic: str, *, provider: str | None = None, brainrot_level: int | None = None) -> Story:
    return _generate(STORY_SYSTEM + _brainrot_style(brainrot_level), f"Topic: {topic}", provider)


def rewrite_post(title: str, body: str, *, provider: str | None = None) -> Story:
    return _generate(REWRITE_SYSTEM, f"Title: {title}\n\n{body}", provider)
