---
name: skill-creator
description: "Creates and iteratively improves Agent Skills following the Anthropic Agent Skills specification. Triggers when the user asks to create a new skill, rewrite or improve an existing skill, or package domain knowledge into reusable agent instructions — even when the word 'skill' isn't used explicitly. If the user describes a repeatable workflow, process, or expertise area they want to automate or codify for Claude, this skill applies. Also triggers for editing, auditing, or reviewing existing SKILL.md files. Does NOT apply to one-off tasks or always-on behavioral constraints that belong in a system prompt rather than a skill."
---

# Skill Creator

Creates and iteratively improves Agent Skills following Anthropic's Agent Skills specification.

Core loop: **capture intent → write draft → validate → self-test → iterate**.

---

## Two Entry Points

Is this for an existing skill?
- **YES** → Read the current SKILL.md in full, compare against the checklist below, add what's missing without rewriting what works, then continue from Step 4: Self-Test.
- **NO** → Start from Step 1: Capture Intent.

When improving an existing skill: preserve the `name` field unchanged — it is the skill's identity and must match the folder name.

---

## Step 1: Capture Intent

First, decide: **skill or system prompt instruction?**

- **Skill** — domain expertise or a repeatable workflow triggered on demand when relevant. Packaged as a folder with SKILL.md. Lives alongside other skills; can be enabled or disabled independently.
- **System prompt instruction** — an always-on behavioral constraint ("always respond in Russian", "never use semicolons"). This belongs in the system prompt, not in a skill.

If it's a system prompt instruction → stop. Help the user phrase it correctly for their system prompt instead.

If it's a skill, extract from context (the current conversation may already demonstrate the workflow):

1. What should this skill enable Claude to do?
2. When should it trigger? (user phrases, domains, file types, situations)
3. What is the expected output or behavior?
4. Is this a repeatable workflow or a one-off? (repeatable → good skill candidate)
5. Which category fits best?
   - **Document & Asset Creation** — generating consistent output: documents, designs, code, presentations
   - **Workflow Automation** — multi-step processes that benefit from consistent methodology
   - **MCP Enhancement** — workflow guidance layered on top of an MCP server's tool access

If the user already has a draft SKILL.md, skip to Step 3: Validate.

---

## Step 2: Check for Related Skills

Before writing, scan available skills for overlap. Avoid duplicating existing capabilities; identify where to add cross-references instead. If another skill covers adjacent territory, plan to add a `See also:` note in both.

---

## Step 3: Write the SKILL.md

### Folder structure

```
your-skill-name/
├── SKILL.md          ← required; must be named exactly SKILL.md (case-sensitive)
├── references/       ← detailed docs loaded only when needed
├── scripts/          ← executable scripts; output enters context, source does not
└── assets/           ← templates, fonts, icons used in output
```

**Critical naming rules:**
- Folder name: kebab-case only (`my-skill`, not `My Skill`, `my_skill`, or `MySkill`)
- File name: exactly `SKILL.md` — no variations (`skill.md`, `SKILL.MD`) are accepted
- Do not include `README.md` inside the skill folder; all documentation goes in `SKILL.md` or `references/`
- Do not use `claude` or `anthropic` in the skill name (reserved)

### Frontmatter

```yaml
---
name: skill-name           # required: kebab-case, matches folder name exactly
description: "..."         # required: max 1024 chars, no XML angle brackets (< >)
license: MIT               # optional: for open-source skills
compatibility: "..."       # optional: environment requirements ("Requires Python 3.11, docker")
metadata:                  # optional: arbitrary key-value pairs
  author: Your Name
  version: "1.0.0"
  mcp-server: service-name
---
```

**`name` rules:** lowercase letters, numbers, hyphens only. No spaces, no capitals, no leading/trailing/consecutive hyphens. Must exactly match the folder name.

