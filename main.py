import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv
import disnake
from disnake.ext import commands
from disnake.errors import ConnectionClosed

# Настройка логирования
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
    logger.error("DISCORD_TOKEN не найден в .env")
    sys.exit(1)

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="=", intents=intents)

# Импортируем диспетчер и добавляем в бота
from utils.log_dispatcher import LogDispatcher
bot.log_dispatcher = LogDispatcher(bot)

@bot.event
async def on_ready():
    logger.info(f"Бот вошёл как: {bot.user} (ID: {bot.user.id})")
    print("-" * 30)
    print(f"Готов к работе! Пригласи: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot%20applications.commands")
    print("-" * 30)

def load_cogs():
    cogs_dir = os.path.join(BASE_DIR, "cogs")
    if not os.path.isdir(cogs_dir):
        logger.warning(f"Папка 'cogs' не найдена")
        return
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                bot.load_extension(cog_name)
                logger.info(f"[OK] Загружен ког: {cog_name}")
            except Exception as e:
                logger.error(f"Не удалось загрузить {cog_name}: {e}")

async def main():
    load_cogs()
    logger.info("Подключение к Discord...")
    try:
        await bot.start(DISCORD_TOKEN)
    except disnake.errors.LoginFailure:
        logger.error("Неверный токен")
        sys.exit(1)
    except ConnectionClosed:
        logger.warning("Соединение потеряно")
    except Exception:
        logger.exception("Ошибка")
    finally:
        logger.info("Бот остановлен")

if __name__ == "__main__":
    async def shutdown_handler(signal_name: str):
        logger.info(f"Сигнал {signal_name}, завершение...")
        if bot and not bot.is_closed():
            await bot.close()

    async def main_with_signals():
        load_cogs()
        loop = asyncio.get_running_loop()
        if os.name != 'nt':
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown_handler(signal.Signals(s).name)))
        await bot.start(DISCORD_TOKEN)

    try:
        asyncio.run(main_with_signals())
    except KeyboardInterrupt:
        logger.info("Прервано")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
