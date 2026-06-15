import disnake
from disnake.ext import commands, tasks
from database import get_random_phrase
import random
import os
from typing import Optional

MAX_STATUS_LENGTH = 128

class StatusRotator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guild_id = int(os.getenv("GUILD_ID", 0))

    async def get_random_member(self) -> Optional[disnake.Member]:
        """Возвращает случайного участника (не бота) с указанного сервера."""
        if self.guild_id:
            guild = self.bot.get_guild(self.guild_id)
        else:
            guild = self.bot.guilds[0] if self.bot.guilds else None

        if not guild:
            print("[StatusRotator] Сервер не найден.")
            return None

        members = [m for m in guild.members if not m.bot]
        if not members:
            print("[StatusRotator] На сервере нет обычных участников.")
            return None
        return random.choice(members)

    async def update_status(self):
        """Обновляет статус бота, подставляя случайную фразу и случайного участника."""
        try:
            member = await self.get_random_member()
            if not member:
                return

            try:
                phrase_template = await get_random_phrase()
            except Exception as e:
                print(f"[StatusRotator] Ошибка при получении фразы из БД: {e}")
                phrase_template = None

            phrase_template = phrase_template or "наедине с {nick}"

            if "{nick}" in phrase_template:
                status_text = phrase_template.format(nick=member.display_name)
            else:
                status_text = f"{phrase_template} {member.display_name}"

            # Ограничиваем длину статуса
            if len(status_text) > MAX_STATUS_LENGTH:
                status_text = status_text[:MAX_STATUS_LENGTH]

            activity = disnake.Game(name=status_text)
            try:
                await self.bot.change_presence(status=disnake.Status.idle, activity=activity)
                print(f"[StatusRotator] Статус обновлён: {status_text} (участник: {member.display_name})")
            except Exception as e:
                print(f"[StatusRotator] Ошибка при смене статуса: {e}")
        except Exception as e:
            print(f"[StatusRotator] Непредвиденная ошибка в update_status: {e}")

    @tasks.loop(minutes=30)
    async def status_loop(self):
        """Цикл для автоматического обновления статуса каждые 30 минут."""
        await self.update_status()

    @status_loop.before_loop
    async def before_status_loop(self):
        """Ждём, пока бот полностью запустится, перед началом цикла."""
        await self.bot.wait_until_ready()
        print("[StatusRotator] Бот готов, цикл обновления статуса запущен.")

    def cog_load(self):
        """Запускаем цикл при загрузке кога, избегая двойного старта."""
        try:
            if not self.status_loop.is_running():
                self.status_loop.start()
                print("[StatusRotator] Ког заг��ужен, ротация статуса активирована.")
            else:
                print("[StatusRotator] Цикл уже запущен, пропускаем старт.")
        except Exception as e:
            print(f"[StatusRotator] Ошибка при старте цикла: {e}")


def setup(bot: commands.Bot):
    bot.add_cog(StatusRotator(bot))
