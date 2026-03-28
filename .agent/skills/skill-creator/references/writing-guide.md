# Writing Guide for Skills

Detailed guidance on writing effective SKILL.md files. Read this when authoring a skill body.

---

## Core Principle: Context Budget

The context window is shared between the system prompt, conversation history, all skill metadata, and your actual request. Every token in a skill body competes with everything else.

**Default assumption: the agent is already smart.** Only add what the agent doesn't already know.

Ask for each paragraph:
- Does the agent really need this?
- Can the agent infer this from general knowledge?
- Does this justify its token cost?

---

## Progressive Disclosure

Skills load in three stages:

| Level | Content | When loaded |
|---|---|---|
| 1 — Metadata | `name` + `description` from frontmatter (~100 tokens) | Always, at startup |
| 2 — Instructions | Full `SKILL.md` body (<500 lines ideal) | When skill triggers |
| 3 — Resources | Files in `references/`, `scripts/`, `assets/` | Only when referenced |

**Design for this:** the body should cover the 80% common case. Edge cases, large tables, and variant-specific info belong in `references/`.

When a skill supports multiple domains, organize by variant:
```
cloud-deploy/
├── SKILL.md        ← workflow + selection logic
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```
The agent reads only the relevant file for the task at hand.

---

## Writing Style

### Imperative form

Write instructions as commands to the agent.

```
✅  Run the validation script before committing.
✅  Check .agent/rules/ for existing triggers.

❌  You should run the validation script.
❌  The agent will check .agent/rules/.
❌  Claude can run the validation script.
```

### Explain the why

LLMs respond better to reasoning than to arbitrary rules. When you need the agent to follow a specific behavior, explain why it matters.

```
❌  ALWAYS use third-person in descriptions.

✅  Write descriptions in third-person ("Analyzes Excel files…").
    The description is injected into the system prompt — inconsistent
    point-of-view confuses the model during discovery.
```

If you find yourself writing ALWAYS/NEVER/MUST in all-caps, that's a signal to step back and explain the reason instead.

### No second-person

Don't address the agent using "you" or treat the agent as the grammatical subject of imperative sentences directed *at the reader*. Skills are instructions the agent follows, not a conversation with a person.

Mentioning the user as an *object of the agent's action* is fine — the problem is using "you" to address whoever is reading.

```
❌  You should ask the user for their preferred output format.
❌  You can choose between JSON and CSV output.

✅  Present two format options to the user and let them choose.
✅  Output either JSON or CSV depending on what the user requested.
```

### Theory of mind

Write as if explaining to a smart colleague, not programming a robot. LLMs generalize better when they understand the intent.

```
❌  Step 1: Read file. Step 2: Extract field. Step 3: Validate. Step 4: Output.

✅  The goal is to extract X from the file and validate it against Y.
    Start by reading the file, then locate the field (it may be nested
    under different keys depending on version), validate against Y's rules,
    and present the result with any validation errors highlighted.
```

---

## Output Templates

When output format matters, provide a template. Agents follow templates precisely.

**For strict requirements:**
```markdown
## Report structure

Use this exact template:

# [Title]
## Executive Summary
[One paragraph]

## Key Findings
- Finding with evidence
- Finding with evidence

## Recommendations
1. Actionable step
2. Actionable step
```

**For flexible guidance:**
```markdown
## Report structure

Sensible default — adapt to context:

# [Title]
## Executive Summary
[Overview]
## Key Findings
[Adjust sections based on what you find]
```

---

## Examples Pattern

Concrete input→output pairs are more effective than abstract descriptions.

```markdown
## Commit message format

**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication

**Example 2:**
Input: Fixed bug where dates displayed incorrectly in reports
Output: fix(reports): correct date formatting in timezone conversion
```

---

## Decision Tree Pattern

Use a decision tree when a skill describes a **choice between 2+ approaches** and the agent needs to land on the right one quickly — without reading the entire document.

When to apply:
- The skill body contains "if X then A, else B" logic
- There are 3+ mutually exclusive patterns and the selection criteria are clear
- Context clues (file path, framework, task type) determine which path to take

Recommended format — `text` block with `├─ YES →` / `└─ NO  →` branches:

```
Does condition X apply?
├─ YES → Use pattern A — because reason
└─ NO  → Does condition Y apply?
    ├─ YES → Use pattern B
    └─ NO  → Use pattern C (default)
```

Place the decision tree **at the top of the skill body** (or at the top of the relevant section in `references/`). The agent scans it first and finds the right pattern without reading everything else.

---

## Checklist Pattern

For multi-step workflows where order matters and steps are easy to skip.

For simple checklists:

```markdown
## Pre-commit checklist

Before committing:

- [ ] Run linter: `pnpm lint`
- [ ] Run type check: `pnpm tsc --noEmit`
- [ ] Verify no `as` casts added
- [ ] Check git diff — no unintended changes
```

