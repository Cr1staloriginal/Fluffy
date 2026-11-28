import disnake
from typing import Optional
from disnake.ext import commands
from utils.colors import main_color, accent_color

class Say(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    # ========== КОМАНДА /СКАЖИ (простой текст) ==========
    @commands.slash_command(name="скажи", description="📢 Отправить текстовое сообщение от имени бота", default_member_permissions=disnake.Permissions(administrator=True))
    @commands.has_permissions(administrator=True)
    async def say(
        self,
        inter: disnake.ApplicationCommandInteraction,
        сообщение: str,
        канал: Optional[disnake.TextChannel] = None
    ):
        """Отправляет указанное сообщение в указанный канал (или текущий)."""
        channel = канал or inter.channel
        if not isinstance(channel, disnake.TextChannel) or inter.guild is None or inter.guild.me is None:
            await inter.response.send_message("❌ Не удалось определить текстовый канал.", ephemeral=True)
            return
        if not channel.permissions_for(inter.guild.me).send_messages:
            await inter.response.send_message("❌ У бота нет прав на отправку в этот канал.", ephemeral=True)
            return

        await inter.response.send_message(
            f"✅ Сообщение отправлено в {channel.mention}",
            ephemeral=True
        )
        await channel.send(сообщение)

    # ========== КОМАНДА /СКАЖИ_EMBED (embed с выбором цвета) ==========
    @commands.slash_command(name="скажи_embed", description="📊 Отправить embed сообщение от имени бота", default_member_permissions=disnake.Permissions(administrator=True))
    @commands.has_permissions(administrator=True)
    async def say_embed(
        self,
        inter: disnake.ApplicationCommandInteraction,
        заголовок: str,
        описание: str,
        цвет: str = commands.Param(choices=["основной", "акцентный"], default="основной"),
        канал: Optional[disnake.TextChannel] = None,
        картинка: Optional[str] = None
    ):
        """Отправляет embed с выбранным цветом."""
        # Определяем цвет
        if цвет == "акцентный":
            color = accent_color()
        else:
            color = main_color()

        embed = disnake.Embed(
            title=заголовок,
            description=описание,
            color=color,
            timestamp=disnake.utils.utcnow()
        )
        if картинка and картинка.startswith("http"):
            embed.set_image(url=картинка)

        channel = канал or inter.channel
        if not isinstance(channel, disnake.TextChannel) or inter.guild is None or inter.guild.me is None:
            await inter.response.send_message("❌ Не удалось определить текстовый канал.", ephemeral=True)
            return
        if not channel.permissions_for(inter.guild.me).send_messages:
            await inter.response.send_message("❌ У бота нет прав на отправку в этот канал.", ephemeral=True)
            return

        await inter.response.send_message(
            f"✅ Embed отправлен в {channel.mention}",
            ephemeral=True
        )
        await channel.send(embed=embed)

def setup(bot: commands.InteractionBot):
    bot.add_cog(Say(bot))