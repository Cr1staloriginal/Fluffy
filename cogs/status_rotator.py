import disnake
from disnake.ext import commands, tasks
from database import get_random_phrase
import random
import os
from typing import Optional

class StatusRotator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_id = int(os.getenv("GUILD_ID", 0))

    async def get_random_member(self) -> Optional[disnake.Member]:
        if self.guild_id:
            guild = self.bot.get_guild(self.guild_id)
        else:
            guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            return None
        members = [m for m in guild.members if not m.bot]
        if not members:
            return None
        return random.choice(members)

    async def update_status(self):
        member = await self.get_random_member()
        if not member:
            print("[StatusRotator] Нет участников для статуса")
            return
        phrase_template = await get_random_phrase()
        if "{nick}" in phrase_template:
            status_text = phrase_template.format(nick=member.display_name)
        else:
            status_text = f"{phrase_template} {member.display_name}"
        activity = disnake.Game(name=status_text)
        await self.bot.change_presence(activity=activity)
        print(f"[StatusRotator] Статус: {status_text} (участник: {member.display_name})")

    @tasks.loop(minutes=30)
    async def status_loop(self):
        await self.update_status()

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()

    def cog_load(self):
        """Автоматически запускаем ротацию при загрузке кога"""
        self.status_loop.start()
        print("[StatusRotator] Автоматическая ротация статуса запущена (каждые 30 минут)")

def setup(bot: commands.Bot):
    bot.add_cog(StatusRotator(bot))