# Portable integrations and YouTube

Everything required by the app is in this repository: Python adapters, UI flows,
storytelling guidance, SQL migration, configuration examples, and tests. API calls
run in the backend. Generation still runs in isolated local Claude Code or Codex
sessions with tools disabled; it receives selected reference data as source material.

## Move to another computer

1. Clone the repository and install `requirements.txt` and the frontend dependencies.
2. Install FFmpeg/ffprobe. Sign in to the local generation CLI you intend to use.
3. Copy `.env` and `web/.env` securely, or populate them from the tracked examples.
   Set `VITE_API_URL` to that computer's API address. These files are never committed.
4. Copy the entire `media/` folder. Alternatively, configure `BRAINROT_MEDIA_ROOT`
   to a shared data directory available to the API and worker. Relative roots are
   resolved against the repository, independently of the shell's working directory.
5. Keep using the same Supabase project, or apply all migrations in order to a new
   project. Existing projects need `010_publication_metadata.sql`,
   `011_library_activation.sql`, `012_youtube_metadata_drafts.sql`, and
   `013_youtube_performance.sql` once.
6. Run `python -m brainrot.cli doctor` to check local configuration without printing secrets.

Relative database paths do not transfer files. Two workers on different computers
need the same media files or a shared data folder. A copied Git repository alone
does not include ignored media or credentials. The API host must be able to read
the files written by its worker. Run persistent media storage on your own machine
or a host with persistent disk; a frontend-only Vercel deployment cannot store it.

`BRAINROT_MEDIA_STORAGE=local` is the default. New writes are atomic local files,
never Supabase uploads. Existing cloud objects are cached locally on first access.
`python -m brainrot.cli sync-media` copies referenced existing cloud media in advance
without deleting its cloud originals. Explicitly set `BRAINROT_MEDIA_STORAGE=supabase`
to retain the old cloud-write behavior. Local deletion cleans output and subtitle
files and queues removal of legacy cloud copies through the existing cleanup outbox.

Playback uses expiring, path-specific signed links, including byte-range support.
The dashboard key is not embedded in those links. User-supplied absolute paths,
parent traversal, backslashes, and symlink escapes are rejected.

## Research

Workspace → Tools → Research searches Wikidata. Choose an entity, inspect its
facts and source URLs, then use it for a new story. The backend fetches and stores
a reference snapshot inside the job parameters when creating the job. Retried
jobs reuse their saved script. References are optional; unreferenced claims are
marked unverified. They do not turn fictional premises into debunking requests.

The root `.mcp.json` configures the read-only Wikidata MCP for interactive Claude
project sessions. `config/codex-mcp.example.toml` is an optional project-local Codex
configuration example ([official Codex configuration documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)). Neither is a global installation or a runtime dependency
of the app's generation pipeline.

## Media library

Workspace → Tools → Media library searches NASA videos without a key or Pexels
videos with the optional free `PEXELS_API_KEY`. Save a video locally, then explicitly
add it to rotation. Importing alone does not alter the background pool.

Source URL, creator credit, and usage-information URL are stored in portable JSON
sidecars beneath `media/library/`. Background video files use relative paths under
`media/backgrounds/`. Imports accept provider IDs, not arbitrary download URLs;
downloads are restricted to known HTTPS provider hosts, bounded to 200 MB, and
validated with ffprobe. Review each asset's source and applicable usage conditions.
Pexels attribution is displayed in the app. Copy the media folder to retain provenance.

## YouTube: guided setup

Workspace → YouTube contains the setup steps and the exact callback URI. The app
does not request your Google password.

