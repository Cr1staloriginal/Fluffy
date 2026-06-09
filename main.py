import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
import disnake
from disnake.ext import commands

# --- 1. Настройка логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- 2. Загрузка переменных окружения ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(DOTENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN не найден в файле .env!")
    sys.exit(1)

# --- 3. Настройка Intents ---
intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# --- 4. Создание бота ---
bot = commands.InteractionBot(intents=intents)

# --- 5. Диспетчер логов ---
from utils.log_dispatcher import LogDispatcher
bot.log_dispatcher = LogDispatcher(bot)

# --- 6. Инициализация базы данных ---
from database import init_db

@bot.event
async def on_ready():
    await init_db()
    logger.info(f"Бот успешно запущен: {bot.user} (ID: {bot.user.id})")
    print("-" * 30)
    print("Готов к работе!")
    print("-" * 30)

# --- 7. Загрузка модулей (cogs) из папки cogs ---
def load_cogs():
    cogs_dir = os.path.join(BASE_DIR, "cogs")
    if not os.path.isdir(cogs_dir):
        logger.warning(f"Папка 'cogs' не найдена по пути: {cogs_dir}")
        return
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                bot.load_extension(cog_name)
                logger.info(f"[OK] Загружен модуль: {cog_name}")
            except Exception as e:
                logger.error(f"[ERROR] Не удалось загрузить {cog_name}: {e}")

# --- 8. Запуск бота ---
if __name__ == "__main__":
    load_cogs()
    logger.info("Бот запускается...")
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
    except Exception as e:
        logger.error(f"Произошла критическая ошибка: {e}")