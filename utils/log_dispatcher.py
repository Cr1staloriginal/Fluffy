"""Centralized delivery for Fluffy audit logs."""
import asyncio
import logging
import os

import disnake

logger = logging.getLogger(__name__)

CATEGORY_ENV = {
    "members": "LOG_CH_MEMBERS",
    "messages": "LOG_CH_MESSAGES",
    "tickets": "LOG_CH_TICKETS",
    "voice": "LOG_CH_VOICE",
    "mod": "LOG_CH_MOD",
}

CHANNEL_NAME_HINTS = {
    "members": ("участники",),
    "messages": ("сообщения",),
    "tickets": ("тикеты",),
    "voice": ("голосовые-каналы", "голосовые каналы", "голосовые"),
    "mod": ("модерация",),
}


class LogDispatcher:
    def __init__(self, bot):
        self.bot = bot
        self.channels = {key: int(os.getenv(env, "0") or 0) for key, env in CATEGORY_ENV.items()}
        self._locks = {}

    def set_channel(self, category: str, channel_id: int):
        if category not in CATEGORY_ENV:
            raise ValueError(f"Unknown log category: {category}")
        self.channels[category] = max(0, int(channel_id))

    async def _resolve(self, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
                logger.warning("Log channel %s is unavailable", channel_id, exc_info=True)
                return None
        if not hasattr(channel, "send") or not hasattr(channel, "permissions_for"):
            logger.error("Log target %s is not a messageable guild channel", channel_id)
            return None
        return channel

    async def send(self, category: str, embed: disnake.Embed = None, *, content: str = None, view=None) -> bool:
        if category not in CATEGORY_ENV:
            logger.error("Unknown log category %r", category)
            return False
        channel_id = self.channels.get(category, 0)
        if not channel_id:
            hints = CHANNEL_NAME_HINTS.get(category, ())
            matches = [
                channel
                for guild in self.bot.guilds
                for channel in guild.text_channels
                if any(hint in channel.name.casefold() for hint in hints)
            ]
            if len(matches) == 1:
                channel_id = matches[0].id
                self.channels[category] = channel_id
                logger.info("Auto-detected %s log channel: %s (%s)", category, matches[0].name, channel_id)
            elif len(matches) > 1:
                logger.warning("Multiple possible %s log channels found; set %s explicitly", category, CATEGORY_ENV[category])
                return False
            else:
                logger.debug("No log channel configured or auto-detected for %s", category)
                return False
        channel = await self._resolve(channel_id)
        if channel is None:
            return False

        guild = getattr(channel, "guild", None)
        me = getattr(guild, "me", None) if guild else None
        if me:
            perms = channel.permissions_for(me)
            if not perms.send_messages or (embed is not None and not perms.embed_links):
                logger.warning("Missing permissions in log channel %s", channel_id)
                return False

        lock = self._locks.setdefault(channel_id, asyncio.Lock())
        async with lock:
            for attempt in range(3):
                try:
                    await channel.send(content=content, embed=embed, view=view, allowed_mentions=disnake.AllowedMentions.none())
                    return True
                except disnake.Forbidden:
                    logger.error("Discord denied sending logs to %s", channel_id, exc_info=True)
                    return False
                except disnake.HTTPException as exc:
                    status = getattr(exc, "status", 0)
                    if attempt == 2 or status not in (429, 500, 502, 503, 504):
                        logger.exception("Could not send %s log to %s", category, channel_id)
                        return False
                    await asyncio.sleep(0.75 * (2 ** attempt))
                except (AttributeError, TypeError):
                    logger.exception("Invalid log payload or destination %s", channel_id)
                    return False
        return False
