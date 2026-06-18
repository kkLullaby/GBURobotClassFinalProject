# Handoff Protocol

> This rule is always loaded (no `paths:` frontmatter) — every
> role gets it. It defines the standard structure and discipline
> for handoff files.

## File naming

`docs/handoffs/active/<id>.md` where id = `YYYY-MM-DD-<slug>-NNN`:

- date = creation date, not completion date
- slug = kebab-case short description (3-5 words)
- NNN = daily sequence starting at 001

Move to `docs/handoffs/archive/<id>.md` once everyone involved is
done.

## Frontmatter schema (required)

```yaml
---
id: YYYY-MM-DD-slug-NNN          # matches the filename
from: <role>                      # planner | executor | auditor
to: <role>                        # planner | executor | auditor
type: <type>                      # required only when to: auditor: review | arbitrate | diagnose
status: pending                   # pending | claimed | done | blocked
parent: <handoff-id or null>      # continuous handoff chain
created: YYYY-MM-DD
artifacts:                        # references to large artifacts (paths), not embedded
  - <path>
---
```

## Body sections (appear as needed, in fixed order)

### When planner writes it

```markdown
## Objective
<one sentence, self-contained>

## Constraints
- <hard constraint 1, violation = failure>

## Acceptance Criteria
- [ ] <verifiable condition 1>

## Context Pointers
- @<related file/ADR/historical handoff/contract>

## Out of Scope
- <explicit not-to-do>

## Candidate Root Causes  (mandatory ≥2 for bug-class)
1. <possible cause A> — evidence: ...
2. <possible cause B> — evidence: ...

## For Auditor  (only when to: auditor)
- rubrics:
  - <rubric path>
- must_check:
  - <hard check item>
```

### When executor appends on receipt

```markdown
## Executor's Reading
### What I'll do
- ...

### Assumptions made
- [LOW] ...
- [MED] ...
- [HIGH] ...     ← any HIGH must wait for planner confirmation (status: blocked)
```

### When executor appends on completion

```markdown
## What I Did
- <which files modified>
- <which files created>
- <which tests run, results>

## Open Questions for Auditor
- <if any>
```

### When auditor appends on completion

```markdown
## Auditor Verdict (<review|arbitrate|diagnose>)
<output format per mode, see .claude/agents/auditor.md>
```

## Protocol discipline

1. **frontmatter status agrees with location**: status: done
   handoffs belong in archive/, not active/. PostToolUse hook
   auto-syncs; `/retro` is the fallback if no hook.

2. **status only moves forward**: pending → claimed → done, or
   pending → blocked → pending (reactivate). **No regression
   from done**; to continue work after done, open a new handoff.

3. **Append only, no modify**: once a handoff is out, everything
   except frontmatter status is append-only. To change direction,
   open a new handoff that supersedes it (frontmatter
   `supersedes: <old-id>`).

4. **Section ownership is clear**:
   - planner writes: frontmatter + Objective..For Auditor
   - executor writes: Executor's Reading, What I Did, Open
     Questions
   - auditor writes: Auditor Verdict
   - Don't cross lines.

5. **archive ≠ deleted**: archived handoffs can still be
   referenced via Context Pointers
   (`@docs/handoffs/archive/<id>.md`).

6. **Fresh-Claude test**: after writing a handoff, self-check —
   feed this handoff + project CLAUDE.md + `.claude/rules/` to a
   fresh Claude session; can it start? Yes → pass.

## Assumption-severity rubric

| Level | Example | Handling |
|---|---|---|
| LOW | "assumed snake_case (matches style rule)" | self-decide, write in Reading |
| MED | "assumed field on user table" | self-decide, list separately so user sees on relay |
| HIGH | "assumed v1 API compat may break" | STOP, status: blocked, await user confirmation |

Criteria:

- LOW: easy to roll back, impact < single file
- MED: requires rework, impact < single module
- HIGH: impacts multiple roles/modules/external, or touches
  contract/schema/dependency

## INDEX maintenance

After writing a handoff or changing its status, update
`docs/handoffs/INDEX.md`.

With a PostToolUse hook configured, this is automatic.
Otherwise, planner should update the INDEX's Active section by
hand after writing.

INDEX format: see docs/concepts/vitality.md.

## Boundary vs ADR

- handoff = "please change it from A to B" (action)
- ADR = "why this design" (one-shot decision)
- contract = "what it looks like now" (current fact)

For handoffs involving architectural decisions, planner should
draft an ADR at the same time (status: draft) and reference it
in Context Pointers.
