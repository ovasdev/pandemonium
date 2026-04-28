# Document Templates

Exact templates for each document type produced by the task-workflow skill. Use these as starting points — adapt sections to the specific task context, but preserve the structural headings.

---

## request.md

```markdown
# Request: {Brief Title}

**Date:** {YYYY-MM-DD}
**Author:** User
**Linked ticket:** [{TICKET-CODE}](../../tasks/{TICKET-CODE}/raw.requirements.md) ← if applicable, omit if no ticket

---

## Raw Request

> {User's exact words, verbatim, as a blockquote}

## Context

- Project: {project name}
- Area: {affected area / module}
- Urgency: {low / medium / high} ← optional
```

---

## spec.md

```markdown
# Specification: {Brief Title}

**Date:** {YYYY-MM-DD}
**Author:** Agent (based on {N}.request.md)
**Status:** Draft | Confirmed

---

## Overview

{One paragraph summarizing the formalized requirements}

## Requirements

1. {Requirement 1}
2. {Requirement 2}
3. ...

## Acceptance Criteria

- [ ] {Verifiable criterion 1}
- [ ] {Verifiable criterion 2}
- [ ] ...

## Constraints

- {Technical or business constraints, if any}

## Open Questions

- {Anything unresolved — remove section if none}
```

---

## research.md

```markdown
# Research: {Topic}

**Date:** {YYYY-MM-DD}
**Author:** Agent
**Related:** {N}.spec.md or {N}.request.md

---

## Objective

{What question or problem this research is investigating}

## Findings

### {Finding 1 Title}

{Description, evidence, code references}

### {Finding 2 Title}

{Description, evidence, code references}

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| {A} | ... | ... |
| {B} | ... | ... |

## Recommendation

{Which option and why}

## References

- {Links, file paths, documentation URLs}
```

---

## plan.md

```markdown
# Plan: {Brief Title}

**Date:** {YYYY-MM-DD}
**Author:** Agent
**Based on:** {N}.spec.md, {N}.research.md
**Estimated effort:** {rough time estimate}

---

## Implementation Steps

1. {Step 1 — what and why}
2. {Step 2}
3. ...

## Files to Change

- `path/to/file.ts` — {what changes}
- `path/to/other.ts` — {what changes}

## Risks

- {Potential risk and mitigation}

## Done When

- [ ] {Verifiable acceptance criterion 1}
- [ ] {Verifiable acceptance criterion 2}
- [ ] Tests pass
- [ ] No lint errors introduced
```

---

## notes.md

```markdown
# Notes: {Task Title}

**Date:** {YYYY-MM-DD}
**Author:** Agent

---

## Observations

### {Timestamp or Stage}

{Observation, discovery, or decision made during implementation}

### {Timestamp or Stage}

{Another observation}
```

Notes are append-only during implementation. Each observation is timestamped or associated with a stage. Content can be informal but should be factual — avoid speculation without labeling it as such.

---

## verify.md

```markdown
# Verify: {Task Title}

**Date:** {YYYY-MM-DD}
**Author:** Agent
**Based on:** {N}.request.md | {N}.spec.md acceptance criteria | {N}.plan.md "Done When"

---

## Scope of Verification

{One line: which document's criteria are being checked — request for oneliner, request+research for small, spec+plan for large}

## Criteria

### 1. {Criterion text, copied from source}

**Verdict:** ✅ met | ❌ not met | ⚠️ partial

**Evidence:**
- {Command run + relevant output, or file:line reference, or exact manual action}

**Gap (if ❌ or ⚠️):**
- {What is missing and why it matters}

### 2. {Next criterion}

**Verdict:** ...

**Evidence:**
- ...

---

## Regression Checks

{One or two negative checks — "what would break if this change is wrong?" — with their result}

- {Check 1} — {result}
- {Check 2} — {result}

---

## Overall Verdict

{All ✅ / Mixed — list ❌ and ⚠️ / Blocked — list ❌}

## Next Action

{Proceed to report.md | Fix and re-verify at iteration N+1 | Raise questions.md because spec was wrong}
```

Rules for `verify.md`:
- Every criterion gets a verdict AND evidence — a bare ✅ with no evidence is not verification.
- If no test exists for a new behavior, either write one or record the gap explicitly.
- If runtime verification is impossible in the current environment, say so and mark affected criteria ⚠️ rather than guessing ✅.
- The `Next Action` line dictates what happens next — no report.md until it says "Proceed".

---

## report.md

```markdown
# Report: {Task Title}

**Date:** {YYYY-MM-DD}
**Author:** Agent
**Tier:** {oneliner | small | large}
**Duration:** {approximate time spent}
**Verification:** {N}.verify.md — {all ✅ | partial, see below}

---

## Summary

{One paragraph: what was done and the outcome}

## Changes Made

- `path/to/file.ts` — {what was changed and why}
- `path/to/other.ts` — {what was changed and why}

## Acceptance Criteria Status

- [x] {Criterion 1 — met}
- [x] {Criterion 2 — met}
- [ ] {Criterion 3 — not met, reason: ...} ← if applicable; must also appear in verify.md

## Remaining Work

- {Anything left undone — remove section if fully complete; every ❌ or ⚠️ from verify.md appears here}

## Lessons Learned

- {Optional: anything worth noting for future tasks}
```

---

## questions.md

```markdown
# Questions: {Context}

**Date:** {YYYY-MM-DD}
**Author:** Agent
**Triggered by:** {N}.{type}.md — {reason for backtracking}

---

## Questions

1. {Question 1 — what the agent needs to know and why}
2. {Question 2}
3. ...

## Context

{Explanation of why these questions arose — what was discovered that created ambiguity}
```

---

## answers.md

```markdown
# Answers: {Context}

**Date:** {YYYY-MM-DD}
**Author:** User (recorded by Agent)
**In response to:** {N}.questions.md

---

## Decisions

### Q1: {Original question, abbreviated}

> {User's exact response}

**Decision:** {Formalized decision for downstream documents}

### Q2: {Original question, abbreviated}

> {User's exact response}

**Decision:** {Formalized decision}
```

---

## analysis.md

```markdown
# Analysis: {Subject}

**Date:** {YYYY-MM-DD}
**Author:** Agent

---

## Subject

{What is being analyzed and why}

## Assessment

{Structured analysis — tables, pros/cons, risk evaluation}

## Conclusion

{Summary of findings and recommended path forward}
```
