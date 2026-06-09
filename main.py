import logging
import os
import sys
from dotenv import load_dotenv
import disnake
from disnake.ext import commands

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, '.env')
load_dotenv(DOTENV_PATH)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    logger.error("DISCORD_TOKEN не найден в файле .env!")
    sys.exit(1)

# Интенты
intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# Создание бота
bot = commands.InteractionBot(intents=intents)

# Диспетчер логов
from utils.log_dispatcher import LogDispatcher
bot.log_dispatcher = LogDispatcher(bot)

# Инициализация БД
from database import init_db

@bot.event
async def on_ready():
    await init_db()
    logger.info(f"Бот запущен: {bot.user} (ID: {bot.user.id})")
    print("-" * 30)
    print("Готов к работе!")
    print("-" * 30)

# Загрузка когов (только один раз)
def load_cogs():
    cogs_dir = os.path.join(BASE_DIR, "cogs")
    if not os.path.isdir(cogs_dir):
        logger.warning(f"Папка 'cogs' не найдена: {cogs_dir}")
        return
    
    # Получаем список файлов
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            # Проверяем, не загружен ли уже этот ког
            if cog_name not in bot.extensions:
                try:
                    bot.load_extension(cog_name)
                    logger.info(f"[OK] Загружен: {cog_name}")
                except Exception as e:
                    logger.error(f"[ERROR] {cog_name}: {e}")

if __name__ == "__main__":
    load_cogs()
    logger.info("Запуск бота...")
    try:
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Остановлен вручную.")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")