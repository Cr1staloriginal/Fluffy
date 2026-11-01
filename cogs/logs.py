"""Member and message audit events for Fluffy Town."""
from __future__ import annotations

import logging

import disnake
from disnake.ext import commands

from database import log_event
from utils.colors import main_color, accent_color

logger = logging.getLogger(__name__)


def _value(value, limit=900):
    text = str(value or "").strip()
    return text[:limit] if text else "*пусто*"


class Logs(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def _actor(self, guild, action, target_id):
        try:
            async for entry in guild.audit_logs(limit=8, action=action):
                if getattr(entry.target, "id", None) == target_id:
                    age = (disnake.utils.utcnow() - entry.created_at).total_seconds()
                    if 0 <= age <= 12:
                        return entry.user
        except (disnake.Forbidden, disnake.HTTPException):
            logger.debug("Audit log unavailable for guild %s", guild.id, exc_info=True)
        return None

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        embed = disnake.Embed(
            title="📥 Новый участник",
            description=f"{member.mention}\n**Аккаунт:** {member}\n**ID:** {member.id}",
            color=main_color(),
            timestamp=disnake.utils.utcnow(),
        )
        embed.add_field(name="Создан аккаунт", value=disnake.utils.format_dt(member.created_at, "F"), inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Участников на сервере: {member.guild.member_count or '—'}")
        await self.bot.log_dispatcher.send("members", embed)
        await log_event("member_join", str(member.id))

    @commands.Cog.listener()
    async def on_member_remove(self, member: disnake.Member):
        actor = await self._actor(member.guild, disnake.AuditLogAction.kick, member.id)
        embed = disnake.Embed(
            title="📤 Участник покинул сервер",
            description=f"**Участник:** {member} (<@{member.id}>)\n**ID:** {member.id}",
            color=disnake.Color.orange(),
            timestamp=disnake.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if actor:
            embed.add_field(name="Возможный инициатор", value=f"{actor.mention} ({actor.id})", inline=False)
            embed.set_footer(text="Событие сопоставлено с Audit Log: вероятно, Kick")
        else:
            embed.set_footer(text="Выход или Kick — инициатор не подтверждён")
        await self.bot.log_dispatcher.send("members", embed)
        await log_event("member_remove", str(member.id))

    @commands.Cog.listener()
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        if before.display_name != after.display_name:
            embed = disnake.Embed(title="✏️ Изменён ник", color=main_color(), timestamp=disnake.utils.utcnow())
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            embed.add_field(name="Было", value=_value(before.display_name), inline=False)
            embed.add_field(name="Стало", value=_value(after.display_name), inline=False)
            await self.bot.log_dispatcher.send("members", embed)
            await log_event("member_nickname", f"{after.id}|{before.display_name}->{after.display_name}")

        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles and r.name != "@everyone"]
            removed = [r for r in before.roles if r not in after.roles and r.name != "@everyone"]
            actor = await self._actor(after.guild, disnake.AuditLogAction.member_role_update, after.id)
            embed = disnake.Embed(title="🎭 Изменены роли участника", color=accent_color(), timestamp=disnake.utils.utcnow())
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            if added:
                embed.add_field(name="➕ Добавлены", value=_value(", ".join(r.mention for r in added)), inline=False)
            if removed:
                embed.add_field(name="➖ Сняты", value=_value(", ".join(r.mention for r in removed)), inline=False)
            embed.add_field(
                name="Кто изменил",
                value=f"{actor.mention} ({actor.id})" if actor else "Не удалось достоверно определить",
                inline=False,
            )
            await self.bot.log_dispatcher.send("members", embed)
            await log_event("member_roles", f"{after.id}|+{','.join(str(r.id) for r in added)}|-{','.join(str(r.id) for r in removed)}")

        if before.avatar != after.avatar:
            embed = disnake.Embed(title="🖼️ Изменён аватар участника", color=main_color(), timestamp=disnake.utils.utcnow())
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            embed.set_thumbnail(url=after.display_avatar.url)
            await self.bot.log_dispatcher.send("members", embed)
            await log_event("member_avatar", str(after.id))

        if before.timed_out_until != after.timed_out_until:
            embed = disnake.Embed(title="⏱️ Изменён Timeout", color=disnake.Color.orange(), timestamp=disnake.utils.utcnow())
            embed.add_field(name="Участник", value=f"{after.mention} ({after.id})", inline=False)
            until = disnake.utils.format_dt(after.timed_out_until, "F") if after.timed_out_until else "Timeout отсутствует"
            embed.add_field(name="Состояние", value=until, inline=False)
            await self.bot.log_dispatcher.send("mod", embed)
            await log_event("member_timeout_state", f"{after.id}|{after.timed_out_until}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: disnake.Message):
        if message.guild is None or message.author is None or message.author.bot:
            return
        embed = disnake.Embed(title="🗑️ Сообщение удалено", color=disnake.Color.orange(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Автор", value=f"{message.author.mention} ({message.author.id})", inline=False)
        embed.add_field(name="Канал", value=getattr(message.channel, "mention", str(message.channel.id)), inline=False)
        embed.add_field(name="Содержимое", value=_value(message.content, 1500), inline=False)
        if message.attachments:
            embed.add_field(name="Вложения", value=_value("\n".join(a.url for a in message.attachments)), inline=False)
        if message.embeds:
            embed.add_field(name="Встроенные объекты", value=f"Количество: {len(message.embeds)}", inline=False)
        embed.set_footer(text=f"Сообщение ID: {message.id}")
        await self.bot.log_dispatcher.send("messages", embed)
        await log_event("message_delete", f"{message.author.id}|{message.id}|{message.content or ''}")

    @commands.Cog.listener()
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if before.guild is None or before.author is None or before.author.bot:
            return
        if before.content == after.content and before.attachments == after.attachments:
            return
        embed = disnake.Embed(title="✏️ Сообщение изменено", color=disnake.Color.blue(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Автор", value=f"{before.author.mention} ({before.author.id})", inline=False)
        embed.add_field(name="Канал", value=getattr(before.channel, "mention", str(before.channel.id)), inline=False)
        embed.add_field(name="До изменения", value=_value(before.content, 1400), inline=False)
        embed.add_field(name="После изменения", value=_value(after.content, 1400), inline=False)
        if before.attachments != after.attachments:
            embed.add_field(name="Вложения после изменения", value=_value("\n".join(a.url for a in after.attachments)), inline=False)
        embed.add_field(name="Ссылка", value=f"[Открыть сообщение]({after.jump_url})", inline=False)
        embed.set_footer(text=f"Сообщение ID: {after.id}")
        await self.bot.log_dispatcher.send("messages", embed)
        await log_event("message_edit", f"{before.author.id}|{after.id}|{before.content or ''}->{after.content or ''}")

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[disnake.Message]):
        messages = [m for m in messages if m.guild is not None and m.author is not None and not m.author.bot]
        if not messages:
            return
        embed = disnake.Embed(title="🧹 Массовое удаление сообщений", color=disnake.Color.dark_orange(), timestamp=disnake.utils.utcnow())
        embed.add_field(name="Количество", value=str(len(messages)), inline=True)
        embed.add_field(name="Канал", value=getattr(messages[0].channel, "mention", str(messages[0].channel.id)), inline=True)
        embed.add_field(name="Уникальных авторов", value=str(len({m.author.id for m in messages})), inline=True)
        sample = "\n".join(f"• {m.author} ({m.author.id}): {(m.content or '[без текста]')[:120]}" for m in messages[:8])
        embed.add_field(name="Примеры", value=_value(sample), inline=False)
        await self.bot.log_dispatcher.send("messages", embed)
        await log_event("message_bulk_delete", f"{len(messages)}|{messages[0].channel.id}")


def setup(bot):
    bot.add_cog(Logs(bot))
