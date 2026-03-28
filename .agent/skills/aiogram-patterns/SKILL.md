---
name: aiogram-patterns
description: "Provides aiogram 3.x patterns and idioms for Telegram bot development. Triggers when writing or modifying bot handlers, middleware, inline keyboards, or any aiogram-related code. Also triggers when the user asks about Telegram bot patterns, message handling, or callback queries in the Pandemonium bot project."
compatibility: "Requires aiogram 3.x"
---

# aiogram 3.x Patterns

Reference patterns for Telegram bot development with aiogram 3.

## Bot Structure

```python
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.enums import ChatAction

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
```

## Handlers

```python
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer("Hello!")

@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await message.answer("OK")

# Text messages (not commands)
from aiogram import F

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message) -> None:
    await message.reply("Got it")
```

## Inline Keyboards

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Cancel", callback_data=f"cancel:{request_id}")]
])
await message.reply("Processing...", reply_markup=keyboard)

@router.callback_query(F.data.startswith("cancel:"))
async def on_cancel(callback: CallbackQuery) -> None:
    request_id = int(callback.data.split(":")[1])
    await callback.message.edit_text("Cancelled")
    await callback.answer()
```

## Auth Middleware

```python
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class AuthMiddleware(BaseMiddleware):
    def __init__(self, allowed_ids: set[int]):
        self.allowed_ids = allowed_ids

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user and user.id not in self.allowed_ids:
            if isinstance(event, Message):
                await event.answer("Access denied")
            return
        return await handler(event, data)

# Register on both update types:
dp.message.middleware(AuthMiddleware(allowed_ids))
dp.callback_query.middleware(AuthMiddleware(allowed_ids))
```

## Chat Actions

```python
await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
# Lasts ~5 seconds, repeat in a loop for longer operations
```

## Sending Files

```python
from aiogram.types import BufferedInputFile

file = BufferedInputFile(file=report_bytes, filename=f"report_{number}.md")
await bot.send_document(chat_id=chat_id, document=file, reply_to_message_id=message_id)
```

## Dependency Injection

```python
# At startup
dp["session_manager"] = session_manager
dp["config"] = config

# In handler — auto-injected by name
@router.message()
async def handler(message: Message, session_manager: SessionManager):
    ...
```

## Startup/Shutdown

```python
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```
