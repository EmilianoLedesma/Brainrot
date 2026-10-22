import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from brainrot import llm, repurpose, script
from brainrot.application.retry import classify
from brainrot.domain.jobs import PermanentError


@pytest.fixture
def local_cli(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "_command", lambda provider: [provider])
    monkeypatch.delenv("BRAINROT_CLAUDE_MODEL", raising=False)
    monkeypatch.delenv("BRAINROT_CODEX_MODEL", raising=False)

    def run(command, *, cwd, env, timeout, prompt=None, merge_stderr=False):
        calls.append((command, prompt, env, cwd))
        if "status" in command:
            return json.dumps({"loggedIn": True, "authMethod": "claude.ai"}) if command[0] == "claude-code" else "Logged in using ChatGPT"
        story = {"title": "An escape", "script": "An octopus opens a jar."}
        if command[0] == "codex":
            Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps(story), encoding="utf-8")
            return ""
        return json.dumps({"type": "result", "subtype": "success", "is_error": False, "structured_output": story})

    monkeypatch.setattr(llm, "_run", run)
    return calls


@pytest.mark.parametrize("provider", ["claude-code", "codex"])
def test_local_generation_validates_json_without_exposing_prompt_or_secrets(provider, local_cli, monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "secret-database-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "secret-api-key")
    monkeypatch.setenv("OPENAI_API_KEY", "secret-openai-key")
    monkeypatch.setenv("CODEX_API_KEY", "secret-codex-key")
    monkeypatch.setenv("DATABASE_URL", "secret-connection")
    topic = 'octopus $(write-something) & "escape"'
    result = script.write_story(topic, provider=provider)
    assert isinstance(result, script.Story) and result.title == "An escape"
    command, prompt, env, directory = local_cli[-1]
    assert topic in prompt and all(topic not in argument for argument in command)
    assert not any(key in env for key in ("SUPABASE_SERVICE_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CODEX_API_KEY", "DATABASE_URL"))
    assert Path(directory).resolve() != Path.cwd().resolve()
    assert not Path(directory).exists()  # Temporary inputs/outputs are removed.


def test_default_provider_is_local_claude_even_when_an_api_key_exists(local_cli, monkeypatch):
    monkeypatch.delenv("BRAINROT_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-be-used")
    script.write_story("topic")
    assert local_cli[-1][0][0] == "claude-code"


@pytest.mark.parametrize("provider", ["claude-code", "codex"])
@pytest.mark.parametrize("retelling", [False, True], ids=["topic", "retelling"])
def test_storytelling_skill_reaches_isolated_cli_in_one_generation(provider, retelling, local_cli, monkeypatch, tmp_path):
    # A skill edit must reach an already-imported module without CLI discovery.
    skill = tmp_path / "SKILL.md"
    skill.write_text("---\nname: editorial-test\ndescription: Test skill\n---\nReward the opening with an earned ending.", encoding="utf-8")
    monkeypatch.setattr(script, "STORYTELLING_SKILL", skill)
    if retelling:
        script.rewrite_post("A source title", "An unchanged outcome.", provider=provider)
    else:
        script.write_story("Roman silver crisis", provider=provider, brainrot_level=100)

    generations = [call for call in local_cli if "status" not in call[0]]
    assert len(generations) == 1
    command, prompt, _, _ = generations[0]
    system = command[command.index("--system-prompt") + 1] if provider == "claude-code" else prompt
    assert "Reward the opening with an earned ending." in system
    assert "name: editorial-test" not in system
    assert "280-380 words" in system
    if retelling:
        assert "Keep every event" in system
        assert "An unchanged outcome." in prompt
    else:
        assert "Brainrot intensity: 100/100" in system
        assert "Factual mode:" in system and "Fictional mode:" in system
        assert "Roman silver crisis" in prompt


def test_codex_is_selectable_in_worker_environment(local_cli, monkeypatch):
    monkeypatch.setenv("BRAINROT_LLM_PROVIDER", "codex")
    script.write_story("topic")
    assert local_cli[-1][0][0] == "codex"


def test_job_selection_overrides_worker_default_and_is_restored_after_failure(local_cli, monkeypatch):
    monkeypatch.setenv("BRAINROT_LLM_PROVIDER", "claude-code")
    with pytest.raises(RuntimeError):
        with llm.using_provider("codex"):
            script.write_story("topic")
            assert local_cli[-1][0][0] == "codex"
            raise RuntimeError("job failed")
    script.write_story("next topic")
    assert local_cli[-1][0][0] == "claude-code"


def test_explicit_preview_selection_overrides_job_scope(local_cli):
    with llm.using_provider("codex"):
        script.write_story("topic", provider="claude-code")
    assert local_cli[-1][0][0] == "claude-code"


def test_codex_schema_is_closed_at_nested_moment_objects(local_cli, monkeypatch):
    original_run = llm._run

    def run(command, **kwargs):
        if "--output-schema" in command:
            schema = json.loads(Path(command[command.index("--output-schema") + 1]).read_text())
            assert schema["additionalProperties"] is False
            assert schema["$defs"]["Moment"]["additionalProperties"] is False
            Path(command[command.index("--output-last-message") + 1]).write_text(json.dumps({
                "moments": [
                    {"start_seconds": 130, "end_seconds": 250, "title": "second", "reason": "complete", "score": 0.5},
                    {"start_seconds": 1, "end_seconds": 101, "title": "first", "reason": "complete", "score": 0.9},
                ],
            }))
            return ""
        return original_run(command, **kwargs)

    monkeypatch.setattr(llm, "_run", run)
    monkeypatch.setenv("BRAINROT_LLM_PROVIDER", "codex")
    assert [moment.title for moment in repurpose.select_moments([{"start": 0, "text": "story"}])] == ["first", "second"]


@pytest.mark.parametrize("output", [
    "not json",
    '{"is_error":true,"result":"private failure"}',
    '{"subtype":"error_max_turns","result":"private failure"}',
    '{"structured_output":{"title":"missing script"}}',
])
def test_bad_claude_output_is_terminal_and_not_returned_in_errors(output, local_cli, monkeypatch):
    original_run = llm._run
    monkeypatch.setattr(llm, "_run", lambda command, **kw: output if "--print" in command else original_run(command, **kw))
    with pytest.raises(PermanentError) as error:
        script.write_story("private topic", provider="claude-code")
    assert classify(error.value) == "permanent"
    assert "private" not in str(error.value)


@pytest.mark.parametrize("provider,status", [
    ("claude-code", '{"loggedIn":false,"authMethod":"none"}'),
    ("claude-code", '{"loggedIn":true,"authMethod":"api_key"}'),
    ("codex", "Logged in using an API key"),
])
def test_local_modes_require_subscription_login_and_never_fall_back(provider, status, local_cli, monkeypatch):
    monkeypatch.setattr(llm, "_run", lambda *args, **kwargs: status)
    with pytest.raises(PermanentError, match="login"):
        script.write_story("topic", provider=provider)


def test_invalid_provider_does_not_start_a_process(monkeypatch):
    runner = Mock()
    monkeypatch.setattr(llm, "_run", runner)
    with pytest.raises(PermanentError, match="BRAINROT_LLM_PROVIDER"):
        script.write_story("topic", provider="unknown")
    runner.assert_not_called()


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "infinity", "not-a-number"])
def test_invalid_timeout_is_a_setup_error(timeout, local_cli, monkeypatch):
    monkeypatch.setenv("BRAINROT_LLM_TIMEOUT_SECONDS", timeout)
    with pytest.raises(PermanentError, match="TIMEOUT"):
        script.write_story("topic", provider="claude-code")


