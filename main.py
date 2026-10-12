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

bot = commands.InteractionBot(intents=intents)

from utils.log_dispatcher import LogDispatcher
from database import init_db

bot.log_dispatcher = LogDispatcher(bot)


async def load_cogs() -> tuple[int, int]:
    """Load all cogs and report failures without hiding them."""
    cogs_dir = BASE_DIR / "cogs"
    if not cogs_dir.is_dir():
        logger.error("Папка cogs не найдена: %s", cogs_dir)
        return 0, 1

    loaded = failed = 0
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
            logger.exception("Не удалось загрузить ког %s", path.name)

    logger.info("Загрузка cogs завершена: %d успешно, %d с ошибками", loaded, failed)
    return loaded, failed


@bot.event
async def on_ready():
    logger.info("Бот %s готов (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")
    status_cog = bot.get_cog("StatusRotator")
    if status_cog:
        await status_cog.update_status()


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN не задан. Добавьте его в .env или переменные окружения.")

    await init_db()
    logger.info("База данных инициализирована")
    await load_cogs()
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
