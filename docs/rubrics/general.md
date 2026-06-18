# General Rubric

> Universal evaluation criteria, applicable across tech stacks.
> A handoff's For Auditor section references this file:
> `@docs/rubrics/general.md`

## Dimensions

### 1. AC satisfaction (highest weight, hard veto)

- All AC met → full marks
- Some AC unmet → outcome: partial, list the unmet ones
- Critical AC unmet → outcome: fail

### 2. Test coverage

- Changes have corresponding unit/integration tests? (y/n)
- All tests pass? (y/n)
- Beyond happy path, are edge cases covered? (y/n)

### 3. Naming and readability

- Variable/function names communicate clearly? (1-5)
- Code organization matches the project's existing structure? (y/n)
- Comments cover "why" instead of "what"? (y/n)

### 4. Complexity delta

- New LOC count (informational)
- New dependencies? (list, assess necessity)
- Cyclomatic complexity increase? (assess)

### 5. Consistency with existing patterns

- Reuses existing project patterns? (y/n + note)
- Introduces unnecessary new patterns? (y/n + note)

## Verdict output format

```markdown
## Auditor Verdict (review)
- Outcome: pass | fail | partial
- AC results:
  - [✓/✗] AC1: ...
- Rubric scores:
  - AC satisfaction: pass | partial | fail
  - Test coverage: <comment>
  - Naming & readability: <score>/5
  - Complexity delta: <comment>
  - Pattern consistency: <comment>
- Issues found:
  - [blocker] ...
  - [major] ...
  - [minor] ...
- Recommendation: accept | request-rework | escalate-to-diagnose
```

## Discipline

- Default black-box judgment (AC satisfaction + objectively
  measurable items)
- Subjective dimensions (readability, naming) get 1-5 scores
  with a brief justification
- Don't give fix suggestions; only describe the problem
- If an AC is too vague to judge, outcome: blocked and name which AC
