import disnake
from disnake.ext import commands

class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="ping", description="Проверить задержку бота")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        """Безопасно показывает задержку бота"""
        try:
            latency = round((getattr(self.bot, "latency", 0) or 0) * 1000)
            await inter.response.send_message(f"Понг! Задержка: {latency} мс")
        except Exception as e:
            print(f"Info: ошибка при отправке пинга: {e}")
            try:
                await inter.response.send_message("Произошла ошибка при получении пинга.", ephemeral=True)
            except Exception:
                pass

def setup(bot):
    bot.add_cog(Info(bot))
