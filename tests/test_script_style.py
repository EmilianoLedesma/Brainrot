import pytest

from brainrot import llm, script


@pytest.mark.parametrize("level,style", [
    (0, "Grounded:"), (19, "Grounded:"), (20, "Playful:"), (35, "Playful:"),
    (40, "Chaotic:"), (59, "Chaotic:"), (60, "Unhinged:"), (79, "Unhinged:"),
    (80, "Max brainrot:"), (100, "Max brainrot:"),
])
def test_intensity_reaches_the_model_prompt_without_changing_the_topic(monkeypatch, level, style):
    calls = []
    def generate(system, user, output, **options):
        calls.append((system, user, options))
        return script.Story(title="Story", script="Narration.")
    monkeypatch.setattr(llm, "generate", generate)
    script.write_story("Roman silver crisis", provider="codex", brainrot_level=level)
    system, user, options = calls[0]
    assert f"Brainrot intensity: {level}/100" in system and style in system
    assert "120-160 words" in system and "factual core accurate" in system
    assert user == "Topic: Roman silver crisis" and options["provider"] == "codex"


def test_legacy_calls_keep_the_original_prompt(monkeypatch):
    prompts = []
    monkeypatch.setattr(script, "_generate", lambda system, user, provider: prompts.append(system))
    script.write_story("Roman silver crisis")
    assert prompts == [script.STORY_SYSTEM]


@pytest.mark.parametrize("value", [-1, 101, 35.5, "50", True, False])
def test_invalid_intensity_never_calls_a_model(monkeypatch, value):
    monkeypatch.setattr(llm, "generate", lambda *args, **kwargs: pytest.fail("invalid model request"))
    with pytest.raises(ValueError):
        script.write_story("Topic", brainrot_level=value)
