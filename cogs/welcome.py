import disnake
from disnake.ext import commands
import os
import random

class Welcome(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.guild_id = int(os.getenv("GUILD_ID", 0))
        self.welcome_channel_id = int(os.getenv("WELCOME_CHANNEL_ID", 0))
        self.general_channel_id = int(os.getenv("GENERAL_CHANNEL_ID", 0))
        self.verified_role_id = int(os.getenv("VERIFIED_ROLE_ID", 0))
        self.rules_channel_id = int(os.getenv("RULES_CHANNEL_ID", 0))
        self.verify_channel_id = int(os.getenv("VERIFY_CHANNEL_ID", 0))

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        """Приветствие при входе."""
        if not self.welcome_channel_id:
            return
        channel = self.bot.get_channel(self.welcome_channel_id)
        if not channel:
            return

        embed = disnake.Embed(
            title=f"👋 Добро пожаловать в {member.guild.name}!",
            description=f"{member.mention}, мы всегда рады новым пушистикам! 🐾\n\n"
                        "Ознакомься с правилами и пройди верификацию, чтобы получить доступ к серверу.",
            color=disnake.Color.gold(),
            timestamp=disnake.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Участников на сервере: {member.guild.member_count}")

        view = WelcomeButtons(
            guild_id=self.guild_id,
            rules_id=self.rules_channel_id,
            verify_id=self.verify_channel_id
        )
        await channel.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        """Отслеживает выдачу роли верификации."""
        if not self.verified_role_id or not self.general_channel_id:
            return
        before_roles = set(role.id for role in before.roles)
        after_roles = set(role.id for role in after.roles)
        added_roles = after_roles - before_roles

        if self.verified_role_id in added_roles:
            channel = self.bot.get_channel(self.general_channel_id)
            if not channel:
                return

            greetings = [
                f"🎉 {after.mention} успешно прошёл верификацию! Добро пожаловать в нашу дружную семью! 🐾",
                f"✨ {after.mention} теперь с нами! Проходи, устраивайся поудобнее! 🌟",
                f"🥳 {after.mention} подтвердил свою личность! Давайте поприветствуем нового пушистика! 🎈",
                f"🌸 {after.mention} присоединился к нам после верификации! Надеюсь, тебе здесь понравится! 💖",
                f"🎊 {after.mention} теперь полноправный участник сервера! Ура! 🎉",
                f"🐾 {after.mention} прошёл проверку и теперь с нами! Пушистое приветствие! 🌈",
                f"💫 {after.mention} верифицирован! Добро пожаловать в наше уютное сообщество! 🏠"
            ]
            await channel.send(random.choice(greetings))

class WelcomeButtons(disnake.ui.View):
    def __init__(self, guild_id: int, rules_id: int, verify_id: int):
        super().__init__(timeout=None)
        # Кнопка "Правила" — ссылка на канал
        if rules_id and guild_id:
            self.add_item(disnake.ui.Button(
                label="📜 Правила",
                style=disnake.ButtonStyle.link,
                url=f"https://discord.com/channels/{guild_id}/{rules_id}"
            ))
        # Кнопка "Верификация" — ссылка на канал
        if verify_id and guild_id:
            self.add_item(disnake.ui.Button(
                label="✅ Верификация",
                style=disnake.ButtonStyle.link,
                url=f"https://discord.com/channels/{guild_id}/{verify_id}"
            ))

def setup(bot: commands.InteractionBot):
    bot.add_cog(Welcome(bot))