import disnake
from disnake.ext import commands
import time
import logging
from database import increment_messages, add_voice_minutes, set_voice_join_time, get_voice_join_time, add_cookies, ensure_user

logger = logging.getLogger(__name__)

class Activity(commands.Cog):
    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        logger.info("[Activity] Ког загружен")

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or message.guild is None:
            return
        try:
            await ensure_user(message.author.id, str(message.author), message.author.display_name)
            await increment_messages(message.author.id)
            logger.debug("[Activity] Учтено сообщение пользователя %s", message.author.id)
        except Exception as e:
            logger.error(f"[Activity] Ошибка при учёте сообщения: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if member.bot:
            return
        logger.debug("[Activity] Voice state changed for %s", member.id)

        if before.channel is None and after.channel is not None:
            await set_voice_join_time(member.id, time.time())
            logger.debug("[Activity] %s joined voice", member.id)
        elif before.channel is not None and after.channel is None:
            join_time = await get_voice_join_time(member.id)
            if join_time:
                seconds = int(time.time() - join_time)
                minutes = seconds // 60
                if minutes > 0:
                    await add_voice_minutes(member.id, minutes)
                    logger.debug("[Activity] %s voice minutes +%s", member.id, minutes)
                await set_voice_join_time(member.id, None)
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            join_time = await get_voice_join_time(member.id)
            if join_time:
                seconds = int(time.time() - join_time)
                minutes = seconds // 60
                if minutes > 0:
                    await add_voice_minutes(member.id, minutes)
                    logger.debug("[Activity] %s moved voice; minutes +%s", member.id, minutes)
            await set_voice_join_time(member.id, time.time())

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: disnake.RawReactionActionEvent):
        if self.bot.user and payload.user_id == self.bot.user.id:
            return
        if str(payload.emoji) == "🍪":
            logger.debug("[Activity] Cookie reaction from %s", payload.user_id)
            channel = self.bot.get_channel(payload.channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(payload.message_id)
                    if message.author and not message.author.bot:
                        await add_cookies(message.author.id)
                        logger.debug("[Activity] Cookie credited to %s", message.author.id)
                except Exception as e:
                    logger.error(f"[Activity] Ошибка при добавлении печеньки: {e}")

def setup(bot: commands.InteractionBot):
    bot.add_cog(Activity(bot))