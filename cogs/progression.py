"""Server-scoped member levels, profiles, leaderboard, and achievements."""
from __future__ import annotations

import logging
import random

import disnake
from disnake.ext import commands

from utils.colors import main_color
from utils.progression_math import xp_progress
from utils.progression_store import (
    ACHIEVEMENT_LABELS,
    ensure_progression_schema,
    get_achievements,
    get_leaderboard,
    get_progress,
    record_message,
)

logger = logging.getLogger(__name__)


class Progression(commands.Cog):
    """Give members a friendly, anti-spam-limited progression system."""

    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self._schema_ready = False

    async def cog_load(self):
        await ensure_progression_schema()
        self._schema_ready = True
        logger.info("Система уровней и достижений готова")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.guild is None or message.author.bot:
            return
        if len(message.content.strip()) < 3:
            return
        if not self._schema_ready:
            await ensure_progression_schema()
            self._schema_ready = True

        try:
            result = await record_message(
                message.guild.id,
                message.author.id,
                random.randint(8, 15),
            )
            if result["level_up"]:
                await message.channel.send(
                    f"🎉 {message.author.mention}, поздравляю! Ты достиг **{result['level']} уровня**!",
                    allowed_mentions=disnake.AllowedMentions(users=True, roles=False, everyone=False),
                )
            for key in result["new_achievements"]:
                label = ACHIEVEMENT_LABELS.get(key, key)
                try:
                    await message.author.send(
                        f"🏆 Ты получил достижение **{label}** на сервере **{message.guild.name}**!"
                    )
                except (disnake.Forbidden, disnake.HTTPException):
                    logger.debug("Не удалось отправить достижение в ЛС пользователю %s", message.author.id)
        except Exception:
            logger.exception("Ошибка обновления прогресса участника %s", message.author.id)

    @commands.slash_command(name="профиль", description="🐾 Посмотреть уровень и статистику участника")
    async def profile(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = None,
    ):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        member = участник or inter.author
        await ensure_progression_schema()
        data = await get_progress(inter.guild.id, member.id)
        level, current_xp, needed_xp = xp_progress(data["xp"])
        bar_size = 12
        filled = min(bar_size, int(bar_size * current_xp / needed_xp)) if needed_xp else bar_size
        progress_bar = "🟦" * filled + "⬜" * (bar_size - filled)

        embed = disnake.Embed(title=f"🐾 Профиль {member.display_name}", color=main_color())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Уровень", value=f"**{level}**", inline=True)
        embed.add_field(name="Опыт", value=f"**{data['xp']} XP**", inline=True)
        embed.add_field(name="Достижения", value=f"🏆 **{data['achievements']}**", inline=True)
        embed.add_field(
            name="Прогресс до следующего уровня",
            value=f"{progress_bar}\n{current_xp}/{needed_xp} XP",
            inline=False,
        )
        embed.add_field(name="Учтённые сообщения", value=str(data["messages_count"]), inline=True)
        embed.set_footer(text="Опыт начисляется не чаще одного раза в минуту.")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(name="топ", description="🏆 Рейтинг участников по опыту на сервере")
    async def leaderboard(self, inter: disnake.ApplicationCommandInteraction):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        await ensure_progression_schema()
        rows = await get_leaderboard(inter.guild.id, 10)
        embed = disnake.Embed(title=f"🏆 Топ участников — {inter.guild.name}", color=main_color())
        if not rows:
            embed.description = "Пока рейтинга нет. Общайтесь, чтобы получить первый опыт!"
        else:
            lines = []
            medals = ["🥇", "🥈", "🥉"]
            for index, (user_id, xp, level, messages) in enumerate(rows, 1):
                member = inter.guild.get_member(user_id)
                name = member.display_name if member else f"Участник {user_id}"
                medal = medals[index - 1] if index <= 3 else f"{index}."
                lines.append(f"{medal} **{name}** — уровень {level} · {xp} XP")
            embed.description = "\n".join(lines)
        await inter.response.send_message(embed=embed)

    @commands.slash_command(name="достижения", description="🎖️ Посмотреть достижения участника")
    async def achievements(
        self,
        inter: disnake.ApplicationCommandInteraction,
        участник: disnake.Member = None,
    ):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        member = участник or inter.author
        await ensure_progression_schema()
        rows = await get_achievements(inter.guild.id, member.id)
        embed = disnake.Embed(title=f"🎖️ Достижения {member.display_name}", color=main_color())
        if not rows:
            embed.description = "Пока нет достижений. Продолжай участвовать в жизни сервера!"
        else:
            embed.description = "\n".join(
                f"🏅 **{ACHIEVEMENT_LABELS.get(key, key)}** · {earned_at[:10]}"
                for key, earned_at in rows
            )
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(Progression(bot))
