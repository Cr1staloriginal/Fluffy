import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv
from pathlib import Path
import sys
import logging
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.InteractionBot(intents=intents)

# Импортируем init_db из database.py
from database import init_db

async def load_cogs():
    """Загружает все коги из папки cogs."""
    cogs_dir = Path(__file__).parent / "cogs"
    if not cogs_dir.exists():
        logger.warning("Папка cogs не найдена")
        return
    for path in sorted(cogs_dir.iterdir()):
        if path.suffix == ".py" and not path.name.startswith("_"):
            ext = f"cogs.{path.stem}"
            try:
                bot.load_extension(ext)
                logger.info(f"Загружен ког: {path.name}")
            except Exception as e:
                logger.exception(f"Ошибка загрузки кога {path.name}: {e}")

@bot.event
async def on_ready():
    logger.info(f"Бот {bot.user} готов!")

async def main():
    # 1. Инициализируем базу данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # 2. Загружаем коги
    await load_cogs()
    
    # 3. Запускаем бота
    await bot.start(TOKEN)

if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN не задан. Установите переменную окружения DISCORD_TOKEN.")
        sys.exit(1)
    asyncio.run(main())