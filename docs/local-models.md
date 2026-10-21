# Local Claude Code and Codex generation

H2 turns a typed topic into a script. H1 selects moments from a transcript, and
H2b rewrites Reddit text. All three use `brainrot/llm.py` for typed generation.
The worker runs the selected CLI noninteractively and validates its JSON against
the existing Story or Moments contract. There is no new pipeline or database migration.

## Select a provider

Set one value in the worker's local `.env`, then restart the worker:

| Value of `BRAINROT_LLM_PROVIDER` | Authentication |
|---|---|
| `claude-code` (default) | Claude Code's own saved Claude subscription login |
| `codex` | Codex's own saved ChatGPT login |
| `anthropic` | Explicit API usage using `ANTHROPIC_API_KEY` |

For local modes, complete the CLI's official login flow yourself:

```sh
claude auth login
claude auth status
codex login
codex login status
```

No account passwords, OAuth tokens or cookies belong in Brainrot's `.env`.
The adapters do not read credential files or implement their own login flow;
authentication stays with the installed CLIs. They check the reported sign-in
method before generation and reject API-key sessions in local mode.

The adapters target your own private worker on the same computer and OS account
as the signed-in CLI. Subscription allowances and account-level extra usage
settings still apply. Disable extra usage in the relevant account if you want
to stay within its included allowance. Brainrot never switches providers or
falls back to API billing on its own.

## Preview and run

```sh
python -m brainrot.cli generate-script "Why octopuses can open jars" --provider claude-code
python -m brainrot.cli generate-script "Why octopuses can open jars" --provider codex
```

The preview prints validated title/script JSON, creates no database job and does
not upload or publish anything. Omit `--provider` to use the environment setting.
It performs a real model request using the selected provider's allowance.

For the full H2 flow, start the API/worker normally, then choose Generate in
Workspace and type a topic. No Reddit credentials are used for that path.
All jobs on that worker use its configured provider. Existing saved scripts and
selected moments are reused on retry, even if the worker's provider setting changes.

## Configuration

| Variable | Default / purpose |
|---|---|
| `BRAINROT_LLM_PROVIDER` | `claude-code` |
| `BRAINROT_LLM_TIMEOUT_SECONDS` | `180`; integer from 1 to 1800 |
| `BRAINROT_CLAUDE_MODEL` | Empty: use the installed CLI's default model |
| `BRAINROT_CODEX_MODEL` | Empty: use the installed CLI's default model |
| `BRAINROT_CLAUDE_BIN` | Empty: find `claude` on PATH |
| `BRAINROT_CODEX_BIN` | Empty: find `codex` on PATH |

Executable overrides are paths or command names, not shell command strings.
On Windows, native binaries launch without a console window. npm-installed
Claude/Codex shims launch their published JavaScript entry through Node, avoiding
shell interpolation. Keep both Node and the selected CLI on the worker's PATH.
Current Claude Code must support `--safe-mode` and `--json-schema`; Codex must
support `--ignore-user-config`, `--ephemeral` and `--output-schema`.

## Execution boundaries

Prompts go through stdin. Each request runs in a fresh temporary directory, with
no project files and only the requested schema/output files for Codex. Temporary
files are removed afterward. Child environments retain OS/login locations and
network certificate/proxy settings, but exclude application secrets and API keys.

Claude uses safe mode, disables built-in tools, MCP configuration and slash
commands, and disables session persistence. Safe mode preserves subscription
authentication; `--bare` would require API authentication and is intentionally
not used.

Codex ignores user configuration for generation, uses a read-only sandbox,
disables shell/app/plugin/subagent tools and web search, and uses ephemeral
sessions. It retains its normal saved CLI authentication. This avoids inheriting
project instructions, unrelated integrations or custom model-provider routing.
Explicitly configure `BRAINROT_CODEX_MODEL` if you need a particular model.

Managed CLI policy can still apply. These controls keep generation scoped to
text output; they do not replace OS account isolation for an exposed server.
Do not expose a subscription-backed worker as a public multi-user service.

Authentication checks have a 20-second timeout. Generation uses the configured
timeout; exceeding it terminates the process tree before reporting a retryable
timeout. Nonzero exits, refusals and missing/invalid JSON fail without automatic
provider fallback. Raw CLI stdout/stderr is not included in saved worker errors,
because it can contain source text or credentials. Check the CLI directly in
your own terminal for detailed login, model-access or quota diagnostics.

## Validation

On 2026-10-21, real topic-to-Story generation passed through the installed
Claude Code Pro session and Codex ChatGPT session. Regression tests also cover
typed moment selection, authentication rejection, secret isolation, malformed
outputs, actual subprocess stdin handling and timeout cleanup.
The preview checks do not establish full video generation or publishing.

## References

- [Claude Code noninteractive mode](https://code.claude.com/docs/en/headless)
- [Claude Code CLI options](https://code.claude.com/docs/en/cli-reference)
- [Claude authentication and credential rules](https://code.claude.com/docs/en/legal-and-compliance#authentication-and-credential-use)
- [Codex structured output and saved authentication](https://learn.chatgpt.com/docs/non-interactive-mode)
- [Codex ChatGPT sign-in](https://learn.chatgpt.com/docs/auth)
