import pytest

from brainrot import llm, script


@pytest.mark.parametrize("level,style,slang", [
    (0, "Grounded:", "none"), (19, "Grounded:", "none"),
    (20, "Playful:", "light"), (35, "Playful:", "light"),
    (40, "Chaotic:", "moderate"), (59, "Chaotic:", "moderate"),
    (60, "Unhinged:", "heavy"), (79, "Unhinged:", "heavy"),
    (80, "Max brainrot:", "maximum"), (100, "Max brainrot:", "maximum"),
])
def test_intensity_reaches_the_model_prompt_without_changing_the_topic(monkeypatch, level, style, slang):
    calls = []
    def generate(system, user, output, **options):
        calls.append((system, user, options))
        return script.Story(title="Story", script="Narration.")
    monkeypatch.setattr(llm, "generate", generate)
    script.write_story("Roman silver crisis", provider="codex", brainrot_level=level)
    system, user, options = calls[0]
    assert f"Brainrot intensity: {level}/100" in system and style in system
    assert f"Internet slang: {slang}." in system
    assert "sound natural when read aloud" in system
    assert "120-160 words" in system and "Follow the supplied premise at every intensity" in system
    assert user == "Topic: Roman silver crisis" and options["provider"] == "codex"


def test_calls_without_intensity_use_the_base_storytelling_prompt(monkeypatch):
    prompts = []
    monkeypatch.setattr(script, "_generate", lambda system, user, provider: prompts.append(system))
    script.write_story("Roman silver crisis")
    assert prompts == [script.STORY_SYSTEM]


@pytest.mark.parametrize("level", [None, 0, 35, 60, 100])
def test_fictional_premise_is_preserved_at_every_intensity(monkeypatch, level):
    premise = (
        "The GTA six release will trigger the apocalypse. Rockstar accidentally programmed "
        "a perfect simulation of reality; scientists delay it to stop the NPCs discovering "
        "they are more intelligent than humanity."
    )
    calls = []

    def generate(system, user, output, **options):
        calls.append((system, user))
        return script.Story(title="The NPCs Have Escaped", script="The scientists missed one update.")

    monkeypatch.setattr(llm, "generate", generate)
    script.write_story(premise, provider="codex", brainrot_level=level)
    system, user = calls[0]
    assert user == f"Topic: {premise}"
    assert "Treat the supplied premise as true within its story world" in system
    assert "Stay inside the story through the final payoff" in system
    assert "The title must commit to the same premise" in system
    assert "most interesting true thing" not in system
    assert "Fictional mode:" in system and "Factual mode:" in system
    if level is not None:
        assert "intensity never changes factual mode into fictional mode" in system


@pytest.mark.parametrize("level", [None, 0, 35, 100])
def test_normal_history_topics_stay_factual_even_at_maximum_intensity(monkeypatch, level):
    calls = []
    monkeypatch.setattr(script, "_generate", lambda system, user, provider: calls.append((system, user)))
    script.write_story("Rome's silver coin crisis", brainrot_level=level)
    system, user = calls[0]
    assert user == "Topic: Rome's silver coin crisis"
    assert "ordinary real-world subjects, historical topics" in system
    assert '"Rome\'s silver coin crisis" is a factual history topic' in system
    assert "When intent is ambiguous, default to factual mode" in system
    assert "a high slider score alone does not imply fictional intent" in system
    assert "fake evidence, fabricated quotes, statistics or conspiracies cannot" in system


def test_reddit_retelling_keeps_source_fidelity_without_topic_invention(monkeypatch):
    calls = []
    monkeypatch.setattr(script, "_generate", lambda system, user, provider: calls.append((system, user)))
    script.rewrite_post("An actual event", "The original story.", provider="codex")
    system, user = calls[0]
    assert "Keep every event" in system
    assert "Never\ninvent events that are not in the post" in system
    assert "Treat the supplied premise as true within its story world" not in system
    assert user == "Title: An actual event\n\nThe original story."


@pytest.mark.parametrize("value", [-1, 101, 35.5, "50", True, False])
def test_invalid_intensity_never_calls_a_model(monkeypatch, value):
    monkeypatch.setattr(llm, "generate", lambda *args, **kwargs: pytest.fail("invalid model request"))
    with pytest.raises(ValueError):
        script.write_story("Topic", brainrot_level=value)
