# Working in Brainrot

## Start here

1. Read [agent orientation](docs/agents/README.md) and the dated
   [handoff](docs/agents/handoff.md) before resuming work.
2. Read [architecture](docs/agents/architecture.md) for the affected flow and
   [development](docs/agents/development.md) before starting services or tests.
3. Check `git status --short` and `git branch --show-current`. Preserve existing
   changes. Handoff notes are a snapshot; source, migrations and live inspection
   establish current behavior.

## Project constraints

- Keep functionality and runtime guidance in this repository. Another computer
  must not require plugins, skills or absolute paths from the first user's home.
- Support independent local development with the same Supabase project and a
  deliberate media handoff. Use one active local-media computer at a time.
  Follow [the switching guide](docs/moving-between-computers.md).
- Keep `.env`, credentials, OAuth tokens, CLI login state and private media out
  of Git and diagnostics. Inspect configuration presence without printing values.
- Use **Codex / Chat GPT for live model checks** unless the user changes this
  preference. Keep Claude supported; do not consume its quota for validation.
  Do not silently fall back to another provider or paid API.
- The UI labels are **Claude** and **Chat GPT**; saved provider IDs remain
  `claude-code` and `codex`.
- Preserve user-facing behavior in [product decisions](docs/agents/decisions.md):
  factual versus fictional intent, stepped brainrot controls, natural narration,
  measured 90–180-second videos, friendly errors, and reuse on retry.
- Respect each job's YouTube review/auto/off choice and channel binding. A
  completed generation job is different from a successful platform upload.
  Do not create public uploads or live generation solely as an unrequested test.
- Preserve SQL lease ownership, idempotency, publication claims and deletion
  guards. Fix schema issues with a new additive migration; do not rewrite an
  already-applied migration to change an existing database.
- Keep the current branch unless the user requests otherwise. Do not open a new
  PR. Commit and push when requested; inspect the working tree first.

## Commands

```sh
python scripts/bootstrap.py
uv run --locked python -m brainrot.dev --check
uv run --locked python -m brainrot.cli doctor --check-media
uv run --locked python -m brainrot.dev
```

Dashboard: `http://localhost:5173`; API: `http://127.0.0.1:8001`.
`doctor --check-media` reads the configured database. Do not start another worker
while an existing one is running without checking its host reservation and jobs.

```sh
uv run --locked python -m pytest tests -q
uv run --locked python -m scripts.checks.pipeline
npm run build --prefix web
```

The optional motion-graphics edit needs `npm ci --prefix motion` (bootstrap runs it); its
Remotion project and font live in `motion/`, so another computer needs nothing extra.

SQL tests require local Postgres (`PG_BIN` or `pg_ctl` on PATH). Check for skipped
tests before claiming database validation. Follow the development guide for
browser checks and the separate live database scripts.

## Finish and hand off

Update the dated handoff with completed changes, actual validation, remaining
work and relevant limitations. Update the documentation index when adding docs.
Keep durable architecture and product decisions out of the transient status
section. Never save machine PIDs or secrets in tracked handoff files.

`AGENTS.md` guides repository development. Runtime generation receives only the
explicit skills loaded by application code; it does not automatically inherit
this file or a developer's installed plugins.
