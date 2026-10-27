# Why Starting Feels So Hard

An original unpublished English Grounded film, requested on 2026-10-27. The user
asked the directing agent to select the most appropriate Lemo style, remove the
coffee film's progress indicator and fixed header, and improve camera movement
and editing.

The live Codex choice compared **Mid-century Cartoon**, One-line Drawing and
Paper Pop-up Book, then selected **midcentury-toon** for expressive everyday
acting and layered camera movement. The saved rationale is in the ignored
`out/lemo-procrastination/style-choice.json`. A second live directing call reads
the selected STYLE.md and Lemo DIRECTOR.md to produce eighteen chronological
beats, with exact narration cues, action, framing, camera, transitions and sound.

The existing Brainrot storytelling skill and `script.write_story` generated one
original 326-word title/script at level 0, with researched context. Brainrot's
Guy speech and word boundaries measure **123.53 seconds**. No Claude or paid model
API is used. See [FACTS.md](FACTS.md) for the psychology sources and qualifications.

## Film grammar

Original character and props, illustrated emotional cloud, held body with hand/
eye/mouth performance on twos, separately registered flat fills and broken ink
from the actual pinned Lemo cartoon engine. One desk, laptop, phone and character
provide continuity. Side views alternate with newly drawn overhead views and
native-width hand/phone details; these are not the same image scaled up. The
camera tracks, pushes, pulls, follows fingers and separates depth planes.
Circular match/reveals and directional object/color-plane wipes connect views.

There is **no progress bar, persistent upper heading, numbered step header,
series branding or quote/completion card**. Spoken bottom captions remain. The
only scene word is the diegetic DRAFT label on the laptop when it is readable.
The upstream style's manual/step-card defaults are deliberately overridden by
the user's continuous-film direction. Voice, vertical size, duration and mastering
retain Brainrot's rules. The ending shows a small unfinished action while the
illustrative discomfort remains, rather than implying a cure or finished work.

Quiet original vibraphone-like synthesis and procedural foley support the voice.
There are near-silent instrumental intervals at the hesitation and turning point.
No sampled music, imported video, image-generation service or cloned voice.

## Outputs

All generated/private artifacts are ignored in `out/lemo-procrastination/`:

- `final.mp4`, `poster.jpg`, `captions.srt`, `watch.html`;
- saved original script, voice, words, selected style, direction and timed data;
- source HTML/JS, local font/notice, treatment, facts and credits;
- label-check/event/render logs, final timeline/action contact sheets;
- `verification.json` and `playback.json`, when those checks have completed.

This is a directed original film and a local bridge, not a new dashboard or
queue mode. The drawing code follows this film's chosen eighteen-beat plan;
another topic/style needs new direction and art. No job, worker, database or
platform upload is involved. Transfer media deliberately on another computer.

## Reproduce

Bootstrap Brainrot and sign in to Codex on this computer. This experiment reuses
the project-owned Lemo core tools and separately locked npm/audio environment
from [the coffee comparison](../coffee-comparison/README.md). If missing:

```sh
python experiments/coffee-comparison/fetch_lemo.py
npm ci --prefix experiments/coffee-comparison
uv venv experiments/coffee-comparison/.venv --python 3.14
uv pip install --python experiments/coffee-comparison/.venv --require-hashes -r experiments/coffee-comparison/requirements.lock
```

Source and existing output media are separate. The generation stages reuse saved
outputs; do not remove them unless you intend another live generation. A fresh
style decision could select another style; this film's authored drawing adapter
requires the actual selected midcentury-toon. To reproduce the reviewed film on
another computer, transfer its saved narration, words and direction too.

```sh
uv run --locked python experiments/lemo-procrastination/run.py prepare
uv run --locked python experiments/lemo-procrastination/run.py choose
uv run --locked python experiments/lemo-procrastination/run.py direct
uv run --locked python experiments/lemo-procrastination/run.py build
uv run --locked python experiments/lemo-procrastination/run.py produce
```

`build` validates exact spoken cues, saves actual style frames and runs the
upstream text-bounds/reading-time check. `produce` renders with the upstream
frame tool and finishes using Brainrot's −16 LUFS / −1.5 dBTP target. Existing raw
renders are reused; archive `raw.mp4` deliberately before rendering source edits.
Windows uses locally installed Edge/Chrome when available; otherwise set
`PLAYWRIGHT_CHROME` or install the pinned Playwright browser as in the coffee guide.

```sh
# Windows; on Unix use .venv/bin/python
experiments/coffee-comparison/.venv/Scripts/python experiments/lemo-procrastination/verify.py
uv run --locked python experiments/lemo-procrastination/run.py playback
```

Final-file verification includes complete decode, duration, codecs, dimensions,
size, black intervals, measured loudness, timeline sheets and action strips.
Normal-speed browser playback verifies the actual file can reach its end; it
does not establish a sensory watch/listen or audience retention improvement.

The selected style guide, engine and reference docs are MIT at pinned Lemo commit
`413a6bd6d78ebd3bdd5abaec9538a26867f890df`. Hashes/notices are in `guidance/`;
the original treatment predates reading demo code. No demo film, story, character,
still, voice or music is reused. See [CREDITS](CREDITS).

## Recorded media verification

Final output: **123.533333 s, 1080×1920, 30 fps, H.264/AAC, 17,347,231 bytes**.
Full decode, black-interval scan, expected duration/codecs/dimensions/size and
upstream prop-text reading checks passed. Audio measured **−16.05 LUFS /
−1.37 dBTP**. Actual final-file timeline sheets and 0.2-second transition strips
were inspected. Style hashes, local documentation links and Python/JS syntax
passed. The film has no progress or persistent-header layer. Reports remain
beside the ignored output; no claim of full sensory watch/listen is made.
Complete normal-speed headless browser playback of the final file also passed,
reaching its end with no page or media errors.
