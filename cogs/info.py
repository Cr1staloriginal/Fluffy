import disnake
from disnake.ext import commands

class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(name="ping", description="Проверить задержку бота")
    async def ping(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.send_message(f"Понг! Задержка: {round(self.bot.latency * 1000)} мс")

def setup(bot):
    bot.add_cog(Info(bot))