def test_subprocess_errors_do_not_include_raw_cli_output(monkeypatch, tmp_path):
    process = Mock(returncode=1)
    process.communicate.return_value = ("private topic", "private credential")
    monkeypatch.setattr(llm.subprocess, "Popen", Mock(return_value=process))
    with pytest.raises(PermanentError) as error:
        llm._run(["claude"], cwd=tmp_path, env={}, timeout=10, prompt="private topic")
    assert "private" not in str(error.value)


def test_status_capture_includes_codex_stderr(monkeypatch, tmp_path):
    process = Mock(returncode=0)
    process.communicate.return_value = ("Logged in using ChatGPT", None)
    popen = Mock(return_value=process)
    monkeypatch.setattr(llm.subprocess, "Popen", popen)
    assert llm._run(["codex", "login", "status"], cwd=tmp_path, env={}, timeout=10, merge_stderr=True) == "Logged in using ChatGPT"
    assert popen.call_args.kwargs["stderr"] == subprocess.STDOUT


def test_real_process_treats_input_as_data_not_shell_commands(tmp_path):
    source = 'a "quoted" topic with & | $(anything) and espaÃƒÂ±ol'
    result = llm._run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        cwd=tmp_path, env=llm._environment(), timeout=10, prompt=source,
    )
    assert result == source


def test_real_timed_out_process_is_stopped(tmp_path):
    with pytest.raises(TimeoutError):
        llm._run(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=tmp_path, env=llm._environment(), timeout=0.2,
        )


def test_codex_missing_final_answer_is_terminal(local_cli, monkeypatch):
    original_run = llm._run
    monkeypatch.setattr(llm, "_run", lambda command, **kw: "" if "exec" in command else original_run(command, **kw))
    with pytest.raises(PermanentError, match="structured output"):
        script.write_story("topic", provider="codex")


def test_timeout_stops_own_process_tree_and_remains_retryable(monkeypatch, tmp_path):
    process = Mock()
    process.communicate.side_effect = [subprocess.TimeoutExpired(["claude"], 10), ("", "")]
    monkeypatch.setattr(llm.subprocess, "Popen", Mock(return_value=process))
    kill = Mock()
    monkeypatch.setattr(llm, "_kill", kill)
    with pytest.raises(TimeoutError) as error:
        llm._run(["claude"], cwd=tmp_path, env={}, timeout=10, prompt="topic")
    kill.assert_called_once_with(process)
    assert classify(error.value) == "transient"


def test_missing_cli_has_actionable_setup_error(monkeypatch):
    monkeypatch.setattr(llm.shutil, "which", lambda *args: None)
    with pytest.raises(PermanentError, match="install"):
        llm._command("claude-code")


def test_explicit_anthropic_mode_preserves_existing_structured_api(monkeypatch):
    story = script.Story(title="API", script="A story.")
    parse = Mock(return_value=SimpleNamespace(stop_reason="end_turn", parsed_output=story))
    monkeypatch.setattr(llm.anthropic, "Anthropic", lambda: SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    assert script.write_story("topic", provider="anthropic") == story
    assert parse.call_args.kwargs["output_format"] is script.Story


def test_api_refusal_remains_terminal(monkeypatch):
    parse = Mock(return_value=SimpleNamespace(stop_reason="refusal", parsed_output=None))
    monkeypatch.setattr(llm.anthropic, "Anthropic", lambda: SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    with pytest.raises(PermanentError, match="declined"):
        script.write_story("topic", provider="anthropic")
