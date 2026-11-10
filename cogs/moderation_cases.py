"""Staff-only moderation case history commands."""

from __future__ import annotations

import disnake
from disnake.ext import commands

from database import get_moderation_case, get_user_moderation_cases
from utils.colors import main_color

ACTION_LABELS = {
    "warn": "Предупреждение",
    "ban": "Блокировка",
    "kick": "Исключение",
    "mute": "Выдача мута",
    "warn_dismissed": "Снятие предупреждения",
}


def _case_line(case) -> str:
    case_id, _guild_id, target_id, moderator_id, action, reason, source, message_link, created_at = case
    action_label = ACTION_LABELS.get(action, action)
    moderator = f"<@{moderator_id}>" if moderator_id else "Автомод / система"
    reason_text = (reason or "Причина не указана").replace("\n", " ")[:180]
    timestamp = str(created_at or "неизвестно")[:16]
    return (
        f"**#{case_id} · {action_label}** — {timestamp}\n"
        f"Модератор: {moderator}\n"
        f"Причина: {reason_text}"
    )


class ModerationCases(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.slash_command(
        name="cases",
        description="Показать историю модерации участника",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    @commands.has_permissions(moderate_members=True)
    async def cases(
        self,
        inter: disnake.ApplicationCommandInteraction,
        member: disnake.Member,
        limit: int = 10,
    ):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        safe_limit = max(1, min(limit, 25))
        rows = await get_user_moderation_cases(inter.guild.id, member.id, safe_limit)
        if not rows:
            await inter.response.send_message(
                f"У {member.mention} пока нет записей в истории модерации.",
                ephemeral=True,
            )
            return
        embed = disnake.Embed(
            title=f"📚 История модерации: {member.display_name}",
            description="\n\n".join(_case_line(row) for row in rows)[:4000],
            color=main_color(),
            timestamp=disnake.utils.utcnow(),
        )
        embed.set_footer(text=f"Показано записей: {len(rows)} · Новые сверху")
        await inter.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(
        name="case",
        description="Посмотреть отдельную запись истории модерации",
        default_member_permissions=disnake.Permissions(moderate_members=True),
    )
    @commands.has_permissions(moderate_members=True)
    async def case(
        self,
        inter: disnake.ApplicationCommandInteraction,
        case_id: int,
    ):
        if inter.guild is None:
            await inter.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        row = await get_moderation_case(inter.guild.id, case_id)
        if row is None:
            await inter.response.send_message("Запись с таким ID не найдена.", ephemeral=True)
            return

        (
            found_id, _guild_id, target_id, moderator_id, action,
            reason, source, message_link, created_at,
        ) = row
        embed = disnake.Embed(
            title=f"📄 Дело #{found_id} · {ACTION_LABELS.get(action, action)}",
            color=main_color(),
            timestamp=disnake.utils.utcnow(),
        )
        embed.add_field(name="Участник", value=f"<@{target_id}> ({target_id})", inline=False)
        embed.add_field(
            name="Модератор",
            value=f"<@{moderator_id}> ({moderator_id})" if moderator_id else "Автомод / система",
            inline=False,
        )
        embed.add_field(name="Причина", value=(reason or "Не указана")[:1000], inline=False)
        if source:
            embed.add_field(name="Источник", value=source[:200], inline=True)
        if created_at:
            embed.add_field(name="Дата", value=str(created_at)[:100], inline=True)
        if message_link:
            embed.add_field(name="Сообщение", value=f"[Открыть]({message_link})", inline=False)
        await inter.response.send_message(embed=embed, ephemeral=True)


def setup(bot: commands.InteractionBot):
    bot.add_cog(ModerationCases(bot))
