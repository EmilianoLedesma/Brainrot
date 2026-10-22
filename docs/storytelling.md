# Script storytelling skill

The project-owned [brainrot-storytelling skill](../brainrot/skills/brainrot-storytelling/SKILL.md)
is included automatically in every H2 topic generation and H2b Reddit rewrite.
`brainrot.script._generate` loads its body into the system prompt before calling
the selected provider. Claude Code, Codex (Chat GPT), and the explicit Anthropic
API path receive the same guidance, in the existing single generation call.
No plugin installation, tool access, extra API key, or separate critic call is needed.

Edit this file's linked skill to tune writing. It is read for each generation,
including by an already-running worker. Saved scripts are reused on retry, so
create a new job or use `generate-script` to evaluate a change. H1 moment selection
keeps the original video's speech and does not receive this writing skill.

The skill improves hooks, causal development, and payoffs while preserving topic
intent, source fidelity, brainrot/slang settings, narration format, and word limits.
These are writing instructions, not a guarantee of audience retention.

Scripts target 280-380 words, aiming for roughly two minutes. The required range
is 90-180 seconds including the title and pauses, measured from narration and
finished videos before upload. Repurposed clips must also meet that range.
Normal scripts stay in one video; unusually long saved stories are split into
balanced chapters. Each chapter must independently pass the duration checks.
Existing ready chapters retain their boundaries on retry. No automatic rewrite,
unnatural speed adjustment, silence padding, or mid-sentence truncation is used
to force out-of-range material to fit.
Final video encoding also constrains bitrate and checks that each file stays
under 45 MB before upload, leaving headroom below a 50 MB storage object limit.
Retries compare saved chapter words independently of paragraph whitespace, so
normalizing narration into chapters does not invalidate a saved script.

## ECC review

Reviewed local ECC 2.2.1, revision `e04ea0b9cc8248686edf5ac751cadff550e162b8`
([source repository](https://github.com/affaan-m/ECC)). The project skill is an
original, task-specific synthesis; ECC plugins and their hooks are not loaded into
generation sessions.

| ECC skill | Useful application | Decision |
| --- | --- | --- |
| `content-engine` | Early tension, platform-appropriate narration, concrete substance | Apply these principles in the project skill; omit campaign workflows. |
| `article-writing` | Tight prose, distinctive voice, removal of generic AI phrasing | Adapt principles to spoken shorts rather than articles. |
| `brand-voice` | Derive a consistent voice from representative writing samples | Useful follow-up once reference scripts are supplied; do not invent an author's voice profile. |
| `eval-harness` | Compare prompt changes against explicit quality criteria | Use the manual comparison below; avoid adding a second model call per job. |
| `video-editing` | Source footage selection and deterministic editing | Relevant to future H1 editing work, not narration generation. |
| `tasteforge-video` | Reference-based visual style packs and edit timelines | Separate visual workflow; unnecessary for parkour-backed narration. |
| `prompt-optimizer` | Advisory prompt rewriting and ECC component selection | Not a runtime dependency; its advisory-only workflow does not fit automatic script generation. |

## Quality comparison

For a meaningful writing check, generate multiple new previews with Codex before
and after a prompt edit, keeping topic and intensity fixed. Use at least these cases:

- Rome's silver coin crisis, Grounded and Max brainrot: accurate causal explanation;
  humor at maximum must not create invented historical events.
- GTA six simulating reality while scientists delay NPC intelligence, Playful and
  Max brainrot: commit to the fictional premise, progress through consequences,
  and end inside that world rather than debunking it.
- A supplied personal story: preserve events, point of view, and ending without
  adding dialogue, motives, or a new twist.

Judge specificity of the opening, clarity of stakes, progression without filler,
and whether the ending rewards the opening. Compare structure across the samples
as well as individually. Check spoken readability, title length, total word count,
and absence of stage directions or engagement bait. Automated adapter tests verify
that guidance reaches providers; they do not measure story quality or retention.
