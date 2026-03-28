---
name: managing-projects
description: "Manages project entries in the Pandemonium bot config.yaml — add, remove, list, and validate projects. Triggers when the user asks to add a project, register a new project, remove a project, list configured projects, or change a project path. Also triggers on phrases like 'добавь проект', 'новый проект', 'удали проект', 'какие проекты', 'смени путь проекта'. Does NOT apply to creating new codebases or scaffolding — only to managing the bot's project registry in config.yaml."
---

# Managing Projects

Add, remove, list, and validate project entries in the Pandemonium bot's `config.yaml`.

---

## Default Project

Проект бота (`pandemonium-bot`) **всегда** является дефолтным проектом (`projects[0]`). При старте бот автоматически:
- Находит свой проект по совпадению `path` с корнем бота
- Перемещает его на первую позицию в списке
- Если проект не найден — добавляет его автоматически

**Добавление нового проекта не делает его дефолтным.** Новые проекты добавляются после `pandemonium-bot`.

Нельзя удалить проект `pandemonium-bot` — он системный.

---

## Active Project

В сессии бота хранится **активный проект** — проект, с которым пользователь работает в данный момент. При переключении активного проекта:
- Claude Code session сбрасывается (для загрузки контекста нового проекта)
- Агент читает `.agent/` директорию активного проекта (персоны, души, скилы, воркфлоу)
- CRUD операции с персонами/душами/скилами работают в `.agent/` активного проекта

---

## Context

The bot works with projects defined in `config.yaml` under the `projects:` key. Each project has three fields:

```yaml
projects:
  - id: "my-app"        # unique kebab-case identifier
    name: "My Application"  # human-readable name
    path: "/absolute/path/to/project"  # must exist on disk
```

The config file lives in the project root: `config.yaml` (gitignored). The example is `config.example.yaml`.

Pydantic validates `path` on load — the directory must exist, otherwise the bot won't start.

---

## Add a Project

1. Read `config.yaml` from the project root.
2. Ask the user for missing fields (if not provided):
   - `id` — short kebab-case identifier (e.g. `my-api`, `frontend`)
   - `name` — human-readable name
   - `path` — absolute path to the project directory
3. Validate before writing:
   - `id` is unique among existing projects
   - `id` is kebab-case (lowercase, hyphens, no spaces)
   - `path` exists on disk and is a directory
4. Append the new entry under `projects:` in `config.yaml`.
5. Report the result.

### Example

User: "добавь проект filestorage, путь /mnt/b/projects/filestorage2"

```yaml
# Added to config.yaml:
projects:
  - id: "pandemonium-bot"
    name: "Pandemonium Bot"
    path: "/mnt/b/projects/pandemonium-bot"
  - id: "filestorage"
    name: "filestorage"
    path: "/mnt/b/projects/filestorage2"
```

---

## Remove a Project

1. Read `config.yaml`.
2. Find the project by `id` (or `name` if unambiguous).
3. Remove the entry from `projects:`.
4. Report what was removed.

If only one project remains, warn the user — the bot requires at least one project.

**Cannot remove `pandemonium-bot`** — it is the system default project.

---

## Switch Active Project

Когда пользователь говорит, что хочет работать с проектом (например: «работаю с filestorage», «переключись на my-app»):

1. Найти проект по `id` или `name` в `config.yaml`.
2. Переключить активный проект в сессии.
3. Загрузить контекст проекта — прочитать `.agent/` директорию:
   - `.agent/persones/` — персоны проекта
   - `.agent/souls/` — души проекта
   - `.agent/skills/` — скилы проекта
   - `.agent/workflows/` — воркфлоу проекта
   - `.agent/rules/` — правила проекта
4. Если `.agent/` не существует — сообщить пользователю, что проект не содержит агентной конфигурации.
5. Сообщить о переключении.

---

## List Projects

1. Read `config.yaml`.
2. Output a table:

```
| ID          | Name             | Path                              |
|-------------|------------------|-----------------------------------|
| my-app      | My Application   | /mnt/b/projects/my-app            |
```

3. For each project, check if the path exists on disk and note any missing paths.

---

## Update Project Path

1. Read `config.yaml`.
2. Find the project by `id`.
3. Validate the new path exists on disk.
4. Update the `path` field.
5. Report the change.

---

## Validation Rules

| Rule | Why |
|------|-----|
| `id` must be unique | The bot indexes sessions and storage by `project_id` |
| `id` must be kebab-case | Convention enforced across the project |
| `path` must exist and be a directory | Pydantic validates this on config load — bot won't start otherwise |
| At least one project required | Bot expects `config.projects[0]` as default project |

---

## After Changes

Remind the user: the bot must be restarted for config changes to take effect. Use the `managing-bot` skill or run `./restart.sh`.

---

## Update Persona Registry

При добавлении нового проекта — просканировать его `.agent/personas/` и добавить найденные персоны в `.agent/persona-registry.yaml` pandemonium-bot.

При удалении проекта — удалить все его персоны из реестра.

Формат записи в реестре:

```yaml
persona-name:
  project: project-id
  path: /absolute/path/to/project
  soul: soul-name | null
  triggers:
    - trigger 1
    - trigger 2
```

Значения `soul` и `triggers` берутся из frontmatter файла `PERSONA.md`.
