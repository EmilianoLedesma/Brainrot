# World director redesign: the director designs the world

Status: first slice implemented 2026-11-11 (items 1 to 6 below, see the handoff for what ran and what did not); quality of model-designed worlds and the Opus comparison are still open.
Read [world mode](world-mode.md) first; it describes what exists today.

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

Done (offline, with a hand-written fixture; see the handoff for any live check):

1. World spec schema, validator and mapping to the director's manifest: `brainrot/world/spec.py` (presets, primitive parts, effects, framing rule, recipe rules: soft palette, reserved red and yellow).
2. Design stage: `brainrot/skills/world-design/SKILL.md`, `brainrot/world/design.py` (strong tier, one repair round, friendly failure, cache in `out/world-designs/`).
3. Pipeline order: stage `design` runs before `tts`; `direct` receives the designed world; stage names added to the dashboard (EN/ES).
4. Generic renderer `motion/world/packs/generic.tsx` (pieces from specs, effects, rays, stage lifetimes, shared calm camera) registered as pack `generic`.
5. `director.plan` and `director.direct` accept a designed world; the script carries it (`script["world"]`).
6. Tests in `tests/test_world.py` with `tests/world_fixture.py` (validation accept and reject, director on a spec, design repair and cache, stage order).

Live result so far: the design stage on the sunglasses script returned a valid world in 405 s (hero plus seven stages, rules satisfied). The live director and any render of that world were not run.

Still to do:

- Run the director live on the designed sunglasses world (script and timings: `out/direct_live.py` was a scratch probe; rebuild it) and render it fully; then the same for one factual and one fictional topic. Run the design and direction stages live on more than one topic (factual and fictional) and look at full renders, not stills; tune the skill and the presets from what the model actually produces.
- More presets and effects as real designs ask for them (animals with legs that move only during an action, a subject with its own actions as in the birds film, text-free labels, bars and pies).
- Subject-first direction for designed worlds (the curated birds pack had it; `spec.to_pack` sets `subject: null`).
- The Opus comparison below, with the same script through both models.
- Remove or demote the curated packs once the generic path matches them; delete `director.choose_pack` then.

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
- **Narration voice follows the script language.** `tts.VOICE` is always `en-US-AndrewNeural`, even for Spanish scripts. On the sunglasses job one short sentence returned `NoAudioReceived`
  with that voice while `es-MX-JorgeNeural` synthesised it. The job kept failing in `tts`. Left untouched on request; a language-aware voice choice is the likely fix.
- **Video ideas has no tests.** Add an API test for `POST /ideas` (dedupe, avoid list, 502 on failure) and a browser check for Tools → Video ideas → Use this topic.
- **A Vite dev server started for browser checks** may still be running on port 5173.
