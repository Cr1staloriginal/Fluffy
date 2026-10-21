import disnake
from disnake.ext import commands, tasks
from database import get_random_phrase_by_season
from utils.seasons import get_current_season, get_season_name
import random
import os
from typing import Optional


class StatusRotator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_id = int(os.getenv("GUILD_ID", 0))
        self.current_season = None

    async def get_random_member(self) -> Optional[disnake.Member]:
        if self.guild_id:
            guild = self.bot.get_guild(self.guild_id)
        else:
            guild = self.bot.guilds[0] if self.bot.guilds else None
        if not guild:
            print("[StatusRotator] Сервер не найден.")
            return None
        members = [m for m in guild.members if not m.bot]
        if not members:
            return None
        return random.choice(members)

    async def update_status(self):
        try:
            member = await self.get_random_member()
            if not member:
                return

            season = get_current_season()

            if season != self.current_season:
                self.current_season = season
                print(f"[StatusRotator] 🎭 Сезон изменён на: {get_season_name(season)}")

            phrase = await get_random_phrase_by_season(season)
            if "{nick}" in phrase:
                text = phrase.format(nick=member.display_name)
            else:
                text = f"{phrase} {member.display_name}"

            activity = disnake.Game(name=text)
            await self.bot.change_presence(activity=activity)
            print(f"[StatusRotator] ({get_season_name(season)}) Статус: {text}")
        except Exception as e:
            print(f"[StatusRotator] Ошибка: {e}")

    @tasks.loop(minutes=30)
    async def status_loop(self):
        await self.update_status()

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()
        print("[StatusRotator] Цикл статуса запущен.")

    def cog_load(self):
        self.status_loop.start()
        print("[StatusRotator] Ког загружен, ротация включена.")


def setup(bot):
    bot.add_cog(StatusRotator(bot))