---
name: infinite-waterfall
description: "Applies a structured, documented workflow to every development task — producing traceable artifacts in docs/log/ at each stage and verifying completeness before the agent replies to the user. Three tiers (oneliner, small, large) scale ceremony to task complexity. Triggers on any actionable development request even when the word 'workflow' is absent: new feature, bug fix, refactor, investigation, or respec. Trigger phrases: 'запиши требования', 'зафиксируй задачу', 'начни работу над', 'сделай фичу', 'реализуй', 'почини баг', 'рефакторинг', 'log this task', 'start working on', plus respec signals: 'требования изменились', 'пересмотри спек', 'respec', 'requirements changed'. Do NOT apply to pure conversation, to brainstorming without a concrete task, or to questions that need only an answer without code changes."
metadata:
  author: cinemauthor-team
  version: "2.0.0"
  category: workflow
---

# Infinite Waterfall

Applies a structured, traceable workflow to every development task. Each task produces numbered artifacts in `docs/log/` that form a complete audit trail from raw requirements through to a verified completion report.

The goal is that every piece of work — from a one-line fix to a multi-day feature — has a documented rationale, plan, verification, and outcome. This makes project history searchable and decisions traceable, and prevents the agent from reporting "done" when something slipped.

---

## Quick Reference

```
Classify tier → open iteration N → do the stages → VERIFY → report → reply to user
```

Stages by tier:

| Tier | Stages | Use for |
|------|--------|---------|
| **Oneliner** | `request → [execute] → verify → report` | Typo fix, config tweak, trivial rename (< 10 min) |
| **Small** | `request → research → [execute] → verify → report` | Clear bug fix, small feature, scoped refactor (10 min – 2 h) |
| **Large** | `request → spec → research → plan → [execute + notes] → verify → report` | New feature, architectural change, ambiguous requirements (> 2 h) |

The `verify` stage is non-optional in every tier — it is the gate between "I think it's done" and "I tell the user it's done".

---

## Tier Selection

Every task starts with tier classification. Analyze the user's request, then confirm with them before creating artifacts.

```
Is the task trivial and unambiguous (< 10 min, no research needed)?
├─ YES → Oneliner
└─ NO  → Is scope clear and bounded (10 min – 2 h)?
    ├─ YES → Small
    └─ NO  → Large
```

Propose the tier explicitly:

> "Классифицирую задачу как **{tier}**. Подтверждаешь?"

