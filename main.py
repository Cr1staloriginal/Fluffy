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

from config import GUILD_ID
from utils.guild_guard import is_allowed_guild
from utils.log_dispatcher import LogDispatcher
from database import init_db


CRITICAL_COGS = {"antiraid", "automod", "verification", "logs", "tickets"}


async def load_cogs(bot: commands.InteractionBot) -> tuple[int, int]:
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
        except Exception as exc:
            failed += 1
            logger.exception("Не удалось загрузить ког %s", path.name)
            if path.stem in CRITICAL_COGS:
                raise RuntimeError(
                    f"Критически важный модуль {extension} не загрузился. "
                    "Запуск остановлен, чтобы бот не работал без защиты/модерации."
                ) from exc

    logger.info("Загрузка cogs завершена: %d успешно, %d с ошибками", loaded, failed)
    return loaded, failed


async def leave_foreign_guilds(bot: commands.InteractionBot) -> None:
    """Keep the bot connected only to its configured Fluffy Town guild."""
    for guild in list(bot.guilds):
        if is_allowed_guild(guild.id, GUILD_ID):
            continue
        logger.warning(
            "Бот обнаружен на постороннем сервере %s (ID: %s); покидаю его.",
            guild.name,
            guild.id,
        )
        try:
            await guild.leave()
        except disnake.HTTPException:
            logger.exception("Не удалось покинуть посторонний сервер ID=%s", guild.id)


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN не задан. Добавьте его в .env или переменные окружения.")
    if GUILD_ID <= 0:
        raise RuntimeError(
            "GUILD_ID не задан. Укажите ID сервера Fluffy Town в переменных окружения Bothost."
        )

    # Commands are registered only for Fluffy Town, not globally.
    bot = commands.InteractionBot(intents=intents, test_guilds=[GUILD_ID])
    bot.log_dispatcher = LogDispatcher(bot)

    @bot.event
    async def on_guild_join(guild: disnake.Guild):
        if is_allowed_guild(guild.id, GUILD_ID):
            logger.info("Бот добавлен на разрешённый сервер Fluffy Town (ID: %s).", guild.id)
            return
        logger.warning(
            "Бота пригласили на посторонний сервер %s (ID: %s); покидаю его.",
            guild.name,
            guild.id,
        )
        try:
            await guild.leave()
        except disnake.HTTPException:
            logger.exception("Не удалось покинуть посторонний сервер ID=%s", guild.id)

    @bot.event
    async def on_ready():
        logger.info("Бот %s готов (ID: %s)", bot.user, bot.user.id if bot.user else "unknown")
        await leave_foreign_guilds(bot)
        target_guild = bot.get_guild(GUILD_ID)
        if target_guild is None:
            logger.error(
                "Разрешённый сервер Fluffy Town (GUILD_ID=%s) не найден среди доступных боту серверов.",
                GUILD_ID,
            )
        status_cog = bot.get_cog("StatusRotator")
        if status_cog and target_guild is not None:
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
