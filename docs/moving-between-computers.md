# Work locally on another computer

Each computer runs its own frontend, API and worker. Use the same Supabase project
to keep jobs, publishing settings, YouTube connection and analytics. Git carries
the code and storytelling skills; a media archive carries videos, audio, captions,
backgrounds, library credits and downloaded models. Files do not travel through
Supabase automatically when local storage is selected.

Use **one active generation computer at a time**. Migration
`014_local_media_host.sql` prevents updated local workers on different computers
from consuming the shared queue concurrently. Update every checkout before using
this protection; workers from older versions do not participate.

## Set up a computer once

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 24
   with npm, and FFmpeg with ffprobe. Install Codex or Claude Code and sign in on
   that computer. The app does not copy CLI account credentials.
2. Clone this repository, check out the same revision as your other computer,
   and run from the repository root:

   ```sh
   python scripts/bootstrap.py
   ```

   Setup installs Python 3.14 and the versions in `uv.lock`, runs `npm ci` for `web` and `motion`, and
   creates missing settings templates. It preserves existing `.env` files. On
   Windows, `py scripts/bootstrap.py` also works if Python uses the `py` launcher.
   Do not copy `.venv` or `web/node_modules` or `motion/node_modules` between computers.
3. Securely copy your root `.env` from the first computer, or fill in its template.
   Keep the same Supabase project and YouTube OAuth client. Use
   `BRAINROT_MEDIA_STORAGE=local` and `BRAINROT_MEDIA_ROOT=media`; a relative root
   resolves against this checkout, even when the command runs elsewhere. Remove
   machine-specific CLI executable overrides unless they also exist here.
   Never commit settings or put credentials in the media archive.
4. Apply all migrations to a new database, or just unapplied migrations to your
   existing project, in filename order. An existing project through migration 013
   needs `014_local_media_host.sql` once. Applying SQL is separate from bootstrap.

The launcher supplies the frontend's API URL and dashboard key from root `.env`.
You do not need to duplicate the key into `web/.env` when using this launcher.
Google's registered callback remains `http://127.0.0.1:8001/youtube/callback` on
either computer. The connected YouTube account and refreshed tokens live in the
shared database; reconnect only if Google revokes or expires authorization.

## Switch computers

1. Let running generation and uploads finish, then stop the old computer's worker.
   Stop its API too while making the archive, so no one imports or deletes media
   during the copy. With the combined launcher, press Ctrl+C to stop its services.
2. On the computer with the newest files:

   ```sh
   uv run --locked python -m brainrot.cli export-media ../brainrot-handoff.zip
   ```

   Choose a new archive filename each time. The command refuses active jobs or
   uploads. It includes only supported media folders, excludes lock/partial files,
   and records a SHA-256 checksum for every file. It is an ordinary ZIP, **not an
   encrypted backup**; store it privately. It contains no database snapshot.
3. Transfer the archive to the destination computer, pull the same code revision,
   and restore it before starting the worker:

   ```sh
   uv run --locked python -m brainrot.cli import-media ../brainrot-handoff.zip
   uv run --locked python -m brainrot.cli doctor --check-media
   ```

   Import checks the Supabase project identity, paths, sizes and every checksum
   before writing any files. Different existing files cause a refusal. Only use
   `import-media ../brainrot-handoff.zip --overwrite` after deciding that the
   archive is the authoritative copy. Import does not remove extra local files;
   shared database rows determine which outputs the app shows.
4. Start the app:

   ```sh
   uv run --locked python -m brainrot.dev
   ```

   Open **http://localhost:5173**; API: **http://127.0.0.1:8001**. The launcher
   starts all three services from this checkout. `api`, `worker` and `web` are
   optional service arguments for separate terminals. `--check` validates local
   prerequisites without starting services; the worker also audits media against
   database references before taking work.

The old computer's host reservation expires within two minutes of its last
renewal. An interrupted job can retain its job lease for up to ten minutes;
unfinished uploads also block a host switch because their remote outcome needs
review. Do not retry an uncertain upload blindly. Wait for leases or resolve the
interrupted operation instead of running an old worker to bypass the check.

When returning to the first computer, repeat the transfer **from the computer
you last used**. A Git pull alone cannot bring new local videos back. Pending
jobs and saved script progress are already in the shared database; the archive
supplies their corresponding local assets.

## Resources and limits

- Dependencies: `uv.lock` is canonical. `requirements.lock` is a hash-pinned
  runtime export for pip users (`pip install --require-hashes -r requirements.lock`).
  `requirements.txt` points to that export; `requirements-dev.txt` points to the
  corresponding development export. Refresh both exports from `uv.lock` when
  intentionally changing dependencies. Frontend versions come
  from `web/package-lock.json`.
- Captions use the bundled Anton font, independent of installed system fonts.
  Source: [Google Fonts](https://github.com/google/fonts/tree/main/ofl/anton);
  the SIL Open Font License is included beside the font under
  `brainrot/assets/fonts/OFL.txt`.
- H1 downloads and checksum-verifies its pinned OpenCV face detector on demand.
  Whisper downloads its selected model when needed. Both caches now live under
  `media/models/` and travel with the archive. Their first download needs internet.
- Skills and adapted guidance live in `brainrot/skills/` and travel with Git.
  Generation does not depend on plugins installed in the first computer's home
  directory. Install and authenticate the selected model CLI on each computer.
- `sync-media` retrieves older Supabase Storage objects. It cannot retrieve files
  that exist only on another computer's disk. Restore those from its archive.
- FFmpeg builds, GPU availability and model CLI versions can differ across
  systems; the app checks output properties but does not promise identical bytes.
  Local media still requires persistent disk; Vercel hosts the frontend, not the
  local worker or durable videos.
- Speech attempts have a five-minute deadline. A stalled provider stream is
  cancelled and handled by the existing retry policy, preserving the saved script.

Validation includes a fresh locked Python environment, a relocated checkout
configuration test, archive round trips, and real Postgres host-claim tests.
An actual second physical computer still needs the setup and handoff above.
