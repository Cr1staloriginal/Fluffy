import disnake
from disnake.ext import commands
from database import log_event

class VoiceLogs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        try:
            if before.channel == after.channel:
                return

            embed = disnake.Embed(title="🎤 Голосовой канал", timestamp=disnake.utils.utcnow())
            if before.channel is None:
                channel_name = getattr(after.channel, 'name', 'Unknown')
                embed.description = f"{member.mention} подключился к **{channel_name}**"
                embed.color = disnake.Color.green()
            elif after.channel is None:
                channel_name = getattr(before.channel, 'name', 'Unknown')
                embed.description = f"{member.mention} отключился от **{channel_name}**"
                embed.color = disnake.Color.red()
            else:
                before_name = getattr(before.channel, 'name', 'Unknown')
                after_name = getattr(after.channel, 'name', 'Unknown')
                embed.description = f"{member.mention} переместился из **{before_name}** → **{after_name}**"
                embed.color = disnake.Color.gold()

            try:
                await self.bot.log_dispatcher.send("voice", embed)
            except Exception as e:
                print(f"VoiceLogs: не удалось отправить embed в log_dispatcher: {e}")

            try:
                await log_event("voice_update", f"{member.id}|{(before.channel.id if before.channel else 'None')}->{(after.channel.id if after.channel else 'None')}")
            except Exception as e:
                print(f"VoiceLogs: не удалось записать событие в БД: {e}")
        except Exception as e:
            print(f"VoiceLogs: ошибка в обработчике on_voice_state_update: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(VoiceLogs(bot))
