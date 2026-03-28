# Brainstorming — Anti-Patterns

Common facilitation mistakes that break the brainstorming loop. Recognise these early and correct them before the session drifts.

---

## AP-1: Jumping to Solution

**What it looks like:** Proposing a design or architecture before the Understanding Lock (Step 4) has been confirmed.

**Why it's harmful:** The agent designs for its own interpretation of the problem, not the user's. When requirements turn out to be different, the proposed design must be thrown away — wasting both time and rapport.

**Correct behaviour:** Complete Steps 1–3, produce the Understanding Summary, get explicit confirmation, *then* propose approaches.

---

## AP-2: Compound Questions

**What it looks like:**
> "Is this server-rendered or client-rendered? And should it use WebSockets or polling? Oh, and what's the expected load?"

**Why it's harmful:** Asking several questions at once creates decision paralysis. The user can't answer all of them coherently, answers become vague, and the session stalls.

**Correct behaviour:** One question per message. If depth is needed on a topic, decompose into sequential follow-ups.

---

## AP-3: Skipping Non-Functional Requirements

**What it looks like:** Moving from clarification straight to design without addressing performance, scale, security, or reliability.

**Why it's harmful:** NFRs silently constrain architectural options. A design that's correct for 100 users is wrong for 100 000. Discovering scale requirements after the design is proposed forces a complete restart.

**Correct behaviour:** Step 3 is mandatory — always surface NFR assumptions. If the user is unsure, propose defaults and mark them explicitly:
> *"Assuming ≤10 000 MAU — async queue not needed yet. Correct?"*

---

## AP-4: Infinite Clarification Loop

**What it looks like:** Asking questions indefinitely, never reaching the Understanding Lock or design proposal.

**Why it's harmful:** The user came to make a decision. Endless dialogue without progress erodes trust and burns session budget.

**Correct behaviour:** After 4–6 questions, consolidate what's known into the Understanding Summary (Step 4) even if some things are uncertain. Surface remaining open questions explicitly in the summary, then ask for confirmation.

---

## AP-5: Implementing During Brainstorm

**What it looks like:** Writing code, modifying files, or creating implementation artefacts while brainstorming mode is active.

**Why it's harmful:** Premature implementation embeds an unconfirmed design into the codebase. If the design changes during discussion, rollback is expensive and disruptive.

**Correct behaviour:** While this skill is active — design only. No project files are created or modified until the user explicitly accepts the design and the session hands off to implementation.
