import asyncio
import logging
import os
import sys
from pathlib import Path

import disnake
from disnake.ext import commands
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

from utils.log_dispatcher import LogDispatcher
from database import init_db


async def load_cogs(bot: commands.InteractionBot) -> tuple[int, int]:
    """Load all cogs and report failures without hiding them."""
    cogs_dir = BASE_DIR / "cogs"
    if not cogs_dir.is_dir():
        logger.error("Папка cogs не найдена: %s", cogs_dir)
        return 0, 1

    loaded = failed = 0
    failed_names: set[str] = set()
    available_names = {
        path.stem for path in cogs_dir.glob("*.py") if not path.name.startswith("_")
    }
    for path in sorted(cogs_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        extension = f"cogs.{path.stem}"
        try:
            bot.load_extension(extension)
            loaded += 1
            logger.info("Загружен ког: %s", path.name)
        except Exception:
            failed += 1
            failed_names.add(path.stem)
            logger.exception("Не удалось загрузить ког %s", path.name)

    logger.info("Загрузка cogs завершена: %d успешно, %d с ошибками", loaded, failed)

    # Core moderation and member-support cogs must load before the bot starts.
    required_cogs = {"automod", "verification", "logs", "tickets"}
    missing = required_cogs - available_names
    failed_required = required_cogs & failed_names
    if missing or failed_required:
        details = []
        if missing:
            details.append("не найдены: " + ", ".join(sorted(missing)))
        if failed_required:
            details.append("не загрузились: " + ", ".join(sorted(failed_required)))
        raise RuntimeError(
            "Критические модули Fluffy недоступны (" + "; ".join(details) +
            "). Запуск отменён, чтобы бот не работал с отключённой защитой."
        )

    return loaded, failed


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN не задан. Добавьте его в .env или переменные окружения.")

    # Create the Discord client only after asyncio.run() has started its event loop.
    # Creating it at module import time can bind disnake to a different loop,
    # causing "The future belongs to a different loop" during gateway startup.
    bot = commands.InteractionBot(intents=intents)
    bot.log_dispatcher = LogDispatcher(bot)

    @bot.event
    async def on_ready():
        logger.info("Бот %s готов (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")
        status_cog = bot.get_cog("StatusRotator")
        if status_cog:
            await status_cog.update_status()

    await init_db()
    logger.info("База данных инициализирована")
    await load_cogs(bot)

    try:
        await bot.start(TOKEN)
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка по Ctrl+C")
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)
