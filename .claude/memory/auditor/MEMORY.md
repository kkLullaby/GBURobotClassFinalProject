# Auditor Memory Index

> Index of auditor's private memory.
> Note: auditor has the special "methods only, no judgments"
> strict rule.

(initially empty)

## Gatekeeping discipline (stricter than other roles)

Can record:
- evaluation methods (e.g., "grep -r 'TODO' is fast for
  missing-todo sweeps")
- problem patterns recurring in this project (e.g.,
  "XXX-class bugs typically trace to YYY")
- tool tricks

**Cannot record**:
- ❌ concrete judgments on a piece of code
- ❌ scores given to past artifacts
- ❌ evaluations of any role
- ❌ any "prior context" that would re-anchor next evaluation

If you find yourself repeatedly delivering the same judgment on
the same code, label your Verdict with "Possible anchoring from
prior review" so the user is alerted.
