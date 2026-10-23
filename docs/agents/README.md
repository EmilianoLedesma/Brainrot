# Agent orientation

This folder is the entry point for a new coding session. It complements the root
[AGENTS.md](../../AGENTS.md); it does not define new runtime agents or install plugins.

| Read | Purpose |
| --- | --- |
| [Handoff](handoff.md) | Dated progress, verification and remaining work |
| [Architecture](architecture.md) | Where behavior lives and how guidance reaches models |
| [Development](development.md) | Setup, services, checks and safe debugging |
| [Decisions](decisions.md) | Product requirements to preserve |

```text
AGENTS.md                       durable repository instructions
docs/
  index.md                      complete documentation navigation
  agents/
    README.md                   orientation and update protocol
    architecture.md             code map and runtime flows
    development.md              local workflow and verification
    decisions.md                accepted product constraints
    handoff.md                  dated snapshot and next work
  moving-between-computers.md   machine setup and media transfer
  superpowers/                  original reliability plan and specification
brainrot/skills/                 guidance explicitly loaded during generation
  brainrot-storytelling/SKILL.md
  youtube-shorts-publishing/SKILL.md
  motion-graphics/SKILL.md
```

Start with the latest user request, inspect branch/status, then read the handoff.
Read the implementation for the feature being changed rather than loading every
historical document. The original reliability plan records earlier milestones;
its branch names, storage assumptions and pending credentials can be obsolete.

Before ending a session, refresh `handoff.md`. Record what actually ran, what
needs user setup, and whether changes were committed or pushed. Update durable
decisions only when the user changes a requirement. Link new documents from
`docs/index.md` and keep README navigation current. Do not record raw errors,
tokens, private prompts, PIDs or a copy of `.env` here.
