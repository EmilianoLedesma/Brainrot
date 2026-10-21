"""Story generation through the configured local CLI or explicit API provider.

H2 turns a topic into a narration script. H2b feeds a Reddit post through
`rewrite_post` instead, which keeps the events but fixes the telling.
"""

from pydantic import BaseModel

from . import llm

MODEL = llm.API_MODEL

_BRAINROT_STYLES = (
    "Grounded: straightforward, clear storytelling within the supplied premise. No meme slang or absurd comparisons.",
    "Playful: conversational wit, a few jokes and lightly unexpected comparisons. Keep it easy to follow.",
    "Chaotic: punchy meme-fluent delivery, rapid comedic turns and dramatic comparisons; fictional stories can escalate their events.",
    "Unhinged: theatrical overreaction, ridiculous metaphors and escalating jokes; fictional stories can add surreal events.",
    "Max brainrot: maximal comic absurdity. Turn the topic into an over-the-top miniature epic, with ludicrous "
    "comparisons, cartoonish personification and escalating comic energy. In fictional mode, commit completely "
    "to the premise and invent increasingly ridiculous developments. In factual mode, keep the real events "
    "and explanations intact. Make almost every line a payoff.",
)

_BRAINROT_SLANG = (
    "Internet slang: none. Use standard spoken language without meme expressions or online catchphrases.",
    "Internet slang: light. Use one or two natural internet expressions across the script, such as 'low-key' "
    "or 'plot twist', when they fit the topic.",
    "Internet slang: moderate. Use three to five contextual slang phrases across the hook, body and payoff. "
    "Examples include 'chat', 'cooked', 'lore drop', 'main character energy' and 'skill issue'.",
    "Internet slang: heavy. Use six to nine contextual slang phrases. Lean into meme vocabulary, "
    "such as 'bro', 'no cap', 'NPC energy', 'aura points', 'touch grass' and 'let him cook'.",
    "Internet slang: maximum. Use ten to fourteen contextual slang phrases and make meme language a defining "
    "part of the hook, body and payoff. Mix expressions such as 'chat', 'bro is cooked', 'no cap', "
    "'negative aura', 'NPC behavior', 'skill issue', 'lore drop', 'final boss' and 'let him cook'.",
)


def _brainrot_style(level: int | None) -> str:
    if level is None:
        return ""  # Callers without a level use the base storytelling instructions.
    if type(level) is not int or not 0 <= level <= 100:
        raise ValueError("brainrot_level must be an integer from zero to one hundred")
    band = min(level // 20, 4)
    return (
        f"\n\nBrainrot intensity: {level}/100. This controls absurdity and internet-slang density together.\n"
        + _BRAINROT_STYLES[band]
        + "\n" + _BRAINROT_SLANG[band]
        + "\nChoose varied expressions that make sense in context; the examples are options, not a checklist. "
        "Make them sound natural when read aloud, spell out abbreviations when needed, and match the narration's language."
        + "\nApply this intensity to both the title and narration. Follow the supplied premise at every intensity. "
        "Preserve the intent mode chosen from the topic; intensity never changes factual mode into fictional mode. "
        "For factual topics, increase humor, slang and clearly figurative comparisons while keeping events, "
        "causes, people, dates and explanations accurate. For fictional premises, a lower score means calmer "
        "delivery of the same scenario; at higher scores, invent absurd events and consequences within that world. "
        "Keep the spoken format and word count above. Do not mention this setting or its numeric score."
    )

# Keep narration compact while allowing a spoken headline and natural pauses.
_SHARED = """Write narration to be read aloud over a silent background video, for
an audience scrolling a short-form feed.

Structure every script in three beats:
- Hook: one sentence that makes stopping the scroll feel involuntary. No throat
  clearing, no "in this video", no greeting.
- Body: the actual substance, in the order that keeps a viewer watching.
- Close: land the payoff. Never ask for likes, follows, or comments.

Rules:
- 120-160 words total.
- Put a short, speakable headline of three to eight words in the title field.
  The narrator reads this title first, pauses, then reads the script. Do not
  repeat the title in the script or write a pause instruction into either field.
- Plain spoken prose. No headings, emoji, stage directions, or speaker labels.
- Write numbers as words, since this is read by a speech synthesizer.
- Use natural punctuation for breathing and emphasis. Vary short and medium
  sentences, with clear full stops between ideas; avoid run-on sentences and
  strings of exclamation marks or ellipses. Let the payoff land as its own sentence.
- Short sentences. A listener cannot re-read a clause they lost."""

STORY_SYSTEM = _SHARED + """

You write imaginative short-form entertainment from a topic or story premise.

First infer the user's intent from the topic itself, independently of the
brainrot level. Choose the appropriate mode silently; output only title/script.

Factual mode: ordinary real-world subjects, historical topics, and requests for
explanations should teach an interesting, accurate thing about that subject.
For example, "Rome's silver coin crisis" is a factual history topic, even at
maximum brainrot. Preserve real events, causes and outcomes. Slang, dramatic
delivery and obviously figurative comparisons can grow with intensity; invented
events, fake evidence, fabricated quotes, statistics or conspiracies cannot.
If uncertain about a detail, omit it or qualify it instead of inventing it.
Clickbait wording or a high slider score alone does not imply fictional intent.
When intent is ambiguous, default to factual mode.

Fictional mode: use this when the user supplies an explicitly invented,
impossible or ludicrous story premise, or asks for fiction, fantasy or satire.
For example, "GTA six simulates reality and scientists delay its release to stop
the NPCs outsmarting humanity" is an invented premise to develop as fiction.
Treat the supplied premise as true within its story world. Continue with
confident, committed narration. Preserve its central claim, characters, causes,
and stakes, then build specific events and consequences from them.
The title must commit to the same premise as the body.
Stay inside the story through the final payoff. Do not debate, fact-check,
debunk, or correct that fictional premise, compare it against reality, or end
with an "actually" reveal that cancels the scenario. Avoid disclaimers and
reminders that it is fictional; speak as if living inside the story.

In either mode, choose an angle and payoff specific to this topic. Vary the
opening and development instead of defaulting to a debunking or comparison
template. Never announce the chosen mode in the narration."""

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
