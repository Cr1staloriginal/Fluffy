import disnake
from disnake.ext import commands
import time
import logging
from database import increment_messages, add_voice_minutes, set_voice_join_time, get_voice_join_time, add_cookies

logger = logging.getLogger(__name__)

class Activity(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        logger.info("[Activity] Ког загружен")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or message.guild is None:
            return
        logger.info(f"[Activity] on_message от {message.author} в {message.guild}")
        try:
            await increment_messages(message.author.id)
            logger.info(f"[Activity] Сообщение учтено для {message.author.id}")
        except Exception as e:
            logger.error(f"[Activity] Ошибка при учёте сообщения: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if member.bot:
            return
        logger.info(f"[Activity] on_voice_state_update для {member}")

        if before.channel is None and after.channel is not None:
            await set_voice_join_time(member.id, time.time())
            logger.info(f"[Activity] {member} зашёл в войс")
        elif before.channel is not None and after.channel is None:
            join_time = await get_voice_join_time(member.id)
            if join_time:
                seconds = int(time.time() - join_time)
                minutes = seconds // 60
                if minutes > 0:
                    await add_voice_minutes(member.id, minutes)
                    logger.info(f"[Activity] {member} пробыл в войсе {minutes} мин")
                await set_voice_join_time(member.id, None)
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            join_time = await get_voice_join_time(member.id)
            if join_time:
                seconds = int(time.time() - join_time)
                minutes = seconds // 60
                if minutes > 0:
                    await add_voice_minutes(member.id, minutes)
                    logger.info(f"[Activity] {member} переместился, учтено {minutes} мин")
            await set_voice_join_time(member.id, time.time())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) == "🍪":
            logger.info(f"[Activity] Печенька от {payload.user_id}")
            channel = self.bot.get_channel(payload.channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(payload.message_id)
                    if message.author and not message.author.bot:
                        await add_cookies(message.author.id)
                        logger.info(f"[Activity] Печенька добавлена {message.author.id}")
                except Exception as e:
                    logger.error(f"[Activity] Ошибка при добавлении печеньки: {e}")

def setup(bot: commands.InteractionBot):
    bot.add_cog(Activity(bot))