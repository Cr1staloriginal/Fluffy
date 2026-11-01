"""Detailed voice-state audit logging."""
from __future__ import annotations

import logging

import disnake
from disnake.ext import commands

from database import log_event

logger = logging.getLogger(__name__)


class VoiceLogs(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot and member.id == getattr(self.bot.user, "id", None):
            return

        changes = []
        title = "🎙️ Изменение голосового состояния"
        color = disnake.Color.blurple()

        if before.channel != after.channel:
            if before.channel is None and after.channel is not None:
                title, color = "📥 Вход в голосовой канал", disnake.Color.green()
                changes.append(f"**Канал:** {after.channel.mention}")
            elif after.channel is None and before.channel is not None:
                title, color = "📤 Выход из голосового канала", disnake.Color.orange()
                changes.append(f"**Канал:** {before.channel.mention}")
            else:
                title, color = "🔀 Переход между голосовыми каналами", disnake.Color.gold()
                changes.append(f"**Откуда:** {before.channel.mention if before.channel else '—'}")
                changes.append(f"**Куда:** {after.channel.mention if after.channel else '—'}")

        flags = (
            (before.mute, after.mute, "🔇 Серверный микрофон"),
            (before.deaf, after.deaf, "🔕 Серверный звук"),
            (before.self_mute, after.self_mute, "🎙️ Собственный микрофон"),
            (before.self_deaf, after.self_deaf, "🔊 Собственный звук"),
            (before.self_stream, after.self_stream, "🖥️ Демонстрация экрана"),
            (before.self_video, after.self_video, "📷 Камера"),
            (before.suppress, after.suppress, "🎤 Статус выступления"),
        )
        for old, new, label in flags:
            if old != new:
                changes.append(f"**{label}:** {'включено' if new else 'выключено'}")

        if not changes:
            return

        embed = disnake.Embed(
            title=title,
            description="\n".join(changes),
            color=color,
            timestamp=disnake.utils.utcnow(),
        )
        embed.add_field(name="Участник", value=f"{member.mention} ({member.id})", inline=False)
        if before.channel and after.channel and before.channel == after.channel:
            embed.add_field(name="Канал", value=after.channel.mention, inline=False)
        embed.set_footer(text=f"Участник ID: {member.id}")
        await self.bot.log_dispatcher.send("voice", embed)
        try:
            await log_event("voice_state", f"{member.id}|{';'.join(changes)}")
        except Exception:
            logger.exception("Failed to persist voice event for %s", member.id)


def setup(bot: commands.InteractionBot):
    bot.add_cog(VoiceLogs(bot))
