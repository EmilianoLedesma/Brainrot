# Product decisions to preserve

- **Local-first media:** Supabase stores relative paths; new media lives under
  the checkout's ignored `media/` by default. Legacy cloud objects can be cached.
  Git does not synchronize local files. Switching computers is a deliberate
  export/import with one active local-media worker host.
- **Provider choice:** show Claude and Chat GPT, store `claude-code` and `codex`.
  Each computer authenticates its own CLI. No automatic provider or paid API
  fallback. Use Codex for live checks under the current user preference.
- **Premise intent:** ordinary factual topics stay accurate. Explicit absurd
  fiction develops inside its premise rather than reflexively debunking it.
  Brainrot intensity changes delivery and slang; it does not turn facts into
  fabricated events. Reddit retellings preserve the supplied events.
- **Intensity control:** five named steps: Grounded, Playful, Chaotic, Unhinged,
  Max brainrot. Keep the underlying numeric API contract for compatibility.
- **Speech and duration:** begin with a short spoken title, pause, then natural
  narration with thought pauses. Target 280–380 words; measured narration and
  video must each pass 90–180 seconds. Do not pad, truncate or force unnatural
  speed to hide a failed duration check.
- **Backgrounds:** rotate through active clips and retain each story's saved
  selection on retry. The configured project has a five-clip parkour pool;
  do not hard-code a dependency on those particular rows.
- **Queue:** four rows per page; Inspect, Retry and Delete align in one row.
  Confirm deletion, including running jobs. Retry resumes saved progress and
  resets the displayed attempt history; detailed diagnostics remain available.
- **Deletion:** revoke a running job's lease, remove its related records and
  generated media, and prevent late writes. Shared backgrounds remain. Active
  platform uploads block deletion. Remote published posts are not deleted by
  deleting the local job.
- **YouTube:** publishing choices belong in New Job. Respect review/auto/off,
  privacy, audience declarations and the selected channel. Connecting OAuth
  alone must not publish an old backlog. Metadata must match the actual video.
- **Output and Inspect:** share video playback, saved narration, upload details
  and performance/retention tools. Insights is embedded here; do not restore a
  separate top-level Insights tab just because its component still exists.
- **User-facing errors:** short, understandable messages. Raw stack traces,
  upstream URLs and error dumps belong in developer diagnostics.
- **Portability of guidance:** runtime skills live in the repository and are
  explicitly loaded by code. Optional interactive MCP integrations are separate.
  Do not require the author's personal plugin installation to generate content.
