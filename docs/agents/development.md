# Local development and verification

Install uv, Node.js 24/npm, FFmpeg/ffprobe and the chosen generation CLI. Use the
[computer handoff guide](../moving-between-computers.md) for credentials and media.
Do not copy virtual environments or `node_modules` between machines.

```sh
python scripts/bootstrap.py
uv run --locked python -m brainrot.cli doctor --check-media
uv run --locked python -m brainrot.dev
```

The launcher starts API `127.0.0.1:8001`, frontend `localhost:5173` and worker;
Ctrl+C stops its children. Service arguments `api`, `web`, `worker` allow separate
terminals. It supplies frontend credentials from root `.env`. Apply unapplied
migrations before starting the matching worker. Setup does not apply SQL.

`pyproject.toml` plus `uv.lock` define Python dependencies; `.python-version`
selects 3.14. `requirements/runtime.lock` and `requirements/dev.lock` are hashed pip
exports, used by the traditional requirements entrypoints. Update all exports
when intentionally changing dependencies. Use `npm ci` with the frontend lock and, for the motion-graphics edit, `npm ci --prefix motion`
(`scripts/bootstrap.py` runs both).

## Validate the affected boundary

```sh
uv run --locked python -m pytest tests -q
uv run --locked python -m scripts.checks.pipeline
npm run build --prefix web
npm run check --prefix motion
git diff --check
```

SQL tests create disposable local databases with every migration. Set `PG_BIN`
to your Postgres binaries when needed. On Windows PowerShell, for example:

```powershell
$env:PG_BIN = 'C:\Program Files\PostgreSQL\18\bin'
uv run --locked python -m pytest tests -q
```

Use your installed version's directory. Ensure database tests ran rather than
skipped: without usable binaries (an old install such as PostgreSQL 9.2 does not
count) about a fifth of the suite skips with "no Postgres binaries". FFmpeg tests check playable audio/video, pauses and caption alignment.

For the browser smoke, start a separate frontend on port 5189, then run
`uv run --locked python tests/browser/check_workspace.py --url http://127.0.0.1:5189`.
It intercepts API requests with synthetic responses. On non-Windows systems,
install Playwright Chromium first. See [operations](../operations.md) for the
live `scripts/checks/database.py` and rollback-only `scripts/checks/live.py` boundaries; they are not part
of routine offline pytest. Never present mocks as real generation or upload checks.

## Existing services and failures

Check listeners, owned process command lines, queue activity and logs before
starting or stopping services. On Windows launch background services hidden and
stop only this checkout's verified processes, including Python launcher children.
Do not stop an unrelated service using a familiar port. This user's development
API uses 8001; keep the registered YouTube callback consistent.

An ignored `out/dev-services/` folder may contain local process metadata and logs;
it is operational scratch, not a portable source of truth. Inspect it afresh.
Never assume recorded PIDs still belong to this app.

HTTP 200 polling is normal. Read job/stage state to diagnose generation errors.
Keep raw diagnostics in developer tools or server logs, never the user-facing
input row. A speech attempt has a five-minute deadline and can retry from its
saved script. For an uncertain remote upload, inspect its outcome before retrying.
