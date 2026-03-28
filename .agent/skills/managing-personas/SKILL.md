---
name: managing-personas
description: "Creates, edits, lists, and removes agent personas in .agent/personas/. A persona defines a role with a set of competencies, assigned skills, and optionally a soul. Each persona lives in its own folder with a PERSONA.md main file. Triggers when the user asks to create a persona, add a new role, edit persona skills, assign a soul to a persona, list personas, or remove a persona. Also triggers on: 'создай персону', 'новая роль', 'добавь скил персоне', 'привяжи душу', 'какие персоны есть', 'удали персону'. Does NOT apply to creating skills themselves (use skill-creator) or creating souls (use managing-souls)."
---

# Managing Personas

Create, edit, list, and remove agent personas in `.agent/personas/`.

---

## Project Context

Персоны создаются в `.agent/personas/` **активного проекта**:

1. Определи активный проект — это проект, с которым пользователь сейчас работает.
2. Базовый путь: `{project.path}/.agent/personas/`.
3. Если директория `.agent/personas/` не существует — создай её (`mkdir -p`).
4. Все операции (создание, чтение, удаление) используют этот путь.

---

## What Is a Persona

A persona is a named agent role that bundles:

- **Идентификация** — имя, роль, стиль общения
- **Компетенции** — области знания и экспертиза
- **Скилы** — список скилов из `.agent/skills/`, которыми персона владеет
- **Душа** (опционально) — ссылка на душу из `.agent/souls/{soul-name}/SOUL.md`, задающую личностные характеристики
- **Память** (опционально) — хранится в той же папке персоны

Персона без души действует функционально — кратко, по делу, без эмоциональной окраски. Персона с душой приобретает характер, стиль мышления и пресуппозиционный контекст, заданный душой.

---

## File Structure

```
.agent/personas/
└── {persona-name}/        ← папка персоны (kebab-case)
    ├── PERSONA.md          ← главный файл (обязательный)
    └── memory/             ← память персоны (опционально)
        └── INDEX.md
```

Имя папки — kebab-case, совпадает с идентификатором персоны.

---

## Persona Template

```markdown
---
name: {persona-name}
soul: {soul-name | null}
triggers: ["trigger1", "trigger2", ...]
---

# {Display Name}

{Описание роли и компетенций персоны. Что персона знает, в чём разбирается, за что отвечает.}

## Принципы

- {Принцип 1}
- {Принцип 2}

## Стек / Инструменты

- {Технология или инструмент 1}
- {Технология или инструмент 2}

## Скилы

| Скил | Назначение |
|------|-----------|
| `skill-name` | Краткое описание |

## Антипаттерны

- {Чего не делать 1}
- {Чего не делать 2}
```

---

## Create a Persona

1. Спросить у пользователя (если не указано):
   - Имя и роль
   - Области компетенций
   - Какие скилы назначить (проверить, что существуют в `.agent/skills/`)
   - Нужна ли душа (если да — проверить, что папка существует в `.agent/souls/{soul-name}/SOUL.md`)
2. Проверить, что папка с таким именем ещё не существует в `.agent/personas/`.
3. Создать папку `{persona-name}/` и файл `PERSONA.md` по шаблону.
4. Если персоне назначен скил `remembering` — создать `memory/INDEX.md` в папке персоны.
5. Обновить реестр персон в `bot_administrator` (если существует).
6. Обновить `.agent/persona-registry.yaml` в pandemonium-bot — добавить/удалить запись персоны с полями `project`, `path`, `soul`, `triggers`.

### Validation

| Правило | Почему |
|---------|--------|
| Имя папки — kebab-case | Единообразие со скилами и душами |
| Главный файл — `PERSONA.md` | Аналогия со `SKILL.md` и `SOUL.md` |
| Скилы существуют в `.agent/skills/` | Ссылка на несуществующий скил бесполезна |
| Душа существует в `.agent/souls/{name}/SOUL.md` | Аналогично |
| Имя уникально | Не перезаписывать существующую персону без явного запроса |

---

## Edit a Persona

### Add a Skill

1. Прочитать `PERSONA.md` персоны.
2. Проверить, что скил существует в `.agent/skills/`.
3. Добавить строку в таблицу скилов.

### Remove a Skill

1. Прочитать `PERSONA.md` персоны.
2. Удалить строку из таблицы скилов.

### Assign a Soul

1. Проверить, что душа существует в `.agent/souls/{soul-name}/SOUL.md`.
2. Обновить поле `soul` во frontmatter.

### Detach a Soul

1. Установить поле `soul` в `null`.

---

## List Personas

1. Прочитать все `PERSONA.md` файлы в подпапках `.agent/personas/`.
2. Вывести таблицу:

```
| Персона            | Роль                        | Душа        | Скилов |
|--------------------|-----------------------------|-------------|--------|
| bot-administrator  | Административный агент      | —           | 14     |
```

---

## Remove a Persona

1. Подтвердить удаление у пользователя.
2. Удалить папку персоны целиком из `.agent/personas/`.
3. Обновить реестр в `bot_administrator`.
4. Удалить запись персоны из `.agent/persona-registry.yaml` в pandemonium-bot.

---

## Cross-references

- Для создания нового скила → `skill-creator`
- Для создания новой души → `managing-souls`
- Для управления проектами → `managing-projects`
- Для переключения между персонами → `switching-personas`
