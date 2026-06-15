import disnake
from disnake.ext import commands
import aiosqlite
from pathlib import Path
from database import DB_PATH

class RestoreDB(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="восстановить_бд", description="Восстановить таблицы базы данных (только для владельца)")
    @commands.is_owner()
    async def restore_db(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            # Создаём таблицу phrases, если её нет
            await db.execute("""
                CREATE TABLE IF NOT EXISTS phrases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT UNIQUE
                )
            """)
            # Загружаем фразы из templates.txt
            templates_path = Path(__file__).parent.parent / "templates.txt"
            if templates_path.exists():
                with open(templates_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and "{nick}" in line]
                for line in lines:
                    await db.execute("INSERT OR IGNORE INTO phrases (text) VALUES (?)", (line,))
                await db.commit()
                await inter.edit_original_response(content=f"✅ Таблица phrases создана, загружено {len(lines)} фраз.")
            else:
                await inter.edit_original_response(content="❌ Файл templates.txt не найден.")
        await inter.followup.send("✅ Готово! Теперь статус будет меняться.", ephemeral=True)

def setup(bot):
    bot.add_cog(RestoreDB(bot))