For complex workflows, use **grouped multi-level checklists** so the agent can triage priority:

```markdown
## Pre-commit checklist

**Critical (block commit)**
- [ ] No `as` casts in production code
- [ ] `quick_validate.py` passes
- [ ] No hardcoded secrets or paths

**Important (fix before merge)**
- [ ] JSDoc updated for all changed public APIs
- [ ] Integration audit done (rules, workflows, cross-skill refs)

**Patterns**
- [ ] Decision tree present if ≥2 approaches exist
- [ ] `evals/trigger-evals.json` created or updated
```

Grouping helps the agent prioritise correctly: critical items block immediately, pattern checks run at the end.


## Anti-Patterns

### Too verbose

```
❌  PDF (Portable Document Format) files are a common file format that
    contains text, images, and other content. To extract text from a
    PDF, you'll need to use a library...

✅  Use pdfplumber for text extraction:
    import pdfplumber
    with pdfplumber.open("file.pdf") as pdf:
        text = pdf.pages[0].extract_text()
```

### Overfitting to examples

```
❌  When the user mentions "Q4 sales report" specifically, use pivot tables.

✅  For financial reports, use pivot tables to aggregate data by time period.
```

Fiddly, narrow conditions break on any input that doesn't match exactly.

### Rigid chaining without reasoning

```
❌  Step 1: Do X. Step 2: Do Y. Step 3: Do Z. Always in this order.

✅  Start with X to understand the scope. Then do Y (which depends on X's output).
    Finally Z — this must come last because it modifies state that X and Y read.
```

### Phantom references

```
❌  Run scripts/validate.sh to check the output.
    (if scripts/validate.sh doesn't exist)
```

Never reference a file, script, or resource that isn't actually present in the skill directory.

---

## Scripts vs Instructions

| Use instructions | Use scripts |
|---|---|
| Flexible reasoning needed | Deterministic transformation |
| Output depends on context | Same operation every time |
| Decision-making | Parsing, sorting, formatting |
| Interpretation | Validation with fixed rules |

Scripts in `scripts/` are executed via bash. The script's **source code never loads into context** — only its output does. This makes scripts extremely efficient for repetitive or large transformations.

---

## Pattern Catalogue + Anti-Patterns

For skills with **5+ distinct patterns**, keep `SKILL.md` compact by splitting pattern documentation into two dedicated reference files:

| File | Purpose |
|---|---|
| `references/pattern-catalogue.md` | Positive catalogue: full code examples, when to use, why |
| `references/anti-patterns.md` | Negative catalogue: named anti-patterns with symptom, cause, fix |

`SKILL.md` references these files but **never duplicates their examples**.

### Format for `anti-patterns.md`

```markdown
## AP-N: <Name>
**Symptom:** what the developer sees
**Cause:** why this is wrong
**Instead:** correct pattern with example
```

Example:

```markdown
## AP-1: Hardcoded hex colour
**Symptom:** `color: '#949494'` in component styles.
**Cause:** Bypasses the theme system — won't respond to theme changes and breaks design-token traceability.
**Instead:** Use a theme callback: `css(({ theme }) => ({ color: theme.palette.icon.secondary }))` or the token constant.
```

### Format for `pattern-catalogue.md`

````markdown
## Pattern N: <Name>
**When to use:** ...
**Why:** ...

```tsx
// full working example
```
````

Prefer this split over a monolithic `SKILL.md` when the inline examples would push the file past ~300 lines.

---

## Debugging / Common Failures

For skills involving tools or frameworks with **non-obvious behaviour**, add a Debugging section.

Use a symptom-cause-fix table pattern:

```markdown
## Debugging

| Symptom | Cause | Fix |
|---|---|---|
| ... | ... | ... |
```

Or bullet format:

```markdown
## Debugging

- **No output generated** → missing `evals/` directory → create it before running the eval script
- **`quick_validate.py` reports unexpected top-level keys** → community-installed skill with non-spec fields (`risk`, `source`) → move those fields under `metadata:` or ignore for read-only community skills
- **Skill never triggers despite matching description** → description contains XML angle brackets → remove `<` and `>` characters
```

Apply this section to skills that interact with external tools (CLIs, APIs, validators) where failure modes are hard to diagnose from error messages alone.

---

## When to Split Into References

Move content to `references/` when:
- It's needed only in specific scenarios (not every invocation)
- It's > ~100 lines
- It's framework/provider-specific (e.g., `references/aws.md`)
- It's dense reference material (schemas, API docs, tables)

Reference clearly from the SKILL.md body:
```markdown
For form filling specifics, read `references/forms.md` before proceeding.
```

If a reference file is > 300 lines, add a table of contents at the top.
