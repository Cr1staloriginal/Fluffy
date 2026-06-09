import os
import disnake
from disnake.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = disnake.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.InteractionBot(intents=intents)

@bot.event
async def on_ready():
    print(f"Бот {bot.user} готов!")

# Автоматически загружаем все коги из папки cogs
for filename in os.listdir("./cogs"):
    if filename.endswith(".py") and not filename.startswith("_"):
        try:
            bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Загружен ког: {filename}")
        except Exception as e:
            print(f"Ошибка загрузки кога {filename}: {e}")

if __name__ == "__main__":
    bot.run(TOKEN)