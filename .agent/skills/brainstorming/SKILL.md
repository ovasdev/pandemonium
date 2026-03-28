---
name: brainstorming
description: "Facilitates structured design and ideation sessions before any implementation begins — transforms vague ideas into validated designs through disciplined dialogue. Use this skill when the user wants to think through a feature, architecture, behavior, or product decision before writing code. Triggers even when 'brainstorm' is not used explicitly — if the user says 'let's think through', 'how should we approach', 'I have an idea for', 'help me design', 'let's figure out', 'давай подумаем', 'как лучше сделать', 'обсудим архитектуру', 'есть идея', this skill applies. Does NOT apply when the user already has a confirmed design and is asking to implement it directly — in that case, skip to execution."
metadata:
  source: community
  date_added: "2026-02-27"
  version: "1.1.0"
---

# Brainstorming — Ideas Into Designs

Turns raw ideas into **clear, validated designs** through structured dialogue before any implementation begins.

Prevents: premature implementation, hidden assumptions, misaligned solutions, fragile systems.

Implementing before the design is understood leads to expensive rewrites and missed requirements. While this skill is active, act as a design facilitator only — do not implement, code, or modify any project files.

---

## Entry Point Decision

```text
Does the user have a design they want to discuss or refine?
├─ YES, and it's confirmed → Exit brainstorming; hand off to implementation
├─ YES, but it's a draft or hypothesis → Start from Step 4 (Understanding Lock)
└─ NO, idea is vague → Start from Step 1
```

---

## Pre-Session Checklist

Run this before Step 1 at the start of every session.

**Critical (hard gate — do not skip)**
- [ ] Entry point determined (vague idea / draft / confirmed design)
- [ ] Existing project context read (what already exists, what is new)
- [ ] No code or project files modified while this skill is active

**Important (complete before Step 5)**
- [ ] NFR assumptions surfaced and marked explicitly (Step 3)
- [ ] Understanding Lock confirmed by the user (Step 4)

**Patterns**
- [ ] Trade-off matrix used when presenting ≥2 approaches
- [ ] Decision Log updated after every confirmed decision
- [ ] Design output in sections of 200–300 words max (Step 6)

---

## Step 1: Read Context

Before asking any questions, review what's already in scope:

- Existing project files, docs, and prior decisions
- What already exists vs. what is proposed
- Implicit constraints that haven't been confirmed yet

Do not design yet — just understand the domain.

---

## Step 2: Clarify the Idea (One Question at a Time)

The goal is **shared clarity**, not speed.

Rules:
- Ask **one question per message** — multiple questions at once trigger satisficing: the user answers the easiest one and skips the rest, producing shallow signal
- Prefer **multiple-choice questions** when possible — they lower cognitive load and produce concrete answers
- Use open-ended questions only when necessary
- If a topic needs depth, decompose it into sequential follow-up questions rather than packing them together

Focus on:
- Purpose (what problem does this solve?)
- Target users
- Constraints (technical, business, time)
- Success criteria
- Explicit non-goals

---

## Step 3: Non-Functional Requirements (Mandatory)

Explicitly clarify or propose assumptions for:

- Performance expectations
- Scale (users, data, traffic)
- Security / privacy constraints
- Reliability / availability
- Maintenance and ownership

If the user is unsure — propose reasonable defaults and **mark them clearly as assumptions**.

---

## Step 4: Understanding Lock (Hard Gate)

Before proposing any design, pause and produce:

**Understanding Summary** (5–7 bullets):
- What is being built
- Why it exists
- Who it's for
- Key constraints
- Explicit non-goals

**Assumptions:** list all assumptions explicitly.

**Open Questions:** list anything unresolved.

Then ask:

> "Does this accurately reflect your intent? Please confirm or correct before we move to design."

Do not proceed until the user gives explicit confirmation.

---

## Step 5: Explore Approaches

Once understanding is confirmed, propose **2–3 viable approaches**:

- Lead with the recommended option
- Explain trade-offs: complexity, extensibility, risk, maintenance
- Apply YAGNI ruthlessly — skip anything not needed for the stated goals

This is still exploration, not final design.

---

## Step 6: Present the Design (Incrementally)

Break the design into sections of **200–300 words max**. After each section, ask:

> "Does this look right so far?"

Cover as relevant:
- Architecture
- Components
- Data flow
- Error handling
- Edge cases
- Testing strategy

---

## Step 7: Decision Log (Mandatory)

Maintain a running Decision Log throughout the session.

For each decision record:
- What was decided
- Alternatives considered
- Why this option was chosen

Preserve the log — it feeds into documentation and the implementation plan.

---

## After Design is Confirmed

### Documentation

Write the finalized design to Markdown using this template:

```markdown
# [Feature Name] — Design

## Understanding Summary
- What is being built:
- Why it exists:
- Who it's for:
- Key constraints:
- Explicit non-goals:

## Assumptions
- ...

## Decision Log

| Decision | Alternatives Considered | Why Chosen |
|----------|------------------------|------------|
| ...      | ...                    | ...        |

## Design

[Architecture / components / data flow / error handling / edge cases]
```

Persist according to the project's documentation conventions (e.g., `docs/specs/` in the relevant sub-repo).

### Implementation Handoff

Only after documentation is complete, ask:

> "Ready to move to implementation?"

If yes — create an explicit implementation plan and proceed incrementally.

---

## Exit Criteria (Hard Stop)

Exit brainstorming mode **only when all of the following are true**:

- [ ] Understanding Lock confirmed by the user
- [ ] At least one design approach explicitly accepted
- [ ] All major assumptions documented
- [ ] Key risks acknowledged
- [ ] Decision Log complete

If any criterion is unmet — continue refinement. Do not proceed to implementation.

---

## Debugging / Common Failures

- **Session stalls after 6+ questions with no design** — produce the Understanding Summary immediately even if some items are uncertain; surface remaining open questions as a list within it (see `references/anti-patterns.md` AP-4)
- **User says "that's not what I meant" after seeing the design** — Understanding Lock was skipped or confirmed too quickly; restart from Step 4, not Step 1
- **User asks to implement mid-session** — stay in facilitation mode; explain that implementing before the design is locked leads to expensive rewrites; complete the session first
- **Two approaches look equally good** — present a trade-off matrix (Complexity / Extensibility / Risk columns); if still tied, ask one priority question: "Simplicity now vs. extensibility later?" (see `references/pattern-catalogue.md` PC-4)
- **NFR assumptions turn out wrong after design is proposed** — mark the incorrect assumption, renegotiate the affected design section only; don't restart the whole session

---

> For concrete input→output examples of the full facilitation flow, read [`references/examples.md`](references/examples.md).

> For common facilitation mistakes and how to avoid them, read [`references/anti-patterns.md`](references/anti-patterns.md).

> For proven facilitation patterns with templates, read [`references/pattern-catalogue.md`](references/pattern-catalogue.md).

> See also: `feature-spec-writer` — when the brainstormed design is ready to be turned into structured spec documents for the cinemauthor sub-repos.
