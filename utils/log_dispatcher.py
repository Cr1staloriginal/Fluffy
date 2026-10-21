<<<<<<< HEAD
<<<<<<< HEAD
import disnake
import os
=======
import disnake
import os
import logging

logger = logging.getLogger(__name__)
>>>>>>> f42350e9a5a07c86594c560b74edb37ad7a73064

class LogDispatcher:
    def __init__(self, bot):
        self.bot = bot
        self.channels = {
            "members": int(os.getenv("LOG_CH_MEMBERS", 0)),
            "messages": int(os.getenv("LOG_CH_MESSAGES", 0)),
            "tickets": int(os.getenv("LOG_CH_TICKETS", 0)),
            "voice": int(os.getenv("LOG_CH_VOICE", 0)),
            "mod": int(os.getenv("LOG_CH_MOD", 0)),
        }
<<<<<<< HEAD
=======
        logger.info(f"LogDispatcher инициализирован: {self.channels}")
>>>>>>> f42350e9a5a07c86594c560b74edb37ad7a73064

    async def send(self, category: str, embed: disnake.Embed):
        channel_id = self.channels.get(category)
        if not channel_id:
<<<<<<< HEAD
            return
        channel = self.bot.get_channel(channel_id)
        if channel and channel.permissions_for(channel.guild.me).send_messages:
=======
import disnake
import os

class LogDispatcher:
    def __init__(self, bot):
        self.bot = bot
        self.channels = {
            "members": int(os.getenv("LOG_CH_MEMBERS", 0)),
            "messages": int(os.getenv("LOG_CH_MESSAGES", 0)),
            "tickets": int(os.getenv("LOG_CH_TICKETS", 0)),
            "voice": int(os.getenv("LOG_CH_VOICE", 0)),
            "mod": int(os.getenv("LOG_CH_MOD", 0)),
        }

    async def send(self, category: str, embed: disnake.Embed):
        channel_id = self.channels.get(category)
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel and channel.permissions_for(channel.guild.me).send_messages:
>>>>>>> a2cbbfd3c08ef828549733ad5e2b9ddb35acf3ad
            await channel.send(embed=embed)
=======
            logger.warning(f"Нет ID канала для категории '{category}'")
            return
        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Канал с ID {channel_id} не найден")
            return
        me = channel.guild.me
        if not channel.permissions_for(me).send_messages:
            logger.error(f"Нет прав на отправку в канал {channel.name}")
            return
        try:
            await channel.send(embed=embed)
            logger.debug(f"Лог отправлен в {channel.name}")
        except Exception as e:
            logger.exception(f"Ошибка при отправке лога: {e}")
>>>>>>> f42350e9a5a07c86594c560b74edb37ad7a73064
