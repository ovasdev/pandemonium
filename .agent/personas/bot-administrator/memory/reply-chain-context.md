---
type: project
date: 2026-03-28
---

Добавлена функциональность reply chain context в `bot/handlers.py`. При реплае на сообщение бот собирает цепочку до 2 уровней (reply-to + его reply-to) и передаёт в Claude Code с разметкой `[Message from ...]`, `[Reply to message from ...]`, `[User's message (reply)]`.

**Why:** Пользователь хочет, чтобы контекст реплая попадал в промпт для LLM.
**How to apply:** При изменениях в `handle_reply_message` или `_build_reply_context` — сохранять формат разметки и глубину цепочки (2 уровня).