**`description` rules:**
- Must include BOTH: what the skill does AND when to use it (trigger conditions)
- Be specific: include phrases users would actually say, mention relevant file types
- Avoid vague phrasing ("Helps with projects" won't trigger reliably)
- Max 1024 characters, no XML angle brackets (`<` or `>`)
- Add negative triggers when the skill risks overlapping with others: "Do NOT use for simple data exploration."

Good description structure: `[What it does] + [When to trigger] + [Key capabilities]`

```
# Good
description: Analyzes Figma design files and generates developer handoff docs.
Use when user uploads .fig files, asks for "design specs", "component documentation",
or "design-to-code handoff".

# Bad — too vague, no trigger phrases
description: Helps with projects.
```

### Body: writing rules

Keep `SKILL.md` under **5,000 words**. Move anything beyond that to `references/` and link to it.

- **Imperative form**: "Run the script" — not "You should run" or "Claude will run"
- **Explain the why**: reasoning is more effective than bare prohibitions. Instead of `NEVER do X`, explain what goes wrong when X happens.
- **Progressive disclosure**: keep the body focused on the core workflow; edge cases and large reference tables go in `references/`
- **Output templates**: when format matters, provide an exact template — Claude follows them precisely
- **Concrete examples**: input → output pairs outperform abstract descriptions

### When to use `references/`

Move content here when it is only needed in specific scenarios (e.g. `references/aws.md`, `references/gcp.md`), when it is a large table or API schema, or when any block exceeds ~100 lines and is not always relevant. Reference it explicitly from the body so Claude knows when to load it.

### When to use `scripts/`

Use scripts for deterministic, repetitive operations where correctness matters more than flexibility (parsing, validation, transformation). The script runs via bash; only its output enters the context window — the source never does.

### Naming conventions

Prefer **gerund form**: `processing-pdfs`, `analyzing-spreadsheets`, `reviewing-code`.

Avoid generic names: `helper`, `utils`, `tools`, `data`, `documents`.

---

## Step 4: Self-Test

Test the skill by applying it yourself before handing it to the user.

1. Write 2–3 realistic prompts a real user would send. Include at least one ambiguous edge case — something close to the skill's domain that might plausibly go elsewhere.
2. For each prompt, apply the skill's instructions as if you are the agent. Trace the steps.
3. Present results in this format and ask "Does this match what you expected?":

```
Prompt 1: "<realistic user message>"
→ Triggers skill: yes/no
→ What agent does: <step-by-step trace>
→ Output: <what user sees>

Prompt 2: ...

Edge case: "<ambiguous prompt>"
→ Triggers skill: yes/no — because <reason>
→ What agent does: ...
```

Focus on: does the skill trigger on the right prompts? Does it produce the right format? Does it handle edge cases gracefully?

---

## Step 5: Iterate

Apply user feedback using this table:

| Problem | Fix |
|---|---|
| Undertriggering | Add more trigger phrase variants; be more specific in description |
| Overtriggering | Add explicit "Do NOT use when…" to description or body |
| Wrong output format | Add an explicit output template to the body |
| Instructions ignored | Add the *why* — explain the reasoning, not just the rule |
| Body too long | Move reference content to `references/`; keep only the core procedure in the body |
| Works only for test cases | Generalize — avoid overfit conditions; use principles over specific patterns |

Avoid bare MUST/ALWAYS/NEVER rules. If you find yourself writing one, it is a signal to explain the reasoning instead.

---

## Step 6: Trigger Evaluation

After the body is stable, optimize the description for triggering accuracy.

Generate 10–18 trigger eval queries — a realistic mix of:
- **should-trigger (6–10):** same intent phrased formally, casually, with typos, without naming the skill explicitly
- **should-not-trigger (3–5):** near-misses sharing vocabulary but needing something else
- **ambiguous (2–3):** borderline cases where the correct answer is debatable

Realistic queries include personal context, file paths, casual phrasing — never abstract ("process data").

Present the eval set to the user for review. Iteratively revise the description by analyzing which queries misfire and why.

If the environment supports it, save evals to `evals/trigger-evals.json` as a permanent regression suite:

```json
{
  "skill": "skill-name",
  "evals": [
    { "id": "ST-01", "priority": "core", "query": "...", "should_trigger": true, "reason": "..." },
    { "id": "SN-01", "query": "...", "should_trigger": false, "reason": "..." },
    { "id": "AM-01", "query": "...", "should_trigger": true, "reason": "Borderline: ..." }
  ]
}
```

Groups: `ST-*` (should trigger), `SN-*` (should not), `AM-*` (ambiguous). For `ST-*` entries, mark `"priority": "core"` for must-trigger queries and `"edge"` for less critical ones.

---

## Pre-Upload Checklist

**Critical — fix before uploading**
- [ ] Folder named in kebab-case; matches `name` field exactly
- [ ] File named exactly `SKILL.md` (case-sensitive)
- [ ] YAML frontmatter has `---` delimiters on both sides
- [ ] `name`: kebab-case only, no spaces or capitals
- [ ] `description`: includes WHAT and WHEN; ≤1024 chars; no XML angle brackets
- [ ] No `README.md` inside the skill folder
- [ ] No references to scripts or files that don't exist

**Important — fix before sharing**
- [ ] Description includes specific trigger phrases users would actually say
- [ ] Body uses imperative form throughout
- [ ] Body is under 5,000 words; overflow moved to `references/`
- [ ] Error handling covered for foreseeable failure cases
- [ ] If skill uses MCP: MCP tool names are correct and case-sensitive references verified
- [ ] Related skills checked; cross-references added where relevant

**Patterns — recommended for quality**
- [ ] Decision tree present if the skill describes two or more approaches
- [ ] Concrete examples provided (input → output pairs)
- [ ] Trigger eval queries generated and reviewed

---

## Troubleshooting

**Skill won't upload: "Could not find SKILL.md"**
Cause: file not named exactly `SKILL.md`. Rename it (case-sensitive). Verify with `ls -la`.

**Skill won't upload: "Invalid frontmatter"**
Cause: YAML formatting error. Common mistakes:
```yaml
# Wrong — missing --- delimiters
name: my-skill

# Wrong — unclosed quote
description: "Does things

# Correct
---
name: my-skill
description: Does things
---
```

**Skill won't upload: "Invalid skill name"**
Cause: spaces or capitals in `name`. Use `my-cool-skill`, not `My Cool Skill`.

**Skill never triggers**
Revise the `description` field. Quick checklist: Is it too generic? Does it include phrases users would actually say? Does it mention relevant file types? Debug by asking Claude: "When would you use the [skill name] skill?" — Claude will quote the description back. Adjust based on what's missing.

**Skill triggers too often**
Add negative triggers to the description: "Do NOT use for simple data exploration (use data-viz skill instead)." Narrow the scope with more specific phrasing.

**MCP calls fail when skill loads**
Test MCP independently first: ask Claude to call the MCP tool directly without the skill. If that fails, the issue is in the MCP connection, not the skill. Verify tool names are correct — they are case-sensitive.

**Instructions not followed**
Keep instructions concise; put the most critical steps at the top. Add explicit reasoning for requirements. For critical validations, consider a script in `scripts/` — deterministic code is more reliable than language instructions.
