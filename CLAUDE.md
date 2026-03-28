# Pandemonium Telegram bot — Инструкции для агента

## Система персон

Если установлена `PANDEMONIUM_ACTIVE_PERSONA` — прочитай `.agent/personas/$PANDEMONIUM_ACTIVE_PERSONA/PERSONA.md` из проекта-владельца (реестр: `.agent/persona-registry.yaml`). Иначе — **Bot Administrator** (`.agent/personas/bot-administrator/PERSONA.md`).

Переключение персон → скил `switching-personas`. Реестр всех персон: `.agent/persona-registry.yaml`.

## Проект

**Pandemonium Telegram bot** — мост между Telegram и Claude Code CLI. Пользователь пишет в Telegram, бот запускает Claude Code в контексте проекта, стримит результаты и возвращает отчёт.

Правила разработки, стек и конвенции → скил `pandemonium-dev`.

## Отправка файлов

```bash
$PANDEMONIUM_SEND_FILE /path/to/file "Необязательная подпись"
```

Переменные `PANDEMONIUM_SEND_FILE`, `PANDEMONIUM_BOT_TOKEN`, `PANDEMONIUM_CHAT_ID` установлены в окружении.

## Активный проект

Переменные: `PANDEMONIUM_ACTIVE_PROJECT_ID`, `PANDEMONIUM_ACTIVE_PROJECT_PATH`.

Если активный проект — не pandemonium-bot:
1. Прочитай `$PANDEMONIUM_ACTIVE_PROJECT_PATH/CLAUDE.md` — дополняет этот промпт, не заменяет. Базовые правила бота приоритетнее.
2. Прочитай `$PANDEMONIUM_ACTIVE_PROJECT_PATH/.agent/` — персоны, души, скилы проекта.
3. CRUD персон/душ/скилов — в `.agent/` активного проекта.
4. Рабочая директория — `$PANDEMONIUM_ACTIVE_PROJECT_PATH`.
