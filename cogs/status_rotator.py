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
        """Возвращает случайного участника (не бота) с указанного сервера."""
        if self.guild_id:
            guild = self.bot.get_guild(self.guild_id)
        else:
            # Если GUILD_ID не задан, берём первый попавшийся сервер
            guild = self.bot.guilds[0] if self.bot.guilds else None

        if not guild:
            print("[StatusRotator] Сервер не найден.")
            return None
        # Исключаем ботов из списка
        members = [m for m in guild.members if not m.bot]
        if not members:
            print("[StatusRotator] На сервере нет обычных участников.")
            return None
        return random.choice(members)

    async def update_status(self):
        """Обновляет статус бота, подставляя случайную фразу и случайного участника."""
        member = await self.get_random_member()
        if not member:
            print("[StatusRotator] Не удалось получить участника для статуса.")
            return

        phrase_template = await get_random_phrase()
        print(f"[StatusRotator] Получена фраза из БД: {phrase_template}")

        # Подставляем ник участника в фразу
        if "{nick}" in phrase_template:
            status_text = phrase_template.format(nick=member.display_name)
        else:
            # Если в фразе нет {nick}, просто добавляем ник в конец
            status_text = f"{phrase_template} {member.display_name}"

        # Устанавливаем статус "Играет в ..."
        activity = disnake.Game(name=status_text)
        await self.bot.change_presence(status=disnake.Status.idle, activity=activity)
        print(f"[StatusRotator] Статус обновлён: {status_text} (участник: {member.display_name})")

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
        """Запускаем цикл при загрузке кога."""
        self.status_loop.start()
        print("[StatusRotator] Ког загружен, ротация статуса активирована.")


def setup(bot: commands.Bot):
    bot.add_cog(StatusRotator(bot))