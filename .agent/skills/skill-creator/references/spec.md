# Agent Skills Specification — Quick Reference

Source: https://agentskills.io/specification

---

## Frontmatter Fields

| Field | Required | Type | Constraints |
|---|---|---|---|
| `name` | ✅ | string | 1–64 chars; `[a-z0-9-]` only; no leading/trailing/consecutive hyphens; must match directory name |
| `description` | ✅ | string | 1–1024 chars; no XML angle brackets (`<`, `>`); non-empty |
| `license` | ❌ | string | SPDX identifier (e.g., `Apache-2.0`, `MIT`) |
| `compatibility` | ❌ | string | 1–500 chars; describes env requirements |
| `metadata` | ❌ | object | Arbitrary key-value pairs (`author`, `version`, `category`, etc.) |
| `allowed-tools` | ❌ | string (space-delimited) | Experimental; pre-approves tools. Format: `Bash(git:*) Read Write` |

**Important:** only these six fields are valid at the top level. Fields like `version`, `author`, `platforms`, `tags`, `risk` must be nested under `metadata:`.

---

## `name` Validation Rules

```
✅  pdf-processing
✅  analyzing-spreadsheets
✅  code-review-backend

❌  PDF-Processing     (uppercase)
❌  pdf processing     (spaces)
❌  -pdf-processing    (leading hyphen)
❌  pdf-processing-    (trailing hyphen)
❌  pdf--processing    (consecutive hyphens)
❌  anthropic-helper   (reserved word)
❌  claude-tools       (reserved word)
```

Reserved words that cannot appear in `name`: `anthropic`, `claude`.

---

## `description` Writing Rules

1. **Third-person** — "Analyzes files…" not "I can…" or "You can use this to…"
2. **Include what AND when** — "Extracts PDF text. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction."
3. **Pushy by design** — Claude undertriggers. Add: "Use this skill even if the user doesn't mention X explicitly — if they describe Y, this skill applies."
4. **Max 1024 characters** — count before saving
5. **No XML** — no `<` or `>` characters

---

## Directory Structure

```
skill-name/              ← directory name = name field
├── SKILL.md             ← required: frontmatter + body
├── references/          ← optional: docs loaded when referenced
│   ├── REFERENCE.md
│   └── domain.md
├── scripts/             ← optional: executable code
│   └── process.py
├── assets/              ← optional: templates, data, fonts
│   └── template.docx
└── evals/               ← optional: machine-readable trigger tests
    └── trigger-evals.json
```

### `evals/trigger-evals.json` format

```json
{
  "skill": "skill-name",
  "description": "Human-readable note about what these evals cover.",
  "evals": [
    { "id": "ST-01", "priority": "core", "query": "...", "should_trigger": true,  "reason": "..." },
    { "id": "ST-02", "priority": "edge", "query": "...", "should_trigger": true,  "reason": "..." },
    { "id": "SN-01",                     "query": "...", "should_trigger": false, "reason": "..." },
    { "id": "AM-01",                     "query": "...", "should_trigger": true,  "reason": "Borderline: ..." }
  ]
}
```

Groups: `ST-*` (should trigger), `SN-*` (should not trigger), `AM-*` (ambiguous).
The `priority` field applies only to `ST-*` entries: `"core"` = skill is useless without this trigger, `"edge"` = should trigger but failure is less critical.

---

## Progressive Disclosure (3 levels)

```
Level 1: name + description   → always loaded at startup (~100 tokens/skill)
Level 2: SKILL.md body        → loaded when skill triggers (<500 lines recommended)
Level 3: references/, scripts/ → loaded only when explicitly accessed by the agent
```

**Body limit:** 500 lines (platform.claude.com recommends this). Exceeding it degrades performance. Move overflow to `references/`.

---

## Discovery Locations

Agent clients scan these directories (in priority order).

> **Note:** The upstream Agent Skills spec uses `.agents/` (plural). This project uses `.agent/` (singular) — the Antigravity client scans `.agent/skills/` at the repo root.

**Upstream spec locations (general):**
```
<project>/.agents/skills/          ← project-level
<project>/.<client>/skills/        ← client-specific project
~/.agents/skills/                  ← user-level
~/.<client>/skills/                ← client-specific user
```

**This project (Antigravity):**
```
.agent/skills/
```

---

## Skill Catalog XML (how clients disclose skills to the model)

```xml
<available_skills>
  <skill>
    <name>pdf-processing</name>
    <description>Extract text from PDFs. Use when...</description>
    <location>/path/to/pdf-processing/SKILL.md</location>
  </skill>
</available_skills>
```

---

## Validation

Run the bundled script to validate **spec-compliant** skills (new skills you create, or skills before publishing):

> **Note:** Community-installed skills (e.g. installed via `install-skill`) may include extra top-level keys like `risk`, `source`, `date_added`. These are not part of the spec and will be flagged by the validator. That's expected — either ignore the warning for read-only community skills, or move those fields under `metadata:` to make them spec-compliant.

```bash
python3 .agent/skills/skill-creator/scripts/quick_validate.py .agent/skills/<skill-name>
```

Checks performed by the script:
- `SKILL.md` exists
- Valid YAML frontmatter (parseable)
- No unexpected top-level keys (only `name`, `description`, `license`, `allowed-tools`, `metadata`, `compatibility`)
- `name` present, non-empty, string type, regex `[a-z0-9-]+`, no leading/trailing/consecutive hyphens, length ≤64
- `description` present, non-empty, string type, length ≤1024, no XML angle brackets
- `compatibility` (if present): non-empty string, length ≤500

> **Not checked by script** (verify manually): `name` matches directory name, reserved words (`anthropic`, `claude`) absence.

---

## Naming Conventions (Best Practice)

**Gerund form (recommended):**
- `processing-pdfs`
- `analyzing-spreadsheets`
- `reviewing-code`
- `writing-documentation`

**Acceptable alternatives:**
- Noun phrase: `pdf-processing`, `code-review`
- Action: `process-pdfs`, `review-code`

**Avoid:**
- Vague standalone: `helper`, `utils`, `tools`, `data`, `files`, `documents`, `backend`, `frontend` (not descriptive enough on their own)
- Reserved: anything containing `anthropic` or `claude`

> **Note:** `backend`/`frontend` as *qualifiers* in a descriptive compound name are fine — e.g., `code-review-backend`, `code-review-frontend`. The rule is against them as the *entire* name.

---

## `allowed-tools` Format (Experimental)

Space-delimited list of pre-approved tool uses. Syntax depends on the client.

Examples:
```yaml
allowed-tools: Bash(git:*) Read Write
allowed-tools: Bash Read
```

Support varies between clients. Not all agents honor this field.

---

## `compatibility` Examples

```yaml
compatibility: "Requires git, Node.js 18+, pnpm"
compatibility: "Requires docker, docker compose"
compatibility: "Requires Python 3.11+, uv"
```

---

## Security Notes (from Anthropic)

- Treat skills like software packages — install only from trusted sources
- Audit all bundled files: `SKILL.md`, `scripts/`, `references/`, `assets/`
- Watch for unexpected network calls, file access patterns, or operations not matching the stated purpose
- Skills that fetch external URLs are particularly risky — content may contain malicious instructions
