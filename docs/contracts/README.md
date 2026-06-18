# Contracts

> A factual record of cross-stack interfaces — "what they look
> like now."
> Not the design rationale (that's an ADR), not the change
> action (that's a handoff).

## Structure

```
contracts/
├── README.md           # you are reading this
├── api/
│   ├── v1/             # old version, frozen
│   ├── v2/             # current version
│   ├── current/        # pointer: symlink or explicit file → v2
│   ├── deprecated/     # truly retired; must not be referenced
│   └── CHANGELOG.md    # cross-version change log
└── schemas/
    └── ...             # data schemas (if applicable)
```

## Discipline

- Changing a contract → must change `docs/contracts/` first,
  before any code
- Changing a contract → mandatorily triggers a handoff prefixed
  `[contract]`
- The contract-change handoff has special AC: all referring
  sides must update simultaneously, or explicitly flag backward
  compatibility

## Relationship to other doc types

```
ADR      = "why we decided this" (one-shot decision)
contract = "what it looks like now" (current fact)  ← you are here
handoff  = "please change it from A to B" (action)
```
