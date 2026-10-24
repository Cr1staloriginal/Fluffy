"""Safely dispatch embeds to configured Discord log channels."""
import logging
import os

import disnake

logger = logging.getLogger(__name__)


class LogDispatcher:
    def __init__(self, bot):
        self.bot = bot
        self.channels = {
            "members": int(os.getenv("LOG_CH_MEMBERS", "0") or 0),
            "messages": int(os.getenv("LOG_CH_MESSAGES", "0") or 0),
            "tickets": int(os.getenv("LOG_CH_TICKETS", "0") or 0),
            "voice": int(os.getenv("LOG_CH_VOICE", "0") or 0),
            "mod": int(os.getenv("LOG_CH_MOD", "0") or 0),
        }
        logger.info("LogDispatcher initialized")

    async def send(self, category: str, embed: disnake.Embed) -> None:
        channel_id = self.channels.get(category)
        if not channel_id:
            logger.debug("No log channel configured for category %r", category)
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                logger.warning("Log channel %s not found or inaccessible", channel_id)
                return

        guild = getattr(channel, "guild", None)
        me = getattr(guild, "me", None) if guild else None
        if me is not None and not channel.permissions_for(me).send_messages:
            logger.warning("No permission to send logs in channel %s", channel_id)
            return

        try:
            await channel.send(embed=embed)
        except (disnake.Forbidden, disnake.HTTPException, AttributeError):
            logger.exception("Could not send log embed to channel %s", channel_id)
