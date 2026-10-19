"""Временные голосовые комнаты, создаваемые при входе в лобби."""
import logging
import os

import disnake
from disnake.ext import commands

logger = logging.getLogger(__name__)


def _read_id(name: str) -> int:
    try:
        return int(os.getenv(name, "0") or 0)
    except ValueError:
        logger.warning("Некорректный ID в переменной %s; временные комнаты отключены.", name)
        return 0


class TemporaryVoiceRooms(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.lobby_id = _read_id("TEMP_VOICE_LOBBY_ID")
        self.category_id = _read_id("TEMP_VOICE_CATEGORY_ID")
        self.prefix = os.getenv("TEMP_VOICE_PREFIX", "🔊・").strip() or "🔊・"

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: disnake.Member,
        before: disnake.VoiceState,
        after: disnake.VoiceState,
    ):
        if member.bot or member.guild is None:
            return

        # Create a personal room when the member joins the configured lobby.
        if after.channel and after.channel.id == self.lobby_id and before.channel != after.channel:
            lobby = after.channel
            category = member.guild.get_channel(self.category_id) if self.category_id else lobby.category
            try:
                room = await member.guild.create_voice_channel(
                    name=f"{self.prefix}{member.display_name}"[:100],
                    category=category,
                    overwrites=lobby.overwrites,
                    reason=f"Temporary voice room for {member} ({member.id})",
                )
                await member.move_to(room, reason="Move member to their temporary voice room")
            except (disnake.Forbidden, disnake.HTTPException):
                logger.exception("Не удалось создать временную комнату для участника %s", member.id)
                return

        # Delete only an empty temporary room. The lobby must never be deleted,
        # even if its name accidentally starts with the temporary-room prefix.
        old_channel = before.channel
        if (
            old_channel
            and old_channel.id != self.lobby_id
            and isinstance(old_channel, disnake.VoiceChannel)
            and old_channel.name.startswith(self.prefix)
            and (not self.category_id or old_channel.category_id == self.category_id)
            and not old_channel.members
        ):
            try:
                await old_channel.delete(reason="Empty temporary voice room")
            except (disnake.Forbidden, disnake.HTTPException):
                logger.exception("Не удалось удалить пустую временную комнату %s", old_channel.id)


def setup(bot: commands.InteractionBot):
    bot.add_cog(TemporaryVoiceRooms(bot))
