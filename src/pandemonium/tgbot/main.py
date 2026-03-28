"""Pandemonium Telegram bot entry point — load config, init DB, start bot."""

import asyncio
import logging
import signal
import sys

from aiogram import Bot, Dispatcher

from pandemonium.tgbot.bot.callbacks import router as callbacks_router
from pandemonium.tgbot.bot.handlers import router as handlers_router
from pandemonium.tgbot.bot.middleware import AuthMiddleware
from pandemonium.tgbot.config import ConfigError, load_config, resolve_config_path
from pandemonium.tgbot.db import init_db, update_request_status
from pandemonium.tgbot.session.manager import SessionManager
from pandemonium.tgbot.storage.protocol import ProtocolStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _recover_interrupted_requests(database, storage: ProtocolStorage) -> None:
    """Mark any running/awaiting requests as errors after a restart."""
    cursor = await database.execute(
        "SELECT id, project_id, request_number FROM requests "
        "WHERE status IN ('running', 'awaiting_input', 'pending')"
    )
    rows = await cursor.fetchall()
    for row in rows:
        request_id = row["id"]
        project_id = row["project_id"]
        req_number = row["request_number"]
        logger.warning(
            "Recovering interrupted request #%s (project=%s)",
            req_number, project_id,
        )
        await update_request_status(
            database, request_id, "error",
            error_text="Pandemonium bot was restarted",
        )
        await storage.save_error(project_id, req_number, "Pandemonium bot was restarted")
        await storage.save_meta(project_id, req_number, {
            "request_number": req_number,
            "status": "error",
            "error": "Pandemonium bot was restarted",
        })


async def main() -> None:
    config_path = resolve_config_path()
    logger.info("Loading config from %s", config_path)

    try:
        config = load_config(config_path)
    except ConfigError as e:
        logger.error("Failed to load config: %s", e)
        sys.exit(1)

    db_path = config.storage.base_path / "pandemonium.db"
    database = await init_db(db_path)
    storage = ProtocolStorage(config.storage.base_path)

    # Recover interrupted requests from previous run
    await _recover_interrupted_requests(database, storage)

    bot = Bot(token=config.telegram.bot_token)
    dp = Dispatcher()

    # Fetch bot info (needed for @mention detection in group chats)
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""
    logger.info("Bot username: @%s", bot_username)

    session_manager = SessionManager(config, database, storage, bot)

    # Dependency injection
    dp["config"] = config
    dp["config_path"] = config_path
    dp["db"] = database
    dp["session_manager"] = session_manager
    dp["bot_username"] = bot_username

    # Middleware
    auth = AuthMiddleware(config.allowed_user_ids)
    dp.message.middleware(auth)
    dp.callback_query.middleware(auth)

    # Routers
    dp.include_router(handlers_router)
    dp.include_router(callbacks_router)

    # Graceful shutdown handler
    shutdown_event = asyncio.Event()

    def _signal_handler(sig: int, _frame: object) -> None:
        logger.info("Received signal %s, initiating shutdown...", sig)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    logger.info("Starting bot (long polling)...")

    polling_task = asyncio.create_task(dp.start_polling(bot))

    # Wait for either polling to end or shutdown signal
    shutdown_wait = asyncio.create_task(shutdown_event.wait())
    done, _ = await asyncio.wait(
        [polling_task, shutdown_wait],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if shutdown_event.is_set():
        logger.info("Graceful shutdown initiated...")
        await session_manager.shutdown()
        await dp.stop_polling()

    await database.close()
    await bot.session.close()
    logger.info("Pandemonium bot stopped.")


def cli() -> None:
    """CLI entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
