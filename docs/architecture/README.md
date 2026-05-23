# Architecture Context

These files are the canonical architecture context for future Codex or AI-assisted implementation work on StudyFlow AI.

## Purpose

- provide stable context for roadmap execution
- reduce prompt size
- reduce implementation entropy
- preserve architectural invariants across steps
- keep future prompts focused on the requested roadmap slice

These files are not end-user product documentation. They are engineering context documents intended to be authoritative unless superseded by a later architecture update.

## How Future Prompts Should Use These Docs

Before implementing, read:

- `docs/architecture/runtime-architecture.md`
- `docs/architecture/project-direction.md`
- `docs/architecture/engineering-principles.md`
- `docs/architecture/simulado-runtime-chain.md`

Follow those invariants. Implement only the requested roadmap step.

Recommended prompt preamble:

> Before implementing, read:
> - docs/architecture/runtime-architecture.md
> - docs/architecture/project-direction.md
> - docs/architecture/engineering-principles.md
> - docs/architecture/simulado-runtime-chain.md
>
> Follow those invariants. Implement only the requested roadmap step.

## Status of These Files

- stable context
- canonical architecture guidance
- not user-facing product docs
- intended to make future prompts shorter and safer
- authoritative until a later architecture update replaces or amends them
