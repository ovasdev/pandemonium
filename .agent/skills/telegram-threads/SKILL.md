---
name: telegram-threads
description: "Telegram Bot API: threads (forum topics) in private chats, sendMessageDraft for streaming AI responses, threaded mode. Triggers when implementing threaded conversations, AI chatbot streaming, message drafts, or forum topics in private chats with aiogram 3.x. Also triggers on: 'threads', 'треды', 'потоки в чате', 'стриминг ответов', 'sendMessageDraft', 'createForumTopic в приватном чате', 'threaded mode'. Extends aiogram-patterns skill. Does NOT apply to forum topics in supergroups (that's standard aiogram)."
---

# Telegram Threads — AI Chatbot Integration

Telegram Bot API 9.4+ позволяет ботам создавать **треды (forum topics) в приватных чатах** и **стримить ответы** через message drafts. Это ключевая инфраструктура для AI-ботов, позволяющая вести параллельные тематические беседы с пользователем.

See also: `aiogram-patterns` (базовые паттерны aiogram), `pandemonium-dev` (конвенции проекта).

---

## Концепция

Threaded Mode превращает приватный чат бота в аналог форума: каждая тема — отдельный тред с `message_thread_id`. Пользователь видит список тредов и может переключаться между ними. Бот стримит ответы через `sendMessageDraft`, показывая текст по мере генерации — как в ChatGPT или Claude.

### Когда использовать

- AI-бот, ведущий несколько параллельных бесед с пользователем
- Бот, стримящий длинные ответы по мере генерации
- Любой сценарий, где нужна организация диалога по темам в приватном чате

---

## API Reference

### Включение Threaded Mode

Threaded Mode включается через @BotFather. После включения приватный чат бота поддерживает forum topics.

Поле `allows_users_to_create_topics` в объекте `User` (Bot API 9.4) — указывает, могут ли пользователи сами создавать и удалять топики. Настраивается через @BotFather Mini App.

### createForumTopic — создание треда

Создаёт topic в приватном чате (или supergroup). Возвращает `ForumTopic`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | ID чата или username supergroup |
| `name` | String | Yes | Название топика, 1-128 символов |
| `icon_color` | Integer | No | RGB-цвет иконки. Допустимые: `0x6FB9F0`, `0xFFD67E`, `0xCB86DB`, `0x8EEE98`, `0xFF93B2`, `0xFB6F5F` |
| `icon_custom_emoji_id` | String | No | Custom emoji для иконки (см. `getForumTopicIconStickers`) |

Для приватных чатов `chat_id` — это user ID собеседника.

### editForumTopic — редактирование треда

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer or String | Yes | ID чата |
| `message_thread_id` | Integer | Yes | ID треда |
| `name` | String | No | Новое название, 0-128 символов. Пустое = сохранить текущее |
| `icon_custom_emoji_id` | String | No | Новый custom emoji. Пустая строка = убрать иконку |

### sendMessageDraft — стриминг ответов

Стримит частичное сообщение пользователю по мере генерации. Возвращает `True`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | Integer | Yes | ID приватного чата |
| `message_thread_id` | Integer | No | ID треда (для threaded mode) |
| `draft_id` | Integer | Yes | Уникальный ID черновика; должен быть ненулевым. Изменения черновиков с одинаковым ID анимируются |
| `text` | String | Yes | Текст сообщения, 1-4096 символов |
| `parse_mode` | String | No | Режим парсинга entities (Markdown, HTML и т.д.) |
| `entities` | Array of MessageEntity | No | Специальные entities вместо parse_mode |

**Ключевой паттерн:** вызывай `sendMessageDraft` с одним и тем же `draft_id` многократно по мере генерации текста. Telegram анимирует переход между версиями. Когда генерация завершена — отправь финальное сообщение обычным `sendMessage`, и черновик исчезнет.

### message_thread_id в сообщениях

Поле `message_thread_id` в объекте `Message` работает в приватных чатах (Bot API 9.4+). Используй его для маршрутизации входящих сообщений по тредам.

---

## Паттерны для aiogram 3.x

### Создание треда

```python
from aiogram import Bot
from aiogram.types import ForumTopic

async def create_thread(bot: Bot, user_id: int, name: str) -> ForumTopic:
    return await bot.create_forum_topic(chat_id=user_id, name=name)
```

### Стриминг ответа через sendMessageDraft

aiogram 3.x может не иметь встроенного метода `send_message_draft` (зависит от версии). Если метода нет — используй raw API:

```python
import random
from aiogram import Bot

async def stream_draft(
    bot: Bot,
    chat_id: int,
    text: str,
    draft_id: int,
    message_thread_id: int | None = None,
) -> bool:
    """Send or update a message draft for streaming effect."""
    params: dict = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "text": text,
    }
    if message_thread_id is not None:
        params["message_thread_id"] = message_thread_id
    return await bot(method="sendMessageDraft", **params)


async def stream_response(
    bot: Bot,
    chat_id: int,
    chunks: AsyncIterator[str],
    message_thread_id: int | None = None,
) -> None:
    """Stream an AI response chunk by chunk, then send the final message."""
    draft_id = random.randint(1, 2**31)
    accumulated = ""

    async for chunk in chunks:
        accumulated += chunk
        await stream_draft(bot, chat_id, accumulated, draft_id, message_thread_id)

    # Final message replaces the draft
    await bot.send_message(
        chat_id=chat_id,
        text=accumulated,
        message_thread_id=message_thread_id,
    )
```

> Если aiogram добавит нативный `bot.send_message_draft()` — используй его вместо raw API.

### Маршрутизация по тредам

```python
from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.message_thread_id)
async def handle_threaded_message(message: Message) -> None:
    thread_id = message.message_thread_id
    # Маршрутизируй по thread_id — каждый тред может иметь свой контекст
    ...

@router.message(~F.message_thread_id)
async def handle_unthreaded_message(message: Message) -> None:
    # Сообщение вне треда — предложить создать новый или использовать General
    ...
```

### Проверка поддержки threaded mode

```python
from aiogram.types import User

async def user_supports_topics(bot: Bot, user_id: int) -> bool:
    """Check if the bot's private chat with user has threaded mode enabled."""
    user: User = await bot.get_chat(user_id)
    return getattr(user, "allows_users_to_create_topics", False)
```

---

## Архитектурные соображения

### draft_id

- Должен быть ненулевым целым числом
- Один и тот же `draft_id` = обновление существующего черновика (с анимацией)
- Разные `draft_id` = разные черновики
- Генерируй случайно (`random.randint(1, 2**31)`) или используй ID запроса

### Жизненный цикл черновика

1. `sendMessageDraft(draft_id=X, text="Generating...")` — появляется черновик
2. `sendMessageDraft(draft_id=X, text="Generating... partial result")` — обновляется с анимацией
3. `sendMessage(text="Final result")` — черновик заменяется финальным сообщением

### Ограничения

- `sendMessageDraft` работает только в приватных чатах (`chat_id` — Integer, не String)
- Текст черновика: 1-4096 символов (как у обычных сообщений)
- Threaded mode включается только через @BotFather — программно включить нельзя
- Плата за Telegram Stars (Section 6.2.6 Bot Developer ToS) может применяться

### Интеграция с Pandemonium

В контексте Pandemonium-бота треды позволяют:
- Каждую сессию Claude Code вести в отдельном треде
- Стримить вывод Claude через `sendMessageDraft` вместо периодических `editMessageText`
- Сохранять историю по темам — пользователь видит список всех бесед
