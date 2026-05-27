import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
import disnake
from disnake.ext import commands

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(DOTENV_PATH)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN не найден")
    sys.exit(1)

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# Бот без префикса, только слеш-команды
bot = commands.Bot(intents=intents, test_guilds=[int(os.getenv("GUILD_ID", 0))])  # для мгновенной синхронизации на одном сервере

# Подключаем диспетчер логов
from utils.log_dispatcher import LogDispatcher
bot.log_dispatcher = LogDispatcher(bot)

from database import init_db

@bot.event
async def on_ready():
    await init_db()
    logger.info(f"Бот: {bot.user} (ID: {bot.user.id})")
    # Синхронизация слеш-команд
    await bot.sync_commands()
    logger.info("Слеш-команды синхронизированы")
    print("-" * 30)
    print(f"Готов! Пригласи: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
    print("-" * 30)

def load_cogs():
    cogs_dir = os.path.join(BASE_DIR, "cogs")
    if not os.path.isdir(cogs_dir):
        logger.warning("Папка cogs не найдена")
        return
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                bot.load_extension(cog_name)
                logger.info(f"[OK] {cog_name}")
            except Exception as e:
                logger.error(f"Ошибка загрузки {cog_name}: {e}")

if __name__ == "__main__":
    load_cogs()
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")