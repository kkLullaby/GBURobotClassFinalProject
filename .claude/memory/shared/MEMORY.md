# Shared Memory Index

> Index of all "fact files" under shared/.
> This file itself holds no facts; it only lists which fact
> files exist.
> Each fact file enters a session via CLAUDE.md `@import`.

## Current fact files

- [tech-stack.md](tech-stack.md) — what this project uses
- [global-commands.md](global-commands.md) — universal commands

<!-- when adding a new fact file, add a line here and add an @import in CLAUDE.md -->

## Gatekeeping discipline

shared/ holds only "facts," not "judgments / opinions /
methods." Admission criteria: see docs/concepts/auto-memory.md.

`/promote-to-shared <file>` can help promote "facts" from a
role's private memory into shared/.
