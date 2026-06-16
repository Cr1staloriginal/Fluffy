import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv
from pathlib import Path
import sys
import logging

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.InteractionBot(intents=intents)

@bot.event
async def on_ready():
    logger.info(f"Бот {bot.user} готов!")
    # Автоматически загружаем все коги из папки cogs
    cogs_dir = Path(__file__).parent / "cogs"
    if cogs_dir.exists():
        for path in sorted(cogs_dir.iterdir()):
            if path.suffix == ".py" and not path.name.startswith("_"):
                ext = f"cogs.{path.stem}"
                try:
                    bot.load_extension(ext)
                    logger.info(f"Загружен ког: {path.name}")
                except Exception as e:
                    logger.exception(f"Ошибка загрузки кога {path.name}: {e}")
    else:
        logger.warning("Папка cogs не найдена, пропускаю загрузку когов.")

if __name__ == "__main__":
    if not TOKEN:
        logger.error("DISCORD_TOKEN не задан. Установите переменную окружения DISCORD_TOKEN.")
        sys.exit(1)
    bot.run(TOKEN)