# Brainrot

### Create, review, and publish short-form video from one workspace.

[![License: MIT OR Apache-2.0](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-2563eb)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776ab)](.python-version)
[![React + Vite](https://img.shields.io/badge/dashboard-React%20%2B%20Vite-646cff)](web/package.json)

Turn a topic, a longer YouTube video, or an approved Reddit story into a vertical
video. Shape the narration, follow generation progress, review the result, and
manage publishing without leaving the dashboard.

**Your local worker. Your media library. Your publishing choices.**

[Quick start](#quick-start) · [Features](#features) · [Integrations](#integrations) · [Documentation](docs/index.md) · [License](#license)

---

## The workspace

Brainrot brings the content workflow together: **create → generate → review → publish → learn**.

| Start with | Brainrot produces |
| --- | --- |
| **A topic** | An original narrated story with paced speech, timed captions, and a vertical render. |
| **A YouTube video** | Selected moments with the source speech, face-tracked framing, and captions. |
| **A Reddit story** | A faithful retelling from approved API access, followed by the narrated-video pipeline. |

Finished narration and videos are checked against a **90–180-second** duration
range. Generated scripts aim for **280–380 words** at a natural pace.

## Features

| Capability | What you can do |
| --- | --- |
| **Choose your writing provider** | Select **Claude** or **Chat GPT** per job using your local CLI sign-in. |
| **Control the tone** | Move through Grounded, Playful, Chaotic, Unhinged, and Max brainrot. Factual topics stay factual; explicit fiction stays inside its premise. |
| **Create captioned videos** | Combine natural narration, timed captions, and rotating background clips. |
| **Try motion graphics** | Choose an experimental Remotion edit for generated stories, with keyword animations and narration-based visual devices. |
| **Follow every job** | Inspect stages, timing, errors, saved narration, and finished videos. Retry from saved progress. |
| **Control YouTube publishing** | Choose review, automatic publishing, or off, with a selected channel and privacy settings. |
| **Review performance** | Explore available YouTube metrics and retention reports alongside the video. Import retention CSVs and timed subtitles for local analysis. |
| **Bring your media** | Manage backgrounds and optional reference assets through the library. |
| **Switch computers deliberately** | Use independent local checkouts, a shared Supabase project, and verified media export/import. |

> **Motion graphics is experimental.** The runtime option uses reusable templates;
> the hand-built films in [`experiments/`](experiments/remotion-explainer/README.md)
> demonstrate richer editing. Live model-driven scene planning still needs validation.

## How it works

1. **Create a job.** Choose an input, provider, tone, and publishing settings.
2. **Generate locally.** The worker prepares the content, creates or reuses saved stages, and renders the video.
3. **Review the output.** Open playback, narration, metadata, and execution details in the shared inspector.
4. **Publish and learn.** Approve a YouTube draft or use the job's automatic setting, then review available performance data.

Generation and publishing have separate states. A finished video can be ready to
review while a platform upload is still scheduled or needs credentials.

## Quick start

### 1. Install the prerequisites

- **Git** and **Python** to clone the project and run setup.
- **uv** for the locked Python environment; bootstrap selects Python 3.14.
- **Node.js 24 and npm** for the dashboard and motion renderer.
- **FFmpeg and ffprobe** on your worker's PATH.
- A **Supabase project** and a signed-in **Codex or Claude Code CLI**.

### 2. Clone and bootstrap

```sh
git clone https://github.com/EmilianoLedesma/Brainrot.git brainrot
cd brainrot
python scripts/bootstrap.py
```

Bootstrap installs the locked Python and npm dependencies and creates missing
settings templates. Existing settings are preserved.

### 3. Connect your project

Apply every unapplied SQL file in [`migrations/`](migrations/) in filename order
through the Supabase SQL editor. Bootstrap does not apply database migrations.

Edit the generated root `.env` using [`.env.example`](.env.example) as the reference:

| Setting | Purpose |
| --- | --- |
| `SUPABASE_URL` | Your Supabase project URL. |
| `SUPABASE_SERVICE_KEY` | Server-side database access. Keep it private. |
| `DASHBOARD_API_KEY` | Shared dashboard/API secret; bootstrap generates one for a new settings file. |
| `BRAINROT_LLM_PROVIDER` | `codex` for Chat GPT or `claude-code` for Claude. |

Sign in to the selected CLI on the computer that will run the worker. Job-level
provider choices override the configured default. Provider limits still apply;
Brainrot does not automatically switch providers or opt into a paid API.

For generated stories using background clips, add footage you have permission to use:

```sh
uv run --locked python -m brainrot.cli add-background background.mp4
```

Reddit access and platform publishing have additional credentials. Set them up
only for the integrations you intend to use: [integration guide](docs/integrations.md).

### 4. Check and launch

```sh
uv run --locked python -m brainrot.dev --check
uv run --locked python -m brainrot.cli doctor --check-media
uv run --locked python -m brainrot.dev
```

| Service | Local address |
| --- | --- |
| **Dashboard** | [localhost:5173](http://localhost:5173) |
| **API** | [127.0.0.1:8001](http://127.0.0.1:8001) |

The launcher runs the dashboard, API, and worker together. Use **Ctrl+C** to stop
them. Open **Workspace → New job** to create your first video.

For a second computer or an existing shared project, follow the
[computer-switching guide](docs/moving-between-computers.md) before starting a worker.

## Integrations

| Integration | Current scope |
| --- | --- |
| **Chat GPT / Codex** | Local subscription-backed CLI for generation and selection. |
| **Claude Code** | Local subscription-backed CLI; an Anthropic API path is available only when explicitly configured. |
| **YouTube** | OAuth connection, metadata drafts, review/automatic upload choices, and performance ingestion. |
| **TikTok & Instagram** | Publishing adapters require separate credentials and platform setup. |
| **Reddit** | Approved API access for story discovery and retelling. |
| **Supabase** | Job state, saved content records, publishing settings, and analytics. |

Connecting YouTube alone does not publish an old backlog. Each job keeps its
own publishing choice and channel binding. Missing platform credentials leave
publications scheduled. See [integrations](docs/integrations.md) for setup and limits.

## Local media and deployment

Brainrot runs locally with a cloud database. Generated media stays under the
ignored `media/` directory by default; database records store portable paths.
Git does not synchronize videos, backgrounds, credentials, or model caches.

A verified export/import transfers media when you switch computers. One active
local-media computer consumes the shared queue at a time.
[Read the handoff workflow →](docs/moving-between-computers.md)

The dashboard can be deployed separately, including to Vercel. The API and
generation worker need their own running host. Keep the dashboard private:
its shared API credential is included in the browser build.
[Deployment guide →](docs/deployment.md)

## Development

```sh
# Offline test suite; SQL tests need local PostgreSQL
uv run --locked python -m pytest tests -q

# Offline pipeline and FFmpeg self-checks
uv run --locked python -m scripts.checks.pipeline

# Dashboard build and motion TypeScript check
npm run build --prefix web
npm run check --prefix motion
```

SQL tests use disposable local databases. Configure `PG_BIN` or put `pg_ctl` on
PATH, and check for skipped tests before treating a run as database validation.
Live database checks are separate operator actions.
[Development and browser checks →](docs/agents/development.md)

### Repository map

```text
brainrot/       Python API, worker, pipelines, and runtime guidance
web/            React + Vite dashboard
motion/         Runtime Remotion compositions and bundled assets
migrations/     Ordered database migrations
tests/          Unit, integration, SQL, and browser checks
scripts/        Bootstrap, source packaging, and explicit operator checks
requirements/   Hash-pinned pip exports and compatibility entrypoints
experiments/    Standalone animation prototypes and reference studies
docs/           Setup, operations, architecture, and product decisions
```

## Documentation

| I want to… | Start here |
| --- | --- |
| Set up or move to another computer | [Local setup and media handoff](docs/moving-between-computers.md) |
| Connect publishing and content sources | [Integrations](docs/integrations.md) |
| Understand the generation flow | [Architecture](docs/agents/architecture.md) |
| Tune storytelling and evaluate scripts | [Storytelling](docs/storytelling.md) |
| Inspect retention and content quality | [Content quality](docs/content-quality.md) |
| Troubleshoot jobs, retries, and uploads | [Operations](docs/operations.md) |
| Look up pipeline behavior and operator commands | [Pipeline reference](docs/pipeline-reference.md) |
| Explore the animation prototypes | [Remotion experiment](experiments/remotion-explainer/README.md) |
| Prepare a source upload | [GitHub upload guide](docs/distribution/github-upload.md) |
| Run setup and operator checks | [Script commands](scripts/README.md) |

[Browse all documentation →](docs/index.md)

### Contributing

Start with [AGENTS.md](AGENTS.md), the [development guide](docs/agents/development.md),
and the [current handoff](docs/agents/handoff.md). Keep runtime functionality and
guidance in the repository so another computer can reproduce the workflow.

## License

Brainrot's original software and documentation are available under
**[MIT](LICENSE-MIT) OR [Apache 2.0](LICENSE-APACHE)**, at your choice.
See [LICENSE](LICENSE) for the grant and [NOTICE](NOTICE) for attribution.

**Created by Emiliano Ledesma and contributors.**

Bundled fonts, third-party software, and imported media keep their respective
licenses. See [third-party notices](docs/distribution/third-party-notices.md).

