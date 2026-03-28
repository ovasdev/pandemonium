---
name: switching-personas
description: "Switches the active agent persona based on user request or trigger match. Reads persona-registry.yaml to find the persona across all configured projects, loads PERSONA.md and optionally SOUL.md, and switches the working context to the persona's project. Triggers when the user addresses a persona by name, asks to switch roles, or uses a trigger phrase matching a registered persona. Also triggers on: 'переключись на', 'будь', 'говори как', 'верни персону', 'стань'. Does NOT apply to creating or editing personas (use managing-personas)."
---

# Switching Personas

Switch the active agent persona across all configured projects.

---

## Registry

Реестр персон: `.agent/persona-registry.yaml` в корне pandemonium-bot.

Формат записи:

```yaml
persona-name:
  project: project-id
  path: /absolute/path/to/project
  soul: soul-name | null
  triggers:
    - trigger phrase 1
    - trigger phrase 2
```

Реестр обновляется скилами `managing-personas` и `managing-projects`.

---

## When to Switch

Переключение происходит когда:

1. **Явный запрос** — пользователь называет персону по имени: «переключись на backend-engineer», «будь game-designer», «верни backend-engineer»
2. **Возврат к дефолту** — «верни администратора», «администрирование», административный запрос → переключение на `bot-administrator`
3. **По триггеру** — сообщение пользователя содержит триггерную фразу из реестра (матчинг по вхождению, регистронезависимо)

Приоритет: явный запрос > возврат к дефолту > триггер.

При конфликте триггеров (фраза матчит несколько персон) — не переключаться, уточнить у пользователя.

---

## Switching Procedure

### 1. Найти персону в реестре

Прочитать `.agent/persona-registry.yaml`. Найти запись по имени или триггеру.

Если персона не найдена — сообщить пользователю: «Персона `{name}` не найдена в реестре. Доступные персоны: ...»

### 2. Загрузить PERSONA.md

Прочитать `{path}/.agent/personas/{persona-name}/PERSONA.md`.

Если файл не найден — сообщить об ошибке (реестр устарел).

### 3. Загрузить душу (если есть)

Если `soul` не `null` — прочитать `{path}/.agent/souls/{soul}/SOUL.md`.

### 4. Загрузить контекст проекта (если проект отличается от текущего)

Если `project` персоны отличается от `PANDEMONIUM_ACTIVE_PROJECT_ID`:

1. Прочитать `{path}/CLAUDE.md` — дополняет базовые инструкции pandemonium-bot, не заменяет их.
2. Принять `{path}` как рабочую директорию.

Если проект совпадает — контекст уже загружен, пропустить.

### 5. Принять роль

Принять роль, стиль и компетенции из PERSONA.md. Если загружена душа — принять характер и пресуппозиции из SOUL.md.

---

## Returning to Default

Возврат к `bot-administrator`:

1. Загрузить `.agent/personas/bot-administrator/PERSONA.md` из pandemonium-bot
2. Вернуть рабочую директорию на pandemonium-bot (`/mnt/b/projects/pandemonium-bot`)
3. Сбросить контекст другого проекта

Возврат происходит при:
- Прямом обращении к администратору
- Административном запросе (создание персон, душ, скилов, проектов)
- Явном запросе «верни администратора»

---

## Cross-references

- Создание и редактирование персон → `managing-personas`
- Создание и редактирование душ → `managing-souls`
- Управление проектами → `managing-projects`
