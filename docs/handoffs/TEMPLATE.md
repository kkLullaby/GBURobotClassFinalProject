---
id: YYYY-MM-DD-slug-NNN
from: planner
to: executor
type:                          # required only when to: auditor: review | arbitrate | diagnose
status: pending
parent:                        # parent handoff id, or leave empty
created: YYYY-MM-DD
artifacts:
  - <path-to-large-artifact-if-any>
---

## Objective

<one-sentence goal, self-contained>

## Constraints

- <hard constraint 1>
- <hard constraint 2>

## Acceptance Criteria

- [ ] <verifiable condition 1>
- [ ] <verifiable condition 2>

## Context Pointers

<Tier 2 information: paths, not embedded content>

- @<related code path>
- @docs/adr/<related ADR>
- @docs/handoffs/archive/<related history>
- @docs/contracts/api/<related contract>

## Out of Scope

- <explicitly not done>

## Candidate Root Causes

<mandatory ≥2 for bug-class only>

1. <possible cause A> — evidence: ...
2. <possible cause B> — evidence: ...

## For Auditor

<only when to: auditor>

- rubrics:
  - @docs/rubrics/<related rubric>.md
- must_check:
  - "<hard check item 1>"
  - "<hard check item 2>"
- Reproduce: <how to verify the AC>

---

<!--
The sections below are appended by the receiving role (executor /
auditor) on demand. Don't pre-fill them.

Section ownership:
  - Executor's Reading / What I Did / Open Questions for Auditor → executor
  - Auditor Verdict → auditor
-->

## Executor's Reading

### What I'll do

### Assumptions made

- [LOW]
- [MED]
- [HIGH]

## What I Did

## Open Questions for Auditor

## Auditor Verdict (review | arbitrate | diagnose)