1. Open [Google Cloud Console](https://console.cloud.google.com/apis/dashboard)
   and create/select your project.
2. Enable **YouTube Data API v3** and **YouTube Analytics API** for that project.
3. Configure Google Auth Platform/OAuth consent (branding and audience). While
   in testing, add the Google account that owns your channel as a test user.
4. Create an OAuth **Web application** client. Add this authorized redirect URI:
   `http://127.0.0.1:8001/youtube/callback`. If changing it, register the exact new
   URI in Google and set `YOUTUBE_REDIRECT_URI` to the same value.
5. Put `YOUTUBE_CLIENT_ID` and `YOUTUBE_CLIENT_SECRET` in the project's `.env`,
   then restart the API. Never commit them or paste them into chat.
6. In YouTube, refresh status, select Connect YouTube, then open Google sign-in.
   Choose your channel-owning account and grant upload, read, and analytics access.
7. Return to the app and refresh status. The connected channel's name is shown.

OAuth uses PKCE and ten-minute, one-use server-side state under ignored `.brainrot/`.
Callback codes are redacted from API access logs. Refresh tokens stay in the existing
RLS-protected credentials table; OAuth client secrets remain in `.env`. Each computer
using that connection needs the same client configuration. Disconnect removes the
app's stored connection; Google account permissions can also be revoked in Google.

Connecting leaves `auto_publish` off and defaults new reviewed uploads to **private**.
It never uploads the existing queue simply because consent was granted. Existing
legacy credentials retain their prior automation behavior until replaced by this flow.

### Upload a Short

New Job includes an always-visible **YouTube Shorts publishing** section alongside
the topic/source and model. Choose review before uploading (default), automatic
upload, or generate without a YouTube upload. Visibility and audience/synthetic
declarations are included in the job review and saved with its parameters.
Automatic mode requires a connected channel and is bound to that channel by the
server. That job's due outputs upload even when the legacy global default is off;
review mode stays held even if the global default is on. Switching channels does
not silently redirect a job's automatic uploads. These choices only control YouTube.

Review-mode videos retain their visibility/declarations when opened in the
YouTube upload preview. Jobs choosing no YouTube upload create no YouTube
publication; they can still be uploaded manually later. Jobs created without
these fields (for example by older CLI clients) retain the existing defaults.

Choosing a finished video automatically drafts its title, description, hashtags,
and tags with the video's job-selected writing provider. The repo-owned
[Shorts publishing skill](../brainrot/skills/youtube-shorts-publishing/SKILL.md)
is passed explicitly to the isolated CLI; no global plugin installation is needed.
The draft uses that chapter's narration or that clip's transcript interval, in
the narration's language, and appends saved source credits. Review or edit any
field, or choose **Regenerate upload details** for another draft. If generation
fails, manual editing remains available. This does not change the spoken title.

Drafts are cached in `youtube_metadata_drafts` (migration
`012_youtube_metadata_drafts.sql`) and deleted with their target/job. Changes to
the narration, provider, or publishing skill invalidate the cache. Previewing
never creates an upload claim. Automatic publishing uses the same generator
when an upload has no reviewed title and saves its metadata before transmission;
reviewed fields are preserved. Connecting a channel still leaves automation off.

In YouTube, choose a finished output, edit title/description/tags/visibility and
the audience/synthetic-content declarations, review
the video and channel, then upload. Metadata choices are saved before transmission.
The existing publication claim prevents the worker or a second click from uploading
the same target simultaneously. Already-published targets return the existing result.
Failures with ambiguous outcomes stay failed: inspect YouTube Studio before retrying.
The activity view shows progress and the resulting YouTube link.

Uploads use YouTube's resumable-upload protocol. Interrupted uploads are not blindly
repeated; automatic session recovery is not implemented. A process crash can leave
an uploading row needing operator reconciliation with YouTube Studio.

YouTube categorizes qualifying square/vertical videos up to three minutes as Shorts.
The app's finished videos remain 90–180 seconds. The app explicitly defaults to
private uploads; choose the visibility you want during review.
See [upload guidance](https://developers.google.com/youtube/v3/guides/uploading_a_video)
and [Shorts eligibility](https://support.google.com/youtube/answer/15424877).

### Channel retention

The YouTube page also shows performance for videos published by this app: views,
engaged views, likes, comments, and average percentage watched. **Sync video
performance** requests eligible updates. The worker checks hourly, with each
publication eligible once every six hours. Each pass processes at most ten
videos, oldest checks first; missing reports and failed requests are throttled.
Reports cover publication date through yesterday and may lag behind Studio.

Raw YouTube metrics are kept on the publication (`analytics`); chapter averages
also enter `chapter_metrics` for the existing pacing policy. No views/engaged
views or an absent report cannot create zero-retention pacing evidence. For
rewatches above 100%, the raw value is preserved in the report and only the
policy input is capped at 100%. Average percentage watched is not a completion
rate. Pacing uses each platform's latest snapshot, then the best of those values,
rather than the highest historical observation forever. No-data fallback remains.

### Automatic uploads

Open **Automatic uploads** on the YouTube page to enable/disable worker uploads
and choose their visibility for jobs without per-job choices. This panel is
always expanded. New Job choices take precedence. Saving an enable action covers newly queued videos
by default; including the existing queue requires checking the explicit option.
The worker uses generated Shorts metadata for unreviewed uploads. Reviewed titles
and descriptions remain authoritative. Disabling stops new claims; an upload
already transmitting continues. Connecting alone never enables automation.

YouTube analytics and upload work are independent: unavailable analytics cannot
stop publishing or change publication status. These controls do not enable TikTok
or Instagram, which still need their own platform credentials.

Load channel videos, select one and a date range, then open retention in Insights.
YouTube watch ratios and elapsed-time fractions are converted explicitly. The
report identifies its actual first observed sample; it does not fabricate data at
time zero. Recent videos may not yet have enough analytics. Stored local SRT
sidecars for new generated videos provide matching spoken excerpts when available.
CSV import continues to work without a Google connection.

### Other publishing platforms

YouTube and TikTok send file bytes directly and can read local media. Instagram
fetches a video URL itself, so it requires a publicly reachable API configured with
`BRAINROT_PUBLIC_API_URL`. A localhost URL is not reachable by Instagram.
