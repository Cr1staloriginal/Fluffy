"""Audit log listeners for server structure and moderation actions."""
from __future__ import annotations

import logging

import disnake
from disnake.ext import commands

from database import log_event

logger = logging.getLogger(__name__)


class AuditLogs(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    async def actor_for(self, guild, action, target_id):
        try:
            async for entry in guild.audit_logs(limit=10, action=action):
                if getattr(entry.target, "id", None) != target_id:
                    continue
                age = (disnake.utils.utcnow() - entry.created_at).total_seconds()
                if 0 <= age <= 15:
                    return entry.user, entry.reason
        except (disnake.Forbidden, disnake.HTTPException):
            logger.debug("Audit log unavailable for guild %s", guild.id, exc_info=True)
        return None, None

    async def emit(self, title, description, *, actor=None, reason=None, color=None, event_type=None):
        embed = disnake.Embed(
            title=title,
            description=description[:3500],
            color=color or disnake.Color.blurple(),
            timestamp=disnake.utils.utcnow(),
        )
        if actor:
            embed.add_field(name="Инициатор", value=f"{actor.mention} ({actor.id})", inline=False)
        else:
            embed.add_field(name="Инициатор", value="Не удалось достоверно определить", inline=False)
        if reason:
            embed.add_field(name="Причина из Audit Log", value=str(reason)[:900], inline=False)
        await self.bot.log_dispatcher.send("mod", embed)
        if event_type:
            await log_event(event_type, description[:1500])

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        actor, reason = await self.actor_for(channel.guild, disnake.AuditLogAction.channel_create, channel.id)
        await self.emit("🆕 Создан канал", f"**Канал:** {channel.name} ({channel.id})\n**Тип:** {channel.type}", actor=actor, reason=reason, event_type="channel_create")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        actor, reason = await self.actor_for(channel.guild, disnake.AuditLogAction.channel_delete, channel.id)
        await self.emit("🗑️ Удалён канал", f"**Канал:** {channel.name} ({channel.id})\n**Тип:** {channel.type}", actor=actor, reason=reason, color=disnake.Color.red(), event_type="channel_delete")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        changes = []
        for attr, label in (
            ("name", "Название"),
            ("category_id", "Категория"),
            ("slowmode_delay", "Медленный режим"),
            ("bitrate", "Битрейт"),
            ("user_limit", "Лимит участников"),
            ("nsfw", "NSFW"),
        ):
            old, new = getattr(before, attr, None), getattr(after, attr, None)
            if old != new:
                changes.append(f"**{label}:** {old} → {new}")
        if before.overwrites != after.overwrites:
            changes.append("**Права доступа:** изменены")
        if not changes:
            return
        actor, reason = await self.actor_for(after.guild, disnake.AuditLogAction.channel_update, after.id)
        channel_label = getattr(after, "mention", after.name)
        await self.emit("🛠️ Изменён канал", f"**Канал:** {channel_label} ({after.id})\n" + "\n".join(changes), actor=actor, reason=reason, event_type="channel_update")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        actor, reason = await self.actor_for(role.guild, disnake.AuditLogAction.role_create, role.id)
        await self.emit("🆕 Создана роль", f"**Роль:** {role.name} ({role.id})\n**Права:** {role.permissions.value}", actor=actor, reason=reason, event_type="role_create")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        actor, reason = await self.actor_for(role.guild, disnake.AuditLogAction.role_delete, role.id)
        await self.emit("🗑️ Удалена роль", f"**Роль:** {role.name} ({role.id})", actor=actor, reason=reason, color=disnake.Color.red(), event_type="role_delete")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        changes = []
        for attr, label in (
            ("name", "Название"),
            ("color", "Цвет"),
            ("hoist", "Отдельное отображение"),
            ("mentionable", "Упоминание"),
        ):
            old, new = getattr(before, attr), getattr(after, attr)
            if old != new:
                changes.append(f"**{label}:** {old} → {new}")
        if before.permissions != after.permissions:
            changes.append("**Разрешения:** изменены")
        if before.position != after.position:
            changes.append(f"**Позиция:** {before.position} → {after.position}")
        if not changes:
            return
        actor, reason = await self.actor_for(after.guild, disnake.AuditLogAction.role_update, after.id)
        await self.emit("🛠️ Изменена роль", f"**Роль:** {after.name} ({after.id})\n" + "\n".join(changes), actor=actor, reason=reason, event_type="role_update")

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        actor, reason = await self.actor_for(guild, disnake.AuditLogAction.ban, user.id)
        await self.emit("🔨 Участник заблокирован", f"**Участник:** {user} ({user.id})", actor=actor, reason=reason, color=disnake.Color.red(), event_type="member_ban")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        actor, reason = await self.actor_for(guild, disnake.AuditLogAction.unban, user.id)
        await self.emit("🔓 Блокировка снята", f"**Участник:** {user} ({user.id})", actor=actor, reason=reason, color=disnake.Color.green(), event_type="member_unban")

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        changes = []
        for attr, label in (
            ("name", "Название"),
            ("description", "Описание"),
            ("verification_level", "Уровень верификации"),
            ("explicit_content_filter", "Фильтр контента"),
            ("default_notifications", "Уведомления"),
        ):
            old, new = getattr(before, attr, None), getattr(after, attr, None)
            if old != new:
                changes.append(f"**{label}:** {old} → {new}")
        if not changes:
            return
        actor, reason = await self.actor_for(after, disnake.AuditLogAction.guild_update, after.id)
        await self.emit("🏠 Изменены настройки сервера", "\n".join(changes), actor=actor, reason=reason, event_type="guild_update")


def setup(bot: commands.InteractionBot):
    bot.add_cog(AuditLogs(bot))
