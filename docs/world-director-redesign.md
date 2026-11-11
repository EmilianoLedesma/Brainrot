# Pending: a director that designs the world, not only directs it

Status: not started. Written 2026-11-11 so the work can be picked up later. Read [world mode](world-mode.md) first; it describes what exists today.

## The problem

The continuous 3D world edit works end to end offline, but the director only chooses among scenes that a developer built by hand. A pack
(`brainrot/world/packs/<id>.json` plus `motion/world/packs/<id>.tsx`) fixes the stations, props, actors and actions for one topic family. The director picks stations, shots,
and actions inside that vocabulary and nothing else. Consequence: a topic outside the two packs (zebras, birds on power lines) stops at the `direct` stage with
"no scene pack". This was seen on a real job, "La invención de los lentes de sol": the story and research were fine, `director.choose_pack` answered `none`.

The intended behaviour is the opposite: the topic and the generated script should be enough, and the director should decide the scenes and what they contain.
The pack rule ("the director only uses the manifest vocabulary") was a design choice made while integrating the experiments, not a product decision. Do not build more
hand-made packs as the answer; that is the thing to replace.

## Target flow

```text
topic -> (web research) -> script -> DESIGN -> narration (TTS) -> DIRECTION -> render
                                     ^ new                         ^ exists, adapted
```

1. **Design** runs right after the script exists and before narration, so it can overlap the narration and fail fast. Input: topic, script, research facts. Output, a validated
   JSON "world spec": the ideas of the video in order (stations), the setting of each, the pieces each station needs, the protagonist if any, and the actions each piece can perform
   with a duration. Example for sunglasses: snow goggles of ivory, smoky quartz for judges, a tinted lens with a light beam, ultraviolet rays stopped by a lens, a stall and a crowd,
   a plane and a polarising filter, a pie of "protection versus looks".
2. **Direction** runs after narration, as today (`brainrot/world/director.py`): beats from the word timings, scene nature, calm camera, actions locked to cue words, with the code-enforced
   rules. It reads the world spec instead of a pack manifest. The manifest and the spec should share one schema so existing rules (`design`, `_camera`, `beats`) keep working.
3. **Render** reads the spec and the script and draws everything with a generic renderer.

## Decisions to take or confirm

- **Pieces are data, not code.** The model describes each piece as a spec (base shapes, sizes, colours, parts, anchor points, which actions it supports). A generic renderer in
  `motion/world/` draws it. Never execute model-written code in the render: it cannot be validated before a render that takes tens of minutes, and it would run on the user's computer.
- **A base library** of low-poly building blocks the specs compose: rounded boxes, ellipsoids, cylinders, cones, discs, rays and beams, bars, pies, arrows, people, simple animals, ground
  stages (plinths), weather and light. The current zebra and birds renderers become reference pieces of that library; the two manifests become example world specs.
- **Generic actions**: appear, move along a path, scale, change colour, light up, split or grow (bars, pies), a ray reaching or being blocked, a character putting something on. Each has
  a duration so the existing no-overlap rule keeps working.
- **Validation in code before TTS and before render**: every piece uses library parts only, sizes stay inside the stage (about 8 units from its centre), at most N pieces per stage for
  frame rate, every action names an existing piece, durations fit the beats. A spec that fails is repaired once by the model with the validator message, then the job stops with a friendly error.
- **Quality bar**: the hand-built films look better than anything composed from a generic library will at first. Test with the already generated sunglasses script
  (`stories` row of job `8650e624…`) and with one factual and one fictional topic before enabling the option by default. Keep the packs as an optional "curated" path until the generic one
  matches them.
- **Stays as is**: opt-in per job (`params.world`), no silent fallback to another edit or provider, YouTube review/auto/off, friendly errors, 90–180 s target, natural narration. The script is
  not rewritten to suit the visuals.

## Work items

1. World spec schema and validator (Python, plus a TypeScript type in `motion/world/kit.ts`); convert the zebra and birds manifests into specs as the first test cases.
2. Design stage: prompt (`skills/world-design/SKILL.md`), typed model answer, repair-once loop, code validation, plan cache keyed by script hash (like `out/world-plans/`).
3. Move the design call before TTS in `pipeline.produce`, as its own stage named `design`; add it to the stage names in `web/src/i18n.jsx` (EN/ES).
4. Generic renderer: pieces from specs, library parts, generic actions, stage lifetimes and the calm camera reused from the current packs.
5. Adapt `director.plan` to read a spec; keep the pack path working until the generic path is as good.
6. Tests: spec validation (accept and reject cases), design defaults, director on a spec, pipeline stage order with fake models, a still-render smoke per example spec.
7. Docs: update `world-mode.md`, architecture, the handoff; remove the "scene packs" limitation wording once the generic path ships.

## Model tiers: strong for the director, standard for the rest

Decision (user, 2026-11-11): the director uses the most capable model; everything else (script, ideas, web research, YouTube metadata, repurpose selection) uses a cheaper one such as Sonnet.
Verified in code: `llm.generate(..., tier=...)` passes `--model` to the Claude CLI; `strong` resolves to `opus` and `standard` to `sonnet` (`llm._TIER_DEFAULTS`). The world director asks for `strong`
(pack choice and beat direction); a call that names no tier is now `standard` (it used to fall through to the CLI's own default model, which could be Opus on some plans). Overrides, in order:
`BRAINROT_<CLAUDE|CODEX>_MODEL_STRONG` or `_STANDARD`, then `BRAINROT_<CLAUDE|CODEX>_MODEL`, which pins every call and therefore disables the split, then the built-in default. Codex has no
built-in default, so set its tier variables in `.env` to get the same split. Covered by `tests/test_llm.py`. The future design stage should also ask for `strong`.

Still worth measuring before treating Opus as settled: run the same sunglasses script through design and direction with both models and compare validator corrections per beat (`scene["notes"]`),
design repairs, beats with the intended station and actions, time and tokens per call (the unchunked director took about 12 minutes on the experiments) and three stills. If the code-corrected
direction stage shows no gain, keep `strong` only for design.

## Related pending items found in the same session

- **Cancel button for active jobs.** Requested 2026-11-11. Today only pending jobs can be cancelled (`domain/jobs.py` allows `PENDING -> CANCELLED`; migrations 006 and 008 mark jobs cancelled
  when deleting). A running job needs: an API route, a SQL function that marks the lease owner's job cancelled without breaking lease ownership, idempotency and deletion guards (additive migration
  only), a cooperative check in the worker between stages, killing of long subprocesses (Remotion, the model CLI), and a Cancel button in the queue with a confirmation. Not started.
- **Fail fast when no pack fits** (only until the redesign lands): choose the pack right after the script, before narration.
- **Narration voice follows the script language.** `tts.VOICE` is always `en-US-AndrewNeural`, even for Spanish scripts. On the sunglasses job one short sentence returned `NoAudioReceived`
  with that voice while `es-MX-JorgeNeural` synthesised it. The job kept failing in `tts`. Left untouched on request; a language-aware voice choice is the likely fix.
- **Video ideas has no tests.** Add an API test for `POST /ideas` (dedupe, avoid list, 502 on failure) and a browser check for Tools → Video ideas → Use this topic.
- **A Vite dev server started for browser checks** may still be running on port 5173.
