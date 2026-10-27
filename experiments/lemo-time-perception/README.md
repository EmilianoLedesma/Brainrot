# Why Your Years Seem to Shrink

A Grounded English **Data Storytelling** film requested with **Claude Opus 5.5**
on 2026-10-27. This task explicitly overrides the usual Codex validation preference;
the application's defaults and `.env` stay unchanged.

The subscription CLI receives `--model claude-opus-5-5` on every live call. Its
sanitized reported-model audit is saved beside the output, and a different
reported model is rejected. There is no Claude API or other-provider fallback.
Claude writes the original Brainrot-guided narration, visual direction and chart
artwork/transformations module (`film/scenes.js`); the source is reviewed before
local execution. The camera/caption/render shell, finishing and verification are
local repository code. The initial full-film code request timed out after 1200 s;
a compact, low-effort request to the same model succeeded instead. It did not
regenerate the saved story, direction or voice.

The voice uses Brainrot's existing edge-tts Guy narration, with measured duration
and exact word boundaries. Utterance caching allows retries of a flaky speech
stream without discarding successful earlier segments. The original script and
voice are reused, not regenerated on render retry.

## Visual and factual design

One continuous cream paper world, acting red–blue pencil, handwritten pinned
notes, count charts, chart-operation transformations and motivated camera moves.
No progress bar, persistent upper header, branding or slideshow. Bottom spoken
captions remain. Newsreader, Caveat and IBM Plex Mono are self-hosted with OFL
notices and source hashes.

The numerical inputs in [dataset.json](dataset.json) are study sample/design
counts, not memory quantities or time-speed outcomes. Memory landmarks and
routine are illustrated as a possible account; those sketches are labelled
illustration, without an invented measurement axis. No synthetic age curve,
individual participants, brain scan or causal percentage is generated. The
research caveat is part of the spoken script. See [FACTS.md](FACTS.md).

The last direction beat is retimed to the start of the concluding paragraph,
instead of its final four words, so the final chart operation has time to read.
Speech stays unchanged. The engine's hard-coded landscape camera/buffers require
a vertical wrapper; upstream code remains unchanged and hash-verified.

## Outputs and scope

Ignored local artifacts live in `out/lemo-time-perception/`: final MP4, SRT,
poster/player, saved script/voice/words, direction, timed chart data, provider
audit, authored-source notes, source review, render/check logs and contact sheets.
These must be transferred separately to another computer. No queue, database,
worker, platform upload or global plugin is involved. This is an authored film,
not a new autonomous dashboard mode or a viewer-retention experiment.

## Reproduction

Bootstrap Brainrot, sign in to Claude Code with a subscription that supports the
specified model, and install the coffee experiment's locked local browser/audio
dependencies as documented in [its guide](../coffee-comparison/README.md).
The new selected style/engine and fonts are bundled here with notices/hashes;
no developer-home installation is needed.

```sh
uv run --locked python experiments/lemo-time-perception/run.py prepare
uv run --locked python experiments/lemo-time-perception/run.py direct
uv run --locked python experiments/lemo-time-perception/run.py author-compact
# Review film/film.js and record its SHA256 in out/.../source-review.json first.
uv run --locked python experiments/lemo-time-perception/run.py build
uv run --locked python experiments/lemo-time-perception/run.py produce
```

Source review is a local code-review record by the implementing agent, not an
extra user-approval requirement. `build` refuses a source hash that differs from
that reviewed record (both the shell and chart layer). It validates exact spoken cues and runs actual style
frames, text reading-time checks and event export. Cached raw renders must be
archived deliberately before rendering changed picture code.

```sh
# Windows; use .venv/bin/python on Unix
experiments/coffee-comparison/.venv/Scripts/python experiments/lemo-time-perception/verify.py
uv run --locked python experiments/lemo-time-perception/run.py playback
```

Actual-file checks cover full decode, duration, dimensions, codecs, size, black
intervals, loudness, model audit, timeline/action sheets and complete normal-speed
browser playback. These checks do not establish a full sensory watch/listen or
audience performance. [TREATMENT.md](TREATMENT.md) and [CREDITS](CREDITS) record the
original approach and attribution.

Lemo code/docs are MIT, pinned to
`413a6bd6d78ebd3bdd5abaec9538a26867f890df`. Demo movies, climate data, artwork,
story and music are not reused. The selected engine/reference was read after
the original treatment was written.

The reviewed source includes small local edits to Opus's labels, a clearer
negative-result annotation, readable sampling-group reveals and the vertical
wrapper. The initial Windows dataset read used the default encoding; it was
corrected to explicit UTF-8. The affected 101.7–110.1 s window was rerendered and
assembled at exact frame boundaries. A fresh full render from the corrected
UTF-8 data does not need that repair; the optional `repair-finish` stage reuses the
saved repair clip when working with this older cached raw render.

Recorded export: **127.033333 s, 1080×1920, 30 fps, H.264/AAC,
11,101,176 bytes**, measured **−16.07 LUFS / −1.48 dBTP**. Actual-file decode,
black-interval, media-contract and three-call reported-model checks passed.
Timeline/action sheets of the final corrected file were inspected. No claim of
full sensory watch/listen or reference-channel production quality is made.
Complete normal-speed browser playback of the corrected final file also passed
with no page or media errors.
