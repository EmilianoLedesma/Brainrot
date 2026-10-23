# Repository scripts

Run these commands from the repository root. Application commands live under
`python -m brainrot.cli`; these scripts support setup, verification and distribution.

| Command | Purpose |
| --- | --- |
| `python scripts/bootstrap.py` | Install locked Python, dashboard and motion dependencies; create missing settings templates. |
| `python scripts/package_source.py` | Create a source archive in ignored `out/releases/`, checking for private configuration. |
| `uv run --locked python -m scripts.checks.pipeline` | Run offline pipeline and FFmpeg checks. |
| `uv run --locked python -m scripts.checks.database` | Explicit live Supabase REST/Storage check; creates and removes its diagnostic job and media, retaining metric observations. |
| `uv run --locked python -m scripts.checks.live` | Explicit rollback-only SQL check using `DATABASE_URL` and synthetic pipeline execution. |

Routine offline tests use `uv run --locked python -m pytest tests -q`. The live
checks above are separate operator actions and require configured credentials.
See [development](../docs/agents/development.md) and
[operations](../docs/operations.md) for their boundaries.

The canonical Python dependency definition remains `pyproject.toml` and `uv.lock`.
Pip users can install `requirements/runtime.txt` or `requirements/dev.txt`; each
includes its adjacent hashed lockfile. Root license files and platform entrypoints
stay at the root so repository hosting and development tools can discover them.