Proceed only after confirmation. Wrong-tier starts cost little — see [Mid-Task Upgrade](#mid-task-upgrade) below for escalation.

---

## Core Concepts

### Document Log Directory

All artifacts live in `./docs/log/` (flat directory). Create it if missing.

### Iteration Numbering

`N` in `{N}.{type}.md` is the **iteration number**, not a per-document counter. Think of it as a single forward pass through the workflow — every document produced in one pass shares the same N.

- File format: `{N}.{type}.md` — e.g., `1.request.md`, `1.spec.md`, `1.verify.md`
- All documents within one iteration share the same N
- The combination `{N}.{type}.md` is unique — never reused
- N increments only when a **new task** begins or a **backtrack** forces redoing an earlier stage

To find the next N: scan `docs/log/`, take the highest numeric prefix, add 1.

### Immutability

Once written, a document is never modified. If something invalidates it, increment N and create a fresh version from the stage that needs revision. The reason is simple: an edited document loses the history of what was believed true at that moment. The log's value collapses the moment it starts lying about the past.

### Index File

`docs/log/index.md` is an append-only metadata table. Add a row when starting a new task. Update the status column in place — but never rewrite existing rows.

```markdown
# Task Log Index

| # | Date | Tier | Status | Summary | Linked Ticket |
|---|------|------|--------|---------|---------------|
| 1 | 2026-04-22 | large | ✅ done | Feature X implementation | PROJ-123 |
```

`#` is the N of the task's `request.md`. Statuses: `🔄 in-progress`, `✅ done`, `❌ cancelled`, `⏸ paused`.

### Ticket Linkage

If a ticket file exists at `./tasks/{ticket-code}/raw.requirements.md` (or similar), reference it in `request.md`:

```markdown
**Linked ticket:** [TICKET-123](../../tasks/TICKET-123/raw.requirements.md)
```

---

## Document Types

| Type | Purpose |
|------|---------|
| `request` | Raw user request captured verbatim |
| `spec` | Formalized requirements + acceptance criteria |
| `research` | Feasibility investigation, references, technical options |
| `plan` | Implementation steps + "Done When" criteria |
| `notes` | Observations and decisions captured during implementation |
| `verify` | Self-check against acceptance criteria / request intent before reporting |
| `report` | Summary of completed work, files changed, outcomes |
| `questions` | Agent's clarification questions when blocked |
| `answers` | User's responses to questions |
| `analysis` | Standalone analytical assessment of a problem or tradeoff |

Templates for every type are in `references/templates.md`. Read that file when producing an artifact the first time in a session.

Structural requirements enforced by the templates:
- Every `plan.md` has a `## Done When` section with verifiable criteria.
- Every `request.md` contains the raw user input as a blockquote.
- Every `spec.md` has `## Requirements` and `## Acceptance Criteria`.
- Every `verify.md` lists every acceptance criterion with a verdict and evidence.
- Every `report.md` lists affected files and the verification outcome.

---

## Workflow by Tier

All documents within one pass share the same iteration N.

### Oneliner

1. `{N}.request.md` — capture the user's request verbatim
2. Execute the task
3. `{N}.verify.md` — confirm the change matches the request and nothing adjacent broke (see [Verification Step](#verification-step))
4. `{N}.report.md` — brief summary
5. Reply to the user

### Small

1. `{N}.request.md` — capture requirements
2. `{N}.research.md` — scan the codebase, identify existing patterns, pick an approach
3. Execute the task
4. `{N}.verify.md` — check against the request and the approach chosen in research
5. `{N}.report.md` — summary with list of changed files
6. Reply to the user

### Large

1. `{N}.request.md` — capture requirements verbatim
2. `{N}.spec.md` — formalize requirements, add acceptance criteria
3. Present the spec and ask for confirmation before continuing
4. `{N}.research.md` — deep investigation, references, tradeoffs
5. `{N}.plan.md` — implementation steps + "Done When" checklist
6. Present the plan and ask for confirmation before continuing
7. Execute the task, appending to `{N}.notes.md` as observations arise
8. `{N}.verify.md` — systematic pass through every acceptance criterion and "Done When" item
9. `{N}.report.md` — comprehensive summary referencing the verification result
10. Reply to the user

---

## Verification Step

The verification step runs after implementation and before `report.md`. Its purpose is to catch the gap between "code compiles" and "the thing the user asked for actually works". Skipping it is how the agent ends up confidently announcing a broken result.

### What to produce

Always create `{N}.verify.md`, even for oneliners. It is cheap and keeps every task's audit trail symmetric.

### What to check

The verification source depends on tier:

| Tier | Checked against |
|------|-----------------|
| Oneliner | `{N}.request.md` — the raw request |
| Small | `{N}.request.md` + approach decided in `{N}.research.md` |
| Large | `{N}.spec.md` acceptance criteria + `{N}.plan.md` "Done When" |

### How to check

For each criterion, pick the cheapest evidence that actually proves it:

1. **Static checks** — type checker, linter, formatter. Run the project's actual commands (e.g. `uv run pytest`, `npm run typecheck`). "Should compile" is not evidence — running the compiler is.
2. **Automated tests** — run the relevant suite. If no test exists for a new behavior, write one or record the gap explicitly in the verdict.
3. **Runtime smoke** — for UI or integration changes, actually run the feature. Don't infer behavior from the diff. If UI can't be exercised in this environment, state that explicitly rather than claiming success.
4. **Re-read the diff** — compare what you changed against what you claimed to change. Catches stray debug prints, half-applied edits, and files you meant to touch but didn't.
5. **Check the negative** — ask "what would break if this change is wrong?" and test one such case. Regression-thinking catches what acceptance-thinking misses.

### Verdict format

Every criterion gets one of:

- ✅ **met** — include evidence (command output, file/line reference, manual check description)
- ❌ **not met** — include the specific gap; this blocks the report
- ⚠️ **partial** — include what's covered, what's missing, and whether it's acceptable to ship; require user acknowledgement to proceed

### What to do with the result

| Overall verdict | Action |
|-----------------|--------|
| All ✅ | Proceed to `report.md`, then reply |
| Any ❌ | Do not write `report.md`. Either fix in place and re-verify (same N, overwrite `verify.md` is NOT allowed — instead, fix, then replace the verdict by incrementing to `{N+1}.verify.md` as part of a new plan pass) or raise `{N}.questions.md` if the gap means the spec was wrong |
| Any ⚠️ | Write `report.md` with the partial criterion called out explicitly in `## Acceptance Criteria Status` and `## Remaining Work`; mention it in the reply to the user |

The reply to the user reflects the verification verdict — never claim done when verify shows ❌ or unmentioned ⚠️.

See `references/templates.md` for the `verify.md` template.

---

## Backtracking

When a stage reveals a previous document is invalid, do not edit the old document. Increment N and create fresh documents starting from the stage that needs revision. Documents from earlier stages that remain valid do not need re-creation — the new iteration references them.

**Straight-through pass (no backtrack):**

```
1.request.md
1.spec.md
1.research.md
1.plan.md
1.notes.md
1.verify.md
1.report.md
```

**Backtrack after research:**

```
1.request.md
1.spec.md
1.research.md     ← discovers the spec is infeasible
1.questions.md    ← agent asks user for direction
1.answers.md
2.spec.md         ← revised spec
2.research.md
2.plan.md
2.notes.md
2.verify.md
2.report.md
```

**Verification reveals plan was wrong:**

```
1.request.md
1.spec.md
1.research.md
1.plan.md
1.notes.md
1.verify.md       ← some criteria ❌
2.plan.md         ← revised plan
2.notes.md
2.verify.md
2.report.md
```

When to increment N:
- Research proves the spec infeasible → `questions.md` + `answers.md` at current N, then increment
- User changes requirements mid-task → increment → new `request.md` or `spec.md`
- Implementation reveals the plan needs revision → increment → new `plan.md`
- Verification fails and the fix is non-trivial → increment → new `plan.md`
- Any ambiguity → `questions.md` + `answers.md` first, then increment only if an earlier stage needs redo
- User explicitly requests respec → see [User-Triggered Respec](#user-triggered-respec)

### User-Triggered Respec

During implementation, requirements often evolve through discussion. The user can explicitly ask to increment and revise the spec at any time — even if no stage has technically failed.

Triggers: "давай пересмотрим требования", "требования изменились", "respec", "пересмотри спек", "requirements changed", "let's revise the spec".

When triggered, capture the changed requirements, rerun research if scope changed significantly, produce a new spec and plan at the next N, and continue.

```
1.request.md
1.spec.md
1.research.md
1.plan.md
1.notes.md         ← implementation in progress
                    ← user: "требования изменились"
2.request.md       ← captures what changed and why
2.research.md      ← fresh research if scope shifted
2.spec.md          ← revised spec
2.plan.md          ← revised plan
2.notes.md
2.verify.md
2.report.md
```

---

## Starting a Task — Step by Step

1. **Scan `docs/log/`** — determine the next available N
2. **Create `{N}.request.md`** — capture the user's request verbatim
3. **Update `index.md`** — append a new row with status `🔄 in-progress`
4. **Classify tier** — propose a tier, confirm with the user
5. **Follow the tier workflow** — produce documents in order
6. **Run the verification step** — produce `{N}.verify.md`
7. **On success** — create `{N}.report.md`, update `index.md` status to `✅ done`, reply to the user

### Mid-Task Upgrade

If a task classified as oneliner grows into a small or large one, do not restart — upgrade in place. Keep the current N, create the extra documents at that N (e.g. an oneliner that grew into small: add `{N}.research.md` before `{N}.verify.md`), update the tier column in `index.md`. The verification step still runs once, at the end, against whatever the final tier's checklist is.

---

## Anti-Patterns

### Skipping the request document
**Symptom:** Agent jumps straight to implementation without logging the request.
**What goes wrong:** The audit trail is broken — nothing records what was asked for at the moment it was asked. Later iterations or reviewers can't reconstruct why decisions were made.
**Instead:** Start with `request.md`, even for oneliners. It takes 30 seconds.

### Skipping verification
**Symptom:** Agent writes `report.md` as soon as the code compiles, or replies "done" without running the test suite.
**What goes wrong:** Compilation proves the syntax, not the behavior. Reports based on "should work" are routinely wrong in ways the user discovers on the next run.
**Instead:** Always produce `verify.md` first. It is a gate, not a formality.

### Editing existing documents
**Symptom:** Agent updates `1.spec.md` in place after research invalidates it.
**What goes wrong:** The original version is lost — subsequent readers can't see that the spec changed, only the current shape of it.
**Instead:** Increment to 2, create `2.spec.md`. Keep `1.spec.md` as a historical record.

### Over-classifying trivial tasks
**Symptom:** Agent creates six documents for a typo fix.
**What goes wrong:** Ceremony slows simple work and creates noise that buries meaningful entries.
**Instead:** Oneliner tier — `request.md` + `verify.md` + `report.md` only.

### Empty boilerplate documents
**Symptom:** Agent creates `research.md` containing "No research needed".
**What goes wrong:** Adds no information, clutters the log, and reduces trust in other documents.
**Instead:** If a type has no content for this task, skip it. The tier system already decides what is required.

### Treating verification as optional
**Symptom:** `verify.md` says "looks good" with no evidence.
**What goes wrong:** A verify document without evidence is just a second `report.md`. Evidence is the whole point.
**Instead:** For every ✅, paste the command output, line reference, or exact manual action that proves it.

---

## Integration with Other Skills

- **brainstorming** — invoked during the research phase for complex tasks
- **managing-git** — commits should land after `verify.md` passes, never before
- **skill-creator** — if the work includes creating a skill, that work is itself a task and gets its own iteration N
- **remembering** — verification findings that generalize beyond this task (patterns, gotchas) can be saved as memory entries referenced from `notes.md`

> See also: brainstorming, managing-git, skill-creator, remembering

---

## Troubleshooting

- **Duplicate `{N}.{type}.md`** → the same iteration already has this document → a backtrack happened without incrementing N; increment first, then create the document.
- **Missing index row** → task has documents but no index entry → retroactively append it; always create the entry at the `request.md` step.
- **Tier chose wrong** → upgrade in place (see [Mid-Task Upgrade](#mid-task-upgrade)); don't restart.
- **`docs/log/` missing** → first task in the project → create the directory and `index.md` as part of the first `request.md` step.
- **Confused which N to use** → N is the iteration number, not a counter. All documents in one forward pass share the same N. Increment on new task or when backtracking forces a redo.
- **Verification can't actually run the code** (no working env, no test fixtures) → state that explicitly in `verify.md`: list which criteria are ✅ by static means and which are ⚠️ because runtime verification wasn't possible. Surface this in the reply to the user so they decide whether to ship.
