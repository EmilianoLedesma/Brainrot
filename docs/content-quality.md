# Content quality and retention

## Generation

The shared [storytelling skill](../brainrot/skills/brainrot-storytelling/SKILL.md)
now asks the chosen model to consider three different openings and select the
best-fitting one, then silently review narrative promises, causal progression,
world consistency, and the ending. It returns the same title/script JSON in the
existing single model call. No extra model invocation or numeric virality score
is introduced. Actual audience performance remains unverified until measured.

Eight adaptable opening approaches give variety without forcing a second-person
address, a fabricated statistic, a twist, or an evidence-free deadline. Factual
topics retain accuracy; clearly fictional premises remain true within their world.
The spoken title, pauses, brainrot/slang setting, and 90–180-second rule remain.
Saved scripts are reused on retry, so new guidance affects newly generated scripts.

H1 selection now prefers context-independent openings, a meaningful development,
and complete endings. It rejects overlapping lower-ranked candidates and returns
at most three clips within the transcript's recorded end time. Source speech is
preserved; it does not invent a replacement hook or add synthesized narration.

## Insights flow

Workspace → Output → Inspect opens the shared video detail view, also used by
Queue's Inspect button. It combines playback, saved narration, upload metadata,
YouTube performance and retention analysis with execution history. There is no
separate Insights tab. Click a video thumbnail or its Inspect button to open it.

The embedded retention tool has two steps: import, then review. Import a retention CSV
and enter the finished video's actual duration. Choose both the position and
retention units explicitly. The analyzer never infers percentages from a short
timeline. Optional SRT subtitles connect drop intervals to spoken passages.

By default, position is column one and retention is column two. Expand the column
settings to select different columns. Comma, semicolon, or tab delimiters, a UTF-8
BOM, and header rows are accepted. Numeric decimals use a period. Position units:

- Seconds: numeric seconds, `mm:ss`, or `hh:mm:ss`.
- Percent: positions from zero to one hundred, with optional percent signs.
- Fraction: positions from zero to one.

Retention units are percentage points on the usual percentage scale, or fractions
which are converted to that scale. Values over one hundred percent are preserved
for rewatches. Files are limited to 250 KB each, and curves to 5,000 data points.
At least three points are required, starting at time zero, with strictly increasing
positions and no points beyond the video's duration. Invalid rows are rejected
rather than silently removed after data starts. Example:

```csv
seconds,retention
0,100
15,92
30,80
60,74
90,68
120,60
```

The report shows the first thirty seconds' change (interpolated between samples),
or the available shorter span, the last observed retention, and the five steepest
downward intervals ranked by percentage points lost per second. The chart can be
explored with the keyboard or slider. These are observations, not causal diagnoses,
virality predictions, or universal healthy/unhealthy grades. Partial exports are
not labeled as completion rates. No automatic script rewrite, publishing action,
or pacing decision follows from a report.

Imports and reports remain in memory per video while switching between Output,
Queue and other workspace screens. Saved SRT captions and playback duration are
pre-filled when available. Different videos keep independent analysis sessions.
Download
the JSON report to preserve it when leaving the workspace or refreshing. Data is
processed by the authenticated API; it is not saved to Supabase or sent to an LLM.
The endpoint is `POST /insights/retention` with the dashboard API key.

## Finished-video checks

The renderers normalize final audio toward minus sixteen LUFS with a minus one
point five dBTP target using FFmpeg's loudness filter. This is an export target,
not a claim that every recording achieves identical perceived loudness. Before
upload, output is checked for duration, file size, expected picture dimensions,
H.264 video, and AAC audio. Existing videos remain unchanged.

## Sources and adaptation

The repo-owned [Shorts publishing skill](../brainrot/skills/youtube-shorts-publishing/SKILL.md)
adapts the same promise/payoff and source-fidelity criteria to upload titles,
descriptions, hashtags, and tags. It considers title angles silently, packages
the actual finished narration, and avoids claims of guaranteed reach. Preview
and automatic publishing share this guidance; they do not invoke a global
plugin or change the original narration. This is an additional model call per
uncached draft, with explicit regeneration available in the upload details view.

These are project-specific implementations inspired by reviewed MIT-licensed
resources; no upstream installer, agent personality, or executable was installed.

- [YouTube script guidance](https://github.com/Jakeschincariol/youtube-agent-skill/blob/main/skills/yt-script/SKILL.md)
  and [hook library](https://github.com/Jakeschincariol/youtube-agent-skill/blob/main/skills/yt-script/hooks.json):
  adapt opening variety and self-review; omit interactive approval, on-screen
  directions, and closing engagement requests.
- [Hook scorer](https://github.com/Jakeschincariol/youtube-agent-skill/blob/main/skills/yt-script/hookscore.py):
  use editorial criteria without English keyword scoring, digit bonuses, mandatory
  direct address, or a supposed success probability.
- [Retention tool](https://github.com/Jakeschincariol/youtube-agent-skill/blob/main/skills/yt-retention/retention.py):
  implement explicit units, validated inputs, interpolation, slope-ranked drops,
  and subtitle alignment rather than its axis-size heuristic.
- [Shorts selection](https://github.com/Jakeschincariol/youtube-agent-skill/blob/main/skills/yt-shorts/SKILL.md):
  adapt self-contained moments while retaining our duration range and original audio.
- [Narratologist](https://github.com/msitarzewski/agency-agents/blob/main/academic/academic-narratologist.md):
  adapt promises, payoffs, structure choice, and internal consistency; omit academic
  analysis from generated narration.
- [Editing Coach](https://github.com/msitarzewski/agency-agents/blob/main/marketing/marketing-short-video-editing-coach.md):
  adapt audio consistency and export checks to FFmpeg.
- [Reality Checker](https://github.com/msitarzewski/agency-agents/blob/main/testing/testing-reality-checker.md):
  adopt evidence-based user-journey verification with existing pytest and browser
  checks. Do not import its hardcoded commands, automatic rejection of first passes,
  or grading rituals. It is software QA, not a debunker of fictional stories.

## Verification

`tests/test_retention.py` covers explicit units, short timelines, uneven sampling,
partial exports, rewatches, subtitles, malformed input, limits, and authenticated
API access. `tests/test_moment_quality.py` covers overlap, ranking, count, and source
bounds. The real render fixture checks the produced video; browser smoke verifies
import, report exploration, validation, tab persistence, and mobile layout.
