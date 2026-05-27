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
            await channel.send(embed=embed)