# Deployment

## Vercel dashboard

The repository contains both Python and Vite. Vercel's automatic FastAPI
detection finds `brainrot/api.py`, but that module is outside its default
entrypoint locations. The failed build for `dd4d1e4` stopped at this detection
step with "No FastAPI entrypoint found".

The root `vercel.json` explicitly selects the dashboard build:

| Setting | Value |
|---|---|
| Root Directory in Vercel | Repository root (leave empty) |
| Framework | `vite` |
| Install Command | `npm ci --prefix web` |
| Build Command | `npm run build --prefix web` |
| Output Directory | `web/dist` |

The framework and commands in the file override the corresponding project
settings. See [Vercel's configuration reference](https://vercel.com/docs/project-configuration/vercel-json).
The app uses hash routes, so it needs no SPA rewrite rule.

Set these build-time environment variables for each Vercel environment that
will use Workspace:

- `VITE_API_URL`: the separately hosted HTTPS API origin, without a trailing slash.
- `VITE_API_KEY`: the same shared secret as the API's `DASHBOARD_API_KEY`.

Vite embeds these values into the browser bundle. Keep Workspace deployments
private using Vercel Deployment Protection, as required by the existing shared
secret design. Keep Supabase service-role and platform credentials on the API
and worker hosts.

After changing Vite environment variables, rebuild the deployment. The local
`web/.env` is gitignored and does not configure Git-triggered builds.

To validate the same commands locally, run from the repository root:

```sh
npm ci --prefix web
npm run build --prefix web
```

Push changes to the PR branch to trigger a preview. A passing local build does
not establish that the Vercel preview is ready; check its deployment status too.

## API and worker

Run FastAPI and the long-running media worker separately from the static
dashboard, with the server-side environment variables in `.env.example`.
Configure `DASHBOARD_ORIGINS` with the exact dashboard origins allowed to call
the API, separated by commas. Preview origins need to be allowed explicitly.

Apply migrations in order before starting the matching worker version.
`002_job_execution.sql` is required for leased execution, and
`003_stage_execution.sql` is required for stage tracking. Both migrations were
applied to the configured Supabase project on 2026-10-21 and validated with
rolled-back lease and stage smoke tests plus REST schema/RPC checks. The
existing pending job was left unchanged.

H2/H2b require an active background clip. H1 requires the YuNet face model at
`models/face_detection_yunet_2023mar.onnx` in the media bucket; the repository
still has no model-upload command. OAuth consent and platform credentials are
also manual setup steps.
