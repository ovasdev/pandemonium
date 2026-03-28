# Brainstorming — Pattern Catalogue

Proven facilitation patterns used across the brainstorming workflow. Apply these deliberately, not by accident.

---

## PC-1: Decision Tree Entry

**When to apply:** Every session start.

**Pattern:** Before asking a single question, determine the correct entry point:

```text
Has the user confirmed a design?
├─ YES, confirmed → exit; hand off to implementation
├─ YES, draft/hypothesis → Step 4 (Understanding Lock)
└─ NO, vague idea → Step 1 (Read Context)
```

**Why it matters:** Skipping the entry decision wastes steps — a user with a near-final design doesn't need 5 rounds of clarification.

---

## PC-2: Single-Track Questioning

**When to apply:** Step 2 (Clarify the Idea).

**Pattern:** One question per message. Prefer multiple-choice:
> "Is this feature blocking a release, or is it exploratory work for the next quarter?"

If the topic requires depth, decompose sequentially across messages rather than packing questions together.

**Why it matters:** Multiple questions trigger satisficing — users pick whichever is easiest to answer and skip the rest. Sequential questions surface better signal.

---

## PC-3: Explicit Assumption Flagging

**When to apply:** Step 3 (NFR) and throughout the session whenever something is assumed rather than confirmed.

**Pattern:** Always mark assumptions visibly:
> *"Assumption: ≤10 000 MAU, so synchronous delivery is fine. Does that hold?"*

Log each assumption in the running list under the Understanding Summary.

**Why it matters:** Unmarked assumptions become invisible constraints. When they turn out to be wrong, the design collapses silently.

---

## PC-4: Trade-off Matrix (Step 5)

**When to apply:** Step 5 (Explore Approaches), when presenting 2–3 options.

**Pattern:** Present options in a table for quick scanning:

| Approach | Complexity | Extensibility | Risk |
|----------|-----------|---------------|------|
| Option A (recommended) | Low | Medium | Low |
| Option B | Medium | High | Medium |
| Option C | High | High | High |

Lead with the recommended option. Explain each trade-off in 1–2 sentences below the table.

**Why it matters:** Inline prose trade-off comparisons across 3 options are cognitively expensive. A table lets the user absorb differences instantly.

---

## PC-5: Progressive Design Disclosure (Step 6)

**When to apply:** Step 6 (Present the Design).

**Pattern:** Break the design into sections of 200–300 words max. After each section, ask:
> "Does this look right so far?"

Do not present the entire design as one block.

**Why it matters:** A full design dump (500+ words) is hard to review. Chunking creates natural feedback checkpoints and catches misalignments early, before the user is committed to a large design they partially don't agree with.

---

## PC-6: Living Decision Log (Step 7)

**When to apply:** Throughout the entire session, updated after every confirmed decision.

**Pattern:**

```markdown
## Decision Log

| Decision | Alternatives Considered | Why Chosen |
|----------|------------------------|------------|
| Synchronous delivery | Domain events, microservice | Scale doesn't justify async complexity |
| Read-time grouping | Write-time aggregation | Simpler; no background job needed |
```

**Why it matters:** The decision log is not a summary — it's a trace of the reasoning. It feeds directly into the final design document and guards against revisiting settled decisions.
