---
name: remembering
description: "Saves and recalls information in the active persona's memory. Triggers when the user asks to remember, save, note, recall, or forget something — or when the conversation reveals important context worth preserving for future sessions. Also triggers on: 'запомни', 'запиши', 'сохрани', 'напомни', 'вспомни', 'забудь', 'что ты помнишь', 'что я тебе говорил'. Does NOT apply to writing code, creating files for the project, or managing tasks."
---

# Remembering

Save and recall information across conversations using per-persona memory storage.

## How Memory Works

Each persona has a private directory: `.agent/persones/.{persona_name}/memory/`.

Memory is a collection of small Markdown files — one fact per file. Files are named descriptively in kebab-case (e.g., `user-prefers-terse-responses.md`, `project-deadline-april-15.md`).

An `INDEX.md` file in the memory directory serves as a quick-lookup table — one line per memory, so the persona can scan what it knows without reading every file.

### Memory Types

| Type | Purpose | Example |
|------|---------|---------|
| `user` | Who the user is, their preferences, expertise | "User is a senior backend dev, prefers concise answers" |
| `feedback` | How the user wants work done — corrections and confirmations | "Don't add type annotations to unchanged code" |
| `project` | Ongoing work, decisions, deadlines | "Merge freeze starts 2026-04-01 for release" |
| `reference` | Pointers to external resources | "Bug tracker: Linear project INGEST" |

## Saving a Memory

1. Determine the memory type from the table above.
2. Check `INDEX.md` — does a similar memory already exist? If yes, update that file instead of creating a new one.
3. Write the memory file:

```markdown
---
type: {user|feedback|project|reference}
date: {YYYY-MM-DD}
---

{Memory content. Be specific and concise.
For feedback/project types, include **Why:** and **How to apply:** lines.}
```

4. Update `INDEX.md` — add or update a one-line entry:

```markdown
- [{short title}]({filename}.md) — {one-line description}
```

### File Naming

- kebab-case, descriptive: `user-prefers-russian.md`, `deploy-freeze-april.md`
- No generic names: `note1.md`, `memory.md`, `temp.md`

### What to Save

- User preferences, role, expertise
- Corrections: "don't do X" / confirmations: "yes, keep doing Y"
- Project decisions, deadlines, constraints
- Pointers to external tools and resources

### What NOT to Save

- Code patterns or architecture — read the code instead
- Git history — use `git log`
- Ephemeral task state — use tasks/plans instead
- Anything already in CLAUDE.md or docs/

## Recalling Memories

1. Read `INDEX.md` from the active persona's memory directory.
2. Scan entries for relevance to the current question.
3. Read the full memory file only for entries that seem relevant.
4. Before acting on a memory — verify it's still current (e.g., if it names a file, check the file exists).

Stale memories should be updated or removed on the spot.

## Forgetting

When the user asks to forget something:

1. Find the relevant entry in `INDEX.md`.
2. Delete the memory file.
3. Remove the line from `INDEX.md`.

## Memory Directory Structure

```
.agent/persones/.{persona_name}/
└── memory/
    ├── INDEX.md
    ├── user-prefers-russian.md
    ├── feedback-no-trailing-summaries.md
    └── project-rename-tca-to-pandemonium.md
```

## For Other Personas

Any persona can use this skill. The memory directory is always at:

```
.agent/persones/.{active_persona_name}/memory/
```

Each persona has isolated memory — one persona does not read another's memories unless explicitly asked to.

When adopting this skill, the persona must:
1. Know its own directory name (`.{persona_name}` in snake_case matching the persona file)
2. Create `INDEX.md` on first write if it doesn't exist
3. Read `INDEX.md` at the start of a conversation if memory is relevant
