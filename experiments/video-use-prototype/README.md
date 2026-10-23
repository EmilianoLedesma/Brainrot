# Video-use explainer prototype

An isolated, original 10-scene explainer: **Why metal feels colder**. This evaluates
the agent-directed editing workflow before deciding how to integrate it into Brainrot.
It does not create database jobs, claim worker leases, or publish videos.

The selected engine is Pillow drawing original vector-style illustrations, encoded
with FFmpeg. Three Codex agents authored opening, mechanism, and payoff scenes in
parallel. The pinned upstream video-use helpers perform scene concatenation,
EDL-based finishing, audio normalization, and output filmstrip inspection.

## Reproduce

From the repository root, with Python 3.12–3.14, uv and FFmpeg/ffprobe installed:

```powershell
uv sync --locked --project experiments/video-use-prototype
uv run --locked --project experiments/video-use-prototype python experiments/video-use-prototype/prepare.py
uv run --locked --project experiments/video-use-prototype python experiments/video-use-prototype/build.py
uv run --locked --project experiments/video-use-prototype python experiments/video-use-prototype/verify.py
```

If an existing uv cache has Windows permission problems, use `uv sync --no-cache
--locked --project experiments/video-use-prototype`. All Python dependencies are
locked separately from the production application. No globally installed agent
skill or personal filesystem path is required. Fonts and their licenses are bundled.

`prepare.py` calls Brainrot's existing Edge TTS implementation over the network;
this is not offline speech synthesis. The prototype explicitly selects Guy because
Andrew returned no audio when word boundaries were requested during this session.
The production voice setting is unchanged. No ElevenLabs key, transcription call,
paid model API, Claude usage, or image/video generation API is required.

## Edit and inspect

The default output directory is the ignored `out/video-use-prototype/edit/`:

| Artifact | Purpose |
| --- | --- |
| `final.mp4` | Finished portrait explainer |
| `scene-plan.json` | Editorial scenes mapped to actual narration timings |
| `narration.txt`, `narration.mp3`, `words.json`, `narration.srt` | Saved speech and word timing |
| `edl.json` | Video-use edit decisions; continuous narration is retained intact |
| `animations/slot_*/` | Individual renders, sample stills, reasoning and cache hashes |
| `contact-sheet.jpg` | Ten frames extracted from the finished video |
| `verify/` | Cut-boundary filmstrips, opening/ending samples, audio measurement log |
| `verification.json`, `project.md` | Measured checks and editorial review record |

Edit `story.json` to change narration and the editorial scene plan. Edit `scenes_*.py`
and `visual.py` to change motion, layout and drawings. `prepare.py` reuses the saved
narration when its inputs match; `build.py` reuses matching rendered scenes.
To inspect stills without encoding, pass `build.py --stills`. To render one scene,
pass `build.py --scene 4` (one-based), then run the normal build to reassemble.
`--edit-dir` selects another generated-output directory and must be supplied to all
three scripts when overriding the default.

Scene timing follows real TTS boundaries; frame counts share one global 24fps grid.
Scene diagrams use selective labels. The complete word-timed subtitle sidecar stays
available without covering the diagrams with full-time karaoke captions. Temperature
numbers are illustrative; particle motion and melting are qualitative illustrations,
not measured experiments or thermal simulations. Factual sources are in `story.json`.

## Upstream and adaptations

Selected files under `vendor/video-use/` are unmodified copies from
[browser-use/video-use](https://github.com/browser-use/video-use), commit
`43cfc566833548093455c9d4a46bd69913b7e552`, under its bundled MIT license.
Only the skill/install reference and helpers used by this experiment are included;
this is not a complete global installation. See `provenance.json` for file hashes.

The approved prototype strategy substitutes generated narration and existing word
timings for video-use's raw-footage inventory and Scribe transcription. It authors
full-frame scene clips instead of placing small overlays over filmed takes. Source
clips are joined with the upstream concat helper; a continuous narration source is
finished through its EDL renderer. This keeps speech intact across visual cuts.
The inspection helper receives the bundled font through a local wrapper.

The interactive agent performs the review and revisions. This prototype does not
implement an unattended editing agent or a production queue adapter. Remotion,
Manim and HyperFrames are not installed by this experiment. A renderer choice and
successful media checks do not establish scientific accuracy or audience retention.

Generated media is local and ignored by Git. To review it on another computer,
transfer the output directory deliberately or reproduce it using this source.
