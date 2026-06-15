import disnake
from disnake.ext import commands
from utils.colors import main_color

class Announce(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(name="объявление", description="📢 Сделать объявление (только для администраторов)")
    @commands.has_permissions(administrator=True)
    async def announce(
        self,
        inter: disnake.ApplicationCommandInteraction,
        заголовок: str,
        текст: str,
        цвет: str = commands.Param(choices=["синий", "зелёный", "красный", "жёлтый", "фиолетовый", "оранжевый", "голубой (основной)"], default="голубой (основной)"),
        картинка: str = None
    ):
        colors = {
            "синий": disnake.Color.blue(),
            "зелёный": disnake.Color.green(),
            "красный": disnake.Color.red(),
            "жёлтый": disnake.Color.gold(),
            "фиолетовый": disnake.Color.purple(),
            "оранжевый": disnake.Color.orange(),
            "голубой (основной)": main_color()
        }
        color = colors.get(цвет.lower(), main_color())
        embed = disnake.Embed(
            title=заголовок,
            description=текст,
            color=color,
            timestamp=disnake.utils.utcnow()
        )
        if картинка:
            embed.set_image(url=картинка)
        embed.set_footer(text=f"Объявление от {inter.author.display_name}")
        await inter.response.send_message(embed=embed)

def setup(bot: commands.InteractionBot):
    bot.add_cog(Announce(bot))