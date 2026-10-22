# Handoff — 2026-10-22

Read this with the latest user request and `git status`; this is a dated snapshot,
not a live dashboard. Do not assume another checkout has its credentials, media
or migrations just because this development machine does.

## Current work

The user wants to develop and generate locally from either their main computer
or another computer. They clarified that they do not want a central hosting
redesign. The solution uses independent checkouts, the same Supabase database,
and a verified media transfer when switching. AI-driven video editing is for a
later discussion. Factual storytelling improvements were authorized now.

The current branch is `master`. The user requested committing and pushing this
batch directly on that branch, without a new PR. Check Git status and history for
the exact commit and remote state. The user also requested this root `AGENTS.md`
and agent documentation structure.

## Implemented this session

- Locked Python dependencies, pip exports and Python 3.14 setup; a bootstrap
  script preserves existing settings. A local launcher starts API/worker/Vite
  with matching frontend credentials and origins.
- Checkout-root environment loading, project-local face detector and Whisper
  caches, and a bundled licensed Anton caption font.
- Streaming, checksummed media export/import with path validation, project
  identity checking and conflict protection; paginated missing-media audits.
- Migration 014 and a renewable local-media host reservation prevent updated
  workers on independent computers from consuming one shared queue concurrently.
  The migration is applied to this machine's configured Supabase project.
- Optional factual narrative progression: observation, mechanism/evidence,
  plausible alternative, distinguishing evidence, consequence. No invented
  studies or compulsory debunking. Fiction and source fidelity rules remain.
- A five-minute speech deadline cancels stalled provider streams and uses the
  existing retry policy, preserving saved scripts.
- Fixed mixed-platform scheduling: every bulk publication row includes an empty
  metadata object unless it has platform-specific metadata. Otherwise PostgREST
  filled missing metadata with NULL and violated the database constraint.

## Validation and live state

- Fresh locked Python environment: full offline suite passed **470 tests**.
  SQL tests used disposable local Postgres 18. Scheduling regression coverage
  also passed separately. Frontend production build passed.
- Codex-only factual preview about metal versus wood: 326 words, coherent
  heat-transfer explanation. No Claude usage for live validation.
- Exported and restored the real local media into a separate directory with
  checksum verification. The final snapshot contained 15 files, and all 12
  database-referenced paths were present. This is not an automatic sync service.
- Live API/dashboard smoke passed. A second synthetic host reservation was
  denied while this computer held its reservation.
- The existing job `daac226e-0eed-41c4-a517-89c637fabd17` completed speech and render,
  then exposed the scheduling bug. After the fix, retry reused its saved video
  and completed the generation job. Its original automatic YouTube upload was
  subsequently confirmed **published** in the database. TikTok and Instagram
  remain scheduled without their required credentials. No extra upload was
  created solely as a test. The older failed job
  `46a02463-092b-45b5-a767-5c04f3de3101` was not retried in this recovery; inspect
  its current state before taking further action.
- API and worker were reloaded; frontend remains at `http://localhost:5173`, API
  at `http://127.0.0.1:8001`. Inspect live state and ignored service metadata before
  reusing or stopping processes. No tracked PIDs or credentials belong here.
- Agent/runbook links and documentation-index coverage were checked with no
  broken local links or missing document entries; `git diff --check` passed.

## Remaining work and limits

1. Complete an actual second-computer setup using the
   [handoff guide](../moving-between-computers.md). Tests simulate relocation and
   restoration on Windows; another physical machine and other OSes remain to verify.
2. Pull the updated `master` on the other computer. Transfer credentials securely,
   sign in to the CLI there, and make a fresh
   media export after the last generation. Never copy a venv or `node_modules`.
3. Discuss the desired AI video editor workflow before integrating it. The current
   H2 renderer uses backgrounds and captions, not topic-specific animated diagrams.
   Reference Short reviewed: `https://www.youtube.com/shorts/F7nZV4p5c40`.
4. H1 and approved Reddit H2b end-to-end checks remain separate from successful H2
   generation. H2 topic input does not require Reddit credentials.
5. Interrupted remote upload reconciliation, other platform authorization and
   analytics, and multi-host shared-file processing remain separate future work.
   Prompt checks do not establish improved viewer retention.

The original reliability plan under `docs/superpowers/` is historical. Its old
branches, credential blockers and cloud-only storage assumptions are superseded
by current code and the focused guides linked above.
